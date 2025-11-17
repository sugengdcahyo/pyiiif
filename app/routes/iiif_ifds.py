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
        print(info)
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
