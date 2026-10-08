"""人工基线：生成 → 可见样例测试 → 根据错误修复，样例全过则停止。"""
import re


def solve(task, tools):
    messages = [{"role": "user", "content": task["prompt"] + "\nReturn a complete Python code block."}]
    best, best_score = "", -1
    while tools.calls_left > 0:
        reply = tools.llm(messages, temperature=0.2)
        match = re.search(r"```(?:python)?\s*\n(.*?)```", reply, re.S)
        code = match.group(1) if match else reply
        result = tools.run_tests(code)
        if result["passed"] > best_score:
            best, best_score = code, result["passed"]
        if result["passed"] == result["total"]:
            break
        feedback = "\n".join(f"{f['test']}\n{f['error']}" for f in result["failures"])
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": "Fix these failures. Return the complete corrected Python code.\n" + feedback}]
    return best
