import boto3
import json
import io
import base64
import os
from botocore.config import Config
from PIL import Image, ImageFile
from pathlib import Path
from flask import abort
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None  # disable DecompressionBombError


s3cfg = Config(
    retries={"max_attempts": 2, "mode": "standard"},
    connect_timeout=2,
    read_timeout=5
)

#-- singleton boto3 client --
session = boto3.Session()
s3 = session.client(
    "s3",
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
    region_name=os.environ.get("AWS_REGION", ""),
    config=s3cfg
)


@lru_cache(maxsize=512)
def _load_metadata(bucket, key):
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj["Body"].read())
    except s3.exceptions.NoSuchKey:
        abort(404, description="File not found.")
    except Exception as e:
        abort(500, description=f"S3 error: {e}")


def _choose_level(info, zoom, target_w, region_w):
    # hitung rasio downsample yang dibutuhkan
    desired_scale = region_w / target_w   # contoh: 16384 / 512 = 32

    # pilih level dengan downsample terdekat
    best = min(
        zoom["levels"],
        key=lambda l: abs(l.get("downsample", 1) - desired_scale)
    )
    return best["level"]


def get_info(identifier, cfg, request):
    name, ext = Path(identifier).stem, Path(identifier).suffix

    if ext.lower() not in cfg['VALID_EXTENSIONS']:
        abort(400, description="Unsupported file extension")

    identifier = f"iiif/wsi/{identifier}"
    key = f"{cfg['S3_PREFIX'].rstrip('/')}/info/{name}.info.json"
    bucket = cfg['S3_BUCKET']

    metadata = _load_metadata(bucket=bucket, key=key)

    # try:
    #     obj = s3.get_object(Bucket=bucket, Key=key)
    #     body = obj["Body"].read()
    #     metadata = json.loads(body)
    # except s3.exceptions.NoSuchKey:
    #     abort(404, description="File not found")
    # except Exception as e:
    #     abort(500, description=str(e))

    if not metadata:
        abort(404, description="Metadata not found")

    base = request.url_root.rstrip("/")
    image_id_url = f"{base}/iiif/{name}{ext}"

    metadata.update({"@id": image_id_url})
    return metadata


def get_tile(identifier, region, size, rotation, quality, fmt, cfg):
    bucket = cfg["S3_BUCKET"]
    prefix_info = cfg.get("PREFIX_INFO", "iiif/info")
    prefix_zoom = cfg.get("PREFIX_ZOOM", "iiif/zoom")
    prefix_wsi = cfg.get("PREFIX_WSI", "iiif/wsi")

    name = Path(identifier).stem
    ext = Path(identifier).suffix

    # pakai cache
    info = _load_metadata(bucket, f"{prefix_info}/{name}.info.json")
    zoom = _load_metadata(bucket, f"{prefix_zoom}/{name}.zoomlevel.json")

    # --- parse region ---
    if region == "full":
        x, y, w, h = 0, 0, info["width"], info["height"]
    else:
        x, y, w, h = map(int, region.split(","))

    # --- parse size ---
    if size == "full":
        target_w, target_h = w, h
    elif size.endswith(","):
        target_w = int(size[:-1]); target_h = int(h * (target_w / w))
    elif size.startswith(","):
        target_h = int(size[1:]); target_w = int(w * (target_h / h))
    else:
        target_w, target_h = map(int, size.split(","))

    # --- pilih level adaptif ---
    best_level = _choose_level(info, zoom, target_w, w)
    level_meta = next(l for l in zoom["levels"] if l["level"] == best_level)

    scale = int(round(level_meta.get("downsample", 1)))

    # konversi region ke koordinat level ini
    lx, ly = x // scale, y // scale
    lw, lh = w // scale, h // scale

    tile_w, tile_h = level_meta["tile_width"], level_meta["tile_height"]
    tiles_per_row = (level_meta["width"] + tile_w - 1) // tile_w

    tile_x, tile_y = lx // tile_w, ly // tile_h
    tile_index = tile_y * tiles_per_row + tile_x

    print(f"Level: {best_level}, Tile: ({tile_x}, {tile_y}) idx {tile_index}, \
            Region: ({x},{y},{w},{h}) -> ({lx},{ly},{lw},{lh}), \
            Target size: ({target_w},{target_h}), Scale: {scale}")

    if tile_index >= len(level_meta["tiles"]):
        raise ValueError(f"Tile index {tile_index} out of\
                          range for level {best_level}")

    tile_meta = level_meta["tiles"][tile_index]

    # --- ambil fragmen dari S3 ---
    offset, length = tile_meta["offset"], tile_meta["length"]
    wsi_key = f"{prefix_wsi}/{name}{ext}"

    resp = s3.get_object(
        Bucket=bucket, Key=wsi_key,
        Range=f"bytes={offset}-{offset+length-1}"
    )
    fragment = resp["Body"].read()

    # --- gabungkan jpegtables + fragment ---
    tables = base64.b64decode(zoom.get("jpegtables", "")) if "jpegtables" in zoom else b""
    jpeg_bytes = tables + fragment

    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")

    # --- crop sesuai region relatif ke tile ---
    crop_x, crop_y = lx % tile_w, ly % tile_h
    crop_w = min(lw, img.width - crop_x)
    crop_h = min(lh, img.height - crop_y)
    img = img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

    # --- resize sesuai target size (IIIF spec) ---
    if (img.width, img.height) != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.LANCZOS)

    # --- rotation ---
    if rotation != "0":
        img = img.rotate(-float(rotation), expand=True)

    # --- quality ---
    if quality == "gray":
        img = img.convert("L")

    # --- save ---
    buf = io.BytesIO()
    fmt_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "tif": "TIFF", "tiff": "TIFF"}
    pil_fmt = fmt_map.get(fmt.lower())
    if not pil_fmt:
        raise ValueError(f"Unsupported format: {fmt}")

    img.save(buf, format=pil_fmt)
    buf.seek(0)

    return buf.getvalue()
