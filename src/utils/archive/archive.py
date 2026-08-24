from pathlib import Path

from .constants import ARCHIVE_EXTENSIONS, ARCHIVE_EXTENSION_GROUPS, ARCHIVE_SIGNATURE_GROUPS, ARCHIVE_TAR_USTAR_OFFSET, ARCHIVE_TAR_USTAR_SIGNATURE
from .types import ArchiveKind

from ..filesystem import FS


class Archive:
    @staticmethod
    def suffix_from_name(name: str) -> str:
        low = name.lower()
        for extension in ARCHIVE_EXTENSIONS:
            if low.endswith(extension):
                return extension
        return Path(name).suffix

    @staticmethod
    def detect_kind(path: Path, *, name_hint: str | None = None) -> str | None:
        by_name = Archive.kind_from_name(name_hint or path.name)
        if by_name is not None:
            return by_name

        by_signature = Archive.kind_from_signature(FS.read_file_head(path))
        if by_signature is not None:
            return by_signature

        if Archive.is_tar(path):
            return 'tar'

        return None

    @staticmethod
    def kind_from_name(name: str) -> ArchiveKind | None:
        low = name.lower()
        for kind, extensions in ARCHIVE_EXTENSION_GROUPS:
            if low.endswith(extensions):
                return kind
        return None

    @staticmethod
    def kind_from_signature(head: bytes) -> ArchiveKind | None:
        if not head:
            return None
        for kind, signatures in ARCHIVE_SIGNATURE_GROUPS:
            if any(head.startswith(signature) for signature in signatures):
                return kind
        return None

    @staticmethod
    def is_tar(path: Path) -> bool:
        try:
            with open(path, 'rb') as f:
                f.seek(ARCHIVE_TAR_USTAR_OFFSET)
                return f.read(len(ARCHIVE_TAR_USTAR_SIGNATURE)) == ARCHIVE_TAR_USTAR_SIGNATURE
        except OSError:
            return False
