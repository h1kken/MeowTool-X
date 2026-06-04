from copy import deepcopy
from typing import Any


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
    def parse_numeric(value: Any) -> Any:
        from src.utils.string import safe_literal_eval

        if isinstance(value, str):
            return safe_literal_eval(value)
        return value

    def validate(
        self,
        user_value: Any | None,
        default_value: Any | None,
    ) -> Any:
        if default_value is None:
            return self._convert_without_default(user_value)

        match default_value:
            case tuple() if len(default_value) == 3 and all(
                isinstance(v, (int, float)) and not isinstance(v, bool)
                for v in default_value
            ):
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
                return (
                    deepcopy(user_value)
                    if isinstance(user_value, (list, dict))
                    else deepcopy(default_value)
                )
            case _:
                return deepcopy(default_value)

    def _convert_without_default(self, user_value: Any) -> Any:
        if isinstance(user_value, str):
            parsed = self.convert_to_bool(user_value)
            if isinstance(parsed, bool):
                return parsed
        return user_value

    def _validate_bounded(
        self,
        default_value: tuple[Any, Any, Any],
        user_value: Any,
    ) -> Any:
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
            return deepcopy(default_value)

        if min_value <= parsed <= max_value:
            return parsed
        return default_scalar

    def _validate_bool(self, default_value: bool, user_value: Any) -> bool:
        if isinstance(user_value, str):
            parsed = self.convert_to_bool(user_value)
            if isinstance(parsed, bool):
                return parsed
            return default_value
        if isinstance(user_value, bool):
            return user_value
        return default_value

    def _validate_int(self, default_value: int, user_value: Any) -> int:
        parsed = self.parse_numeric(user_value)
        if isinstance(parsed, bool):
            return default_value
        if isinstance(parsed, int):
            return parsed
        if isinstance(parsed, float) and parsed.is_integer():
            return int(parsed)
        return default_value

    def _validate_float(self, default_value: float, user_value: Any) -> float:
        parsed = self.parse_numeric(user_value)
        if isinstance(parsed, bool):
            return default_value
        if isinstance(parsed, (int, float)):
            return float(parsed)
        return default_value


config_validator = ConfigValidator()
