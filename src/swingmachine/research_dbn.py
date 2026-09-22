"""Offline streaming Zstandard/DBN framing, adapted from Trading212.

Upstream: t212-ier-edge-003a at eddd6d892326c0a3b87290d18bf31c6518621429,
src/t212_ai_bot/research/databento_dbn_read.py, SHA-256
b185c2c78ef9cae46cfbda81004d806eacf396edd364f4760f1ad740400f85bd.
Only byte mechanics are reused. Swing owns strict metadata/record validation,
source confinement, date guards and integrity checks. No Trading212 imports.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import struct
from collections.abc import Iterable, Iterator

DBN_METADATA_PREFIX_LENGTH = 112


class DBNReadError(ValueError):
    """Structural byte-stream failure with no raw record output."""


class _ZstdInBuffer(ctypes.Structure):
    _fields_ = [
        ("src", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
        ("pos", ctypes.c_size_t),
    ]


class _ZstdOutBuffer(ctypes.Structure):
    _fields_ = [
        ("dst", ctypes.c_void_p),
        ("size", ctypes.c_size_t),
        ("pos", ctypes.c_size_t),
    ]


def _zstd_library() -> ctypes.CDLL:
    name = ctypes.util.find_library("zstd") or "libzstd.so.1"
    library = ctypes.CDLL(name)
    library.ZSTD_createDStream.argtypes = []
    library.ZSTD_createDStream.restype = ctypes.c_void_p
    library.ZSTD_initDStream.argtypes = [ctypes.c_void_p]
    library.ZSTD_initDStream.restype = ctypes.c_size_t
    library.ZSTD_freeDStream.argtypes = [ctypes.c_void_p]
    library.ZSTD_freeDStream.restype = ctypes.c_size_t
    library.ZSTD_decompressStream.restype = ctypes.c_size_t
    library.ZSTD_decompressStream.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_ZstdOutBuffer),
        ctypes.POINTER(_ZstdInBuffer),
    ]
    library.ZSTD_isError.argtypes = [ctypes.c_size_t]
    library.ZSTD_isError.restype = ctypes.c_uint
    library.ZSTD_getErrorName.argtypes = [ctypes.c_size_t]
    library.ZSTD_getErrorName.restype = ctypes.c_char_p
    return library


def iter_zstd_chunks(chunks: Iterable[bytes], chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    if type(chunk_size) is not int or chunk_size <= 0:
        raise DBNReadError("invalid_decode_chunk_size")
    library = _zstd_library()
    stream = library.ZSTD_createDStream()
    if not stream:
        raise DBNReadError("zstd_stream_creation_failed")
    try:
        result = library.ZSTD_initDStream(stream)
        if library.ZSTD_isError(result):
            raise DBNReadError("zstd_stream_initialization_failed")
        last_result = 0
        for compressed in chunks:
            input_buffer = ctypes.create_string_buffer(compressed)
            incoming = _ZstdInBuffer(ctypes.cast(input_buffer, ctypes.c_void_p), len(compressed), 0)
            while incoming.pos < incoming.size:
                output_buffer = ctypes.create_string_buffer(chunk_size)
                outgoing = _ZstdOutBuffer(
                    ctypes.cast(output_buffer, ctypes.c_void_p), chunk_size, 0
                )
                previous_pos = incoming.pos
                last_result = library.ZSTD_decompressStream(
                    stream, ctypes.byref(outgoing), ctypes.byref(incoming)
                )
                if library.ZSTD_isError(last_result):
                    name = library.ZSTD_getErrorName(last_result).decode("ascii", "replace")
                    raise DBNReadError(f"zstd_decompression_failed:{name}")
                if outgoing.pos:
                    yield output_buffer.raw[: outgoing.pos]
                if not outgoing.pos and incoming.pos == previous_pos:
                    raise DBNReadError("zstd_decoder_made_no_progress")
            # A full output buffer can leave decoded bytes pending after all
            # compressed input was consumed. Drain those bytes before EOF checks.
            while compressed and last_result and outgoing.pos == chunk_size:
                outgoing.pos = 0
                last_result = library.ZSTD_decompressStream(
                    stream, ctypes.byref(outgoing), ctypes.byref(incoming)
                )
                if library.ZSTD_isError(last_result):
                    raise DBNReadError("zstd_decompression_failed_during_drain")
                if outgoing.pos:
                    yield output_buffer.raw[: outgoing.pos]
        if last_result != 0:
            raise DBNReadError("truncated_zstd_stream")
    finally:
        library.ZSTD_freeDStream(stream)


def iter_dbn_blocks(chunks: Iterable[bytes]) -> Iterator[tuple[str, bytes]]:
    """Frame every record without filtering, repair or semantic reinterpretation.

    Emit one metadata block followed by all records. Unsupported record types
    remain visible for the structural caller to reject and account for.
    """
    buffer = bytearray()
    metadata_done = False
    metadata_size = None
    for chunk in chunks:
        buffer.extend(chunk)
        if not metadata_done:
            if len(buffer) < 8:
                continue
            if buffer[:3] != b"DBN":
                raise DBNReadError("invalid_dbn_magic")
            if metadata_size is None:
                metadata_size = struct.unpack_from("<I", buffer, 4)[0] + 8
                if not DBN_METADATA_PREFIX_LENGTH <= metadata_size <= 1024 * 1024:
                    raise DBNReadError("invalid_dbn_metadata_size")
            if len(buffer) < metadata_size:
                continue
            yield "metadata", bytes(buffer[:metadata_size])
            del buffer[:metadata_size]
            metadata_done = True
        offset = 0
        while offset < len(buffer):
            size = buffer[offset] * 4
            if size < 16:
                raise DBNReadError("invalid_dbn_record_length")
            if len(buffer) - offset < size:
                break
            yield "record", bytes(buffer[offset : offset + size])
            offset += size
        if offset:
            del buffer[:offset]
    if not metadata_done or buffer:
        raise DBNReadError("truncated_dbn_payload")
