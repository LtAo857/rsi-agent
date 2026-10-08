"""OpenAI 兼容客户端（默认 DashScope / Qwen）。"""
import os
import shlex
import time
from pathlib import Path

from openai import OpenAI


def load_env(path):
    """加载项目 KEY=value 配置；已有环境变量优先，不执行 shell 表达式。"""
    if not path.is_file():
        return
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, sep, raw = line.partition("=")
        key = key.strip()
        if not sep or not key.isidentifier():
            raise ValueError(f"invalid environment assignment on line {number} of {path.name}")
        try:
            values = shlex.split(raw, comments=True)
        except ValueError:
            raise ValueError(f"invalid environment value on line {number} of {path.name}") from None
        if len(values) > 1:
            raise ValueError(f"quote environment value on line {number} of {path.name}")
        os.environ.setdefault(key, values[0] if values else "")


load_env(Path(__file__).resolve().parent.parent / ".env")

BASE_URL = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY", "")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "qwen-turbo")   # 被进化的 Agent 用的模型（弱一点，留出提升空间）
META_MODEL = os.environ.get("META_MODEL", "qwen3-max")      # 负责改写 Agent 的模型

_client = None


def chat(messages, model, temperature=0.7, max_tokens=4096, retries=6):
    """返回 (text, usage_tokens)。"""
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=API_KEY or "EMPTY", timeout=180)
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
    for attempt in range(retries):
        try:
            r = _client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
            tokens = r.usage.total_tokens if r.usage else 0
            return r.choices[0].message.content or "", tokens
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(min(5 * 2 ** attempt, 60))   # 5,10,20,40,60s：扛过短暂断网
