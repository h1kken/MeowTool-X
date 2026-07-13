import json
import mmap
import shutil
import zipfile
from collections.abc import Collection, Mapping, MutableMapping
from pathlib import Path
from typing import Any, TypeVar, cast

from src.exceptions.json import NotADictionaryError
from src.app.paths import PATH_APP_ROOT
from src.utils.logging.decorators import log_action
from src.utils.filesystem.constants import (
    FILENAME_SPECIAL_CHARS,
    START_DIR_PATHS,
    START_FILE_PATHS,
)
from src.utils.filesystem.types import JsonObject
from src.utils.logging import logger

TDefault = TypeVar("TDefault")


class FS:
    @staticmethod
    @log_action('delete folder')
    def delete_folder(path: Path, *, ignore_errors: bool = True) -> None:
        shutil.rmtree(path, ignore_errors=ignore_errors)

    @staticmethod
    @log_action('ensure dir')
    def ensure_dir(path: Path) -> Path:
        if path.exists():
            if not path.is_dir():
                raise NotADirectoryError(path)
            return path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    @log_action('ensure file')
    def ensure_file(path: Path, *, overwrite: bool = False) -> Path:
        if path.exists():
            if path.is_dir():
                raise IsADirectoryError(path)
            if overwrite:
                path.write_text('', encoding='utf-8')
            return path

        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    @staticmethod
    @log_action('copy file')
    def copy_file(src: Path, dest: Path, *, overwrite: bool = True) -> None:
        if overwrite or not dest.exists():
            shutil.copy(src, dest)

    @staticmethod
    @log_action('replace file')
    def replace_file(src: Path, dest: Path) -> None:
        src.replace(dest)

    @staticmethod
    @log_action('delete file')
    def delete_file(path: Path, *, missing_ok: bool = True) -> None:
        path.unlink(missing_ok=missing_ok)

    @staticmethod
    @log_action('create archive')
    def create_archive(path: Path, *, overwrite: bool = True) -> None:
        source_path = Path(path)
        if not source_path.exists():
            return

        archive_dir = source_path.parent / 'archives'
        archive_path = archive_dir / f'{source_path.stem}.zip'
        if archive_path.exists() and not overwrite:
            return

        archive_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if source_path.is_file():
                zipf.write(source_path, source_path.name)
                return

            for file_path in source_path.rglob('*'):
                if not file_path.is_file():
                    continue
                if archive_dir in file_path.parents:
                    continue
                zipf.write(file_path, file_path.relative_to(source_path))


def create_start_paths() -> None:
    for path in START_DIR_PATHS:
        FS.ensure_dir(PATH_APP_ROOT / path)
    for path in START_FILE_PATHS:
        FS.ensure_file(PATH_APP_ROOT / path)


def load_json(path: Path) -> JsonObject | None:
    try:
        with path.open('r', encoding='utf-8') as f:
            data: object = json.load(f)

        if not isinstance(data, dict):
            raise NotADictionaryError

        raw_data = cast(dict[object, object], data)
        if any(not isinstance(key, str) for key in raw_data):
            raise NotADictionaryError

        return cast(JsonObject, raw_data)
    except FileNotFoundError:
        logger.warning(f'File not found: {path}')
    except NotADictionaryError:
        logger.warning(f'File not contains a dictionary data: {path}')
    except json.JSONDecodeError as e:
        logger.warning(f'Can\'t decode JSON in {path}: {e}')
    except UnicodeDecodeError:
        logger.warning(f'Can\'t decode unicode in {path}')
    except Exception:
        logger.exception(f'Error in {path}')


def get_safe(
    data: Mapping[str, Any],
    key: str,
    *,
    sep: str = '>',
    default: TDefault | None = None,
) -> object | TDefault | None:
    keys = key.split(sep)
    current: object = data
    for part in keys:
        if not isinstance(current, Mapping) or part not in current:
            return default
        mapping = cast(Mapping[str, object], current)
        current = mapping[part]
    return current


def set_safe(data: MutableMapping[str, Any], key: str, value: Any, *, sep: str = '>') -> None:
    keys = key.split(sep)
    current: MutableMapping[str, Any] = data
    for part in keys[:-1]:
        child = current.get(part)
        if isinstance(child, MutableMapping):
            current = cast(MutableMapping[str, Any], child)
            continue
        new_child: MutableMapping[str, Any] = {}
        current[part] = new_child
        current = new_child
    current[keys[-1]] = value


def del_safe(data: MutableMapping[str, Any], key: str, *, sep: str = '>') -> bool:
    keys = key.split(sep)
    current: MutableMapping[str, Any] = data
    stack: list[tuple[MutableMapping[str, Any], str]] = []

    for part in keys[:-1]:
        child = current.get(part)
        if not isinstance(child, MutableMapping):
            return False
        stack.append((current, part))
        current = cast(MutableMapping[str, Any], child)

    leaf = keys[-1]
    if leaf not in current:
        return False
    del current[leaf]

    while stack:
        parent, part = stack.pop()
        child = parent.get(part)
        if isinstance(child, MutableMapping) and not child:
            del parent[part]
            continue
        break

    return True


def get_files_from_folder(path: Path, *, only_files: bool = True) -> list[str]:
    if not path.exists():
        raise FileNotFoundError
    if not path.is_dir():
        raise NotADirectoryError

    return [entry.name for entry in path.iterdir() if entry.is_file() or not only_files]


def count_lines_in_file(path: Path) -> int:
    with path.open('rb') as f:
        if f.seek(0, 2) == 0:
            return 0
        f.seek(0)

        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            count = 0
            pos = 0

            while True:
                pos = mm.find(b'\n', pos)
                if pos == -1:
                    break
                count += 1
                pos += 1

        if count > 0:
            f.seek(-1, 2)
            if f.read(1) != b'\n':
                count += 1

    return count


def validate_filename(name: str, *, black_list: Collection[str] = (), default: str = 'output') -> str:
    name = str(name).strip()
    if (
        not name
        or name in black_list
        or any(char in name for char in FILENAME_SPECIAL_CHARS)
    ):
        return default
    return name

