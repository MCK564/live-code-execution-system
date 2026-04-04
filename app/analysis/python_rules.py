from __future__ import annotations

import ast

from analysis.contracts import Alert, AnalysisContext, Severity


class LoopAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def visit_While(self, node: ast.While) -> None:
        condition_src = ast.unparse(node.test) if hasattr(ast, "unparse") else "..."
        is_unconditional = (
            isinstance(node.test, ast.Constant) and bool(node.test.value)
        ) or (
            isinstance(node.test, ast.NameConstant) and node.test.value is True
        )

        if is_unconditional:
            has_break = self._has_break(node)
            has_return = self._has_return(node)
            has_sys_exit = self._has_call(node, "exit") or self._has_call(node, "sys.exit")

            if not (has_break or has_return or has_sys_exit):
                self.alerts.append(
                    Alert(
                        kind="infinite_loop",
                        severity=Severity.CRITICAL,
                        line=node.lineno,
                        message="Unconditional infinite loop with no exit path",
                        detail=f"`while {condition_src}` has no break, return, or exit call.",
                        fix="Add a break condition or update a guard variable inside the loop.",
                        confidence=0.97,
                    )
                )
            else:
                depth = self._max_break_depth(node)
                if depth > 3:
                    self.alerts.append(
                        Alert(
                            kind="infinite_loop",
                            severity=Severity.MEDIUM,
                            line=node.lineno,
                            message="Loop exit is deeply nested",
                            detail=f"The break path is nested {depth} levels deep.",
                            fix="Move the exit condition closer to the top of the loop.",
                            confidence=0.72,
                        )
                    )
        elif isinstance(node.test, ast.Compare):
            loop_vars = self._extract_compare_names(node.test)
            modified = self._vars_modified_in_body(node, loop_vars)
            if loop_vars and not modified:
                joined_vars = ", ".join(loop_vars)
                self.alerts.append(
                    Alert(
                        kind="infinite_loop",
                        severity=Severity.HIGH,
                        line=node.lineno,
                        message="Loop condition variables are never updated",
                        detail=f"Variables `{joined_vars}` in `while {condition_src}` appear unchanged.",
                        fix="Update the loop variables on each iteration.",
                        confidence=0.85,
                    )
                )

        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        iter_name = node.iter.id if isinstance(node.iter, ast.Name) else None
        if not iter_name:
            self.generic_visit(node)
            return

        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Assign):
                targets = child.targets
            elif isinstance(child, ast.AugAssign):
                targets = [child.target]
            else:
                continue

            for target in targets:
                if isinstance(target, ast.Name) and target.id == iter_name:
                    self.alerts.append(
                        Alert(
                            kind="infinite_loop",
                            severity=Severity.HIGH,
                            line=node.lineno,
                            message=f"Iterator `{iter_name}` is reassigned inside the loop",
                            detail="Reassigning the iterable does not change Python iteration order.",
                            fix="Use a while loop if the iterable itself must change.",
                            confidence=0.88,
                        )
                    )
                    break

        self.generic_visit(node)

    def _has_break(self, node: ast.AST) -> bool:
        return any(isinstance(child, ast.Break) for child in ast.walk(node))

    def _has_return(self, node: ast.AST) -> bool:
        return any(isinstance(child, ast.Return) for child in ast.walk(node))

    def _has_call(self, node: ast.AST, name: str) -> bool:
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue

            if isinstance(child.func, ast.Name) and child.func.id == name:
                return True
            if isinstance(child.func, ast.Attribute) and child.func.attr == name:
                return True
        return False

    def _max_break_depth(self, node: ast.AST, depth: int = 0) -> int:
        max_depth = 0
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Break):
                max_depth = max(max_depth, depth)
            else:
                max_depth = max(max_depth, self._max_break_depth(child, depth + 1))
        return max_depth

    def _extract_compare_names(self, node: ast.Compare) -> list[str]:
        names = {current.id for current in ast.walk(node) if isinstance(current, ast.Name)}
        return sorted(names)

    def _vars_modified_in_body(self, loop_node: ast.While, variable_names: list[str]) -> bool:
        for node in ast.walk(ast.Module(body=loop_node.body, type_ignores=[])):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in variable_names:
                        return True
            if isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name) and node.target.id in variable_names:
                    return True
        return False


class MathRiskAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            right = node.right
            if isinstance(right, ast.Constant) and right.value == 0:
                self.alerts.append(
                    Alert(
                        kind="math_risk",
                        severity=Severity.CRITICAL,
                        line=node.lineno,
                        message="Division by literal zero",
                        detail="This expression raises ZeroDivisionError at runtime.",
                        fix="Guard the denominator or remove the invalid expression.",
                        confidence=1.0,
                    )
                )
            elif isinstance(right, ast.Name):
                self.alerts.append(
                    Alert(
                        kind="math_risk",
                        severity=Severity.MEDIUM,
                        line=node.lineno,
                        message=f"Division by variable `{right.id}` may reach zero",
                        detail=f"If `{right.id}` becomes 0 at runtime, the expression will fail.",
                        fix=f"Check `{right.id}` before dividing.",
                        confidence=0.70,
                    )
                )

        if isinstance(node.op, ast.Pow):
            if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
                if node.right.value > 100:
                    self.alerts.append(
                        Alert(
                            kind="math_risk",
                            severity=Severity.HIGH,
                            line=node.lineno,
                            message=f"Very large exponent `{node.right.value}`",
                            detail="Large exponents can explode memory usage or overflow intermediate values.",
                            fix="Verify the exponent is intentional or switch to a safer formulation.",
                            confidence=0.80,
                        )
                    )

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if not any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            self.generic_visit(node)
            return

        for current in [node.left, *node.comparators]:
            if isinstance(current, ast.Constant) and isinstance(current.value, float):
                self.alerts.append(
                    Alert(
                        kind="math_risk",
                        severity=Severity.MEDIUM,
                        line=node.lineno,
                        message="Float equality comparison is unreliable",
                        detail="Floating-point values rarely compare exactly as expected.",
                        fix="Use math.isclose(...) for float comparisons.",
                        confidence=0.90,
                    )
                )
                break

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        risky_math = {"sqrt", "log", "log2", "log10", "asin", "acos"}
        if isinstance(node.func, ast.Attribute) and node.func.attr in risky_math and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Sub):
                self.alerts.append(
                    Alert(
                        kind="math_risk",
                        severity=Severity.HIGH,
                        line=node.lineno,
                        message=f"`math.{node.func.attr}()` may receive a negative value",
                        detail="Subtraction inside a domain-restricted math call can raise ValueError.",
                        fix=f"Guard the input before calling math.{node.func.attr}().",
                        confidence=0.75,
                    )
                )

        self.generic_visit(node)


class QualityAnalyzer(ast.NodeVisitor):
    def __init__(self) -> None:
        self.alerts: list[Alert] = []
        self._nesting_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        body_lines = (node.end_lineno - node.lineno) if hasattr(node, "end_lineno") else 0
        if body_lines > 50:
            self.alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.MEDIUM,
                    line=node.lineno,
                    message=f"Function `{node.name}` is {body_lines} lines long",
                    detail="Long functions are harder to read, test, and maintain.",
                    fix=f"Split `{node.name}` into smaller helper functions.",
                    confidence=0.85,
                )
            )

        argument_count = len(node.args.args)
        if argument_count > 5:
            self.alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.LOW,
                    line=node.lineno,
                    message=f"Function `{node.name}` has {argument_count} parameters",
                    detail="Functions with many parameters are harder to call and evolve.",
                    fix="Group related parameters into a dataclass or another object.",
                    confidence=0.80,
                )
            )

        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == node.name:
                self.alerts.append(
                    Alert(
                        kind="quality",
                        severity=Severity.LOW,
                        line=node.lineno,
                        message=f"Function `{node.name}` is recursive",
                        detail="Unbounded recursion can hit Python's recursion limit.",
                        fix="Add a strong base case or switch to an iterative approach.",
                        confidence=0.88,
                    )
                )
                break

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._nesting_depth += 1
        if self._nesting_depth >= 4:
            self.alerts.append(
                Alert(
                    kind="quality",
                    severity=Severity.MEDIUM,
                    line=node.lineno,
                    message=f"Nesting depth {self._nesting_depth} is too deep",
                    detail="Deep nesting makes control flow hard to follow.",
                    fix="Use guard clauses or early returns to flatten the code.",
                    confidence=0.88,
                )
            )
        self.generic_visit(node)
        self._nesting_depth -= 1


class SuggestionEngine:
    def generate(self, tree: ast.AST) -> list[Alert]:
        suggestions: list[Alert] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.For):
                continue

            if (
                len(node.body) == 1
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Call)
                and isinstance(node.body[0].value.func, ast.Attribute)
                and node.body[0].value.func.attr == "append"
            ):
                suggestions.append(
                    Alert(
                        kind="suggestion",
                        severity=Severity.LOW,
                        line=node.lineno,
                        message="Consider a list comprehension",
                        detail="This append-only loop may be simpler as a comprehension.",
                        fix="Replace the loop with a list comprehension if readability improves.",
                        confidence=0.78,
                    )
                )

        for function in (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)):
            has_annotations = any(argument.annotation is not None for argument in function.args.args)
            if not has_annotations and function.args.args:
                suggestions.append(
                    Alert(
                        kind="suggestion",
                        severity=Severity.LOW,
                        line=function.lineno,
                        message=f"Add type hints to `{function.name}`",
                        detail="Type hints improve readability and support static analysis.",
                        fix=f"Annotate the parameters and return type of `{function.name}`.",
                        confidence=0.70,
                    )
                )

        return suggestions[:3]


def run_python_rules(ctx: AnalysisContext) -> list[Alert]:
    if ctx.py_tree is None:
        raise ValueError("Python analysis requires a parsed Python AST.")

    loop_analyzer = LoopAnalyzer()
    loop_analyzer.visit(ctx.py_tree)

    math_analyzer = MathRiskAnalyzer()
    math_analyzer.visit(ctx.py_tree)

    quality_analyzer = QualityAnalyzer()
    quality_analyzer.visit(ctx.py_tree)

    alerts = loop_analyzer.alerts + math_analyzer.alerts + quality_analyzer.alerts
    alerts.extend(SuggestionEngine().generate(ctx.py_tree))
    return alerts
