from __future__ import annotations
from flask import Flask, jsonify, send_file, abort, request, make_response
from flask_cors import CORS
from openslide import OpenSlide
from PIL import Image, ImageOps
import os
import io
import math
import functools
from pathlib import Path

# --- Configuration ---
app = Flask(__name__)
CORS(app, origins=["http://localhost:8080", "http://0.0.0.0:8080"])

TILE_SIZE = 512

# ===== Path yang konsisten & absolut =====
BASE_DIR = Path(__file__).resolve().parent          # .../app
PROJECT_ROOT = BASE_DIR.parent                      # .../
SLIDE_PATH = (PROJECT_ROOT / "slides").resolve()    # .../slides  (ABSOLUT!)

VALID_EXTENSIONS = ('.svs', '.tif', '.tiff', '.ndpi', '.vms', '.mrxs')

# JPEG/PNG tuning
JPEG_OPTS = dict(quality=80, optimize=True, progressive=True)
PNG_OPTS  = dict(optimize=True)

# Hard guardrails (hindari abuse)
MAX_OUT_W = 8192
MAX_OUT_H = 8192

# --- Utilities ---
def safe_join_slide(image_id: str) -> str:
    """
    Gabungkan identifier dengan SLIDE_PATH secara aman:
    - buang leading slash & backslash
    - tolak '..'
    - pastikan path akhir masih di bawah SLIDE_PATH
    """
    iid = image_id.lstrip("/").replace("\\", "/")
    if ".." in iid:
        abort(400, description="Invalid identifier")
    candidate = (SLIDE_PATH / iid).resolve()

    # Pastikan candidate adalah anak dari SLIDE_PATH (bukan /slides2, dsb)
    if not (str(candidate) == str(SLIDE_PATH) or str(candidate).startswith(str(SLIDE_PATH) + os.sep)):
        abort(400, description="Invalid identifier")
    return str(candidate)

@functools.lru_cache(maxsize=32)
def load_slide_cached(path: str) -> OpenSlide:
    return OpenSlide(path)

def parse_region(region: str, full_w: int, full_h: int):
    if region == "full":
        return (0, 0, full_w, full_h)
    try:
        x, y, w, h = map(int, region.split(","))
        # tolak nilai negatif
        if w <= 0 or h <= 0:
            abort(400, description="Invalid region size")
        return (x, y, w, h)
    except Exception:
        abort(400, description="Invalid region")

def parse_size(size: str, w: int, h: int):
    if size == "full":
        return (w, h)
    if size.startswith("pct:"):
        try:
            pct = float(size.split(":", 1)[1])
            if pct <= 0:
                abort(400, description="Invalid size pct")
            return (max(1, int(w * pct / 100.0)), max(1, int(h * pct / 100.0)))
        except Exception:
            abort(400, description="Invalid size pct")
    try:
        if size.endswith(","):   # width,
            dst_w = int(size[:-1])
            if dst_w <= 0: abort(400, description="Invalid size")
            dst_h = max(1, int(h * (dst_w / float(w))))
            return (dst_w, dst_h)
        elif size.startswith(","):  # ,height
            dst_h = int(size[1:])
            if dst_h <= 0: abort(400, description="Invalid size")
            dst_w = max(1, int(w * (dst_h / float(h))))
            return (dst_w, dst_h)
        else:  # width,height
            dst_w, dst_h = map(int, size.split(","))
            if dst_w <= 0 or dst_h <= 0: abort(400, description="Invalid size")
            return (dst_w, dst_h)
    except Exception:
        abort(400, description="Invalid size")

def clamp_region(x, y, w, h, full_w, full_h):
    # koreksi ke dalam kanvas
    x = max(0, min(x, full_w))
    y = max(0, min(y, full_h))
    w = max(1, min(w, full_w - x))
    h = max(1, min(h, full_h - y))
    return x, y, w, h

def get_best_level(slide: OpenSlide, src_w: int, src_h: int, dst_w: int, dst_h: int,
                   prefer_no_upsample: bool = True) -> int:
    dst_w = max(1, int(dst_w))
    dst_h = max(1, int(dst_h))
    src_w = max(1, int(src_w))
    src_h = max(1, int(src_h))

    target = max(src_w / dst_w, src_h / dst_h)  # faktor downsample yang diinginkan
    downs = list(slide.level_downsamples)

    if prefer_no_upsample:
        best = 0
        for i, d in enumerate(downs):
            if d <= target + 1e-9:
                best = i
            else:
                break
        return best
    return min(range(len(downs)), key=lambda i: abs(downs[i] - target))

def pil_save_to_bytes(img: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, format=fmt, **JPEG_OPTS)
    elif fmt == "PNG":
        img.save(buf, format=fmt, **PNG_OPTS)
    elif fmt == "TIFF":
        img.save(buf, format=fmt)  # tiff apa adanya
    else:
        img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()

def cache_headers(resp, seconds=31536000, immutable=True):
    resp.headers["Cache-Control"] = f"public, max-age={seconds}" + (", immutable" if immutable else "")
    return resp

# --- JSON error handler ---
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def json_error(e):
    code = getattr(e, "code", 500)
    return jsonify({"error": getattr(e, "description", str(e)), "status": code}), code

# --- IIIF Tile Endpoint ---
@app.route('/iiif/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>')
def tile(identifier, region, size, rotation, quality, format):
    ident_lower = identifier.lower()
    if not ident_lower.endswith(VALID_EXTENSIONS):
        abort(400, description="Unsupported file extension")

    slide_path = safe_join_slide(identifier)
    if not os.path.exists(slide_path):
        abort(404, description="Slide not found")

    try:
        slide = load_slide_cached(slide_path)
    except Exception as e:
        abort(500, description=f"Slide open failed: {e}")

    full_w, full_h = slide.dimensions

    # region/size
    x, y, w, h = parse_region(region, full_w, full_h)
    x, y, w, h = clamp_region(x, y, w, h, full_w, full_h)

    dst_w, dst_h = parse_size(size, w, h)
    if dst_w > MAX_OUT_W or dst_h > MAX_OUT_H:
        abort(400, description="Output size too large")

    # rotation / mirror
    is_mirrored = rotation.startswith("!")
    rotation = rotation.lstrip("!")
    try:
        rotation = int(rotation) % 360
        if rotation not in (0, 90, 180, 270):
            abort(400, description="Invalid rotation")
    except Exception:
        abort(400, description="Invalid rotation")

    if quality not in ("default", "gray"):
        abort(400, description="Unsupported quality")

    # pilih level terbaik untuk menghindari upsample
    lvl = get_best_level(slide, w, h, dst_w, dst_h, prefer_no_upsample=True)
    scale = slide.level_downsamples[lvl]

    # ❗ Koordinat ke OpenSlide SELALU level-0 (JANGAN dibagi scale)
    #    Hanya ukuran yang dikonversi ke piksel pada level terpilih.
    rw = max(1, int(math.ceil(w / scale)))
    rh = max(1, int(math.ceil(h / scale)))
    rx = int(x)
    ry = int(y)

    try:
        region_img = slide.read_region((rx, ry), lvl, (rw, rh)).convert("RGB")

        # Resize ke ukuran yang diminta (IIIF 'size')
        if (dst_w, dst_h) != (rw, rh):
            region_img = region_img.resize((dst_w, dst_h), Image.Resampling.LANCZOS)

        if is_mirrored:
            region_img = ImageOps.mirror(region_img)
        if rotation:
            region_img = region_img.rotate(-rotation, expand=True)
        if quality == "gray":
            region_img = region_img.convert("L")
    except Exception as e:
        abort(500, description=f"Tile read error: {e}")

    fmt = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "tif": "TIFF"}.get(format.lower())
    if fmt is None:
        abort(400, description="Unsupported format")

    data = pil_save_to_bytes(region_img, fmt)
    resp = make_response(data)
    resp.mimetype = "image/tiff" if fmt == "TIFF" else f"image/{format.lower()}"
    return cache_headers(resp)

# --- IIIF info.json Endpoint ---
@app.route("/iiif/<path:image_id>/info.json")
def info_json(image_id):
    path = safe_join_slide(image_id)
    if not os.path.exists(path):
        abort(404, description="Slide not found")

    try:
        slide = load_slide_cached(path)
    except Exception as e:
        abort(500, description=f"Failed to open slide: {e}")

    levels = slide.level_dimensions
    width, height = levels[0]

    # scaleFactors dari level_downsamples -> integer, unik & menaik
    raw = [max(1, int(round(ds))) for ds in slide.level_downsamples]
    scale_factors = sorted(set(raw))
    if 1 not in scale_factors:
        scale_factors.insert(0, 1)

    base_id = request.url_root.rstrip("/")
    image_id_clean = image_id.lstrip("/")
    image_id_url = f"{base_id}/iiif/{image_id_clean}"

    info = {
        "@context": "http://iiif.io/api/image/2/context.json",
        "@id": image_id_url,
        "@type": "iiif:Image",
        "protocol": "http://iiif.io/api/image",
        "width": width,
        "height": height,
        "tiles": [{
            "width": TILE_SIZE,
            "height": TILE_SIZE,
            "scaleFactors": scale_factors
        }],
        "sizes": [{"width": w, "height": h} for (w, h) in reversed(levels)],
        "profile": [
            "http://iiif.io/api/image/2/level2.json",
            {
                "formats": ["jpg", "png", "tif"],
                "qualities": ["default", "gray"],
                "supports": [
                    "sizeByW", "sizeByH", "sizeByPct",
                    "regionByPx", "rotationBy90s"
                ]
            }
        ]
    }
    resp = jsonify(info)
    return cache_headers(resp, seconds=3600, immutable=False)

# --- Healthcheck ---
@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})
