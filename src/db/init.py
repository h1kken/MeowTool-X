from src.db.base import Base
from src.app.paths import PATH_DATABASES_USER
from src.db.models import load_models
from src.db.session import get_engine
from src.utils.filesystem import FS


def initialize_database() -> None:
    load_models()
    FS.ensure_dir(PATH_DATABASES_USER)
    Base.metadata.create_all(get_engine())


__all__ = ("initialize_database",)
