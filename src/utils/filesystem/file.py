import json
import mmap
import shutil
import zipfile
from pathlib import Path
from typing import Any, Collection

from src.exceptions.json import NotADictionaryError
from src.utils.constants import APP_ROOT, FILENAME_SPECIAL_CHARS, START_PATHS
from src.utils.decorators import log_action
from src.utils.logging import logger


class FS:
    @staticmethod
    @log_action('create folder')
    def create_folder(path: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        path.mkdir(parents=parents, exist_ok=exist_ok)

    @staticmethod
    @log_action('delete folder') 
    def delete_folder(path: Path, *, ignore_errors: bool = True) -> None:
        shutil.rmtree(path, ignore_errors=ignore_errors)

    @staticmethod
    @log_action('create file')
    def create_file(path: Path, *, exist_ok: bool = True) -> None:
        path.touch(exist_ok=exist_ok)

    @staticmethod
    @log_action('create clean file')
    def create_clean_file(path: Path, *, overwrite: bool = True) -> None:
        if overwrite or not path.exists():
            open(path, 'w').close()

    @staticmethod
    @log_action('copy file')
    def copy_file(src: Path, dest: Path, *, overwrite: bool = True) -> None:
        if overwrite or not dest.exists():
            shutil.copy(src, dest)

    @staticmethod
    @log_action('replace file', re_raise=True)
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


def create_start_folders_and_files() -> None:
    for path, kind in START_PATHS:
        target_path = APP_ROOT / path
        match kind:
            case 'dir':
                FS.create_folder(target_path, exist_ok=False)
            case 'file':
                FS.create_folder(target_path.parent, exist_ok=False)
                FS.create_file(target_path, exist_ok=False)


def load_json(path: Path) -> dict | None:
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise NotADictionaryError

        return data
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


def get_safe(data: dict, key: str, *, sep: str = '>', default: Any | None = None):
    keys = key.split(sep)
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def set_safe(data: dict, key: str, value: Any, *, sep: str = '>') -> None:
    keys = key.split(sep)
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def del_safe(data: dict, key: str, *, sep: str = '>') -> bool:
    keys = key.split(sep)
    current = data
    stack: list[tuple[dict, str]] = []

    for part in keys[:-1]:
        if not isinstance(current, dict) or part not in current or not isinstance(current[part], dict):
            return False
        stack.append((current, part))
        current = current[part]

    leaf = keys[-1]
    if not isinstance(current, dict) or leaf not in current:
        return False
    del current[leaf]

    while stack:
        parent, part = stack.pop()
        child = parent.get(part)
        if isinstance(child, dict) and not child:
            del parent[part]
            continue
        break

    return True


def get_files_from_folder(path: Path, *, only_files: bool = True) -> list[str]:
    if not path.exists():
        raise FileNotFoundError
    if not path.is_dir():
        raise NotADirectoryError
    
    return [dir.name for dir in path.iterdir() if dir.is_file() or not only_files]


def count_lines_in_file(path: Path) -> int:
    with open(path, 'rb') as f:
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


def validate_filename(filename: str, *, black_list: Collection[str] = (), default: str = 'output') -> str:
    filename = str(filename).strip()
    if (
        not filename
        or filename in black_list
        or any(char in filename for char in FILENAME_SPECIAL_CHARS)
    ):
        return default
    return filename

