"use strict";
// What a labeling page's export is called, and where it goes. One file, because
// every sheet this project ever serves has to agree about both.
//
// The name is the HEAD the sheet was cut for — `smooth_render.json`, never
// `labels.json`. Two sheets are open in two tabs during a session, and a generic
// name is two downloads where the second silently replaces the first.
//
// The destination is the rig's own save endpoint, `PUT /labels/<head>.json`,
// which writes the drop directly and means a session never depends on somebody
// remembering to move a file out of the browser's download directory. A page
// served by a dumb static server gets 404 or 501 back, or nothing at all, and
// falls back to the correctly-named download — so the fallback is a slower path
// to the same file rather than a different outcome.
(function (global) {
  function exportName(head) {
    if (!head) {
      throw new Error(
        "this sheet names no head, so its export has no name; a sheet is cut for a judge"
      );
    }
    return head + ".json";
  }

  function download(head, payload) {
    const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
    const anchor = document.createElement("a");
    anchor.href = URL.createObjectURL(blob);
    anchor.download = exportName(head);
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }

  // Returns {saved, path, note}. `saved` is true only when the rig wrote the drop
  // itself; every other outcome has already downloaded the file under the same
  // name, so the labeler is never left with nowhere their work went.
  async function save(head, payload) {
    const name = exportName(head);
    let answer = null;
    try {
      answer = await fetch("/labels/" + name, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (unreachable) {
      answer = null;
    }
    if (answer && answer.ok) {
      const written = await answer.json();
      return { saved: true, path: written.path, note: written.units + " units saved" };
    }
    download(head, payload);
    if (answer && answer.status === 409) {
      // The drop already holds units this payload does not. That is the one
      // shape a save is refused in, because it is the only one that loses a
      // verdict somebody cast.
      const refusal = await answer.text();
      return { saved: false, path: name, note: "downloaded instead — " + refusal.trim() };
    }
    return { saved: false, path: name, note: "downloaded — this server takes no save endpoint" };
  }

  global.labelExport = { exportName, download, save };
})(window);
