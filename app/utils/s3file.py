import boto3
import io
from openslide import OpenSlide 


class S3FileAdapter(io.RawIOBase):

    def __init__(self, bucket, key, region="ap-southeast-3"):
        self.s3 = boto3.client("s3", region_name=region)
        self.bucket = bucket
        self.key = key 
        
        head = self.s3.head_object(Bucket=bucket, Key=key)
        self.size = head["ContentLength"]
        self.pos = 0

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        
        return self.pos

    def tell(self):
        return self.pos

    def read(self, size=-1):
        if size == -1:
            end = self.size - 1
        else:
            end = min(self.pos + size -1, self.size - 1)

        resp = self.s3.get_object(
            Bucket=self.bucket,
            Key=self.key,
            Range=f"bytes={self.pos}-{end}"
        )
        data = resp["Body"].read()
        self.pos += len(data)
        return data
