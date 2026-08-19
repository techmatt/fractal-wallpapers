Which colors are available: palette assets, palette generation, and palette curation.

`library_import` brings a map across from the source project's pooled library and
writes it here as stops. `space` measures how near two maps are — the gradient as
the renderer really spends it, sampled and converted to Oklab — which is what lets
the palette head's corpus build candidate sets that are near-ties by construction
rather than by luck.

`space` also owns the repository's single copy of the sRGB↔Oklab arithmetic, so the
autolevel operator and the palette descriptor cannot come to disagree about what a
colour is. Its sRGB→linear step is a 256-entry table rather than the transfer curve's
`**2.4`, taken whenever the caller hands over `uint8` — the whole of sRGB8 and
nothing else, so the table is that expression's own answer bit for bit. Hand it a
picture as it was decoded and a tone measurement runs about 30% faster; hand it
fractional values, as a gradient sampled between its stops gives, and it does the
arithmetic.
