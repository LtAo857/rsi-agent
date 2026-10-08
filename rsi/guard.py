"""安全层：进化出的 Agent 源码在被执行前必须通过这些静态检查（锁定文件）。"""
import ast
import re

from rsi.tasks import TASKS

ALLOWED_IMPORTS = {"re", "json", "math", "textwrap", "itertools", "collections", "functools",
                   "random", "string", "typing", "dataclasses", "time", "ast", "difflib", "heapq"}
FORBIDDEN_NAMES = {"open", "exec", "eval", "compile", "__import__", "globals", "vars", "breakpoint",
                   "input", "setattr", "delattr", "__builtins__", "__loader__", "__spec__"}
# 防作弊：Agent 不允许针对具体题目写死逻辑（出现题目函数名，或字符串恰好等于题目 id）
TASK_ENTRIES = {t["entry"] for t in TASKS}
TASK_IDS = {t["id"] for t in TASKS}


def check(source: str) -> str | None:
    """通过返回 None，否则返回拒绝原因。"""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return f"syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    return f"forbidden import: {a.name}"
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                return f"forbidden import: {node.module}"
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            return f"forbidden name: {node.id}"
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return f"private/dunder attribute access: {node.attr}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            hit = next(iter(TASK_ENTRIES & set(re.findall(r"\w+", node.value))), None) or \
                (node.value if node.value in TASK_IDS else None)
            if hit:
                return f"task-specific hardcoding detected: {hit!r}"
    solve = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "solve"]
    if not solve or len(solve[0].args.args) != 2:
        return "must define top-level solve(task, tools)"
    return None
