import os
from pathlib import Path


class Config:
    TILE_SIZE = int(os.getenv("TILE_SIZE", 512))

    # base dir (project root)
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent

    # slide path configurable via .env
    SLIDE_PATH = Path(
        os.getenv("SLIDE_PATH", PROJECT_ROOT / "slides")
    ).resolve()
    
    VALID_EXTENSIONS = ('.svs', '.tif', '.tiff', '.ndpi', '.vms', '.mrxs')
    
    MAX_OUT_W = int(os.getenv("MAX_OUT_W", 8192))
    MAX_OUT_H = int(os.getenv("MAX_OUT_H", 8192))
    
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:8080,http://0.0.0.0:8080"
    ).split(",")


def get_config() -> Config:
    return Config()
