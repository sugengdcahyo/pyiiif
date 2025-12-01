import boto3
import json
import io
import base64
import os
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageFile
from flask import abort
from botocore.config import Config
from math import ceil, floor
from io import BytesIO

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


# ----------------------------------------------------
# S3 CLIENT SINGLETON
# ----------------------------------------------------
# _s3 = None
# def s3_client():
#     global _s3
#     if _s3 is None:
#         s3cfg = Config(
#             retries={"max_attempts": 3, "mode": "standard"},
#             connect_timeout=2,
#             read_timeout=5,
#         )
#         _s3 = boto3.client(
#             "s3",
#             aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
#             aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
#             region_name=os.getenv("AWS_REGION"),
#             config=s3cfg
#         )
#     return _s3


s3cfg = Config(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=2,
    read_timeout=5
)

session = boto3.Session()
s3 = session.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
    region_name=os.environ.get("AWS_REGION", ""),
    config=s3cfg
)


# ----------------------------------------------------
# LOAD METADATA FROM *.ifds.json
# ----------------------------------------------------
@lru_cache(maxsize=512)
def load_ifds(bucket, key):
    """
    Return dict:
    {
      jpegtables: base64string,
      levels: [...]
    }
    """
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(resp["Body"].read())
    except Exception as e:
        abort(404, f"Cannot load IFD metadata: {key}, error: {e}")


# ----------------------------------------------------
# LEVEL SELECTION (IIIF)
# ----------------------------------------------------
def choose_level(levels, full_width, target_width, region_width):
    # jika user request FULL → jangan hitung 'desired_scale', 
    # tetapi pilih level paling rendah yang ada.
    if target_width == region_width:
        # ini artinya size="full" tanpa resizing 
        # → pilih level PALING RENDAH
        return levels[-1]

    desired_scale = region_width / target_width
    best = min(levels, key=lambda lvl: abs(lvl.get("downsample", 1) - desired_scale))
    return best



# ----------------------------------------------------
# FETCH TILE FRAGMENT VIA RANGE GET
# ----------------------------------------------------
def fetch_fragment(bucket, key, offset, length):
    resp = s3.get_object(
        Bucket=bucket,
        Key=key,
        Range=f"bytes={offset}-{offset+length-1}"
    )
    return resp["Body"].read()


# ----------------------------------------------------
# MULTI-TILE COMPOSING (range → image)
# ----------------------------------------------------
def compose_region(level, bucket, wsi_key, lx, ly, lw, lh, jpegtables):
    # pastikan integer
    tile_w = int(level["tile_width"])
    tile_h = int(level["tile_height"])
    width  = int(level["width"])
    height = int(level["height"])
    tiles  = level["tiles"]

    tiles_x = ceil(width / tile_w)
    tiles_y = ceil(height / tile_h)

    # lx, ly, lw, lh bisa datang sebagai float → paksa ke int dulu
    lx = int(lx)
    ly = int(ly)
    lw = int(lw)
    lh = int(lh)

    tx0 = lx // tile_w
    ty0 = ly // tile_h
    tx1 = (lx + lw - 1) // tile_w
    ty1 = (ly + lh - 1) // tile_h

    # clamp tile range within bounds
    tx0 = max(0, min(int(tx0), tiles_x - 1))
    tx1 = max(0, min(int(tx1), tiles_x - 1))
    ty0 = max(0, min(int(ty0), tiles_y - 1))
    ty1 = max(0, min(int(ty1), tiles_y - 1))

    canvas_w = int((tx1 - tx0 + 1) * tile_w)
    canvas_h = int((ty1 - ty0 + 1) * tile_h)

    canvas = Image.new("RGB", (canvas_w, canvas_h))

    tables = base64.b64decode(jpegtables) if jpegtables else b""

    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):

            tile_idx = ty * tiles_x + tx
            if tile_idx >= len(tiles):
                continue

            t = tiles[tile_idx]
            frag = fetch_fragment(bucket, wsi_key, int(t["offset"]), int(t["length"]))

            tile_bytes = tables + frag
            img = Image.open(io.BytesIO(tile_bytes))
            img.load()

            px = int((tx - tx0) * tile_w)
            py = int((ty - ty0) * tile_h)
            canvas.paste(img, (px, py))

    rx = int(lx - tx0 * tile_w)
    ry = int(ly - ty0 * tile_h)

    return canvas.crop((rx, ry, rx + lw, ry + lh))


def fast_thumbnail(level, bucket, wsi_key, jpegtables):
    # ambil 1 tile saja
    tile = level["tiles"][0]
    frag = fetch_fragment(bucket, wsi_key, tile["offset"], tile["length"])

    jpg = base64.b64decode(jpegtables) + frag if jpegtables else frag
    img = Image.open(BytesIO(jpg))
    img.load()

    # thumbnail hard-coded (atau bisa baca target)
    thumb = img.resize((512, 512), Image.LANCZOS)

    buf = BytesIO()
    thumb.save(buf, "JPEG")
    buf.seek(0)
    return buf.getvalue()


# ----------------------------------------------------
# get_info()
# ----------------------------------------------------
def get_info(identifier, cfg, request):
    bucket = cfg["S3_BUCKET"]
    name   = Path(identifier).stem
    ext    = Path(identifier).suffix

    key = f"{cfg['PREFIX_IFDS']}/{name}.ifds.json"
    meta = load_ifds(bucket, key)

    levels = meta["levels"]
    scale_factors = [int(l["downsample"]) for l in levels]

    info = {
        "@context": "http://iiif.io/api/image/2/context.json",
        "@id": f"{request.url_root.rstrip('/')}/iiif/{identifier}",
        "protocol": "http://iiif.io/api/image",
        "width": levels[0]["width"],
        "height": levels[0]["height"],
        "tiles": [
            {
                "width": levels[0]["tile_width"],
                "height": levels[0]["tile_height"],
                # "width": 512,
                # "height": 512,
                "scaleFactors": scale_factors
            }
        ],
        "profile": [
            "http://iiif.io/api/image/2/level2.json",
            {
                "formats": ["jpg","png"],
                "qualities": ["default", "gray"]
            }
        ]
    }
    return info


# ----------------------------------------------------
# get_tile()  (IFDS + jpegtables + multi-tile stitching)
# ----------------------------------------------------
def get_tile(identifier, region, size, rotation, quality, fmt, cfg):
    bucket = cfg["S3_BUCKET"]
    name = Path(identifier).stem
    ext = Path(identifier).suffix

    # load metadata IFD (levels + jpegtables)
    ifds_key = f"{cfg['PREFIX_IFDS']}/{name}.ifds.json"
    meta = load_ifds(bucket, ifds_key)

    levels = meta["levels"]
    jpegtables = meta.get("jpegtables")  # base64 string

    # WSI binary key
    wsi_key = f"{cfg['PREFIX_RAW']}/{name}{ext}"

    # ----------------------------------------------------
    # IIIF Region Parsing
    # ----------------------------------------------------
    if region == "full":
        x = y = 0
        w = int(levels[0]["width"])
        h = int(levels[0]["height"])

    else:
        x, y, w, h = map(int, region.split(","))

    # ----------------------------------------------------
    # IIIF Size Parsing
    # ----------------------------------------------------
    # if TIFF single-resolution and asking for full thumbnail
    if region == "full" and size == "full" and len(levels) == 1:
        return fast_thumbnail(levels[0], bucket, wsi_key, jpegtables)

    elif size.endswith(","):
        tw = int(size[:-1])
        th = int(round(h * (tw / w)))
    elif size.startswith(","):
        th = int(size[1:])
        tw = int(round(w * (th / h)))
    else:
        tw, th = map(int, size.split(","))

    # ----------------------------------------------------
    # Pilih IFD Level Terbaik
    # ----------------------------------------------------
    best = choose_level(levels, levels[0]["width"], tw, w)
    scale = best.get("downsample", 1)

    # Region → coordinate di level ini
    lx = x // scale
    ly = y // scale
    lw = w // scale
    lh = h // scale

    # ----------------------------------------------------
    # Compose multi-tile region
    # --- IMPORTANT ---
    # jpegtables HARUS disertakan agar tile tidak pink / hitam
    # ----------------------------------------------------
    region_img = compose_region(
        level=best,
        bucket=bucket,
        wsi_key=wsi_key,
        lx=lx,
        ly=ly,
        lw=lw,
        lh=lh,
        jpegtables=jpegtables
    )

    # ----------------------------------------------------
    # Resize sesuai IIIF
    # ----------------------------------------------------
    if region_img.size != (tw, th):
        region_img = region_img.resize((tw, th), Image.LANCZOS)

    # ----------------------------------------------------
    # Rotation
    # ----------------------------------------------------
    if rotation not in ("0", "0.0"):
        region_img = region_img.rotate(-float(rotation), expand=True)

    # ----------------------------------------------------
    # Quality
    # ----------------------------------------------------
    if quality == "gray":
        region_img = region_img.convert("L")

    # ----------------------------------------------------
    # Encode Output (safe)
    # ----------------------------------------------------
    buf = io.BytesIO()

    fmt_lower = fmt.lower()

    # Handle IIIF "default" format
    if fmt_lower == "default":
        fmt_lower = "jpg"

    fmt_map = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "png": "PNG",
        "tif": "TIFF",
        "tiff": "TIFF"
    }

    pil_fmt = fmt_map.get(fmt_lower)
    if not pil_fmt:
        raise ValueError(f"Unsupported IIIF output format: {fmt}")

    region_img.save(buf, format=pil_fmt)
    buf.seek(0)

    return buf.getvalue()
