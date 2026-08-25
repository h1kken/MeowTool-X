from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslationKey:
    key: str = ''
    prefix: str = ''
    suffix: str = ''
