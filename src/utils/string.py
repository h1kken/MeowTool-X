import ast
import typing as t


def remove_brackets_and_in(string: str, *, round: bool = True, square: bool = True) -> str:
    new_string = ''
    skip = 0
    for char in string:
        if (char == '(' and round) or (char == '[' and square):
            skip += 1
        elif skip > 0 and ((char == ')' and round) or (char == ']' and square)):
            skip -= 1
        elif skip == 0:
            new_string += char
    return new_string


def safe_literal_eval(value: str) -> t.Any:
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return value
