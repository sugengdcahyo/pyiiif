# app/routes/iiif_ifds.py

import json
import os
import boto3
from io import BytesIO
import io

from math import ceil
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, request, Response, abort
from PIL import Image

from app.config import Config
from app.utils.wsi.io import S3RangeReader  # masih disimpan kalau nanti mau dipakai


iiif_bp = Blueprint("iiif", __name__)


# ---------- SIMPLE CACHE IN MEMORY ----------
_ifds_cache = {}
_reader_cache = {}
_info_cache = {}
_zoom_cache = {}

# Reuse S3 client (singleton)
_s3_client = None


# =========================
# Helpers S3
# =========================

def s3_client():
    """Singleton S3 client, thread-safe untuk dipakai paralel."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION,
        )
    return _s3_client


def load_json_from_s3(bucket: str, key: str) -> dict:
    s3 = s3_client()
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def s3_range(bucket: str, key: str, offset: int, length: int) -> bytes:
    """
    Range GET ke S3 untuk segmen file tile.
    """
    s3 = s3_client()
    r = f"bytes={offset}-{offset + length - 1}"
    obj = s3.get_object(
        Bucket=bucket,
        Key=key,
        Range=r,
    )
    return obj["Body"].read()


# Helper: Build S3 key
def key_raw(image_id: str) -> str:
    """image_id include ext like {svs, tiff, etc}"""
    return f"{Config.PREFIX_RAW}{image_id}"


def key_info(image_id: str) -> str:
    filename, _ = os.path.splitext(image_id)
    return f"{Config.PREFIX_INFO}{filename}.info.json"


def key_ifds(image_id: str) -> str:
    filename, _ = os.path.splitext(image_id)
    return f"{Config.PREFIX_IFDS}{filename}.ifds.json"


# =========================
# Load all metadata (with cache)
# =========================

def load_all_meta(identifier: str):
    """
    identifier = filename tanpa ekstensi (mis: 'BM.1.01 CALRET')

    Memuat info.json, zoom.json, ifds.json dengan cache in-memory.
    """
    # Jika sudah lengkap di cache, langsung pakai
    if (
        identifier in _info_cache
        and identifier in _zoom_cache
        and identifier in _ifds_cache
    ):
        return _info_cache[identifier], _zoom_cache[identifier], _ifds_cache[identifier]

    bucket = Config.S3_BUCKET

    # INFO
    if identifier in _info_cache:
        info_j = _info_cache[identifier]
    else:
        info_key = f"iiif/info/{identifier}.info.json"
        info_j = load_json_from_s3(bucket=bucket, key=info_key)
        _info_cache[identifier] = info_j

    # ZOOM
    if identifier in _zoom_cache:
        zoom_j = _zoom_cache[identifier]
    else:
        zoom_key = f"iiif/zoom/{identifier}.zoom.json"
        zoom_j = load_json_from_s3(bucket=bucket, key=zoom_key)
        _zoom_cache[identifier] = zoom_j

    # IFDS
    if identifier in _ifds_cache:
        ifds_j = _ifds_cache[identifier]
    else:
        ifds_key = f"iiif/ifds/{identifier}.ifds.json"
        ifds_j = load_json_from_s3(bucket=bucket, key=ifds_key)
        _ifds_cache[identifier] = ifds_j

    return info_j, zoom_j, ifds_j


def get_info_document(identifier_with_ext: str) -> dict:
    """
    Helper untuk /info.json:
    - identifier_with_ext: mis 'BM.1.01 CALRET.svs'
    - pakai cache _info_cache
    - return COPY supaya @id tidak merusak cache
    """
    filename, _ = os.path.splitext(identifier_with_ext)
    cache_key = filename
    if cache_key in _info_cache:
        info = _info_cache[cache_key]
    else:
        iiif_key = key_info(image_id=filename)
        info = load_json_from_s3(bucket=Config.S3_BUCKET, key=iiif_key)
        _info_cache[cache_key] = info

    # Kembalikan copy agar modifikasi @id tidak mengubah cache
    return dict(info)


# =========================
# IIIF Helpers
# =========================

def parse_region(region: str, full_w: int, full_h: int):
    if region == "full":
        return 0, 0, full_w, full_h

    if region.startswith("pct:"):
        p = float(region.split(":")[1]) / 100.0
        return 0, 0, int(full_w * p), int(full_h * p)

    x, y, w, h = map(int, region.split(","))
    return x, y, w, h


def parse_size(size: str, rw: int, rh: int):
    if size in ("full", "max"):
        return rw, rh

    if size.startswith("pct:"):
        s = float(size.split(":")[1]) / 100.0
        return int(rw * s), int(rh * s)

    if size.endswith(","):
        w = int(size[:-1])
        h = int(round(rh * (w / rw)))
        return w, h

    if size.startswith(","):
        h = int(size[1:])
        w = int(round(rw * (h / rh)))
        return w, h

    w, h = map(int, size.split(","))
    return w, h


def choose_ifd(ifds, full_w, downscale):
    best = 0
    bestdiff = 9999999

    for i, lvl in enumerate(ifds):
        lvl_w = lvl["width"]
        lvl_scale = full_w / lvl_w
        diff = abs(lvl_scale - downscale)
        if diff < bestdiff:
            bestdiff = diff
            best = i

    return best


def level_coord(level_meta, full_w, rx, ry, rw, rh):
    lw = level_meta["width"]
    scale = full_w / lw

    lx = int(rx / scale)
    ly = int(ry / scale)
    lw2 = int(ceil(rw / scale))
    lh2 = int(ceil(rh / scale))

    return lx, ly, lw2, lh2


def _fetch_tile_image(bucket: str, key: str, offset: int, length: int) -> Image.Image:
    """
    Fetch 1 tile dari S3 (range GET) dan decode jadi PIL Image.
    Dipanggil di thread pool.
    """
    tile_bytes = s3_range(bucket, key, offset, length)
    tile_img = Image.open(BytesIO(tile_bytes))
    tile_img.load()
    return tile_img


def compose_tiles(level_meta, lx, ly, lw, lh, bucket, key):
    """
    Komposisi tiles menjadi 1 region besar:
    - Ambil tile yang dibutuhkan (subset) secara paralel
    - Tempel ke canvas
    - Crop ke region (lx, ly, lw, lh) di level itu
    """
    tiles = level_meta["tiles"]
    tw = level_meta["tileWidth"]
    th = level_meta["tileHeight"]
    txN = level_meta["tilesX"]
    tyN = level_meta["tilesY"]

    # tile index range
    tx0 = lx // tw
    ty0 = ly // th
    tx1 = (lx + lw - 1) // tw
    ty1 = (ly + lh - 1) // th

    tx0 = max(0, tx0)
    ty0 = max(0, ty0)
    tx1 = min(txN - 1, tx1)
    ty1 = min(tyN - 1, ty1)

    canvas_w = (tx1 - tx0 + 1) * tw
    canvas_h = (ty1 - ty0 + 1) * th
    canvas = Image.new("RGB", (canvas_w, canvas_h))

    # Siapkan daftar tile yang perlu di-fetch
    tiles_to_fetch = []
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            idx = ty * txN + tx
            t = tiles[idx]
            tiles_to_fetch.append((tx, ty, t["offset"], t["length"]))

    max_workers = getattr(Config, "IIIF_TILE_THREADS", 8) or 8

    # Parallel fetch + decode tile
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for tx, ty, offset, length in tiles_to_fetch:
            fut = executor.submit(_fetch_tile_image, bucket, key, offset, length)
            futures.append((fut, tx, ty))

        # Paste hasilnya ke canvas di main thread (lebih aman untuk PIL)
        for fut, tx, ty in futures:
            tile_img = fut.result()
            px = (tx - tx0) * tw
            py = (ty - ty0) * th
            canvas.paste(tile_img, (px, py))

    # Crop ke region yang diinginkan
    rx = lx - tx0 * tw
    ry = ly - ty0 * th
    region = canvas.crop((rx, ry, rx + lw, ry + lh))

    return region


# =========================
# IIIF ROUTES
# =========================

@iiif_bp.get("/<path:identifier>/info.json")
def iiif_info(identifier):
    """
    Contoh:
    /iiif/BM.1.01%20CALRET.svs/info.json
    """
    base_url = request.url_root.rstrip("/")

    # Ambil info document dari cache + S3
    iiif_info_doc = get_info_document(identifier)

    # Bangun @id dinamis sesuai base_url saat ini
    iiif_info_doc["@id"] = f"{base_url}/iiif/{identifier}"
    iiif_info_doc.setdefault("protocol", "http://iiif.io/api/image")
    iiif_info_doc.setdefault("profile", "http://iiif.io/api/image/2/level2.json")

    return Response(json.dumps(iiif_info_doc), mimetype="application/json")


@iiif_bp.get("/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>")
def iiif_image(identifier, region, size, rotation, quality, format):
    """
    Contoh:
    /iiif/BM.1.01%20CALRET.svs/full/256,/0/default.jpg
    """
    filename, ext = os.path.splitext(identifier)

    # Rotation & quality constraint sederhana
    if rotation not in ("0", "0.0"):
        abort(400, "Only rotation=0 implemented")

    if quality not in ("default", "color"):
        abort(400, "Only quality=default supported")

    fmt = format.lower()
    if fmt not in ("jpg", "jpeg", "png"):
        abort(400, "Only JPG/PNG supported")

    # ---- Load metadata (cached) ----
    info_j, zoom_j, ifds_j = load_all_meta(filename)

    fw = info_j["width"]
    fh = info_j["height"]

    # region & size di koordinat full-res
    rx, ry, rw, rh = parse_region(region, fw, fh)
    tw, th = parse_size(size, rw, rh)

    # Hitung downscale factor
    downscale = max(rw / tw, rh / th) if tw and th else 1
    if downscale < 1:
        downscale = 1

    # Pilih IFD level paling dekat dengan downscale
    lvl_idx = choose_ifd(ifds_j["levels"], fw, downscale)
    lvl = ifds_j["levels"][lvl_idx]

    # Koordinat di level tersebut
    lx, ly, lw, lh = level_coord(lvl, fw, rx, ry, rw, rh)

    # Raw WSI object di S3
    wsi_bucket = Config.S3_BUCKET
    wsi_key = key_raw(identifier)  # konsisten dengan PREFIX_RAW

    # Compose tile jadi 1 region image
    region_img = compose_tiles(lvl, lx, ly, lw, lh, wsi_bucket, wsi_key)

    # Resize ke target output size jika perlu
    if (tw, th) != region_img.size:
        region_img = region_img.resize((tw, th), Image.LANCZOS)

    # Encode output
    buf = BytesIO()
    fmt_out = "JPEG" if fmt in ("jpg", "jpeg") else "PNG"
    region_img.save(buf, fmt_out)
    buf.seek(0)

    mimetype = "image/jpeg" if fmt_out == "JPEG" else "image/png"
    return Response(buf.getvalue(), mimetype=mimetype)
