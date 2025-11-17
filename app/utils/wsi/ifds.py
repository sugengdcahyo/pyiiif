# wsi/ifds.py

class IFDsBuilder:
    """
    Generate ifds.json untuk IIIF tile server dengan numeric TIFF tags.
    """

    TAG_IMAGE_WIDTH = 256
    TAG_IMAGE_LENGTH = 257
    TAG_TILE_WIDTH = 322
    TAG_TILE_LENGTH = 323
    TAG_TILE_OFFSETS = 324
    TAG_TILE_BYTECOUNTS = 325

    def __init__(self, explorer):
        self.explorer = explorer

    def get_tag_int(self, value):
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, list):
            for v in value:
                if isinstance(v, int):
                    return v
        if isinstance(value, dict):
            for key in ("value", "value_or_offset"):
                if key in value and isinstance(value[key], int):
                    return value[key]
        raise TypeError(f"Cannot convert TIFF tag to int: {value}")

    def build(self):
        ifds = self.explorer.ifds
        pyramid = []

        for idx, ifd in enumerate(ifds):
            tags = ifd["tags"]

            # width/height harus ada
            w = self.get_tag_int(tags.get(self.TAG_IMAGE_WIDTH))
            h = self.get_tag_int(tags.get(self.TAG_IMAGE_LENGTH))

            if not w or not h:
                continue

            # hanya masuk pyramid bila ada TileOffsets & TileByteCounts
            if self.TAG_TILE_OFFSETS not in tags:
                # skip label/macro/thumbnail
                continue

            tileOffsets = tags[self.TAG_TILE_OFFSETS]
            tileByteCounts = tags.get(self.TAG_TILE_BYTECOUNTS, [])

            # normalisasi list
            if not isinstance(tileOffsets, list):
                tileOffsets = [tileOffsets]
            if tileByteCounts and not isinstance(tileByteCounts, list):
                tileByteCounts = [tileByteCounts]

            tileWidth = self.get_tag_int(tags.get(self.TAG_TILE_WIDTH))
            tileHeight = self.get_tag_int(tags.get(self.TAG_TILE_LENGTH))

            pyramid.append({
                "level": None,     # assign setelah sorting
                "ifd": idx,
                "width": int(w),
                "height": int(h),
                "tileWidth": int(tileWidth) if tileWidth else None,
                "tileHeight": int(tileHeight) if tileHeight else None,
                "tileOffsets": tileOffsets,
                "tileByteCounts": tileByteCounts
            })

        # Sort dari resolusi tertinggi ke rendah
        pyramid.sort(key=lambda x: x["width"] * x["height"], reverse=True)

        # assign level ID IIIF (0 = highest)
        for i, lvl in enumerate(pyramid):
            lvl["level"] = i

        return {"levels": pyramid}

