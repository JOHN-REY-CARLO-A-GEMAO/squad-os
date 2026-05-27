"""
Safe expression evaluator for squad.yaml condition strings.

Uses Python's ``ast`` module to parse and evaluate logical expressions
*without* executing arbitrary code.  This prevents injection attacks from
third-party .sqad packages while supporting the operators users need:

    ==  !=  <  <=  >  >=  in  not in
    and  or  not

Usage::

    from squad_os.core.evaluator import SafeEvaluator

    if SafeEvaluator.evaluate("exception_found == True", {"exception_found": True}):
        dispatch(child_task)
"""
import ast
import json
import operator
import re
from typing import Any


class SafeEvaluator:
    """Safely evaluates basic logical conditions from squad.yaml without using eval()."""

    ALLOWED_OPERATORS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda l, r: l in r if r else False,
        ast.NotIn: lambda l, r: l not in r if r else True,
    }

    ALLOWED_BOOL_OPS = {
        ast.And: all,
        ast.Or: any,
    }

    @classmethod
    def evaluate(cls, expression_str: str, context: dict) -> bool:
        """Parse and safely evaluate *expression_str* against *context*.

        Returns ``True`` / ``False``.  Any parse error or unsupported node
        silently returns ``False`` (safe default — block the edge).
        """
        normalized = expression_str.replace("true", "True").replace("false", "False")
        try:
            tree = ast.parse(normalized, mode="eval")
            return cls._eval_node(tree.body, context)
        except Exception:
            return False

    @classmethod
    def _eval_node(cls, node: ast.AST, context: dict) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return context.get(node.id, None)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not cls._eval_node(node.operand, context)

        if isinstance(node, ast.BoolOp):
            values = [cls._eval_node(val, context) for val in node.values]
            return cls.ALLOWED_BOOL_OPS[type(node.op)](values)

        if isinstance(node, ast.Compare):
            left = cls._eval_node(node.left, context)
            op_type = type(node.ops[0])
            if op_type in cls.ALLOWED_OPERATORS:
                right = cls._eval_node(node.comparators[0], context)
                return cls.ALLOWED_OPERATORS[op_type](left, right)

        raise ValueError(f"Unsupported expression node: {type(node).__name__}")


# ── Context Builder ───────────────────────────────────────────────────

_JSON_LINE_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.*)$")


def build_condition_context(task_results: dict, dep_indices: list[int]) -> dict:
    """Build a context dict for condition evaluation from completed task outputs.

    Strategy (JSON-first with plaintext fallback):

    1. Strip markdown code fences from the output.
    2. Try ``json.loads()`` — if it returns a dict, flatten its keys into context.
    3. If that fails, scan for ``key = value`` lines and parse them as Python
       literals (booleans, ints, floats, or bare strings).
    4. Always include the raw text as ``task_<idx>`` for ``in`` / ``not in`` checks.
    """
    ctx: dict[str, Any] = {}

    for dep_idx in dep_indices:
        output = task_results.get(dep_idx, "")
        if not output:
            continue

        ctx[f"task_{dep_idx}"] = output

        # Strip markdown fences
        cleaned = re.sub(r"```(?:json)?\s*\n?", "", output).strip()

        # Try JSON parse first
        if cleaned.startswith("{"):
            try:
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    for k, v in data.items():
                        ctx[k] = v
                    continue  # skip line-by-line fallback
            except json.JSONDecodeError:
                pass

        # Plaintext fallback: key = value lines
        for line in cleaned.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = _JSON_LINE_RE.match(line)
            if m:
                key, raw_val = m.group(1), m.group(2)
                ctx[key] = _parse_literal(raw_val)

    return ctx


def _parse_literal(raw: str) -> Any:
    """Convert a string to bool / int / float, falling back to bare string."""
    val = raw.strip().rstrip(",")
    lower = val.lower()
    if lower in ("true", "yes"):
        return True
    if lower in ("false", "no"):
        return False
    if lower == "none":
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val  # bare string
