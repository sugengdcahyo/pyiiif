from os import wait
from .io import S3RangeReader

def find_tiff_header(reader: S3RangeReader, scan_len=65536):
    """
    Scan header TIFF/BigTIFF
    """
    buf = reader.read(0, scan_len)

    patterns = [
        b"II\x2A\x00",                 # TIFF little endian
        b"MM\x00\x2A",                 # TIFF big endian
        b"II\x2B\x00\x08\x00\x00\x00", # BigTIFF little endian
    ]

    for p in patterns:
        i = buf.find(p)
        if i != -1:
            return i

    return None
