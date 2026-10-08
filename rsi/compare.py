"""固定 Agent 的同调用上限对照；最佳版本仅按开发集选择。"""
import argparse
import hashlib
import html
import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

from rsi import guard, llm
from rsi.evaluate import AGENT_TIMEOUT, LOCKED, ROOT, evaluate
from rsi.evolve import load_nodes, node_fit
from rsi.tasks import DEV, HELDOUT

STRATEGIES = ("seed", "repair", "best_of_n", "evolved")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def select_best(nodes):
    ok = [n for n in nodes if n.get("status") == "ok"]
    confirmed = [n for n in ok if n.get("eval_mean")] or ok
    if not confirmed:
        raise ValueError("run has no successful agents")
    if any("test_rate" not in (n.get("eval_mean") or n["eval"]) for n in confirmed):
        raise ValueError("old archive lacks test_rate; use a current-format run such as demo4")
    return max(confirmed, key=lambda n: (node_fit(n), -n["eval"]["llm_calls"]))


def prepare(args):
    run_dir = ROOT / "runs" / args.run
    best = select_best(load_nodes(run_dir))
    paths = {"seed": run_dir / "node_000/agent.py",
             "repair": ROOT / "baselines/repair.py",
             "best_of_n": ROOT / "baselines/best_of_n.py",
             "evolved": run_dir / f"node_{best['id']:03d}/agent.py"}
    sources = {k: p.read_text() for k, p in paths.items()}
    for name, source in sources.items():
        if reason := guard.check(source):
            raise ValueError(f"{name} rejected by guard: {reason}")
    tasks = DEV if args.split == "dev" else HELDOUT
    if args.limit:
        tasks = tasks[:args.limit]
    budgets = sorted(set(args.budgets))
    config = {"run": args.run, "best_node": best["id"], "split": args.split,
              "task_ids": [t["id"] for t in tasks], "tasks_sha256": digest(json.dumps(tasks, sort_keys=True)),
              "model": llm.AGENT_MODEL, "base_url": llm.BASE_URL,
              "budgets": budgets, "repeats": args.repeats, "workers": args.workers,
              "order_seed": args.order_seed, "timeout_seconds": AGENT_TIMEOUT,
              "smoke_test": bool(args.limit) or llm.AGENT_MODEL.startswith("fake"),
              "agent_sha256": {k: digest(v) for k, v in sources.items()},
              "harness_sha256": {p: digest((ROOT / p).read_text())
                                  for p in LOCKED + ["rsi/llm.py", "rsi/compare.py"]}}
    return sources, tasks, config


def summarize(data):
    rows = []
    for budget in data["config"]["budgets"]:
        for name in STRATEGIES:
            records = [r["eval"] for r in data["records"] if r["budget"] == budget and r["strategy"] == name]
            if not records:
                continue
            mean = lambda key: statistics.mean(r[key] for r in records)
            rows.append({"budget": budget, "strategy": name, "repeats": len(records),
                         "score": mean("score"), "score_min": min(r["score"] for r in records),
                         "score_max": max(r["score"] for r in records), "test_rate": mean("test_rate"),
                         "calls_per_task": statistics.mean(r["llm_calls"] / r["n"] for r in records),
                         "tokens_per_task": statistics.mean(r["tokens"] / r["n"] for r in records),
                         "errors": sum(bool(t["agent_error"]) for r in records for t in r["results"])})
    return rows


def paired_deltas(data):
    """在相同预算、题目和复测编号上配对；仅描述差异，不声称统计显著。"""
    lookup = {(r["budget"], r["strategy"], r["repeat"]): r["eval"] for r in data["records"]}
    rows = []
    for budget in data["config"]["budgets"]:
        for baseline in ("seed", "repair", "best_of_n"):
            wins = losses = ties = 0
            for repeat in range(data["config"]["repeats"]):
                a = lookup.get((budget, "evolved", repeat))
                b = lookup.get((budget, baseline, repeat))
                if a is None or b is None:
                    continue
                by_task = {t["task"]: t["solved"] for t in b["results"]}
                for t in a["results"]:
                    delta = int(t["solved"]) - int(by_task[t["task"]])
                    wins += delta > 0
                    losses += delta < 0
                    ties += delta == 0
            total = wins + losses + ties
            if total:
                rows.append({"budget": budget, "baseline": baseline, "wins": wins,
                             "losses": losses, "ties": ties, "score_delta": (wins - losses) / total})
    return rows


def build_report(data, directory):
    esc = html.escape
    cfg = data["config"]
    summary = summarize(data)
    rows = "".join(
        f"<tr><td>{r['budget']}</td><td>{r['strategy']}</td><td>{r['repeats']}</td>"
        f"<td>{r['score']:.1%}</td><td>{r['score_min']:.1%}–{r['score_max']:.1%}</td>"
        f"<td>{r['test_rate']:.1%}</td><td>{r['calls_per_task']:.2f}</td>"
        f"<td>{r['tokens_per_task']:,.0f}</td><td>{r['errors']}</td></tr>" for r in summary)
    pairs = "".join(
        f"<tr><td>{r['budget']}</td><td>{r['baseline']}</td><td>{r['score_delta']:+.1%}</td>"
        f"<td>{r['wins']} / {r['losses']} / {r['ties']}</td></tr>" for r in paired_deltas(data))
    expected = len(cfg["budgets"]) * len(STRATEGIES) * cfg["repeats"]
    status = "离线 / 子集验证，不代表真实模型效果" if cfg["smoke_test"] else "真实模型对照"
    page = f"""<!doctype html><html lang="zh"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Agent 基线对照</title>
<style>body{{font:15px/1.65 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#20242b}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}
th{{background:#f2f5fa}}.scroll{{overflow:auto}}.note{{background:#eef3fb;padding:16px;border-radius:8px}}h2{{margin-top:30px}}</style>
<h1>Agent 同预算基线对照</h1><p class="note">{status} · 已完成 {len(data['records'])}/{expected} 组评测</p>
<p>模型：{esc(cfg['model'])} · 数据集：{esc(cfg['split'])}（{len(cfg['task_ids'])} 题） ·
进化版本：node_{cfg['best_node']:03d}（仅按开发集选择） · 每题超时：{cfg['timeout_seconds']} 秒</p>
<p>所有策略使用相同模型、题目和调用上限。调用上限不等于实际调用数，也不等于相同 token 成本。
seed 只调用一次；repair 在可见样例全部通过时停止；best_of_n 用完预算并按可见样例选择，同分取最早候选；evolved 保留原有策略。
每次调用最多生成 4096 tokens；表中 token 包含输入和输出，服务内部重试不另算策略调用。</p>
<h2>通过率与推理开销</h2><div class="scroll"><table><tr><th>调用上限/题</th><th>策略</th><th>复测次数</th>
<th>整题通过率</th><th>复测范围</th><th>测试通过率</th><th>调用/题</th><th>tokens/题</th><th>运行错误数</th></tr>{rows}</table></div>
<h2>进化版本相对基线</h2><table><tr><th>调用上限/题</th><th>对照基线</th><th>整题通过率差</th><th>胜 / 负 / 平</th></tr>{pairs}</table>
<p>胜负按相同题目和复测编号配对。复测范围是观测最小值到最大值，并非置信区间；同一道题重复评测不算新的独立题目。
这是一次进化实验中固定版本的对照，尚未验证跨独立进化实验的稳定性；本报告也未计入进化搜索阶段的模型成本。
若根据本报告继续调参，这批留出题就成为开发依据，最终结论需要新的未见题目。</p>
<p>原始结果与源码哈希：<a href="results.json">results.json</a>；本次使用的源码保存在 agents/。</p></html>"""
    (directory / "report.html").write_text(page)
    return directory / "report.html"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", default="demo4")
    ap.add_argument("--name", default="baselines", help="runs/<run>/comparisons/<name>，同名自动续跑")
    ap.add_argument("--split", choices=("dev", "heldout"), default="heldout")
    ap.add_argument("--budgets", type=int, nargs="+", default=[1, 4, 8])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--order-seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0, help="只评测前 N 题；标记为流程验证")
    ap.add_argument("--plan", action="store_true", help="显示计划，不调用模型或写文件")
    args = ap.parse_args()
    if any(Path(s).name != s or s in (".", "..", "") for s in (args.run, args.name)):
        ap.error("run/name must be plain directory names")
    if min(args.budgets) < 1 or args.repeats < 1 or args.workers < 1 or args.limit < 0:
        ap.error("budgets/repeats/workers must be positive; limit must be nonnegative")
    sources, tasks, config = prepare(args)
    jobs = [(b, s, r) for b in config["budgets"] for s in STRATEGIES for r in range(args.repeats)]
    random.Random(args.order_seed).shuffle(jobs)
    if args.plan:
        print(json.dumps({"config": config, "evaluation_groups": len(jobs),
                          "max_strategy_calls": len(tasks) * args.repeats *
                          sum(1 + 3 * b for b in config["budgets"])}, ensure_ascii=False, indent=2))
        return
    if not llm.API_KEY and not llm.AGENT_MODEL.startswith("fake"):
        ap.error("set DASHSCOPE_API_KEY or LLM_API_KEY before running; use --plan to inspect without calls")
    directory = ROOT / "runs" / args.run / "comparisons" / args.name
    result_path = directory / "results.json"
    if result_path.exists():
        data = json.loads(result_path.read_text())
        if data["config"] != config:
            ap.error("configuration/source changed; choose a new --name to avoid mixing experiments")
        for name, source in sources.items():
            if (directory / "agents" / f"{name}.py").read_text() != source:
                ap.error("saved agent snapshot changed; choose a new --name")
    else:
        (directory / "agents").mkdir(parents=True, exist_ok=True)
        for name, source in sources.items():
            (directory / "agents" / f"{name}.py").write_text(source)
        data = {"config": config, "created": datetime.now(timezone.utc).isoformat(), "records": []}
        write_json(result_path, data)
    done = {(r["budget"], r["strategy"], r["repeat"]) for r in data["records"]}
    for budget, strategy, repeat in jobs:
        if (budget, strategy, repeat) in done:
            continue
        print(f"[{len(data['records']) + 1}/{len(jobs)}] {strategy} budget={budget} repeat={repeat + 1}", flush=True)
        ev = evaluate(directory / "agents" / f"{strategy}.py", tasks, args.workers, max_calls=budget)
        bad = [r for r in ev["results"] if r.get("llm_errors") or "runner crashed:" in (r["agent_error"] or "")]
        if bad:
            write_json(directory / "last_error.json", {"strategy": strategy, "budget": budget, "repeat": repeat, "eval": ev})
            build_report(data, directory)
            raise SystemExit("API/runner failure: group not scored; see last_error.json and resume with the same command")
        data["records"].append({"budget": budget, "strategy": strategy, "repeat": repeat, "eval": ev})
        write_json(result_path, data)
        build_report(data, directory)
        print(f"  solved={ev['solved']}/{ev['n']} calls={ev['llm_calls']} tokens={ev['tokens']}", flush=True)
    print(build_report(data, directory))


if __name__ == "__main__":
    main()
