from flask import (
    Blueprint, current_app, request,
    abort, make_response)
from app.utils.http import cache_headers
from app.providers import openslide as openslide_provider
from app.providers import s3range as s3range_provider

bp = Blueprint("iiif", __name__)


def get_provider():
    backend = current_app.config.get("IIIF_BACKEND", "openslide").lower()
    if backend == "openslide":
        return openslide_provider
    elif backend == "s3range":
        return s3range_provider
    else:
        raise ValueError("Unsupported IIIF backend")


@bp.get("/<path:identifier>/info.json")
def info_json(identifier):
    provider = get_provider()
    data = provider.get_info(
        identifier, current_app.config, request
    )
    return data


@bp.get("/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>")
def tile(identifier, region, size, rotation, quality, format):
    provider = get_provider()
    try:
        payload = provider.get_tile(
            identifier, region,
            size, rotation,
            quality, format, current_app.config
        )
        resp = make_response(payload)
        resp.mimetype = f"image/{format.lower()}"
        return cache_headers(resp)
    except ValueError as e:
        abort(400, description=str(e))
    except Exception as e:
        abort(500, description=str(e))
