# wsi/explorer.py
import base64
import struct
from pprint import pprint

from app.utils.wsi.io import S3RangeReader

from .ifd_parser import IFDParser


class WSITagExplorer:
    """
    High-level explorer:
    - Print summary
    - Decode tags
    """

    WSI_TAGS = {
        256: "ImageWidth",
        257: "ImageLength",
        322: "TileWidth",
        323: "TileLength",
        324: "TileOffsets",
        325: "TileByteCounts",
        330: "SubIFDs",
        347: "JPEGTables",
        42112: "Aperio.AppMag",
    }

    TIFF_TYPES = {
        1: ("B", 1),
        2: ("c", 1),
        3: ("H", 2),
        4: ("I", 4),
        5: ("II", 8),
        7: ("B", 1),
        9: ("i", 4),
        10: ("ii", 8),
        12: ("d", 8),
        16: ("Q", 8),
    }

    def __init__(self, reader: S3RangeReader) -> None:
        parser = IFDParser(reader)
        self.ifds = parser.parse()
        self.header_offset = parser.header_offset
        self.endian = parser.endian
        self.offset_size = parser.offset_size

        self.reader = reader

    def _unpack(self, fmt, data):
        return struct.unpack(self.endian + fmt, data)

    def decode_ifd(self, i):
        """
        Decode whole tag in IFD
        """
        tags = self.ifds[i]["tags"]
        decoded = {}

        for tag, meta in tags.items():
            name = self.WSI_TAGS.get(tag, f"Tag_{tag}")
            t, c, v = meta["type"], meta["count"], meta["value"]
            decoded[name] = {
                "type": t,
                "count": c,
                "value": self._decode_value(t, c, v)
            }
        return decoded

    def _decode_value(self, typ, count, val):
        if typ not in self.TIFF_TYPES:
            return val

        code, unit = self.TIFF_TYPES[typ]
        total = unit * count
        inline_limit = 8

        if total <= inline_limit:
            raw = val.to_bytes(inline_limit, byteorder="little")[:total]
        else:
            raw = self.reader.read(self.header_offset + val, total)

        if code == "c":
            return raw.rstrip(b"\x00").decode(errors="ignore")

        if code == "B":
            return list(raw) if count > 1 else raw[0]

        if code == "H":
            tmp = self._unpack(f"{count}H", raw)
            return list(tmp) if count > 1 else tmp[0]

        if code == "I":
            tmp = self._unpack(f"{count}I", raw)
            return list(tmp) if count > 1 else tmp[0]

        if code == "Q":
            tmp = self._unpack(f"{count}Q", raw)
            return list(tmp) if count > 1 else tmp[0]

        if code in ("II", "ii"):
            out = []
            for j in range(count):
                num = self._unpack("I", raw[j*8:j*8+4])[0]
                den = self._unpack("I", raw[j*8+4:j*8+8])[0]
                out.append(num/den if den else 0)
            return out if count > 1 else out[0]

        return val

    def summary(self):
        rows = []
        for i, ifd in enumerate(self.ifds):
            t = ifd["tags"]

            w = t.get(256, {}).get("value")
            h = t.get(257, {}).get("value")
            tw = t.get(322, {}).get("value")
            th = t.get(323, {}).get("value")
            has_tiles = 324 in t and 325 in t

            rows.append({
                "ifd": i,
                "width": w,
                "height": h,
                "tileWidth": tw,
                "tileLength": th,
                "subIFDs": ifd["sub_ifds"],
                "nextIFD": ifd["next_ifd"],
                "iiif_ready": bool(w and h and has_tiles)
            })

        return rows

    def print_summary(self):
        print("==== WSI IFD SUMMARY ====")
        for r in self.summary():
            print(r)

    # ====================================================
    #  NEW UTILS FOR TILE EXTRACTION
    # ====================================================

    def get_raw_range(self, offset: int, size: int) -> bytes:
        """
        Wrapper untuk membaca byte range dari WSI via reader.
        offset pada TIFF = header_offset + value
        """
        return self.reader.read(self.header_offset + offset, size)

    def decode_array_from_tag(self, tag):
        """
        Decode array TileOffsets / TileByteCounts sesuai TIFF type.
        """
        typ = tag["type"]
        count = tag["count"]
        val = tag["value"]

        # TIFF type sizes (compatibel dengan _decode_value)
        type_unit = self.TIFF_TYPES.get(typ, (None, None))[1]
        if not type_unit:
            raise ValueError(f"Unsupported TIFF type: {typ}")

        total = count * type_unit

        # Baca raw bytes dari file (range S3)
        raw = self.get_raw_range(val, total)

        # tentukan format decoding
        code = self.TIFF_TYPES[typ][0]  # contoh: "I" / "Q"
        fmt = self.endian + code * count

        arr = struct.unpack(fmt, raw)
        return list(arr)

    def extract_tile_level(self, ifd):
        """
        Extract satu level tile dari satu IFD.
        Return dict: { width, height, tilesX, tilesY, tiles: [...] }
        """

        tags = ifd["tags"]

        width = tags[256]["value"]
        height = tags[257]["value"]
        tile_w = tags[322]["value"]
        tile_h = tags[323]["value"]

        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h
        expected = tiles_x * tiles_y

        # --- offsets array ---
        off_tag = tags[324]
        offsets = self.decode_array_from_tag(off_tag)

        # --- bytecounts array ---
        bc_tag = tags[325]
        bytecounts = self.decode_array_from_tag(bc_tag)

        tiles = []
        limit = min(len(offsets), len(bytecounts), expected)

        for idx in range(limit):
            x = idx % tiles_x
            y = idx // tiles_x
            tiles.append({
                "x": x,
                "y": y,
                "offset": int(offsets[idx]),
                "length": int(bytecounts[idx]),
            })

        return {
            "width": int(width),
            "height": int(height),
            "tileWidth": int(tile_w),
            "tileHeight": int(tile_h),
            "tilesX": int(tiles_x),
            "tilesY": int(tiles_y),
            "tiles": tiles,
        }
    
    def build_ifds_json(self):
        """
        Hasilkan metadata final IFDS JSON untuk IIIF tile.
        Hanya IFD yang punya TileOffsets dan TileByteCounts.
        """

        def is_tiled(ifd):
            t = ifd["tags"]
            return (
                256 in t and
                257 in t and
                322 in t and
                323 in t and
                324 in t and t[324]["count"] > 0 and
                325 in t and t[325]["count"] > 0
            )

        # 1. filter IFD tiled
        usable = [ifd for ifd in self.ifds if is_tiled(ifd)]

        if not usable:
            return {
                "jpegtables": None,
                "levels": []
            }

        # 2. urutkan berdasarkan resolusi terbesar
        usable_sorted = sorted(
            usable,
            key=lambda x: x["tags"][256]["value"],
            reverse=True
        )

        # 3. Fetch base resolution to count downsample
        base_width = usable_sorted[0]["tags"][256]["value"]

        # 4. Fetch JPEG Tables (with tag code 347)
        jpt = None
        jpeg_tag = usable_sorted[0]["tags"].get(347)

        if jpeg_tag:
            raw = self._decode_value(jpeg_tag["type"], jpeg_tag["count"], jpeg_tag["value"])

            if isinstance(raw, list):
                raw = bytes(raw)

            jpt = base64.b64encode(raw).decode("utf-8")

        # 5. Build all levels
        levels = []
        for level_idx, ifd in enumerate(usable_sorted):
            meta = self.extract_tile_level(ifd)

            offsets = [t["offset"] for t in meta["tiles"]]
            lengths = [t["length"] for t in meta["tiles"]]

            # rename & normalize schema
            lv = {
                "level": level_idx,
                "width": meta["width"],
                "height": meta["height"],
                "tile_width": meta["tileWidth"],
                "tile_height": meta["tileHeight"],
                "downsample": round(base_width / meta["width"], 4),
                "tiles": [
                    {"offset": o, "length": l}
                    for o, l in zip(offsets, lengths)
                ]
            }

            levels.append(lv)

        return {
            "jpegtables": jpt,
            "levels": levels
        }
