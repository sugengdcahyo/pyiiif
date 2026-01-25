import os
import io
import json
import base64
from typing import Dict
import boto3
import tifffile
from PIL import Image
from dotenv import load_dotenv
from typing import Any, Dict

load_dotenv()


aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
aws_region = os.environ.get("AWS_REGION", "")
s3_bucket = os.environ.get("AWS_BUCKET", "")


# --- S3 client ---
s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=s3_bucket
)

BUCKET = s3_bucket


# 1. Upload file asli (.svs / .tiff)
def upload_file_svs_tiff(local_path, slide_id):
    key = f"{slide_id}/{os.path.basename(local_path)}"
    s3.upload_file(local_path, BUCKET, key)
    print(f"Uploaded original file to s3://{BUCKET}/{key}")


# 2. Generate info.json (IIIF standard)
def generate_info_json(local_path, slide_id):
    with tifffile.TiffFile(local_path) as tif:
        page = tif.pages[0]
        width, height = page.imagewidth, page.imagelength
        tile_w = getattr(page, "tilewidth", 512)
        # tile_h = getattr(page, "tilelength", 512)

        info = {
            "@context": "http://iiif.io/api/image/2/context.json",
            "@id": f"https://{BUCKET}.s3.amazonaws.com/{slide_id}",
            "width": width,
            "height": height,
            "tiles": [{
                "width": tile_w,
                "scaleFactors": [2**i for i in range(len(tif.pages))]
            }],
            "profile": ["http://iiif.io/api/image/2/level2.json"]
        }

    key = f"{slide_id}/info.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(info, indent=2), ContentType="application/json")
    print(f"Uploaded info.json to s3://{BUCKET}/{key}")


# 3. Generate zoomlevel.json (offset + length + jpegtables)
def generate_zoomlevel_json(local_path, slide_id):
    metadata: Dict[str, Any] = {}
    metadata["levels"] = []

    with tifffile.TiffFile(local_path) as tif:
        jpegtables = tif.pages[0].jpegtables
        if jpegtables:
            metadata["jpegtables"] = base64.b64encode(jpegtables).decode("utf-8")
        else:
            metadata["jpegtables"] = None

        for level, page in enumerate(tif.pages):
            offsets = page.dataoffsets.tolist()
            lengths = page.databytecounts.tolist()
            level_info = {
                "level": level,
                "width": page.imagewidth,
                "height": page.imagelength,
                "tile_width": getattr(page, "tilewidth", None),
                "tile_height": getattr(page, "tilelength", None),
                "tiles": [{"offset": o, "length": l} for o, l in zip(offsets, lengths)]
            }
            metadata["levels"].append(level_info)

    key = f"{slide_id}/zoomlevel.json"
    s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(metadata, indent=2), ContentType="application/json")
    print(f"Uploaded zoomlevel.json to s3://{BUCKET}/{key}")



# --- Contoh pemakaian ---
local_file = "Philips-1.tiff"
slide_id = "Philips-1"

upload_file_svs_tiff(local_file, slide_id)
generate_info_json(local_file, slide_id)
generate_zoomlevel_json(local_file, slide_id)
# generate_thumbnail(local_file, slide_id)
