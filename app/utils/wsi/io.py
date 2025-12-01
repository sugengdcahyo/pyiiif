import boto3


class S3RangeReader:

    def __init__(self, bucket: str, key: str,
                 aws_access_key_id: str, aws_secret_access_key: str,
                 region_name: str = "ap-southeast-1"):
        self.bucket = bucket
        self.key = key
        self.s3 = boto3.client(
            "s3",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        self._size = None

    @property
    def size(self):
        if self._size is None:
            head = self.s3.head_object(
                Bucket=self.bucket,
                Key=self.key
            )
            self._size = head["ContentLength"]

        return self._size

    def read(self, offset, length):
        end = min(offset + length - 1, self.size - 1)
        resp = self.s3.get_object(
            Bucket=self.bucket, Key=self.key,
            Range=f"bytes={offset}-{end}"
        )

        return resp["Body"].read()
