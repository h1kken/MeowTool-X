from src.db.base import Base
from src.db.paths import PATH_DATABASES
from src.db.models import load_models
from src.db.session import get_engine
from src.utils.filesystem import ensure_dir


def initialize_database() -> None:
    load_models()
    ensure_dir(PATH_DATABASES)
    Base.metadata.create_all(get_engine())


__all__ = ("initialize_database",)
