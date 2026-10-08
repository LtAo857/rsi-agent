"""用参考实现验证题库本身的测试是正确的：uv run python scripts/check_tasks.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rsi.sandbox import run_tests  # noqa: E402
from rsi.tasks import TASKS  # noqa: E402

REF = (Path(__file__).parent / "reference.py").read_text()

bad = 0
for t in TASKS:
    r = run_tests(REF, t["visible"] + t["hidden"])
    status = "ok " if not r["failures"] else "BAD"
    bad += bool(r["failures"])
    print(f"{status} {t['id']:10s} {r['passed']}/{r['total']}")
    for test, why in r["failures"]:
        print("     ", test.replace("\n", " | "), "->", why)
print("ALL GOOD" if not bad else f"{bad} tasks have wrong tests")
sys.exit(bool(bad))
