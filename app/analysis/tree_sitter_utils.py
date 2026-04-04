from __future__ import annotations

from collections.abc import Callable, Iterator

from tree_sitter import Node


CONTROL_NODES = {
    "if_statement",
    "while_statement",
    "for_statement",
    "do_statement",
    "switch_statement",
    "switch_expression",
    "try_statement",
    "catch_clause",
}

EXIT_NODES = {
    "break_statement",
    "return_statement",
    "throw_statement",
}


def walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def node_text(node: Node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def node_line(node: Node) -> int:
    return node.start_point[0] + 1


def first_child_of_type(node: Node, type_name: str) -> Node | None:
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def find_first_node(node: Node, predicate: Callable[[Node], bool]) -> Node | None:
    for current in walk(node):
        if predicate(current):
            return current
    return None


def first_error_line(node: Node) -> int:
    error_node = find_first_node(
        node,
        lambda current: current.type == "ERROR"
        or bool(getattr(current, "is_error", False))
        or bool(getattr(current, "is_missing", False)),
    )
    if error_node is None:
        return 1
    return node_line(error_node)


def has_descendant_type(node: Node, type_names: set[str]) -> bool:
    return any(child.type in type_names for child in walk(node))


def contains_exit_statement(node: Node) -> bool:
    return has_descendant_type(node, EXIT_NODES)


def compact_text(node: Node, source_bytes: bytes) -> str:
    return "".join(node_text(node, source_bytes).split())


def is_true_condition(node: Node, source_bytes: bytes) -> bool:
    return compact_text(node, source_bytes) in {"true", "(true)"}


def is_unbounded_for(node: Node, source_bytes: bytes) -> bool:
    return compact_text(node, source_bytes).startswith("for(;;")


def binary_expression_parts(node: Node) -> tuple[Node, str, Node] | None:
    if node.type != "binary_expression" or len(node.children) < 3:
        return None
    return node.children[0], node.children[1].type, node.children[2]


def is_zero_literal(node: Node, source_bytes: bytes) -> bool:
    text = node_text(node, source_bytes).strip().lower()
    return text in {
        "0",
        "0.0",
        "0f",
        "0d",
        "0l",
        "0u",
        "0ul",
        "0.0f",
        "0.0d",
    }


def is_float_literal(node: Node, source_bytes: bytes) -> bool:
    if node.type in {"decimal_floating_point_literal", "float_literal"}:
        return True

    text = node_text(node, source_bytes).strip().lower()
    return "." in text or text.endswith(("f", "d"))


def max_control_depth(node: Node) -> int:
    def _depth(current: Node, depth: int) -> int:
        max_depth = depth
        for child in current.children:
            child_depth = depth + 1 if child.type in CONTROL_NODES else depth
            max_depth = max(max_depth, _depth(child, child_depth))
        return max_depth

    return _depth(node, 0)


def count_direct_children_of_types(node: Node, type_names: set[str]) -> int:
    return sum(1 for child in node.children if child.type in type_names)
