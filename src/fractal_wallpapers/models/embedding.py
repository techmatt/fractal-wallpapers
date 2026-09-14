"""One vector per picture, from a pretrained encoder that is never trained here.

Every other model in this directory is a **judge**: it was trained on this
repository's own labels, it is shipped as a checkpoint with a sha, and a cut on
its scale is meaningless the moment it is retrained. This is not one. It is a
frozen self-supervised encoder read for the geometry it already sees, and the
only question asked of it is *are these two pictures alike*. Nothing about a
wallpaper's quality is in a vector from here, and nothing here reads a label.

## Which encoder, and why the smallest one

**DINOv2 ViT-S/14** (`vit_small_patch14_dinov2.lvd142m`), 384 dimensions. DINOv2
is self-supervised, so its features are about structure rather than about the
thousand ImageNet nouns none of which is a fractal; the small variant is the one
whose whole population fits in a leg of minutes rather than hours on the GPU
this project has, and the ranking task it is put to — nearest neighbours inside
one narrow visual domain — is the task where a bigger backbone buys least.

The patch size is 14, which is why [`fractal_wallpapers.curation.neutral`] draws
448x252: the frame tiles into whole patches and nothing is resized, cropped or
padded on the way in. `dynamic_img_size` is what lets the position embedding
follow a frame that is not the 518x518 square it was pretrained at.

## The vector is L2-normalized before it is stored

Cosine is the comparison, so the norm is not information — and storing unit
vectors means a nearest-neighbour read is one matrix multiply rather than a
multiply and a division per row. It also makes `float16` safe: the components of
a unit vector are all within a hair of zero, which is where half-precision has
its digits.

## It is fetched from Hugging Face, it is pinned, and the first read needs network

This is the one **third-party** weight in the project and the only
`pretrained=True` in the tree. Everything under `models/weights.json` is
this repository's own: trained here, hashed, and served from a GitHub release.
This one is not re-hosted and should not be — it is somebody else's artifact and
the honest thing is to fetch it from where it lives and say exactly which
revision.

Which is what [`REVISION`] and [`SHA256`] are for, and what they close. Until
2026-09-14 this said `pretrained=True` against `timm/` on the hub's `main`, with
**no revision, no checksum and no size**: whatever that repository held on the day
a machine first ran `curate embed` became this project's embedding basis, an
84 MB download nothing had mentioned, and a silently different one later would
have produced a store of vectors that cannot be compared with the ones already in
it. `timm>=1.0.27` is a floor on the library, not a pin on the weights.

The revision rides in through timm's own `hf_hub_id@revision` spelling
([`hub_id`]), so the pin is the hub's commit and not a copy of the file. `curate
embed` needs the network the first time on any machine and nothing after —
`~/.cache/huggingface` holds it — and [`verify`] is how a machine checks that what
it cached is the artifact this project was measured on.
"""

from __future__ import annotations

#: The timm identifier of the frozen encoder. The whole of this project's
#: dependence on it, spelled once: a store's manifest records this string, and a
#: store whose manifest names a different one is a store of vectors nothing can
#: be compared against.
VARIANT = "vit_small_patch14_dinov2.lvd142m"

#: Where the weights actually come from, and **which commit of it**.
#:
#: The repository is the one timm resolves `VARIANT` to; the revision is the pin,
#: and it is the commit this project's every embedding store was filled from.
#: timm takes it in the `id@revision` spelling its own `hf_split` reads, so this
#: is the hub's pin and not a copy of the file.
HF_REPO = "timm/vit_small_patch14_dinov2.lvd142m"
REVISION = "4610ca143709d58a633b6397a74412c2c3842454"

#: The weight file at that revision, and its sha256 — **84.2 MB, downloaded on
#: first use**. The size is here because it is the part nobody was told: a fresh
#: `curate embed` reached out to the internet for eighty-four megabytes with no
#: document in the tree mentioning it. The hash is here because a pin on a
#: mutable hub is a claim somebody should be able to check, and [`verify`] is
#: how.
ASSET = "model.safetensors"
SHA256 = "04d27f3400d059fc0cfd7d17dd1909a75bf3ea8fb3eeb48b97cb99e57ee20081"
BYTES = 88240510

#: The width of one vector, and the patch size the frame has to be a multiple of.
DIM = 384
PATCH = 14

#: What a stored vector is written as. Half-precision because these are unit
#: vectors of a similarity measure, not quantities: the error it introduces is
#: about 1e-3 of a component, against neighbour distances that differ in the
#: first decimal.
PRECISION = "float16"

#: How many pictures go to the encoder at once. Sized for the 8 GB card this was
#: measured on at 448x252; it is a throughput knob and nothing downstream reads
#: it.
BATCH = 32


class EmbeddingError(RuntimeError):
    """The encoder cannot be built, or cannot be read."""


def hub_id(revision: str | None = REVISION) -> str:
    """`repo@revision`, which is how timm takes a pin.

    `timm.models._hub.hf_split` cuts an id on `@` and passes the tail to the hub
    as `revision`, so this is the whole mechanism — no vendored file, no second
    download path, and the pin is a hub commit rather than a copy of somebody
    else's artifact. `None` asks for whatever `main` holds, which is what this
    did until 2026-09-14 and is kept only so a caller can deliberately measure
    against a newer revision.
    """
    return HF_REPO if not revision else f"{HF_REPO}@{revision}"


def cached_weights(revision: str | None = REVISION):
    """The pinned weight file in this machine's hub cache, or `None` if unfetched.

    Read off the cache layout rather than by asking the hub, so it costs no
    network and answers on a machine that is offline — which is the machine that
    needs the answer.
    """
    import os
    from pathlib import Path

    home = os.environ.get("HUGGINGFACE_HUB_CACHE") or os.environ.get("HF_HOME")
    root = Path(home) if home else Path.home() / ".cache" / "huggingface"
    hub = root / "hub" if (root / "hub").is_dir() else root
    named = hub / ("models--" + HF_REPO.replace("/", "--")) / "snapshots"
    if not named.is_dir():
        return None
    for snapshot in sorted(named.iterdir()):
        if revision and snapshot.name != revision:
            continue
        held = snapshot / ASSET
        if held.is_file():
            return held
    return None


def verify(revision: str | None = REVISION) -> dict:
    """Whether the cached weights are the artifact this project was measured on.

    Stdlib, no network and no timm: it hashes the file the cache already holds.
    A machine that has never run `curate embed` reads `fetched: False`, which is a
    state and not a fault — the download happens on first use.
    """
    import hashlib

    held = cached_weights(revision)
    if held is None:
        return {
            "variant": VARIANT,
            "hub": hub_id(revision),
            "fetched": False,
            "says": (
                f"not in this machine's hub cache. `curate embed` downloads it on first use: "
                f"{BYTES:,} bytes over the network, once."
            ),
        }
    digest = hashlib.sha256()
    with held.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    return {
        "variant": VARIANT,
        "hub": hub_id(revision),
        "fetched": True,
        "path": str(held),
        "bytes": held.stat().st_size,
        "sha256": actual,
        "expected": SHA256,
        "verified": actual == SHA256,
    }


def build(variant: str = VARIANT, revision: str | None = REVISION):
    """The frozen encoder, with its classifier head removed.

    `num_classes=0` is what makes `forward` return the pooled feature rather than
    logits, so the thing that comes out is the vector and not an opinion.

    **Pinned to a hub revision**, through `pretrained_cfg_overlay`, which is the
    supported way to say which commit of a hub repository timm should resolve.
    Without it this asked for `main` and got whatever was there on the day — and a
    store of vectors filled against one revision cannot be compared with one
    filled against another, which is the only thing these vectors are for.

    ⚠ **This is where the network is needed.** First call on a machine downloads
    [`BYTES`] bytes into the hub cache; every call after it is local.
    """
    import timm

    model = timm.create_model(
        variant,
        pretrained=True,
        num_classes=0,
        dynamic_img_size=True,
        pretrained_cfg_overlay={"hf_hub_id": hub_id(revision)},
    )
    return model.eval()


def data_config(model) -> dict:
    """The normalization the encoder was pretrained under, read off the checkpoint.

    Read rather than typed, for the reason `head.data_config` gives: a backbone
    normalized with the wrong constants still produces vectors, slightly worse
    ones, and says nothing about it.
    """
    import timm

    resolved = timm.data.resolve_model_data_config(model)
    return {
        "mean": tuple(float(value) for value in resolved["mean"]),
        "std": tuple(float(value) for value in resolved["std"]),
    }


def describe(model, variant: str = VARIANT, device: str = "cpu") -> dict:
    """What a store's manifest records about the encoder that filled it."""
    return {
        "variant": variant,
        # Which COMMIT of the hub repository, beside the variant name. A manifest
        # naming only the variant cannot say whether two stores are comparable:
        # the name is stable across every revision the hub ever held.
        "hub": hub_id(),
        "weights_sha256": SHA256,
        "dim": int(getattr(model, "num_features", DIM)),
        "patch": PATCH,
        "precision": PRECISION,
        "normalized": "l2",
        "device": device,
        **data_config(model),
    }


def encode(model, paths, device: str, mean, std, batch: int = BATCH):
    """Every picture at `paths` as one unit vector, in the order they were given.

    The pictures are already at the encoder's input size, so there is no resize
    here and no interpolation choice to get wrong: a JPEG is decoded, scaled to
    `[0, 1]`, normalized, and handed over. Anything that is not already the right
    shape is a bug upstream and is refused rather than silently squeezed.
    """
    import numpy
    import torch
    from PIL import Image

    paths = list(paths)
    out = numpy.zeros((len(paths), int(getattr(model, "num_features", DIM))), dtype=numpy.float32)
    mean_t = torch.tensor(mean, dtype=torch.float32).view(1, 3, 1, 1).to(device)
    std_t = torch.tensor(std, dtype=torch.float32).view(1, 3, 1, 1).to(device)
    with torch.no_grad():
        for start in range(0, len(paths), batch):
            chunk = paths[start : start + batch]
            frames = []
            for path in chunk:
                with Image.open(path) as opened:
                    opened.load()
                    frame = numpy.asarray(opened.convert("RGB"), dtype=numpy.uint8)
                if frame.shape[0] % PATCH or frame.shape[1] % PATCH:
                    raise EmbeddingError(
                        f"{path} is {frame.shape[1]}x{frame.shape[0]}, which is not a whole "
                        f"number of {PATCH}-pixel patches on both axes."
                    )
                frames.append(frame)
            stacked = torch.from_numpy(numpy.stack(frames)).permute(0, 3, 1, 2)
            pictures = stacked.to(device, non_blocking=True).float().div_(255.0)
            pictures = (pictures - mean_t) / std_t
            vectors = model(pictures).float()
            vectors = vectors / vectors.norm(dim=1, keepdim=True).clamp_min(1e-12)
            out[start : start + len(chunk)] = vectors.cpu().numpy()
    return out


__all__ = [
    "ASSET",
    "BATCH",
    "BYTES",
    "DIM",
    "HF_REPO",
    "PATCH",
    "PRECISION",
    "REVISION",
    "SHA256",
    "VARIANT",
    "EmbeddingError",
    "build",
    "cached_weights",
    "data_config",
    "describe",
    "encode",
    "hub_id",
    "verify",
]
