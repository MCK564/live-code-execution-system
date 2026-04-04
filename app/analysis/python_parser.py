from __future__ import annotations

import ast


def parse_python(code: str) -> ast.AST:
    return ast.parse(code)
