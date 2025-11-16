import json

def load_json_from_s3(s3, bucket, key):
    obj = s3.get_object(
        Bucket=bucket, Key=key
    )
    return json.loads(obj["Body"].readA().decode("utf-8"))
