import struct
from math import ceil 
from typing import List, Dict, Any, Callable, Optional

from app.utils.wsi.io import S3RangeReader


# type -> size (byte)
TIFF_TYPE_SIZES = {
    1: 1,   # BYTE
    2: 1,   # ASCII
    3: 2,   # SHORT
    4: 4,   # LONG
    5: 8,   # RATIONAL
    12: 8,  # DOUBLE
    16: 8,  # LONG8
    17: 8,  # SLONG8
    18: 8,  # IFD8
}

# type -> format struct to 1 element
TIFF_TYPE_FMT = {
    1: "B",
    2: "B",   # treat ASCII as bytes
    3: "H",
    4: "I",
    5: "II",  # (num,den)RATIONAL → biasanya jarang dipakai di sini
    12: "d",
    16: "Q",  # LONG8
    17: "q",
    18: "Q",
}

def decode_array_from_tag(
    tag: Dict[str, Any],
    read_raw: Callable[[int, int], bytes],
    byteorder: str,
) -> List[int]:
    """
    tag: dict single tag: {'type': 16, 'count': 41209, 'value': 889123123}
    read_raw(offset, size): this function to read raw bytes of file (S3 range reader)
    byteorder: 'little' or 'big'
    """

    tiff_type = tag["type"]
    count = tag["count"]
    offset = tag["value"]

    if tiff_type not in TIFF_TYPE_SIZES:
        raise ValueError(f"Unsupported TIFF type: {tiff_type}")

    item_size = TIFF_TYPE_SIZES(tiff_type)
    total_size = item_size * count

    raw = read_raw(offset, total_size)

    # RATIONAL (type=5) have two UINT32 per value 
    if tiff_type == 5:
        fmt = ("<" if byteorder == "little" else ">") + "II" * count
        unpacked = struct.unpack(fmt, raw)

        return list(unpacked)

    fmt_char = TIFF_TYPE_FMT(tiff_type)
    
    fmt = ("<" if byteorder == "little" else ">") + fmt_char * count
    values = struct.unpack(fmt, raw)
    return list(values)


def make_s3_read_raw(reader: S3RangeReader):
    def _read_raw(offset: int, size: int) -> bytes:
        return reader.read(offset=offset, length=size)

    return _read_raw


def extract_tile_level(
    ifd: Dict[str, Any],
    read_raw: Callable[[int, int], bytes],
    byteorder: str,
) -> Dict[str, Any]:
    """
    Mengubah satu IFD tiled menjadi struktur level tiles lengkap.
    ifd: 1 entry dari explorer.ifds (punya field 'tags')
    """

    tags = ifd["tags"]

    # --- geometry dasar ---
    width = tags[256]["value"]     # ImageWidth
    height = tags[257]["value"]    # ImageLength

    tile_w = tags[322]["value"]    # TileWidth
    tile_h = tags[323]["value"]    # TileLength

    tiles_x = ceil(width / tile_w)
    tiles_y = ceil(height / tile_h)
    num_tiles_expected = tiles_x * tiles_y

    # --- baca array offsets & bytecounts ---
    off_tag = tags[324]  # TileOffsets
    bc_tag = tags[325]   # TileByteCounts

    offsets = decode_array_from_tag(off_tag, read_raw, byteorder)
    bytecounts = decode_array_from_tag(bc_tag, read_raw, byteorder)

    # sanity check (boleh kamu ubah jadi warning/log)
    if len(offsets) < num_tiles_expected or len(bytecounts) < num_tiles_expected:
        # beberapa vendor pakai tile yang tidak lengkap, di sini kita ambil min
        num_tiles = min(len(offsets), len(bytecounts), num_tiles_expected)
    else:
        num_tiles = num_tiles_expected

    tiles = []
    for idx in range(num_tiles):
        y = idx // tiles_x
        x = idx % tiles_x
        tiles.append(
            {
                "x": x,
                "y": y,
                "offset": int(offsets[idx]),
                "length": int(bytecounts[idx]),
            }
        )

    return {
        "width": int(width),
        "height": int(height),
        "tileWidth": int(tile_w),
        "tileHeight": int(tile_h),
        "tilesX": int(tiles_x),
        "tilesY": int(tiles_y),
        "tiles": tiles,
    }


def is_tiled(ifd: Dict[str, Any]) -> bool:
    tags = ifd["tags"]
    return (
        256 in tags and 257 in tags and
        322 in tags and 323 in tags and
        324 in tags and tags[324]["count"] > 0 and
        325 in tags and tags[325]["count"] > 0
    )


def build_ifds_json(
    ifds: List[Dict[str, Any]],
    read_raw: Callable[[int, int], bytes],
    byteorder: str,
) -> Dict[str, Any]:
    """
    Menghasilkan struktur final untuk disimpan sebagai ifds.json
    """

    # 1. filter hanya IFD yang benar-benar tiled
    tiled_ifds = [ifd for ifd in ifds if is_tiled(ifd)]

    # 2. urutkan descending berdasarkan width (level 0 = resolusi terbesar)
    tiled_ifds_sorted = sorted(
        tiled_ifds,
        key=lambda x: x["tags"][256]["value"],
        reverse=True,
    )

    levels = []
    for level_idx, ifd in enumerate(tiled_ifds_sorted):
        level_meta = extract_tile_level(ifd, read_raw, byteorder)
        level_meta["level"] = level_idx
        level_meta["ifd_offset"] = ifd["offset"]  # opsional, untuk debug
        levels.append(level_meta)

    return {"levels": levels}

