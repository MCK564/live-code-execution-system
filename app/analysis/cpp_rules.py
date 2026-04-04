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


def run_cpp_rules(ctx: AnalysisContext) -> list[Alert]:
    if ctx.ts_root is None or ctx.source_bytes is None:
        raise ValueError("C++ analysis requires a Tree-Sitter AST.")

    alerts: list[Alert] = []
    alerts.extend(_loop_alerts(ctx))
    alerts.extend(_math_alerts(ctx))
    alerts.extend(_quality_alerts(ctx))
    return alerts


def _loop_alerts(ctx: AnalysisContext) -> list[Alert]:
    alerts: list[Alert] = []

    for node in walk(ctx.ts_root):
        if node.type == "while_statement":
            condition = first_child_of_type(node, "condition_clause")
            body = first_child_of_type(node, "compound_statement")
            if condition and body and is_true_condition(condition, ctx.source_bytes):
                if not contains_exit_statement(body):
                    alerts.append(
                        Alert(
                            kind="infinite_loop",
                            severity=Severity.CRITICAL,
                            line=node_line(node),
                            message="Unconditional `while(true)` loop with no exit path",
                            detail="This loop stays true forever and no break/return was found.",
                            fix="Add a break condition or make the loop condition mutable.",
                            confidence=0.96,
                        )
                    )

        if node.type == "for_statement":
            body = first_child_of_type(node, "compound_statement")
            if body and is_unbounded_for(node, ctx.source_bytes):
                if not contains_exit_statement(body):
                    alerts.append(
                        Alert(
                            kind="infinite_loop",
                            severity=Severity.CRITICAL,
                            line=node_line(node),
                            message="Unbounded `for(;;)` loop with no exit path",
                            detail="This loop runs forever unless control leaves the body explicitly.",
                            fix="Add a terminating condition or an explicit break path.",
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
                    detail="This expression is invalid and will fail at runtime.",
                    fix="Guard the denominator or replace the expression.",
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
                    detail="Exact float comparisons are often unstable because of representation error.",
                    fix="Compare with an epsilon instead of exact equality.",
                    confidence=0.90,
                )
            )

    return alerts


def _quality_alerts(ctx: AnalysisContext) -> list[Alert]:
    alerts: list[Alert] = []

    for node in walk(ctx.ts_root):
        if node.type != "function_definition":
            continue

        function_name = _function_name(node, ctx.source_bytes)
        function_line = node_line(node)
        body = first_child_of_type(node, "compound_statement")

        body_lines = node.end_point[0] - node.start_point[0] + 1
        if body_lines > 50:
            alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.MEDIUM,
                    line=function_line,
                    message=f"Function `{function_name}` is {body_lines} lines long",
                    detail="Large functions are harder to reason about and test.",
                    fix="Break the function into smaller helpers.",
                    confidence=0.84,
                )
            )

        declarator = first_child_of_type(node, "function_declarator")
        parameters = first_child_of_type(declarator, "parameter_list") if declarator else None
        parameter_count = (
            count_direct_children_of_types(parameters, {"parameter_declaration"})
            if parameters
            else 0
        )
        if parameter_count > 5:
            alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.LOW,
                    line=function_line,
                    message=f"Function `{function_name}` has {parameter_count} parameters",
                    detail="Many parameters usually make the API harder to use correctly.",
                    fix="Group related parameters into a struct or split responsibilities.",
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
                        line=function_line,
                        message=f"Function `{function_name}` reaches nesting depth {nesting_depth}",
                        detail="Deep nesting makes branch-heavy code harder to maintain.",
                        fix="Flatten the logic with early returns or helper functions.",
                        confidence=0.86,
                    )
                )

    return alerts


def _function_name(node, source_bytes: bytes) -> str:
    declarator = first_child_of_type(node, "function_declarator")
    identifier = first_child_of_type(declarator, "identifier") if declarator else None
    if identifier is None:
        return "function"
    return node_text(identifier, source_bytes)
