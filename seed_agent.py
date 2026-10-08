"""第 0 代 Agent：故意很朴素——只问一次模型，取第一个代码块。"""
import re


def solve(task, tools):
    reply = tools.llm(task["prompt"])
    m = re.search(r"```(?:python)?\n(.*?)```", reply, re.S)
    return m.group(1) if m else reply
