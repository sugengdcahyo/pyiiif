# app/routes/iiif_ifds.py

# import json
# import os
# import boto3
# from io import BytesIO

# from app.config import Config
# from flask import Blueprint, request, Response, abort
# from math import ceil
# from PIL import Image


# iiif_bp = Blueprint("iiif", __name__)


# # ---------- SIMPLE CACHE IN MEMORY ----------
# _ifds_cache = {}
# _reader_cache = {}
# _info_cache = {}

# # =========================
# # Helpers S3
# # =========================


# def s3_client():
#     return boto3.client(
#         "s3",
#         aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
#         region_name=Config.AWS_REGION
#     )


# def load_json_from_s3(bucket: str, key: str) -> dict:
#     s3 = s3_client()
#     obj = s3.get_object(Bucket=bucket, Key=key)
#     return json.loads(obj["Body"].read().decode("utf-8"))


# def s3_range(bucket: str, key: str, offset: int, length: int) -> bytes:
#     s3 = s3_client()
#     r = f"bytes={offset}-{offset+length-1}"
#     obj = s3.get_object(
#         Bucket=bucket,
#         Key=key,
#         Range=r
#     )
#     return obj["Body"].read()


# # Helper: Build S3 key
# def key_raw(image_id: str) -> str:
#     """image_id include ext like {svs, tiff, etc}"""
#     return f"{Config.PREFIX_RAW}{image_id}"


# def key_info(image_id: str) -> str:
#     filename, _ = os.path.splitext(image_id)
#     return f"{Config.PREFIX_INFO}{filename}.info.json"


# def key_ifds(image_id: str) -> str:
#     filename, _ = os.path.splitext(image_id)
#     return f"{Config.PREFIX_IFDS}{filename}.ifds.json"

# # =========================
# # Load all metadata
# # =========================


# def load_all_meta(identifier: str):
#     meta_bucket = Config.S3_BUCKET

#     info_j = load_json_from_s3(bucket=meta_bucket, key=f"iiif/info/{identifier}.info.json")
#     zoom_j = load_json_from_s3(bucket=meta_bucket, key=f"iiif/zoom/{identifier}.zoom.json")
#     ifds_j = load_json_from_s3(bucket=meta_bucket, key=f"iiif/ifds/{identifier}.ifds.json")

#     return info_j, zoom_j, ifds_j

# # =========================
# # IIIF Helpers
# # =========================


# def parse_region(region: str, full_w: int, full_h: int):
#     if region == "full":
#         return 0, 0, full_w, full_h

#     if region.startswith("pct:"):
#         p = float(region.split(":")[1]) / 100.0
#         return 0, 0, int(full_w*p), int(full_h*p)

#     x, y, w, h = map(int, region.split(","))
#     return x, y, w, h


# def parse_size(size: str, rw: int, rh: int):
#     if size in ("full", "max"):
#         return rw, rh

#     if size.startswith("pct:"):
#         s = float(size.split(":")[1]) / 100.0
#         return int(rw*s), int(rh*s)

#     if size.endswith(","):
#         w = int(size[:-1])
#         h = int(round(rh*(w/rw)))
#         return w, h

#     if size.startswith(","):
#         h = int(size[1:])
#         w = int(round(rw*(h/rh)))
#         return w, h

#     w, h = map(int, size.split(","))
#     return w, h


# def choose_ifd(ifds, full_w, downscale):
#     best = 0
#     bestdiff = 9999999

#     for i, lvl in enumerate(ifds):
#         lvl_w = lvl["width"]
#         lvl_scale = full_w / lvl_w
#         diff = abs(lvl_scale - downscale)
#         if diff < bestdiff:
#             bestdiff = diff
#             best = i

#     return best


# def level_coord(level_meta, full_w, rx, ry, rw, rh):
#     lw = level_meta["width"]
#     scale = full_w / lw

#     lx = int(rx / scale)
#     ly = int(ry / scale)
#     lw2 = int(ceil(rw / scale))
#     lh2 = int(ceil(rh / scale))

#     return lx, ly, lw2, lh2


# def compose_tiles(level_meta, lx, ly, lw, lh, bucket, key):
#     tiles = level_meta["tiles"]
#     tw = level_meta["tileWidth"]
#     th = level_meta["tileHeight"]
#     txN = level_meta["tilesX"]
#     tyN = level_meta["tilesY"]

#     tx0 = lx // tw
#     ty0 = ly // th
#     tx1 = (lx+lw-1) // tw
#     ty1 = (ly+lh-1) // th

#     tx0 = max(0, tx0)
#     ty0 = max(0, ty0)
#     tx1 = min(txN-1, tx1)
#     ty1 = min(tyN-1, ty1)

#     canvas_w = (tx1 - tx0 + 1) * tw
#     canvas_h = (ty1 - ty0 + 1) * th
#     canvas = Image.new("RGB", (canvas_w, canvas_h))

#     for ty in range(ty0, ty1+1):
#         for tx in range(tx0, tx1+1):
#             idx = ty*txN + tx
#             t = tiles[idx]

#             offset = t["offset"]
#             length = t["length"]

#             tile_bytes = s3_range(bucket, key, offset, length)
#             tile_img = Image.open(BytesIO(tile_bytes))
#             tile_img.load()

#             px = (tx - tx0) * tw
#             py = (ty - ty0) * th
#             canvas.paste(tile_img, (px, py))

#     rx = lx - tx0*tw
#     ry = ly - ty0*th
#     region = canvas.crop((rx, ry, rx+lw, ry+lh))

#     return region

# # =========================
# # IIIF ROUTES
# # =========================


# @iiif_bp.get("/<path:identifier>/info.json")
# def iiif_info(identifier):
#     base_url = request.url_root.rstrip("/")
#     filename, _ = os.path.splitext(identifier)
#     iiif_key = key_info(image_id=filename)
#     iiif_info = load_json_from_s3(
#         bucket=Config.S3_BUCKET,
#         key=iiif_key
#     )
#     iiif_info["@id"] = f"{base_url}/iiif/{identifier}"
#     iiif_info.setdefault("protocol", "http://iiif.io/api/image")
#     iiif_info.setdefault("profile", "http://iiif.io/api/image/2/level2.json")
#     return Response(json.dumps(iiif_info), mimetype="application/json")


# @iiif_bp.get("/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>")
# def iiif_image(identifier, region, size, rotation, quality, format):

#     filename, ext = os.path.splitext(identifier)

#     if rotation not in ("0", "0.0"):
#         abort(400, "Only rotation=0 implemented")

#     if quality not in ("default", "color"):
#         abort(400, "Only quality=default supported")

#     fmt = format.lower()
#     if fmt not in ("jpg", "jpeg", "png"):
#         abort(400, "Only JPG/PNG supported")

#     info_j, zoom_j, ifds_j = load_all_meta(filename)

#     fw = info_j["width"]
#     fh = info_j["height"]

#     rx, ry, rw, rh = parse_region(region, fw, fh)
#     tw, th = parse_size(size, rw, rh)

#     downscale = max(rw/tw, rh/th)
#     if downscale < 1:
#         downscale = 1

#     lvl_idx = choose_ifd(ifds_j["levels"], fw, downscale)
#     lvl = ifds_j["levels"][lvl_idx]

#     lx, ly, lw, lh = level_coord(lvl, fw, rx, ry, rw, rh)

#     wsi_bucket = Config.S3_BUCKET
#     wsi_key = f"raw/{identifier}"

#     region_img = compose_tiles(lvl, lx, ly, lw, lh, wsi_bucket, wsi_key)

#     if (tw, th) != region_img.size:
#         region_img = region_img.resize((tw, th), Image.LANCZOS)

#     buf = BytesIO()
#     fmt_out = "JPEG" if fmt in ("jpg", "jpeg") else "PNG"
#     region_img.save(buf, fmt_out)
#     buf.seek(0)

#     mimetype = "image/jpeg" if fmt_out == "JPEG" else "image/png"
#     return Response(buf.read(), mimetype=mimetype)





# app/routes/iiif.py
from flask import Blueprint, current_app, request, abort, make_response
from app.utils.http import cache_headers

# providers
from app.providers import s3range_ifds as s3range_provider
from app.providers import openslide as openslide_provider


iiif_bp = Blueprint("iiif", __name__)


# -------------------------------
# Provider selector (modular)
# -------------------------------
def get_provider():
    backend = current_app.config.get("IIIF_BACKEND", "s3range").lower()

    if backend == "s3range":
        return s3range_provider
    elif backend == "openslide":
        return openslide_provider
    else:
        raise ValueError(f"Unsupported IIIF Backend: {backend}")


# -------------------------------
# /iiif/<identifier>/info.json
# -------------------------------
@iiif_bp.get("/<path:identifier>/info.json")
def get_info(identifier):
    """
    Endpoint IIIF Info.json
    """
    provider = get_provider()

    try:
        info = provider.get_info(
            identifier,
            current_app.config,
            request
        )
    except Exception as e:
        abort(500, description=f"IIIF info error: {e}")

    resp = make_response(info)
    resp.mimetype = "application/json"

    # opsional: caching agar browser tidak spam metadata
    return cache_headers(resp)


# -------------------------------
# /iiif/<identifier>/<region>/<size>/<rotation>/<quality>.<format>
# -------------------------------
@iiif_bp.get("/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>")
def get_tile(identifier, region, size, rotation, quality, format):
    """
    Endpoint tile IIIF via provider (s3range / openslide)
    """
    provider = get_provider()

    # try:
    tile_bytes = provider.get_tile(
        identifier,
        region,
        size,
        rotation,
        quality,
        format,
        current_app.config
    )
    # except ValueError as e:
    #     abort(400, description=str(e))
    # except FileNotFoundError as e:
    #     abort(404, description=str(e))
    # except Exception as e:
    #     abort(500, description=f"Tile generation error: {e}")

    # MIME otomatis
    fmt = format.lower()
    mimetype = (
        "image/jpeg" if fmt in ("jpg", "jpeg")
        else "image/png" if fmt == "png"
        else "image/tiff" if fmt in ("tif", "tiff")
        else "application/octet-stream"
    )

    resp = make_response(tile_bytes)
    resp.mimetype = mimetype

    # caching helps A LOT for IIIF viewers
    return cache_headers(resp)
