"""评测一个 Agent（锁定文件）。"""
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rsi import sandbox
from rsi.runner import RESULT_MARK

ROOT = Path(__file__).resolve().parent.parent
LOCKED = ["rsi/tasks.py", "rsi/sandbox.py", "rsi/runner.py", "rsi/evaluate.py", "rsi/guard.py"]
MAX_CALLS = 8          # 每道题的 LLM 调用预算
AGENT_TIMEOUT = 300    # 每道题的总时间预算（秒）


def _digest():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in LOCKED}


_FROZEN = _digest()


def verify_integrity():
    changed = [p for p, h in _digest().items() if _FROZEN[p] != h]
    if changed:
        raise RuntimeError(f"locked evaluation files were modified: {changed}")


def run_one(agent_path: Path, task: dict, max_calls: int = MAX_CALLS) -> dict:
    t0 = time.time()
    public = {k: task[k] for k in ("id", "prompt", "entry")} | {"visible_tests": task["visible"]}
    req = {"agent_path": str(agent_path), "task": public, "max_calls": max_calls}
    try:
        p = subprocess.run([sys.executable, "-m", "rsi.runner"], cwd=ROOT, input=json.dumps(req),
                           capture_output=True, text=True, timeout=AGENT_TIMEOUT)
        lines = [l for l in p.stdout.splitlines() if l.startswith(RESULT_MARK)]
        out = json.loads(lines[-1][len(RESULT_MARK):]) if lines else \
            {"code": "", "error": "runner crashed: " + p.stderr[-800:], "llm_calls": 0, "tokens": 0, "log": []}
    except subprocess.TimeoutExpired:
        out = {"code": "", "error": f"agent timeout after {AGENT_TIMEOUT}s", "llm_calls": max_calls, "tokens": 0, "log": []}
    r = sandbox.run_tests(out["code"], task["visible"] + task["hidden"]) if out["code"] else \
        {"passed": 0, "total": len(task["visible"]) + len(task["hidden"]), "failures": []}
    return {"task": task["id"], "solved": bool(out["code"]) and not r["failures"],
            "passed": r["passed"], "total": r["total"], "failures": r["failures"][:5],
            "agent_error": out["error"], "llm_errors": out.get("llm_errors", []),
            "llm_calls": out["llm_calls"], "tokens": out["tokens"],
            "code": out["code"][:4000], "log": out["log"], "seconds": round(time.time() - t0, 1)}


def evaluate(agent_path: Path, tasks: list[dict], workers: int = 8, max_calls: int = MAX_CALLS) -> dict:
    if max_calls < 1 or workers < 1 or not tasks:
        raise ValueError("positive max_calls/workers and nonempty tasks required")
    verify_integrity()
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda t: run_one(agent_path, t, max_calls), tasks))
    solved = sum(r["solved"] for r in results)
    passed, total = sum(r["passed"] for r in results), sum(r["total"] for r in results)
    return {"score": solved / len(tasks), "solved": solved, "n": len(tasks),
            "test_rate": passed / total, "tests_passed": passed, "tests_total": total,
            "llm_calls": sum(r["llm_calls"] for r in results),
            "tokens": sum(r["tokens"] for r in results), "results": results}
