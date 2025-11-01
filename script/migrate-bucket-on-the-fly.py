import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Konfigurasi profil dan prefix ---
SOURCE_PROFILE = "default"
DEST_PROFILE = "mekarsalab"
SOURCE_BUCKET = "dev-neurabot"
DEST_BUCKET = "mekarsa"
PREFIX = "iiif/wsi/"  # folder key yang ingin disalin
MAX_WORKERS = 4       # sesuaikan dengan CPU/network kamu

# --- Inisialisasi session ---
source_session = boto3.Session(profile_name=SOURCE_PROFILE)
dest_session = boto3.Session(profile_name=DEST_PROFILE)
source_s3 = source_session.client("s3")
dest_s3 = dest_session.client("s3")

def copy_single_object(key: str):
    """Copy satu object dari source ke destination (server-side streaming)."""
    try:
        # stream langsung dari S3 ke S3 (tanpa download)
        body = source_s3.get_object(Bucket=SOURCE_BUCKET, Key=key)["Body"]
        dest_s3.upload_fileobj(
            Fileobj=body,
            Bucket=DEST_BUCKET,
            Key=key,
            ExtraArgs={"ACL": "bucket-owner-full-control"},
        )
        return f"✅ {key}"
    except Exception as e:
        return f"❌ {key} - {e}"

def list_objects(bucket, prefix):
    """List semua objek dalam prefix."""
    paginator = source_s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            yield obj["Key"]

def main():
    print(f"🚀 Starting cross-account copy from {SOURCE_BUCKET}/{PREFIX} to {DEST_BUCKET}/{PREFIX}\n")

    keys = list(list_objects(SOURCE_BUCKET, PREFIX))
    print(f"📦 Found {len(keys)} files to transfer.\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(copy_single_object, key) for key in keys]

        for future in as_completed(futures):
            print(future.result())

    print("\n✅ All files transferred successfully.")

if __name__ == "__main__":
    main()

