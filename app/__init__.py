from flask import Flask, jsonify, send_file, abort, request
from flask_cors import CORS
from openslide import OpenSlide
from PIL import Image, ImageOps
import os
import io

# --- Configuration ---
app = Flask(__name__)
CORS(app, origins=["http://localhost:8080", "http://0.0.0.0:8080"])

TILE_SIZE = 512
SLIDE_PATH = "./slides"
VALID_EXTENSIONS = ('.svs', '.tif', '.tiff', '.ndpi', '.vms', '.mrxs')

# --- Utilities ---
def get_slide_path(image_id):
    return os.path.join(SLIDE_PATH, image_id)

# --- helper: parse_region ---
def parse_region(region, full_w, full_h):
    if region == "full":
        return (0, 0, full_w, full_h)
    try:
        # format: x,y,w,h
        x, y, w, h = map(int, region.split(","))
        return (x, y, w, h)
    except:
        return (0, 0, full_w, full_h)  # fallback: full

# --- helper: parse_size ---
def parse_size(size, w, h):
    if size == "full":
        return (w, h)
    if size.startswith("pct:"):
        pct = float(size.split(":")[1])
        return (int(w * pct / 100), int(h * pct / 100))
    try:
        if size.endswith(","):   # format: width,
            dst_w = int(size[:-1])
            dst_h = int(h * (dst_w / w))
            return (dst_w, dst_h)
        elif size.startswith(","):  # format: ,height
            dst_h = int(size[1:])
            dst_w = int(w * (dst_h / h))
            return (dst_w, dst_h)
        else:  # format: width,height
            dst_w, dst_h = map(int, size.split(","))
            return (dst_w, dst_h)
    except:
        return (w, h)  # fallback

def clamp_region(x, y, w, h, full_w, full_h):
    x = max(0, min(x, full_w))
    y = max(0, min(y, full_h))
    w = max(0, min(w, full_w - h))
    h = max(0, min(h, full_h - y))
    return x, y, w, h

def get_best_level(slide, src_w, src_h, dst_w, dst_h, prefer_no_upsample=True):
    dst_w = max(1, int(dst_w))
    dst_h = max(1, int(dst_w))
    src_w = max(1, int(src_w))
    src_h = max(1, int(src_h))

    # downsample target needed
    target = max(src_w / dst_w, src_h / dst_h) 

    downs = list(slide.level_downsamples)
    n = len(downs)

    if prefer_no_upsample:
        best = 0 
        for i in range(n):
            if downs[i] <= target + 1e-9:
                best = i
            else:
                break

            return best

    return min(range(n), key=lambda i: abs(downs[i] - target))

# def get_best_level(slide, target_w, target_h):
#     for level in range(slide.level_count):
#         w, h = slide.level_dimensions[level]
#         if target_w <= w and target_h <= h:
#             return level
#     return slide.level_count - 1

# --- IIIF Tile Endpoint ---
@app.route('/iiif/<path:identifier>/<region>/<size>/<rotation>/<quality>.<format>')
def tile(identifier, region, size, rotation, quality, format):
    if not identifier.lower().endswith(VALID_EXTENSIONS):
        abort(400, description="Unsupported file extension")

    slide_path = get_slide_path(identifier)
    if not os.path.exists(slide_path):
        abort(404, description="Slide not found")

    try:
        slide = OpenSlide(slide_path)
    except Exception as e:
        abort(500, description=f"Slide open failed: {e}")

    full_width, full_height = slide.dimensions

    # --- parse region ---
    x, y, w, h = parse_region(region, full_width, full_height)
    x, y, w, h = clamp_region(x, y, w, h, full_width, full_height)

    # --- parse size ---
    dst_w, dst_h = parse_size(size, w, h)

    # --- parse rotation (IIIF: may start with "!" for mirrored) ---
    is_mirrored = rotation.startswith("!")
    rotation = rotation.lstrip("!")
    try:
        rotation = int(rotation) % 360
        if rotation not in [0, 90, 180, 270]:
            abort(400, description="Invalid rotation")
    except:
        abort(400, description="Invalid rotation")

    # --- select best level ---
    # level = get_best_level(slide, dst_w, dst_h)
    # scale = slide.level_dimensions[0][0] / slide.level_dimensions[level][0]

    level = get_best_level(slide, w, h, dst_w, dst_h, prefer_no_upsample=True) 
    scale = slide.level_downsamples[level]

    try:
        # baca region dari slide
        region_img = slide.read_region(
            (int(x / scale), int(y / scale)),  # posisi
            level,                            # level pyramid
            (int(w / scale), int(h / scale))  # ukuran
        ).convert("RGB")

        # resize bila perlu
        if (dst_w, dst_h) != (w, h):
            region_img = region_img.resize((dst_w, dst_h), Image.Resampling.LANCZOS)

        # mirror / rotate / gray
        if is_mirrored:
            region_img = ImageOps.mirror(region_img)
        if rotation:
            region_img = region_img.rotate(-rotation, expand=True)
        if quality == "gray":
            region_img = region_img.convert("L")

    except Exception as e:
        abort(500, description=f"Tile read error: {e}")

    # --- format output ---
    format_map = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "tif": "TIFF"}
    fmt = format_map.get(format.lower())
    if fmt is None:
        abort(400, description="Unsupported format")

    buffer = io.BytesIO()
    region_img.save(buffer, format=fmt)
    buffer.seek(0)
    return send_file(buffer, mimetype=f"image/{format.lower()}")

# --- IIIF info.json Endpoint ---
@app.route("/iiif/<image_id>/info.json")
def info_json(image_id):
    path = get_slide_path(image_id)
    if not os.path.exists(path):
        abort(404, description="Slide not found")

    try:
        slide = OpenSlide(path)
    except Exception as e:
        abort(500, description=f"Failed to open slide: {e}")

    levels = slide.level_dimensions
    width, height = levels[0]
    scale_factors = [int(width / w) for (w, _) in levels]

    info = {
        "@context": "http://iiif.io/api/image/2/context.json",
        "@id": f"{request.host_url.rstrip('/')}/iiif/{image_id}",
        "@type": "iiif:Image",
        "protocol": "http://iiif.io/api/image",
        "width": width,
        "height": height,
        "tiles": [{
            "width": TILE_SIZE,
            "height": TILE_SIZE,
            "scaleFactors": scale_factors
        }],
        "sizes": [
            {"width": w, "height": h} for (w, h) in reversed(levels)
        ],
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

    return jsonify(info), 200
