from flask import (
    Blueprint, current_app, request,
    abort, make_response, jsonify)
from PIL import Image, ImageOps
from ..services.slide import open_slide
from ..utils.path import safe_join_slide
from ..utils.image import save_to_bytes, pick_level_for_target, level_dims
from ..utils.http import cache_headers

bp = Blueprint("iiif", __name__)


@bp.get("/<path:identifier>/info.json")
def info_json(identifier):
    cfg = current_app.config
    path = safe_join_slide(cfg["SLIDE_PATH"], identifier)
    slide = open_slide(path)

    levels = slide.level_dimensions
    width, height = levels[0]
    raw = [max(1, int(round(ds))) for ds in slide.level_downsamples]
    scale_factors = sorted(set(raw))
    if 1 not in scale_factors:
        scale_factors.insert(0, 1)

    base = request.url_root.rstrip("/")
    image_id_url = f"{base}/iiif/{identifier.lstrip('/')}"
    data = {
        "@context": "http://iiif.io/api/image/2/context.json",
        "@id": image_id_url,
        "@type": "iiif:Image",
        "protocol": "http://iiif.io/api/image",
        "width": width,
        "height": height,
        "tiles": [{
            "width": cfg["TILE_SIZE"],
            "height": cfg["TILE_SIZE"],
            "scaleFactors": scale_factors}],
        "sizes": [{"width": w, "height": h} for (w, h) in reversed(levels)],
        "profile": ["http://iiif.io/api/image/2/level2.json",
                    {
                        "formats": ["jpg", "png", "tif"],
                        "qualities": ["default", "gray"],
                        "supports": ["sizeByW", "sizeByH", "sizeByPct",
                                     "regionByPx", "rotationBy90s"]
                    }],
    }
    return cache_headers(jsonify(data), seconds=3600, immutable=False)


@bp.get("/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>")
def tile(identifier, region, size, rotation, quality, format):
    cfg = current_app.config
    if not identifier.lower().endswith(cfg["VALID_EXTENSIONS"]):
        abort(400, description="Unsupported file extension")

    path = safe_join_slide(cfg["SLIDE_PATH"], identifier)
    slide = open_slide(path)
    full_w, full_h = slide.dimensions

    # --- parse region ---
    if region == "full":
        x, y, w, h = 0, 0, full_w, full_h
    else:
        try:
            x, y, w, h = map(int, region.split(","))
            if w <= 0 or h <= 0:
                abort(400, description="Invalid region size")
        except Exception:
            abort(400, description="Invalid region")
    # clamp
    x = max(0, min(x, full_w))
    y = max(0, min(y, full_h))
    w = max(1, min(w, full_w - x))
    h = max(1, min(h, full_h - y))

    # --- parse size ---
    def parse_size(sz, w, h):
        if sz == "full":
            return (w, h)

        if sz.startswith("pct:"):
            pct = float(sz.split(":", 1)[1])
            if pct <= 0:
                abort(400, description="Invalid size pct")
            return (
                max(1, int(round(w*pct/100))),
                max(1, int(round(h*pct/100)))
            )

        if sz.endswith(","):
            dst_w = int(sz[:-1])
            if dst_w <= 0:
                abort(400, description="Invalid size")
            return (dst_w, max(1, int(round(h*(dst_w/w)))))

        if sz.startswith(","):
            dst_h = int(sz[1:])
            if dst_h <= 0:
                abort(400, description="Invalid size")
            return (max(1, int(round(w*(dst_h/h)))), dst_h)

        dst_w, dst_h = map(int, sz.split(","))

        if dst_w <= 0 or dst_h <= 0:
            abort(400, description="Invalid size")
        return (dst_w, dst_h)

    dst_w, dst_h = parse_size(size, w, h)
    if dst_w > cfg["MAX_OUT_W"] or dst_h > cfg["MAX_OUT_H"]:
        abort(400, description="Output size too large")

    # --- rotation & quality ---
    is_mirror = rotation.startswith("!")
    rotation = rotation.lstrip("!")
    try:
        rotation = int(rotation) % 360
        if rotation not in (0, 90, 180, 270):
            abort(400, description="Invalid rotation")
    except Exception:
        abort(400, description="Invalid rotation")

    if quality not in ("default", "gray"):
        abort(400, description="Unsupported quality")

    # --- pilih level terbaik untuk mendekati dst size ---
    lvl = pick_level_for_target(slide, w, h, dst_w, dst_h)
    rw, rh, scale = level_dims(slide, lvl, w, h)

    rx, ry = int(x), int(y)     # koordinat SELALU level-0
    img = slide.read_region((rx, ry), lvl, (rw, rh)).convert("RGB")

    # resize jika perlu (toleransi 1 px)
    if abs(rw - dst_w) > 1 or abs(rh - dst_h) > 1:
        img = img.resize((dst_w, dst_h), Image.Resampling.LANCZOS)

    if is_mirror:
        img = ImageOps.mirror(img)

    if rotation:
        img = img.rotate(-rotation, expand=True)

    if quality == "gray":
        img = img.convert("L")

    fmt = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "png": "PNG",
        "tif": "TIFF"
    }.get(format.lower())

    if not fmt:
        abort(400, description="Unsupported format")

    payload = save_to_bytes(img, fmt)
    resp = make_response(payload)
    resp.mimetype = (
        "image/tiff" if fmt == "TIFF"
        else f"image/{format.lower()}"
    )
    return cache_headers(resp)
