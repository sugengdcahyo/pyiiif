from dataclasses import dataclass
from typing import Optional, Union
from PIL import Image
import io


@dataclass(frozen=True)
class JpegOpts:
    quality: int = 80
    optimize: bool = True
    progressive: bool = True
    # 0/1/2 atau "4:4:4"/"4:2:2"/"4:2:0"; None = biarkan default Pillow
    subsampling: Optional[Union[int, str]] = None


JPEG_DEFAULT = JpegOpts()
PNG_OPTS = dict(optimize=True)


def _normalize_subsampling(subs: Optional[Union[int, str]]) -> Optional[int | str]:
    """Kembalikan nilai subsampling yang valid untuk Pillow atau None."""
    if subs is None:
        return None
    if subs in (0, 1, 2):
        return subs
    if isinstance(subs, str):
        s = subs.strip()
        if s in ("4:4:4", "444"):
            return 0
        if s in ("4:2:2", "422"):
            return 1
        if s in ("4:2:0", "420"):
            return 2
    # invalid → jangan kirim ke Pillow
    return None


def save_to_bytes(img: Image.Image, fmt: str, jpeg_opts: JpegOpts = JPEG_DEFAULT) -> bytes:
    """Simpan PIL Image ke bytes dengan opsi aman untuk tiap format."""
    fmt = fmt.upper()
    buf = io.BytesIO()

    if fmt == "JPEG":
        # JPEG hanya menerima RGB/L
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # susun kwargs secara defensif
        q = jpeg_opts.quality
        try:
            q = int(q)
        except Exception:
            q = 80
        q = max(1, min(95, q))  # clamp

        opts = {"quality": q}
        if jpeg_opts.optimize:
            opts["optimize"] = True
        if jpeg_opts.progressive and img.mode == "RGB":
            opts["progressive"] = True

        subs = _normalize_subsampling(jpeg_opts.subsampling)
        if subs is not None:
            opts["subsampling"] = subs  # hanya kirim jika valid

        img.save(buf, format="JPEG", **opts)

    elif fmt == "PNG":
        img.save(buf, format="PNG", **PNG_OPTS)

    elif fmt == "TIFF":
        img.save(buf, format="TIFF")

    else:
        img.save(buf, format=fmt)

    return buf.getvalue()


def pick_level_for_target(slide, w, h, dst_w, dst_h) -> int:
    """Pilih level pyramid yang paling mendekati ukuran target (minim resize)."""
    downs = list(slide.level_downsamples)

    def err(i: int) -> float:
        sw, sh = w / downs[i], h / downs[i]
        return max(abs(sw - dst_w), abs(sh - dst_h))

    return min(range(len(downs)), key=err)


def level_dims(slide, level: int, w: int, h: int):
    """Hitung (rw, rh, scale) pada level terpilih; x,y tetap level-0 di caller."""
    scale = slide.level_downsamples[level]
    rw = max(1, int(round(w / scale)))
    rh = max(1, int(round(h / scale)))
    return rw, rh, scale
