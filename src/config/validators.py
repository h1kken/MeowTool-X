from copy import deepcopy
from typing import TypeGuard, cast

from src.config.types import ConfigMap, ConfigValue


class ConfigValidator:
    @staticmethod
    def convert_to_bool(user_value: str) -> bool | str:
        low = user_value.strip().lower()
        if low in ("true", "yes", "да", "on", "+"):
            return True
        if low in ("false", "no", "нет", "off", "-"):
            return False
        return user_value

    @staticmethod
    def parse_numeric(value: object) -> object:
        from src.utils.string import safe_literal_eval

        if isinstance(value, str):
            return safe_literal_eval(value)
        return value

    @staticmethod
    def _is_numeric_bound_tuple(
        value: tuple[ConfigValue, ...],
    ) -> TypeGuard[tuple[int | float, int | float, int | float]]:
        return len(value) == 3 and all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in value
        )

    def validate(
        self,
        user_value: object | None,
        default_value: ConfigValue | None,
    ) -> ConfigValue | object | None:
        if default_value is None:
            return self._convert_without_default(user_value)

        match default_value:
            case tuple() if self._is_numeric_bound_tuple(default_value):
                return self._validate_bounded(default_value, user_value)
            case tuple():
                return deepcopy(default_value[0]) if default_value else None
            case bool():
                return self._validate_bool(default_value, user_value)
            case int() if not isinstance(default_value, bool):
                return self._validate_int(default_value, user_value)
            case float():
                return self._validate_float(default_value, user_value)
            case str():
                return str(user_value) if user_value is not None else default_value
            case list() | dict():
                if isinstance(user_value, list):
                    return cast(ConfigValue, deepcopy(cast(list[ConfigValue], user_value)))
                if isinstance(user_value, dict):
                    return cast(ConfigValue, deepcopy(cast(ConfigMap, user_value)))
                return cast(ConfigValue, deepcopy(default_value))
            case _:
                return cast(ConfigValue, deepcopy(default_value))

    def _convert_without_default(self, user_value: object) -> object:
        if isinstance(user_value, str):
            parsed = self.convert_to_bool(user_value)
            if isinstance(parsed, bool):
                return parsed
        return user_value

    def _validate_bounded(
        self,
        default_value: tuple[int | float, int | float, int | float],
        user_value: object,
    ) -> int | float:
        default_scalar, min_value, max_value = default_value

        if isinstance(default_scalar, int) and not isinstance(default_scalar, bool):
            parsed = self.parse_numeric(user_value)
            if isinstance(parsed, bool):
                return default_scalar
            if isinstance(parsed, float) and not parsed.is_integer():
                return default_scalar
            if not isinstance(parsed, (int, float)):
                return default_scalar
            parsed = int(parsed)

        elif isinstance(default_scalar, float):
            parsed = self.parse_numeric(user_value)
            if isinstance(parsed, bool) or not isinstance(parsed, (int, float)):
                return default_scalar
            parsed = float(parsed)

        else:
            return default_scalar

        if min_value <= parsed <= max_value:
            return parsed
        return default_scalar

    def _validate_bool(self, default_value: bool, user_value: object) -> bool:
        if isinstance(user_value, str):
            parsed = self.convert_to_bool(user_value)
            if isinstance(parsed, bool):
                return parsed
            return default_value
        if isinstance(user_value, bool):
            return user_value
        return default_value

    def _validate_int(self, default_value: int, user_value: object) -> int:
        parsed = self.parse_numeric(user_value)
        if isinstance(parsed, bool):
            return default_value
        if isinstance(parsed, int):
            return parsed
        if isinstance(parsed, float) and parsed.is_integer():
            return int(parsed)
        return default_value

    def _validate_float(self, default_value: float, user_value: object) -> float:
        parsed = self.parse_numeric(user_value)
        if isinstance(parsed, bool):
            return default_value
        if isinstance(parsed, (int, float)):
            return float(parsed)
        return default_value


config_validator = ConfigValidator()
