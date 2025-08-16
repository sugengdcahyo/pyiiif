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

def parse_region(region_str, full_width, full_height):
    if region_str == "full":
        return 0, 0, full_width, full_height
    try:
        return tuple(map(int, region_str.split(',')))
    except:
        return None

def parse_size(size_str, w_orig, h_orig):
    try:
        if size_str == "full":
            return w_orig, h_orig
        elif size_str.startswith("pct:"):
            pct = float(size_str.split(":")[1]) / 100.0
            return int(w_orig * pct), int(h_orig * pct)
        elif size_str.endswith(","):
            width = int(size_str[:-1])
            height = int(h_orig * (width / w_orig))
            return width, height
        elif size_str.startswith(","):
            height = int(size_str[1:])
            width = int(w_orig * (height / h_orig))
            return width, height
        elif "," in size_str:
            return tuple(map(int, size_str.split(",")))
    except:
        return None

def get_best_level(slide, target_w, target_h):
    for level in range(slide.level_count):
        w, h = slide.level_dimensions[level]
        if target_w <= w and target_h <= h:
            return level
    return slide.level_count - 1

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
    x, y, w, h = parse_region(region, full_width, full_height) or (0, 0, full_width, full_height)
    dst_w, dst_h = parse_size(size, w, h) or (w, h)

    is_mirrored = rotation.startswith("!")
    rotation = rotation.lstrip("!")
    try:
        rotation = int(rotation) % 360
        if rotation not in [0, 90, 180, 270]:
            abort(400, description="Invalid rotation")
    except:
        abort(400, description="Invalid rotation")

    level = get_best_level(slide, dst_w, dst_h)
    scale = slide.level_dimensions[0][0] / slide.level_dimensions[level][0]

    try:
        region_img = slide.read_region(
            (int(x / scale), int(y / scale)),
            level,
            (int(w / scale), int(h / scale))
        ).convert("RGB")

        if (dst_w, dst_h) != (w, h):
            region_img = region_img.resize((dst_w, dst_h), Image.Resampling.LANCZOS)
        if is_mirrored:
            region_img = ImageOps.mirror(region_img)
        if rotation:
            region_img = region_img.rotate(-rotation, expand=True)
        if quality == "gray":
            region_img = region_img.convert("L")
    except Exception as e:
        abort(500, description=f"Tile read error: {e}")

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
