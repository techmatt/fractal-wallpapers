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
"""

from __future__ import annotations

#: The timm identifier of the frozen encoder. The whole of this project's
#: dependence on it, spelled once: a store's manifest records this string, and a
#: store whose manifest names a different one is a store of vectors nothing can
#: be compared against.
VARIANT = "vit_small_patch14_dinov2.lvd142m"

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


def build(variant: str = VARIANT):
    """The frozen encoder, with its classifier head removed.

    `num_classes=0` is what makes `forward` return the pooled feature rather than
    logits, so the thing that comes out is the vector and not an opinion.
    """
    import timm

    model = timm.create_model(variant, pretrained=True, num_classes=0, dynamic_img_size=True)
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
    "BATCH",
    "DIM",
    "PATCH",
    "PRECISION",
    "VARIANT",
    "EmbeddingError",
    "build",
    "data_config",
    "describe",
    "encode",
]
