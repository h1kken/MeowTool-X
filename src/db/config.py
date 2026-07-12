from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import DeclarativeBase


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path
    base: type[DeclarativeBase]
