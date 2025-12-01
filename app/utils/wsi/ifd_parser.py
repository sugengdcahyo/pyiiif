# wsi/ifd_parser.py

import struct
from typing import Dict, Any, List, Optional

from app.utils.wsi.io import S3RangeReader

from .iiif_header import find_tiff_header


class IFDParser:
    """
    Low-level TIFF/SVS parser:
    - read header
    - read whole IFDs
    - SubIFDs + Next IFDs
    """

    def __init__(self, reader: S3RangeReader) -> None:
        self.reader = reader
        self.header_offset = None
        self.endian = "<"
        self.is_bigtiff = False
        self.offset_size = 4
        self.ifd_entry_size = 12
        self.ifds = []

    def _read(self, off, length):
        return self.reader.read(off, length)

    def _unpack(self, fmt, data):
        return struct.unpack(self.endian + fmt, data)

    def parse(self):
        """
        Main entry point: parse entire TIFF/WSI
        """
        self.header_offset = find_tiff_header(self.reader)
        if self.header_offset is None:
            raise ValueError("TIFF header not found!")

        hdr = self._read(self.header_offset, 16)
        sig = hdr[:2]

        # endian
        if sig == b"II": self.endian = "<"
        elif sig == b"MM": self.endian = ">"
        else:
            raise ValueError("Invalid TIFF byte order")

        # magic
        magic = self._unpack("H", hdr[2:4])[0]

        if magic == 42:
            self.is_bigtiff = False
            self.offset_size = 4
            self.ifd_entry_size = 12
            first_ifd = self._unpack("I", hdr[4:8])[0]
        elif magic == 43:
            self.is_bigtiff = True
            self.offset_size = 8
            self.ifd_entry_size = 20
            first_ifd = self._unpack("Q", hdr[8:16])[0]
        else:
            raise ValueError("Unknown TIFF magic value")

        start = self.header_offset + first_ifd

        visited = set()
        self.ifds = []

        def walk(off):
            if off in visited:
                return

            visited.add(off)

            ifd = self._parse_ifd(off)
            self.ifds.append(ifd)

            # Sub IFDs
            for s in ifd["sub_ifds"]:
                walk(s)

            # Next IFDs
            if ifd["next_ifd"]:
                walk(ifd["next_ifd"])

        walk(start)
        return self.ifds

    def _parse_ifd(self, off):
        count_len = 8 if self.is_bigtiff else 2
        count = self._unpack("Q" if self.is_bigtiff else "H", 
                             self._read(off, count_len))[0]

        table_len = count * self.ifd_entry_size
        table = self._read(off + count_len, table_len)

        tags = {}
        sub_ifds = []

        for i in range(count):
            b = i * self.ifd_entry_size
            if not self.is_bigtiff:
                tag, typ = self._unpack("HH", table[b:b+4])
                c = self._unpack("I", table[b+4:b+8])[0]
                val = self._unpack("I", table[b+8:b+12])[0]
            else:
                tag, typ = self._unpack("HH", table[b:b+4])
                c = self._unpack("Q", table[b+4:b+12])[0]
                val = self._unpack("Q", table[b+12:b+20])[0]

            tags[tag] = {
                "type": typ,
                "count": c,
                "value": val
            }

            if tag == 330:
                sub_offset = self.header_offset + val
                raw = self._read(sub_offset, c * self.offset_size)
                offs = []

                for j in range(c):
                    bs = raw[j*self.offset_size:(j+1)*self.offset_size]
                    o = self._unpack("I" if self.offset_size == 4 else "Q", bs)[0]
                    offs.append(self.header_offset + o)
                sub_ifds.extend(offs)

        # next IFD
        next_ptr_off = off + count_len + table_len
        next_sz = 8 if self.is_bigtiff else 4
        next_raw = self._read(next_ptr_off, next_sz)
        next_rel = self._unpack("Q" if self.is_bigtiff else "I", next_raw)[0]
        next_ifd = self.header_offset + next_rel if next_rel != 0 else None

        return {
            "offset": off,
            "num_entries": count,
            "tags": tags,
            "sub_ifds": sub_ifds,
            "next_ifd": next_ifd
        }
