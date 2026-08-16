"""Platform-specific process handling, isolated to this one module.

Long render sweeps spawn many engine processes, and on Windows that needs job
objects (so children die with the parent) and priority classes (so a sweep does
not make the desktop unusable). Those calls live here and nowhere else, so the
rest of the package stays plain cross-platform Python.

**Both functions return what actually happened, never a bare success.** A cleanup
guarantee that could not be installed must not be reported as installed: a release
pass that thinks its engines will be reaped, and is wrong, leaves a full-resolution
render running after the run that owned it is gone. On anything but Windows the
answer is "unavailable", which is honest — a POSIX child is reaped with its process
group and nothing here has to arrange it.
"""

from __future__ import annotations

import sys

IS_WINDOWS = sys.platform == "win32"

#: Held for the process's whole life on purpose: closing the handle terminates
#: the job, which is to say this process. It is released by process exit, which
#: is the event the job is armed for.
_JOB = None


def set_background_priority() -> str:
    """Drop this process to a below-normal priority class. Returns what happened."""
    if not IS_WINDOWS:
        return "unavailable (posix; use nice(1) if a sweep needs to yield)"
    import ctypes
    from ctypes import wintypes

    below_normal = 0x00004000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # The argument types are not optional. `GetCurrentProcess` returns the
    # pseudo-handle `(HANDLE)-1`, and a default-typed ctypes call truncates it to
    # a C int — which arrives at `SetPriorityClass` as an invalid handle and
    # fails with error 6. It fails *quietly*, because the return value is the
    # only thing that says so.
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.SetPriorityClass.restype = wintypes.BOOL
    if not kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), below_normal):
        return f"FAILED (SetPriorityClass err {ctypes.get_last_error()})"
    return "below-normal"


def bind_children_to_parent() -> str:
    """Put this process in a job object its children inherit, killed when it closes.

    Every engine process a worker starts inherits the job, so a worker killed by
    anything at all — a reaper, an out-of-memory kill, a pool teardown — takes its
    engine with it. `subprocess.run` already kills its child when the call raises;
    this covers the case where there is no exception because the process simply
    stopped existing.
    """
    global _JOB
    if not IS_WINDOWS:
        return "unavailable (posix; children are reaped by the process group)"
    if _JOB is not None:
        return "job:kill-on-close (already installed)"

    import ctypes
    from ctypes import wintypes

    class _Counters(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class _BasicLimit(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class _ExtendedLimit(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimit),
            ("IoInfo", _Counters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kill_on_close = 0x00002000
    extended_limit_information = 9

    # The argument types are not optional here: `GetCurrentProcess` returns the
    # pseudo-handle `(HANDLE)-1`, and a default-typed ctypes call truncates it to
    # a C int and raises.
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return f"FAILED (CreateJobObject err {ctypes.get_last_error()})"
    limits = _ExtendedLimit()
    limits.BasicLimitInformation.LimitFlags = kill_on_close
    if not kernel32.SetInformationJobObject(
        job, extended_limit_information, ctypes.byref(limits), ctypes.sizeof(limits)
    ):
        return f"FAILED (SetInformationJobObject err {ctypes.get_last_error()})"
    if not kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess()):
        return f"FAILED (AssignProcessToJobObject err {ctypes.get_last_error()})"
    _JOB = job
    return "job:kill-on-close"


__all__ = ["IS_WINDOWS", "bind_children_to_parent", "set_background_priority"]
