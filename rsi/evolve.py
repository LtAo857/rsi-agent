"""进化主循环：迷你 Darwin Gödel Machine。

    uv run python -m rsi.evolve --run demo --iterations 15

每一轮：从档案库按「分数高 + 子代少」采样一个父代 → META 模型阅读它的源码和失败案例，
改写出一个新 Agent → 安全检查 → 在开发集上评测 → 入档（失败/被拒的也记录）。
结束后在留出集上对比种子 Agent 和最佳 Agent。
"""
import argparse
import json
import math
import random
import re
import shutil
import statistics
import time
from pathlib import Path

from rsi import guard, llm
from rsi.evaluate import MAX_CALLS, ROOT, evaluate
from rsi.tasks import DEV, HELDOUT

TOOLS_DOC = f"""\
The agent is a Python module defining `solve(task, tools) -> str` that returns Python source code solving the task.
- task: dict with keys "id", "prompt" (the problem statement), "entry" (function/class name to implement),
  "visible_tests" (list of example test snippets, each a small piece of Python using assert).
- tools.llm(messages, temperature=0.2) -> str   # messages: str or OpenAI-style list of dicts. Budget: {MAX_CALLS} calls per task,
  raises an exception when exhausted. tools.calls_left tells how many remain.
- tools.run_tests(code) -> {{"passed": int, "total": int, "failures": [{{"test": str, "error": str}}]}}
  runs ONLY the visible tests in a sandbox (cheap, does not use the LLM budget).
- tools.log(msg)  # optional trace
The returned code is graded on many HIDDEN tests (edge cases) that the agent never sees. Time limit: 300s per task."""

CONSTRAINTS = f"""\
Hard constraints (violations are rejected automatically):
- Only these imports: {", ".join(sorted(guard.ALLOWED_IMPORTS))}.
- No open/exec/eval/compile/__import__/globals/vars/setattr, no attribute names starting with "_".
- The agent must be GENERAL: never mention specific task names or special-case particular problems.
- Keep a top-level `def solve(task, tools):`."""


def meta_prompt(parent: dict, source: str, history: list[dict], ideas: list[str]) -> str:
    fails = [r for r in parent["eval"]["results"] if not r["solved"]]
    random.shuffle(fails)
    cases = []
    for r in fails[:4]:
        task = next(t for t in DEV if t["id"] == r["task"])
        detail = "\n".join(f"    {f[0]!r} -> {f[1]}" for f in r["failures"][:3]) or "    (no code returned)"
        cases.append(f"### Task (unsolved)\n{task['prompt']}\nAgent error: {r['agent_error'] or 'none'}\n"
                     f"LLM calls used: {r['llm_calls']}\nFailing tests:\n{detail}\n"
                     f"Code it produced (truncated):\n```python\n{r['code'][:1200]}\n```")
    hist = "\n".join(f"- [{h['score_delta']:+.2f}] {h['summary']}" for h in history) or "- (none yet)"
    tried = "\n".join(ideas) or "- (none yet)"
    return f"""You are improving an AI coding agent by rewriting its own source code. This is the self-improvement loop:
your rewrite will be evaluated, and the best versions will be improved again.

## Agent interface
{TOOLS_DOC}

{CONSTRAINTS}

## Current agent (solves {parent['eval']['solved']}/{parent['eval']['n']} dev tasks fully, passes {parent['eval']['tests_passed']}/{parent['eval']['tests_total']} individual tests)
```python
{source}
```

## Some failures of this agent
{chr(10).join(cases) if cases else "(it solved everything it was given)"}

## Previous attempts in this lineage (fitness change vs. their parent; REJECTED ones never ran)
{hist}

## Ideas already tried anywhere in the archive (fitness change vs. their parent)
{tried}

## Your job
Diagnose WHY the agent fails in general (not just these tasks), then propose ONE focused, general improvement.
Explore: do NOT submit yet another variant of an idea listed above unless that idea clearly helped (positive change);
prefer a genuinely different direction. Examples of directions: sampling several independent candidates and picking
the one that passes the most tests; differential testing (two independent implementations compared on many inputs);
writing the spec as an explicit checklist of rules first; few-shot prompting with a worked example; using different
temperatures for exploration vs. repair; splitting the budget between generation and repair differently;
simplifying an over-complicated agent. Use the LLM budget ({MAX_CALLS} calls/task) wisely.

Reply in exactly this format:
SUMMARY: <one line describing the change>
```python
<the complete new agent source>
```"""


def parse_reply(text: str):
    # 贪婪匹配到最后一个 ```：Agent 源码里经常自己也含有 ``` （比如提取代码块的正则）
    m = re.search(r"```python\n(.*)```", text, re.S)
    s = re.search(r"SUMMARY:\s*(.+)", text)
    return (s.group(1).strip() if s else "(no summary)"), (m.group(1) if m else None)


def fitness(ev: dict) -> float:
    """整题通过率和单条测试通过率各占一半：「差一点就做对」的进步也能被看见。"""
    return (ev["score"] + ev["test_rate"]) / 2


def node_fit(n: dict) -> float:
    """复测过的节点用多次评测的平均值，否则用单次评测。"""
    return fitness(n.get("eval_mean") or n["eval"])


def archive_ideas(nodes: list[dict], limit: int = 30) -> list[str]:
    """整个档案库里试过的思路（不只是当前谱系），让 meta 模型避免原地打转。"""
    by_id = {n["id"]: n for n in nodes}
    out = [f"- [{node_fit(n) - node_fit(by_id[n['parent']]):+.3f}] {n['summary']}"
           for n in nodes if n["parent"] is not None and n["status"] in ("ok", "broken")]
    return out[-limit:]


def confirm(run_dir: Path, node: dict, runs: int, workers: int):
    """对候选最佳再评测 runs-1 次取平均，防止一次运气好的评测被当成进步。"""
    agent = run_dir / f"node_{node['id']:03d}" / "agent.py"
    evs = [node["eval"]]
    for _ in range(runs - 1):
        ev = evaluate(agent, DEV, workers)
        check_infra(ev)
        evs.append(ev)
    mean = lambda k: statistics.mean(e[k] for e in evs)
    node["eval_mean"] = {"runs": len(evs), "n": evs[0]["n"], "tests_total": evs[0]["tests_total"],
                         **{k: mean(k) for k in ("score", "test_rate", "solved", "tests_passed", "llm_calls")},
                         "fitness_runs": [round(fitness(e), 4) for e in evs]}


def propose(parent: dict, psrc: str, history: list[dict], ideas: list[str], max_repairs: int = 2):
    """让 meta 模型改写 Agent；被安全层拒绝时把原因回传，让它当场修正（最多 max_repairs 次）。
    返回 (summary, source, reason, repairs)，reason 为 None 表示通过。"""
    messages = [{"role": "user", "content": meta_prompt(parent, psrc, history, ideas)}]
    for repairs in range(max_repairs + 1):
        try:
            reply, _ = llm.chat(messages, model=llm.META_MODEL, temperature=0.8, max_tokens=8192)
        except Exception as e:
            raise InfraError(f"meta call failed: {e}")
        summary, source = parse_reply(reply)
        reason = "no ```python code block in reply" if source is None else guard.check(source)
        if not reason:
            return summary, source, None, repairs
        log(f"      guard rejected ({reason}), asking meta model to fix ...")
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"Your agent was REJECTED by the safety checker: {reason}\n"
                      f"{CONSTRAINTS}\nKeep the same idea but comply with every constraint. "
                      "Reply again in exactly the same format (SUMMARY line + full source)."}]
    return summary, source or reply, reason, repairs


def load_nodes(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(run_dir.glob("node_*/node.json"))]


def save_node(run_dir: Path, node: dict, source: str):
    d = run_dir / f"node_{node['id']:03d}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "agent.py").write_text(source)
    (d / "node.json").write_text(json.dumps(node, ensure_ascii=False, indent=1))


def select_parent(nodes: list[dict]) -> dict:
    """DGM 式采样：分数越高越可能被选，子代越多越不容易被选（保持探索）。"""
    alive = [n for n in nodes if n["status"] == "ok"]
    med = statistics.median(node_fit(n) for n in alive)
    children = {n["id"]: sum(c["parent"] == n["id"] for c in nodes) for n in alive}
    weights = [1 / (1 + math.exp(-10 * (node_fit(n) - med))) / (1 + children[n["id"]]) for n in alive]
    return random.choices(alive, weights=weights)[0]


def lineage_history(nodes: list[dict], node: dict) -> list[dict]:
    """父代链上 + 父代的直接子代里尝试过的改动，作为「经验」喂给 meta 模型。"""
    by_id = {n["id"]: n for n in nodes}
    chain, cur = [], node
    while cur["parent"] is not None:
        chain.append(cur)
        cur = by_id[cur["parent"]]
    siblings = [n for n in nodes if n["parent"] == node["id"]]
    out = []
    for n in list(reversed(chain)) + siblings:
        p = by_id[n["parent"]]
        delta = (node_fit(n) - node_fit(p)) if n["status"] == "ok" else -1
        tag = "" if n["status"] == "ok" else f" (REJECTED: {n['reason']})"
        out.append({"summary": n["summary"] + tag, "score_delta": delta})
    return out[-12:]


class InfraError(RuntimeError):
    """推理服务不可用：中止本次运行，而不是把网络故障当成 Agent 的成绩记下来。"""


def check_infra(ev: dict):
    bad = [r["task"] for r in ev["results"] if "APIConnectionError" in (r["agent_error"] or "")
           or "APITimeoutError" in (r["agent_error"] or "")]
    if bad:
        raise InfraError(f"LLM connection errors on {len(bad)} tasks: {bad}")


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="demo", help="runs/<name> 目录，已存在则续跑")
    ap.add_argument("--iterations", type=int, default=15)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--heldout-only", action="store_true", help="只重跑留出集评估")
    ap.add_argument("--reevals", type=int, default=3, help="候选最佳的评测次数（取平均）")
    args = ap.parse_args()
    random.seed(args.seed)
    run_dir = ROOT / "runs" / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"agent model={llm.AGENT_MODEL}  meta model={llm.META_MODEL}  run={run_dir}")

    nodes = load_nodes(run_dir)
    try:
        if not args.heldout_only:
            nodes = evolve_loop(run_dir, nodes, args)
        final_heldout(run_dir, nodes, args.workers, args.reevals)
    except InfraError as e:
        log(f"ABORT: {e}")
        log(f"推理服务恢复后用同样的命令续跑：uv run python -m rsi.evolve --run {args.run} --iterations N")
        raise SystemExit(2)


def evolve_loop(run_dir: Path, nodes: list[dict], args) -> list[dict]:
    if not nodes:
        source = (ROOT / "seed_agent.py").read_text()
        (run_dir / "node_000").mkdir(exist_ok=True)       # 先只放源码；node.json 等评测成功后再写
        (run_dir / "node_000" / "agent.py").write_text(source)
        log("evaluating seed agent on dev set ...")
        ev = evaluate(run_dir / "node_000" / "agent.py", DEV, args.workers)
        check_infra(ev)
        nodes = [{"id": 0, "parent": None, "status": "ok", "summary": "seed agent", "reason": None,
                  "created": time.time(), "eval": ev}]
        confirm(run_dir, nodes[0], args.reevals, args.workers)   # 基线也取平均，比较才公平
        save_node(run_dir, nodes[0], source)
        log(f"seed fitness over {args.reevals} runs: {nodes[0]['eval_mean']['fitness_runs']}")
        log(f"seed: {ev['solved']}/{ev['n']} tasks, {ev['tests_passed']}/{ev['tests_total']} tests")

    start = len(nodes)
    for i in range(start, start + args.iterations):
        parent = select_parent(nodes)
        psrc = (run_dir / f"node_{parent['id']:03d}" / "agent.py").read_text()
        log(f"[{i}] parent=node_{parent['id']:03d} ({parent['eval']['solved']}/{parent['eval']['n']}) → asking meta model ...")
        node = {"id": i, "parent": parent["id"], "created": time.time(), "eval": None, "reason": None}
        node["summary"], source, reason, node["repairs"] = propose(parent, psrc, lineage_history(nodes, parent),
                                                                       archive_ideas(nodes))
        if reason:
            node.update(status="rejected", reason=reason)
            save_node(run_dir, node, source)
            nodes.append(node)
            log(f"[{i}] REJECTED by guard after {node['repairs']} repairs: {reason}")
            continue
        save_node(run_dir, node, source)
        log(f"[{i}] {node['summary']}" + (f"  (passed guard after {node['repairs']} repair(s))" if node["repairs"] else ""))
        node["eval"] = evaluate(run_dir / f"node_{i:03d}" / "agent.py", DEV, args.workers)
        try:
            check_infra(node["eval"])
        except InfraError:
            shutil.rmtree(run_dir / f"node_{i:03d}")   # 不入档，续跑时重做这一轮
            raise
        # 什么都解不出来的变体不再作为父代（通常是写坏了）
        node["status"] = "ok" if node["eval"]["solved"] > 0 else "broken"
        best_before = max(node_fit(n) for n in nodes if n["status"] == "ok")
        if node["status"] == "ok" and node_fit(node) > best_before and args.reevals > 1:
            log(f"[{i}] single-run fitness {node_fit(node):.3f} beats best {best_before:.3f} → re-evaluating to confirm ...")
            try:
                confirm(run_dir, node, args.reevals, args.workers)
            except InfraError:
                shutil.rmtree(run_dir / f"node_{i:03d}")
                raise
            log(f"[{i}] confirmed fitness runs {node['eval_mean']['fitness_runs']} → mean {node_fit(node):.3f}")
        save_node(run_dir, node, source)
        nodes.append(node)
        best = max(node_fit(n) for n in nodes if n["status"] == "ok")
        ev = node["eval"]
        log(f"[{i}] dev {ev['solved']}/{ev['n']} tasks, {ev['tests_passed']}/{ev['tests_total']} tests, "
            f"fitness {node_fit(node):.3f} (parent {node_fit(parent):.3f}, best {best:.3f})")
    return nodes


def final_heldout(run_dir: Path, nodes: list[dict], workers: int, runs: int = 3):
    """留出集：进化过程中完全没见过的题，检验改进是否泛化（而不是过拟合开发集）。"""
    ok = [n for n in nodes if n["status"] == "ok"]
    # 只在复测过的节点里选最佳（单次评测的高分可能是运气）
    confirmed = [n for n in ok if n.get("eval_mean")] or ok
    best = max(confirmed, key=lambda n: (node_fit(n), -n["eval"]["llm_calls"]))
    out = {}
    for n in {0: nodes[0], best["id"]: best}.values():
        evs = []
        for k in range(runs):
            log(f"held-out eval of node_{n['id']:03d} ({k + 1}/{runs}) ...")
            ev = evaluate(run_dir / f"node_{n['id']:03d}" / "agent.py", HELDOUT, workers)
            check_infra(ev)
            evs.append(ev)
        ev = evs[0]
        ev["mean"] = {k: statistics.mean(e[k] for e in evs) for k in ("solved", "tests_passed", "score", "test_rate")}
        ev["mean"]["runs"] = runs
        ev["mean"]["tests_passed_runs"] = [e["tests_passed"] for e in evs]
        out[str(n["id"])] = ev
        m = ev["mean"]
        log(f"node_{n['id']:03d}: held-out mean {m['solved']:.1f}/{ev['n']} tasks, "
            f"{m['tests_passed']:.1f}/{ev['tests_total']} tests (runs: {m['tests_passed_runs']})")
    (run_dir / "heldout.json").write_text(json.dumps({"best": best["id"], "evals": out}, ensure_ascii=False, indent=1))
    log(f"done. report: uv run python -m rsi.report --run {run_dir.name}")


if __name__ == "__main__":
    main()
