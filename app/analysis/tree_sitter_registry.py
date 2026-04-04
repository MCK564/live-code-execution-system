from __future__ import annotations

from functools import lru_cache

import tree_sitter_cpp as tscpp
import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser


SUPPORTED_TREE_SITTER_LANGUAGES = ("java", "cpp")

_LANGUAGE_LOADERS = {
    "java": tsjava.language,
    "cpp": tscpp.language,
}


@lru_cache(maxsize=None)
def get_tree_sitter_language(language: str) -> Language:
    normalized = language.lower()
    if normalized not in _LANGUAGE_LOADERS:
        raise ValueError(f"Unsupported Tree-Sitter language: {language}")
    return Language(_LANGUAGE_LOADERS[normalized]())


@lru_cache(maxsize=None)
def get_tree_sitter_parser(language: str) -> Parser:
    return Parser(get_tree_sitter_language(language))


def parse_tree_sitter(language: str, code: str) -> tuple[bytes, Node]:
    source = code.encode("utf-8")
    tree = get_tree_sitter_parser(language).parse(source)
    return source, tree.root_node
