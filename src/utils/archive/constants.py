from .types import ArchiveKind


# Extensions
ARCHIVE_ZIP_CONTAINER_EXTENSIONS = ('.zip', '.docx', '.xlsx', '.pptx', '.docm', '.xlsm', '.pptm', '.dotx', '.dotm', '.xltx', '.xltm', '.odt', '.ods', '.odp', '.odg', '.odf', '.epub', '.jar', '.war', '.ear', '.apk', '.xpi', '.ipa', '.vsix', '.nupkg', '.xps', '.appx', '.msix', '.whl', '.egg', '.cbz',)
ARCHIVE_TAR_EXTENSIONS = ('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz',)
ARCHIVE_7Z_EXTENSIONS = ('.7z', '.cb7',)
ARCHIVE_RAR_EXTENSIONS = ('.rar', '.cbr',)
ARCHIVE_GZIP_EXTENSIONS = ('.gz',)
ARCHIVE_BZIP2_EXTENSIONS = ('.bz2',)
ARCHIVE_XZ_EXTENSIONS = ('.xz', '.lzma', '.tar.lzma', '.tlzma',)
ARCHIVE_ZST_EXTENSIONS = ('.zst', '.tar.zst', '.tzst',)
ARCHIVE_LZ4_EXTENSIONS = ('.lz4', '.tar.lz4', '.tlz4',)

ARCHIVE_EXTENSION_GROUPS: tuple[tuple[ArchiveKind, tuple[str, ...]], ...] = (
    ('tar', ARCHIVE_TAR_EXTENSIONS),
    ('zip', ARCHIVE_ZIP_CONTAINER_EXTENSIONS),
    ('7z', ARCHIVE_7Z_EXTENSIONS),
    ('rar', ARCHIVE_RAR_EXTENSIONS),
    ('gz', ARCHIVE_GZIP_EXTENSIONS),
    ('bz2', ARCHIVE_BZIP2_EXTENSIONS),
    ('xz', ARCHIVE_XZ_EXTENSIONS),
    ('zst', ARCHIVE_ZST_EXTENSIONS),
    ('lz4', ARCHIVE_LZ4_EXTENSIONS),
)

ARCHIVE_EXTENSIONS = tuple(
    sorted(
        (
            extension
            for _kind, extensions in ARCHIVE_EXTENSION_GROUPS
            for extension in extensions
        ),
        key=len,
        reverse=True
    )
)

# Signatures
ARCHIVE_ZIP_SIGNATURES = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')
ARCHIVE_7Z_SIGNATURE = b'7z\xBC\xAF\x27\x1C'
ARCHIVE_RAR4_SIGNATURE = b'Rar!\x1A\x07\x00'
ARCHIVE_RAR5_SIGNATURE = b'Rar!\x1A\x07\x01\x00'
ARCHIVE_GZIP_SIGNATURE = b'\x1f\x8b'
ARCHIVE_BZIP2_SIGNATURE = b'BZh'
ARCHIVE_XZ_SIGNATURE = b'\xfd7zXZ\x00'
ARCHIVE_ZSTD_SIGNATURE = b'\x28\xB5\x2F\xFD'
ARCHIVE_LZ4_SIGNATURES = (b'\x04\x22\x4D\x18', b'\x50\x2A\x4D\x18')

ARCHIVE_SIGNATURE_GROUPS: tuple[tuple[ArchiveKind, tuple[bytes, ...]], ...] = (
    ('zip', ARCHIVE_ZIP_SIGNATURES),
    ('7z', (ARCHIVE_7Z_SIGNATURE,)),
    ('rar', (ARCHIVE_RAR4_SIGNATURE, ARCHIVE_RAR5_SIGNATURE)),
    ('gz', (ARCHIVE_GZIP_SIGNATURE,)),
    ('bz2', (ARCHIVE_BZIP2_SIGNATURE,)),
    ('xz', (ARCHIVE_XZ_SIGNATURE,)),
    ('zst', (ARCHIVE_ZSTD_SIGNATURE,)),
    ('lz4', ARCHIVE_LZ4_SIGNATURES),
)

ARCHIVE_TAR_USTAR_OFFSET = 257
ARCHIVE_TAR_USTAR_SIGNATURE = b'ustar'

ARCHIVE_STREAM_COPY_CHUNK_BYTES = 5 * 1024 * 1024
