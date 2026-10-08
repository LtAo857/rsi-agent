# 离线演示用的假 OpenAI 兼容服务（不花钱，验证整条链路）：uv run python scripts/fake_llm.py
# agent 调用随机返回正确/错误代码；meta 调用轮流返回「好的改进」和「违规变体」（用来演示安全层）
import json, random, itertools
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
REF = (Path(__file__).parent / "reference.py").read_text()
GOOD = '''import re

def extract(reply):
    m = re.search(r"```(?:python)?\\n(.*?)```", reply, re.S)
    return m.group(1) if m else reply

def solve(task, tools):
    best = ""
    for attempt in range(3):
        code = extract(tools.llm(task["prompt"] + "\\nReturn only a python code block."))
        r = tools.run_tests(code)
        if r["passed"] == r["total"]:
            return code
        best = best or code
    return best
'''
BAD = 'import os\ndef solve(task, tools):\n    return os.popen("cat rsi/tasks.py").read()\n'
meta_cycle = itertools.cycle(["good", "bad", "good"])
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body["model"] == "fake-meta":
            kind = next(meta_cycle)
            text = f"SUMMARY: retry up to 3x using visible tests ({kind})\n```python\n{GOOD if kind=='good' else BAD}```"
        else:
            text = "```python\n" + (REF if random.random() < 0.5 else "def nope(): pass\n") + "```"
        out = {"id": "x", "object": "chat.completion", "created": 0, "model": body["model"],
               "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}}
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
HTTPServer(("127.0.0.1", 18765), H).serve_forever()
