from collections import defaultdict
from functools import lru_cache
from flask import (
    Blueprint, request, abort
)

import json
import boto3
from dotenv import load_dotenv

import os


#--- load .env ---
load_dotenv()


bucket_name = "dev-neurabot"
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

bp = Blueprint("metadata", __name__)


def group_by_size(data):
    """
    Kategorikan iiif/wsi files berdasarkan size → Carbon Tree format
    """
    groups = {"small": [], "medium": [], "large": []}

    for f in data.get("iiif/wsi/", []):
        size = f["size"]
        name_noext = os.path.splitext(f["name"])[0]

        node = {
            "id": f"{f['type']}-{name_noext}",
            "value": name_noext,
            "name": name_noext.replace("_", " "),
            "iiif": f"/iiif/{f['name']}/info.json"
        }

        if size < 100 * 1024 * 1024:           # < 100MB
            groups["small"].append(node)
        elif size < 1024 * 1024 * 1024:        # < 1GB
            groups["medium"].append(node)
        else:
            groups["large"].append(node)

    tree = []
    for cat, children in groups.items():
        tree.append({
            "id": cat,
            "value": cat.capitalize(),
            "name": cat.capitalize(),
            "folder": True,
            "expanded": True,
            "children": children
        })

    return tree


def group_by_type(data):
    """
    Kategorikan iiif/wsi files berdasarkan ekstensi → Carbon Tree format
    """
    grouped = defaultdict(list)

    for f in data.get("iiif/wsi/", []):
        ftype = f.get("type", "unknown").lower()
        name_noext = os.path.splitext(f["name"])[0]

        node = {
            "id": f"{ftype}-{name_noext}",
            "value": name_noext,
            "name": name_noext.replace("_", " "),
            "iiif": f"/iiif/{f['name']}/info.json"
        }
        grouped[ftype].append(node)

    tree = []
    for ftype, children in grouped.items():
        tree.append({
            "id": ftype,
            "value": f"{ftype.upper()} Samples",
            "name": f"{ftype.upper()} Samples",
            "folder": True,
            "expanded": True,
            "children": children
        })

    return tree


@lru_cache(maxsize=512)
@bp.get("/menu")
def get_menu():
    key = "iiif/metadata/iiif_data.json"
    obj = s3.get_object(
        Bucket=bucket_name,
        Key=key
    )

    body = obj["Body"].read().decode("utf-8")
    data = json.loads(body)

    group_by = request.args.get("group_by", None)

    if group_by == "type":
        data = group_by_type(data)
    elif group_by == "size":
        data = group_by_size(data)

    return data


@bp.get("/zoom-level/<slide_id>")
def get_zoom_level(slide_id):
    return {
        "data": slide_id
    }

