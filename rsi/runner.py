"""子进程入口：加载一个 Agent 源文件，让它解一道题（锁定文件）。

stdin:  {"agent_path", "task": {id, prompt, entry, visible_tests}, "max_calls"}
stdout: 最后一行 RESULT_MARK + {"code", "llm_calls", "tokens", "error", "log"}
注意：隐藏测试从不进入这个进程。
"""
import contextlib
import importlib.util
import io
import json
import sys
import traceback

from rsi import llm, sandbox

RESULT_MARK = "@@AGENT-RESULT@@"


class BudgetExceeded(Exception):
    pass


class Tools:
    """Agent 唯一能接触外部世界的接口。"""

    def __init__(self, task, max_calls):
        self.task = task
        self.max_calls = max_calls
        self.llm_calls = 0
        self.tokens = 0
        self.llm_errors = []
        self._log = []

    @property
    def calls_left(self):
        return self.max_calls - self.llm_calls

    def llm(self, messages, temperature=0.2):   # 默认低温：降低评测噪声，需要多样性时 Agent 可自己调高
        if self.llm_calls >= self.max_calls:
            raise BudgetExceeded(f"LLM budget of {self.max_calls} calls exhausted")
        self.llm_calls += 1
        try:
            text, tokens = llm.chat(messages, model=llm.AGENT_MODEL, temperature=temperature)
        except Exception as e:
            self.llm_errors.append(type(e).__name__)
            raise
        self.tokens += tokens
        return text

    def run_tests(self, code):
        """只跑题目给出的可见样例。"""
        r = sandbox.run_tests(code, self.task["visible_tests"])
        return {"passed": r["passed"], "total": r["total"],
                "failures": [{"test": t, "error": e} for t, e in r["failures"]]}

    def log(self, msg):
        self._log.append(str(msg)[:500])


def main():
    req = json.loads(sys.stdin.read())
    tools = Tools(req["task"], req["max_calls"])
    out = {"code": "", "error": None}
    noise = io.StringIO()
    try:
        spec = importlib.util.spec_from_file_location("agent", req["agent_path"])
        agent = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(noise):
            spec.loader.exec_module(agent)
            code = agent.solve(dict(req["task"]), tools)
        out["code"] = code if isinstance(code, str) else ""
        if not isinstance(code, str):
            out["error"] = f"solve() returned {type(code).__name__}, expected str"
    except BaseException:
        out["error"] = traceback.format_exc(limit=3)[-1500:]
    out.update(llm_calls=tools.llm_calls, tokens=tools.tokens,
               llm_errors=tools.llm_errors, log=tools._log[-20:])
    sys.stdout.write("\n" + RESULT_MARK + json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
