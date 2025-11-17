from collections import defaultdict
from functools import lru_cache
from flask import (
    Blueprint, request, abort
)
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.json_util import dumps
from collections import defaultdict

import boto3
import os


#--- load .env ---
load_dotenv()


prefixes = ["iiif/info/", "iiif/zoom/", "iiif/wsi/"]


#--- get credentials from env ---
aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
aws_region = os.getenv("AWS_REGION", "")
aws_s3_bucket = os.getenv("S3_BUCKET", "")
aws_s3_prefix = os.getenv("S3_SLIDE_PREFIX", "")

session = boto3.Session()

s3 = boto3.client(
    "s3", aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)

# =====================================================
# MongoDB Configuration
# =====================================================
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
collection = db[MONGO_COLLECTION]

bp = Blueprint("metadata", __name__)


def group_by_size(collection):
    """
    Kelompokkan file berdasarkan `size_range` dari MongoDB
    dan urutkan file di dalam tiap folder dari ukuran terkecil ke terbesar.
    """

    groups = defaultdict(list)

    cursor = collection.find({}, {
        "_id": 0,
        "file_name": 1,
        "file_ext": 1,
        "size_bytes": 1,
        "size_gb": 1,
        "size_range": 1,
        "last_modified": 1
    })

    for f in cursor:
        name_noext = os.path.splitext(f["file_name"])[0]
        ext = f.get("file_ext", "unknown")

        node = {
            "id": f"{ext}-{name_noext}",
            "value": name_noext,
            "name": name_noext.replace("_", " "),
            "type": ext,
            "iiif": f"/iiif/{f['file_name']}/info.json",
            "size_gb": round(f.get("size_gb", 0), 3),
            "size_bytes": f.get("size_bytes", 0),
            "last_modified": f.get("last_modified")
        }

        category = f.get("size_range", "UNKNOWN")
        groups[category].append(node)

    # Sortir tiap kategori berdasarkan size_bytes ASC
    result = []
    for category, files in groups.items():

        files_sorted = sorted(files, key=lambda x: x["size_bytes"])

        result.append({
            "id": category,
            "name": category,
            "expanded": True,
            "folder": True,
            "children": files_sorted
        })

    return result


def group_by_type(data):
    """
    Kategorikan IIIF/WSI files berdasarkan tipe ekstensi file (.svs, .ndpi, .tiff, dll)
    dan formatkan hasilnya ke Carbon Tree style.
    """
    pipeline = [
        {"$group": {
            "_id": "$file_ext",
            "files": {
                "$push": {
                    "file_name": "$file_name",
                    "size_gb": "$size_gb",
                    "last_modified": "$last_modified",
                    "size_bytes": "$size_bytes"
                }
            },
            "total_files": {"$sum": 1},
            "total_size_gb": {"$sum": "$size_gb"}
        }},
        {"$sort": {"_id": 1}}
    ]

    groups = []
    for group in collection.aggregate(pipeline):
        ext = group["_id"] or "unknown"
        files = []
        for f in group["files"]:
            name_noext = os.path.splitext(f["file_name"])[0]
            files.append({
                "id": f"{ext}-{name_noext}",
                "value": name_noext,
                "name": name_noext.replace("_", " "),
                "type": ext,
                "iiif": f"/iiif/{f['file_name']}/info.json",
                "size_gb": round(f.get("size_gb", 0), 3),
                "last_modified": f.get("last_modified")
            })

        groups.append({
            "id": ext,
            "name": ext.upper(),
            "total_files": group["total_files"],
            "total_size_gb": round(group["total_size_gb"], 3),
            "expanded": True,
            "folder": True,
            "children": sorted(files, key=lambda x: x["size_gb"], reverse=True)
        })

    return groups


# =====================================================
# Endpoint utama
# =====================================================
@lru_cache(maxsize=512)
@bp.get("/menu")
def get_menu():
    """
    Endpoint untuk mengambil metadata dari MongoDB.
    Bisa digrouping berdasarkan `?group_by=type` atau `?group_by=size`.
    """
    group_by = request.args.get("group_by", None)

    if group_by == "type":
        data = group_by_type(collection)
    elif group_by == "size":
        data = group_by_size(collection)
    else:
        # default: tampilkan semua data granular
        data = list(collection.find({}, {"_id": 0}).limit(100))  # limit untuk keamanan

    return data


@bp.get("/zoom-level/<slide_id>")
def get_zoom_level(slide_id):
    return {
        "data": slide_id
    }

