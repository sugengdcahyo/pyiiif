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


s3 = boto3.client(
    "s3", aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=aws_region
)


def list_s3_objects(bucket, prefix):
    """List objects dari S3 dengan prefix tertentu"""
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    results = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if key.strip("/") == prefix.strip("/"):
                continue

            name = key.split("/")[-1]
            ext = name.split(".")[-1].lower() if "." in name else "unknown"
            size = obj.get("Size", 0)

            results.append({
                "key": key,
                "name": name,
                "type": ext,
                "size": size
            })
    return results


def build_data_store():
    data_store = {}
    for pref in prefixes:
        objects = list_s3_objects(bucket_name, pref)
        data_store[pref] = objects
    return data_store


def copy_to_wsi(bucket, source_key):
    """Copy 1 file ke prefix iiif/wsi/"""
    filename = os.path.basename(source_key)  # ambil nama file saja
    target_key = f"iiif/wsi/{filename}"

    s3.copy_object(
        Bucket=bucket,
        CopySource={"Bucket": bucket, "Key": source_key},
        Key=target_key
    )
    print(f"[!] Copied {source_key} -> {target_key}")


def bulk_copy(bucket, prefixes):
    """Copy semua file dari prefix list ke iiif/wsi/"""
    for pref in prefixes:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=pref):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # skip folder marker
                if key.endswith("/"):
                    continue
                copy_to_wsi(bucket, key)


if __name__ == "__main__":
    data = build_data_store()
    key = "iiif/metadata/iiif_data.json"

    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json"
    )

    print(f"[!] Data store berhasil disimpan ke {key}")

