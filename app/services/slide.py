import functools
from openslide import OpenSlide


@functools.lru_cache(maxsize=32)
def open_slide(path: str) -> OpenSlide:
    return OpenSlide(path)
