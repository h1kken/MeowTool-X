import ast
import typing as t


class String:
    @staticmethod
    def remove_brackets(s: str, *, round: bool = True, square: bool = True, remove_inner: bool = True) -> str:
        if not (round or square):
            return s
        
        if not remove_inner:
            if round:
                s = s.replace('(', '').replace(')', '')
            if square:
                s = s.replace('[', '').replace(']', '')
            return s
        
        result: list[str] = []
        skip = 0
        
        for char in s:
            if (char == '(' and round) or (char == '[' and square):
                skip += 1
                continue

            if skip and ((char == ')' and round) or (char == ']' and square)):
                skip -= 1
                continue

            if skip == 0:
                result.append(char)
                
        return ''.join(result)

    @staticmethod
    def safe_literal_eval(value: str) -> t.Any:
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value

    @staticmethod
    def decode_token(raw: bytes) -> str | None:
        if not raw:
            return

        token = raw.decode(encoding='utf-8', errors='ignore').strip()
        if not token:
            return
        
        return token
