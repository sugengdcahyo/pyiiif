import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# base dir (project root)
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"

LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
load_dotenv(ENV_PATH)


class Config:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOG_DIR / "app.log"
    TILE_SIZE = int(os.getenv("TILE_SIZE", 512))

    BASE_DIR = BASE_DIR
    PROJECT_ROOT = PROJECT_ROOT
    SLIDE_PATH = Path(
        os.getenv("SLIDE_PATH", PROJECT_ROOT / "slides")
    ).resolve()
    
    VALID_EXTENSIONS = (
        '.svs', '.tif', '.tiff', 
        '.ndpi', '.vms', '.mrxs'
    )
    
    MAX_OUT_W = int(os.getenv("MAX_OUT_W", 8192))
    MAX_OUT_H = int(os.getenv("MAX_OUT_H", 8192))

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5050,http://localhost:8080"
        ).split(",")
        if origin.strip()
    ]

    AWS_SECRET_KEY_ID = os.getenv("AWS_SECRET_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION = os.getenv("AWS_REGION", "")
    S3_BUCKET = os.getenv("S3_BUCKET", "")
    S3_PREFIX = os.getenv("S3_SLIDE_PREFIX", "")

    # config backend enginee
    IIIF_BACKEND = os.getenv("IIIF_BACKEND", "openslide")

    # === MongoDB Cloud (Atlas) ===
    MONGO_USER = os.getenv("MONGO_USER")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
    MONGO_HOST = os.getenv("MONGO_HOST", "cluster0.mongodb.net")
    MONGO_DB = os.getenv("MONGO_DB", "iiif")
    MONGO_PARAMS = os.getenv("MONGO_PARAMS", "retryWrites=true&w=majority")

    @classmethod
    def mongo_uri(cls) -> str:
        """Build MongoDB Cloud connection URI"""
        return (
            f"mongodb+srv://{cls.MONGO_USER}:{cls.MONGO_PASSWORD}@"
            f"{cls.MONGO_HOST}/{cls.MONGO_DB}?{cls.MONGO_PARAMS}"
        )

    @classmethod
    def to_dict(cls) -> dict:
        result = {}

        for key, value in cls.__dict__.items():
            if not key.startswith("_"):
                # sanitize secret value
                if any(x in key for x in ["PASSWORD", "SECRET", "ACCESS_KEY"]):
                    result[key] = "***"
                else:
                    result[key] = value
        return result

# === Accessor ===
def get_config() -> Config:
    return Config()
