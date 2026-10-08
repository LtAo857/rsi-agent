"""人工基线：独立采样 N 个候选，按可见样例通过数选择；同分保留最早候选。"""
import re


def solve(task, tools):
    best, best_score = "", -1
    while tools.calls_left > 0:
        reply = tools.llm(task["prompt"] + "\nReturn a complete Python code block.", temperature=0.7)
        match = re.search(r"```(?:python)?\s*\n(.*?)```", reply, re.S)
        code = match.group(1) if match else reply
        result = tools.run_tests(code)
        if result["passed"] > best_score:
            best, best_score = code, result["passed"]
    return best
