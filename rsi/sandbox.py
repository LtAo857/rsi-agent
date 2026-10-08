"""在独立子进程里执行候选代码 + 测试（锁定文件）。"""
import json
import secrets
import subprocess
import sys
import tempfile

_HARNESS = r'''
import json, sys
from datetime import datetime, date, timedelta
payload = json.loads(sys.stdin.read())
nonce = payload["nonce"]

def _raises(exc, fn, *a, **k):
    try:
        fn(*a, **k)
    except exc:
        return True
    except Exception:
        return False
    return False

ns = {"__name__": "solution", "datetime": datetime, "date": date, "timedelta": timedelta}
try:
    exec(compile(payload["code"], "solution.py", "exec"), ns)
    load_error = None
except BaseException as e:
    load_error = f"{type(e).__name__}: {e}"

results = []
for t in payload["tests"]:
    if load_error:
        results.append([False, "solution failed to load: " + load_error])
        continue
    g = dict(ns)
    g["_raises"] = _raises
    try:
        exec(t, g)
        results.append([True, ""])
    except AssertionError:
        results.append([False, "assertion failed"])
    except BaseException as e:
        results.append([False, f"{type(e).__name__}: {e}"[:300]])
sys.stdout.write("\n" + nonce + json.dumps(results) + "\n")
'''


def run_tests(code: str, tests: list[str], timeout: float = 10) -> dict:
    """返回 {passed, total, failures: [(test, reason)]}。"""
    nonce = "@@RESULT-" + secrets.token_hex(8) + "@@"
    total = len(tests)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            p = subprocess.run([sys.executable, "-I", "-c", _HARNESS], cwd=tmp, text=True,
                               input=json.dumps({"code": code, "tests": tests, "nonce": nonce}),
                               capture_output=True, timeout=timeout)
        lines = [l for l in p.stdout.splitlines() if l.startswith(nonce)]
        if not lines:
            reason = (p.stderr.strip().splitlines() or ["no result (crashed?)"])[-1][:300]
            return {"passed": 0, "total": total, "failures": [(t, reason) for t in tests]}
        results = json.loads(lines[-1][len(nonce):])
    except subprocess.TimeoutExpired:
        return {"passed": 0, "total": total, "failures": [(t, f"timeout after {timeout}s") for t in tests]}
    failures = [(t, why) for t, (ok, why) in zip(tests, results) if not ok]
    return {"passed": total - len(failures), "total": total, "failures": failures}
