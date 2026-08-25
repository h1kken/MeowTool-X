import typing as t
import collections.abc as cabc

import mmap


class ReadableBinaryStream(t.Protocol):
    def read(self, size: int = -1, /) -> bytes: ...


class Bytes:
    @staticmethod
    def iter_lines(data: bytes | mmap.mmap) -> cabc.Iterator[bytes]:
        start = 0
        data_len = len(data)
        
        while start < data_len:
            end = data.find(b'\n', start)
            
            if end == -1:
                line = data[start:data_len]
                start = data_len
            else:
                line = data[start:end]
                start = end + 1
                
            if line.endswith(b'\r'):
                line = line[:-1]
                
            yield line
