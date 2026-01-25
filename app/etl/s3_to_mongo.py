import os
import pandas as pd
from datetime import datetime, timezone
import boto3
from pymongo import MongoClient


class IIIFFileCatalogGranular:
    def __init__(self,
                 aws_access_key_id: str,
                 aws_secret_access_key: str,
                 region_name: str = "ap-southeast-1",
                 bucket_name: str = "mekarsa",
                 prefix: str = "raw/",
                 mongo_uri: str = None,
                 mongo_db: str = "iiif_metadata",
                 mongo_collection: str = "file_granular"):

        # --- AWS Config ---
        self.s3 = boto3.client(
            "s3",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        self.bucket = bucket_name
        self.prefix = prefix

        # --- Mongo Config ---
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.mongo_collection = mongo_collection


    # =======================================================
    # 1️⃣ Fetch semua object dari S3
    # =======================================================
    def fetch_s3_objects(self):
        paginator = self.s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(
            Bucket=self.bucket, 
            Prefix=self.prefix
        )

        objects = []
        for page in pages:
            for obj in page.get("Contents", []):
                objects.append({
                    "key": obj["Key"],
                    "size_bytes": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                })
        print(f" {len(objects)} objek ditemukan di s3://{self.bucket}/{self.prefix}")
        return objects


    # =======================================================
    # 2️⃣ Transform ke DataFrame granular
    # =======================================================
    def transform(self, objects):
        if not objects:
            print("⚠️ Tidak ada objek ditemukan.")
            return pd.DataFrame()

        df = pd.DataFrame(objects)
        df["file_name"] = df["key"].apply(lambda x: os.path.basename(x))
        df["file_ext"] = df["file_name"].apply(lambda x: os.path.splitext(x)[1].replace(".", "").lower())
        df["size_mb"] = (df["size_bytes"] / 1024 / 1024).round(2)
        df["size_gb"] = (df["size_bytes"] / 1024 / 1024 / 1024).round(2)

        # Buat kategori ukuran file
        df["size_range"] = pd.cut(
            df["size_mb"],
            bins=[0, 100, 500, 1000, 5000, 10000, float("inf")],
            labels=["<100MB", "100-500MB", "500MB-1GB", "1-5GB", "5-10GB", ">10GB"]
        )

        df["generated_at"] = datetime.now(timezone.utc).isoformat()
        return df


    # =======================================================
    # 3️⃣ Load granular ke MongoDB
    # =======================================================
    def load_to_mongo(self, df):
        if df.empty:
            print("⚠️ Data kosong, tidak disimpan.")
            return

        if not self.mongo_uri:
            print("⚠️ MongoDB URI belum diatur.")
            return

        client = MongoClient(self.mongo_uri)
        col = client[self.mongo_db][self.mongo_collection]
        col.delete_many({})  # bersihkan koleksi lama (optional)
        col.insert_many(df.to_dict(orient="records"))

        print(f"✅ {len(df)} metadata file berhasil disimpan ke MongoDB ({self.mongo_db}.{self.mongo_collection})")


    # =======================================================
    # 4️⃣ Flush semua koleksi dalam database MongoDB
    # =======================================================
    def flush_all_collections(self):
        if not self.mongo_uri:
            print("⚠️ MongoDB URI belum diatur.")
            return

        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]

        collections = db.list_collection_names()
        if not collections:
            print(f"ℹ️ Tidak ada koleksi di database '{self.mongo_db}'.")
            return

        for coll in collections:
            result = db[coll].delete_many({})
            print(f"🗑️ Koleksi '{coll}' dihapus {result.deleted_count} dokumen.")

        print(f"✅ Semua koleksi dalam database '{self.mongo_db}' sudah di-flush.")


    # =======================================================
    # 🔁 Pipeline utama
    # =======================================================
    def run(self):
        objects = self.fetch_s3_objects()
        df = self.transform(objects)
        self.load_to_mongo(df)
        return df

