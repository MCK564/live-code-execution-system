from __future__ import annotations

from analysis.contracts import Alert, AnalysisContext, Severity
from analysis.tree_sitter_utils import (
    binary_expression_parts,
    contains_exit_statement,
    count_direct_children_of_types,
    first_child_of_type,
    is_float_literal,
    is_true_condition,
    is_unbounded_for,
    is_zero_literal,
    max_control_depth,
    node_line,
    node_text,
    walk,
)


def run_java_rules(ctx: AnalysisContext) -> list[Alert]:
    if ctx.ts_root is None or ctx.source_bytes is None:
        raise ValueError("Java analysis requires a Tree-Sitter AST.")

    alerts: list[Alert] = []
    alerts.extend(_loop_alerts(ctx))
    alerts.extend(_math_alerts(ctx))
    alerts.extend(_quality_alerts(ctx))
    return alerts


def _loop_alerts(ctx: AnalysisContext) -> list[Alert]:
    alerts: list[Alert] = []

    for node in walk(ctx.ts_root):
        if node.type == "while_statement":
            condition = first_child_of_type(node, "parenthesized_expression")
            body = first_child_of_type(node, "block")
            if condition and body and is_true_condition(condition, ctx.source_bytes):
                if not contains_exit_statement(body):
                    alerts.append(
                        Alert(
                            kind="infinite_loop",
                            severity=Severity.CRITICAL,
                            line=node_line(node),
                            message="Unconditional `while(true)` loop with no exit path",
                            detail="This loop never changes its condition and no break/return was found.",
                            fix="Add a break condition or change the loop condition.",
                            confidence=0.96,
                        )
                    )

        if node.type == "for_statement":
            body = first_child_of_type(node, "block")
            if body and is_unbounded_for(node, ctx.source_bytes):
                if not contains_exit_statement(body):
                    alerts.append(
                        Alert(
                            kind="infinite_loop",
                            severity=Severity.CRITICAL,
                            line=node_line(node),
                            message="Unbounded `for(;;)` loop with no exit path",
                            detail="This loop runs forever unless a break, return, or throw is reached.",
                            fix="Add an exit condition or convert it to a bounded loop.",
                            confidence=0.96,
                        )
                    )

    return alerts


def _math_alerts(ctx: AnalysisContext) -> list[Alert]:
    alerts: list[Alert] = []

    for node in walk(ctx.ts_root):
        parts = binary_expression_parts(node)
        if parts is None:
            continue

        left, operator, right = parts
        if operator in {"/", "%"} and is_zero_literal(right, ctx.source_bytes):
            alerts.append(
                Alert(
                    kind="math_risk",
                    severity=Severity.CRITICAL,
                    line=node_line(node),
                    message="Division or modulo by literal zero",
                    detail="This expression will fail at runtime.",
                    fix="Guard the denominator or replace the invalid expression.",
                    confidence=1.0,
                )
            )

        if operator in {"==", "!="} and (
            is_float_literal(left, ctx.source_bytes) or is_float_literal(right, ctx.source_bytes)
        ):
            alerts.append(
                Alert(
                    kind="math_risk",
                    severity=Severity.MEDIUM,
                    line=node_line(node),
                    message="Float equality comparison is brittle",
                    detail="Exact comparison on floating-point values can be unstable.",
                    fix="Compare with an epsilon or use a tolerance-based helper.",
                    confidence=0.90,
                )
            )

    return alerts


def _quality_alerts(ctx: AnalysisContext) -> list[Alert]:
    alerts: list[Alert] = []

    for node in walk(ctx.ts_root):
        if node.type != "method_declaration":
            continue

        method_name = _method_name(node, ctx.source_bytes)
        method_line = node_line(node)
        body = first_child_of_type(node, "block")

        body_lines = node.end_point[0] - node.start_point[0] + 1
        if body_lines > 50:
            alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.MEDIUM,
                    line=method_line,
                    message=f"Method `{method_name}` is {body_lines} lines long",
                    detail="Large methods are harder to test and maintain.",
                    fix="Extract smaller helper methods.",
                    confidence=0.84,
                )
            )

        parameters = first_child_of_type(node, "formal_parameters")
        parameter_count = (
            count_direct_children_of_types(
                parameters,
                {"formal_parameter", "spread_parameter", "receiver_parameter"},
            )
            if parameters
            else 0
        )
        if parameter_count > 5:
            alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.LOW,
                    line=method_line,
                    message=f"Method `{method_name}` has {parameter_count} parameters",
                    detail="High parameter counts usually signal mixed responsibilities.",
                    fix="Group related parameters into an object or split the method.",
                    confidence=0.80,
                )
            )

        if body:
            nesting_depth = max_control_depth(body)
            if nesting_depth >= 4:
                alerts.append(
                    Alert(
                        kind="quality",
                        severity=Severity.MEDIUM,
                        line=method_line,
                        message=f"Method `{method_name}` reaches nesting depth {nesting_depth}",
                        detail="Deep nesting makes branch logic harder to follow.",
                        fix="Use early returns or extract nested blocks into helper methods.",
                        confidence=0.86,
                    )
                )

    return alerts


def _method_name(node, source_bytes: bytes) -> str:
    identifier = first_child_of_type(node, "identifier")
    if identifier is None:
        return "method"
    return node_text(identifier, source_bytes)
