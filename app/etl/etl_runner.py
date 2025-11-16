import json
import os
import boto3
from botocore.retries.adaptive import bucket

from app.config import Config
from app.utils.wsi.iiif import IIIFInfoBuilder, ZoomLevelBuilder
from app.utils.wsi.io import S3RangeReader
from app.utils.wsi.explorer import WSITagExplorer

from datetime import datetime


class WSIETLPipeline:

    def __init__(self, mongo_collection,
                 bucket: str, aws_access_key_id: str,
                 aws_secret_access_key: str, region: str) -> None:
        self.col = mongo_collection
        self.bucket = bucket
        self.region = region
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )

    def upload_json(self, key: str, data: dict):
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(data),
            ContentType="application/json"
        )
        print(f"[UPLOAD] {key}")

    def process_one(self, doc):
        s3_key = doc["key"]
        filename, _ = os.path.splitext(doc["file_name"])

        print(f"\n=== Processing {s3_key} ===")

        try:
            reader = S3RangeReader(
                bucket=self.bucket,
                key=s3_key,
                region_name=self.region,
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
            )

            explorer = WSITagExplorer(reader)

            iiif_builder = IIIFInfoBuilder(explorer)
            iiif_json = iiif_builder.build()

            zoom_builder = ZoomLevelBuilder()
            zoom_json = zoom_builder.build(info=iiif_json)

            ifds_json = explorer.build_ifds_json()

            # Upload to S3 
            self.upload_json(f"iiif/info/{filename}.info.json", iiif_json)
            self.upload_json(f"iiif/zoom/{filename}.zoom.json", zoom_json)
            self.upload_json(f"iiif/ifds/{filename}.ifds.json", ifds_json)

            # Returned summary for logging
            return {
                "file": filename,
                "info_size": len(json.dumps(iiif_json)),
                "zoom_size": len(json.dumps(zoom_json)),
                "ifds_size": len(json.dumps(ifds_json)),
                "timestamp": datetime.utcnow().isoformat(),
                "status": "success",
                "error": None
            }
        except Exception as e:
            return {
                "file": filename,
                "key": s3_key,
                "status": "error",
                "error": str(e)
            }

    def run(self, limit=None):
        docs = self.col.find()
        if limit:
            docs = docs.limit(limit)

        success = []
        error = []

        for doc in docs:
            res = self.process_one(doc)

            if res["status"] == "success":
                success.append(res)
            else:
                error.append(res)

        # save record log ETL 
        with open("etl_success.json", "w") as f:
            json.dump(success, f, indent=2)

        with open("etl_errors.json", "w") as f:
            json.dump(error, f, indent=2)

        print(f"\nETL FINISHED: {len(success)} success, {len(error)} error!")
