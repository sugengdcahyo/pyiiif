from PIL import Image, ImageOps
from ..services.slide import open_slide
from ..utils.image import save_to_bytes, pick_level_for_target, level_dims


def get_info(identifier, cfg, request):
    path = cfg["SLIDE_PATH"]
    slide = open_slide(f"{path}/{identifier}")

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
    return data


def get_tile(identifier, region, size, rotation, quality, fmt, cfg):
    """
    Ambil tile pakai OpenSlide backend (lokal storage).
    """
    if not identifier.lower().endswith(cfg["VALID_EXTENSIONS"]):
        raise ValueError("Unsupported file extension")

    path = f"{cfg['SLIDE_PATH']}/{identifier}"
    slide = open_slide(path)
    full_w, full_h = slide.dimensions

    # --- parse region ---
    if region == "full":
        x, y, w, h = 0, 0, full_w, full_h
    else:
        try:
            x, y, w, h = map(int, region.split(","))
            if w <= 0 or h <= 0:
                raise ValueError("Invalid region size")
        except Exception:
            raise ValueError("Invalid region")
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
                raise ValueError("Invalid size pct")
            return (
                max(1, int(round(w * pct / 100))),
                max(1, int(round(h * pct / 100)))
            )

        if sz.endswith(","):
            dst_w = int(sz[:-1])
            if dst_w <= 0:
                raise ValueError("Invalid size")
            return (dst_w, max(1, int(round(h * (dst_w / w)))))

        if sz.startswith(","):
            dst_h = int(sz[1:])
            if dst_h <= 0:
                raise ValueError("Invalid size")
            return (max(1, int(round(w * (dst_h / h)))), dst_h)

        dst_w, dst_h = map(int, sz.split(","))
        if dst_w <= 0 or dst_h <= 0:
            raise ValueError("Invalid size")
        return (dst_w, dst_h)

    dst_w, dst_h = parse_size(size, w, h)
    if dst_w > cfg["MAX_OUT_W"] or dst_h > cfg["MAX_OUT_H"]:
        raise ValueError("Output size too large")

    # --- rotation & quality ---
    is_mirror = rotation.startswith("!")
    rotation = rotation.lstrip("!")
    try:
        rotation = int(rotation) % 360
        if rotation not in (0, 90, 180, 270):
            raise ValueError("Invalid rotation")
    except Exception:
        raise ValueError("Invalid rotation")

    if quality not in ("default", "gray"):
        raise ValueError("Unsupported quality")

    # --- pilih level terbaik ---
    lvl = pick_level_for_target(slide, w, h, dst_w, dst_h)
    rw, rh, scale = level_dims(slide, lvl, w, h)

    rx, ry = int(x), int(y)     # koordinat selalu level-0
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

    fmt_map = {
        "jpg": "JPEG",
        "jpeg": "JPEG",
        "png": "PNG",
        "tif": "TIFF"
    }
    pil_fmt = fmt_map.get(fmt.lower())
    if not pil_fmt:
        raise ValueError("Unsupported format")

    return save_to_bytes(img, pil_fmt)