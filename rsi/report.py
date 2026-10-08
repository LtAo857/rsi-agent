"""生成自包含的 HTML 报告：uv run python -m rsi.report --run demo"""
import argparse
import difflib
import html
import json

from rsi.evaluate import ROOT
from rsi.evolve import load_nodes, node_fit


def build(run: str):
    run_dir = ROOT / "runs" / run
    nodes = load_nodes(run_dir)
    by_id = {n["id"]: n for n in nodes}
    src = {n["id"]: (run_dir / f"node_{n['id']:03d}" / "agent.py").read_text() for n in nodes}
    heldout = json.loads((run_dir / "heldout.json").read_text()) if (run_dir / "heldout.json").exists() else None

    ok = [n for n in nodes if n["status"] == "ok"]
    best = by_id[heldout["best"]] if heldout else max(ok, key=node_fit)
    lineage, cur = [], best
    while cur:
        lineage.append(cur["id"])
        cur = by_id.get(cur["parent"])
    lineage.reverse()

    rows = []
    for n in nodes:
        ev = n.get("eval_mean") or n["eval"]   # 复测过的节点显示平均值
        parent_src = src.get(n["parent"], "")
        diff = "".join(difflib.unified_diff(parent_src.splitlines(True), src[n["id"]].splitlines(True),
                                            f"node_{n['parent']}", f"node_{n['id']}")) if n["parent"] is not None else src[0]
        rows.append({"id": n["id"], "parent": n["parent"], "status": n["status"], "summary": n["summary"],
                     "reason": n["reason"], "solved": ev["solved"] if ev else None, "n": ev["n"] if ev else None,
                     "tp": ev.get("tests_passed") if ev else None, "tt": ev.get("tests_total") if ev else None,
                     "repairs": n.get("repairs", 0),
                     "calls": n["eval"]["llm_calls"] if ev else None, "tokens": n["eval"]["tokens"] if ev else None,
                     "tasks": {r["task"]: r["solved"] for r in n["eval"]["results"]} if ev else {},
                     "runs": ev.get("runs", 1) if ev else 0,
                     "lineage": n["id"] in lineage, "diff": diff})
    ho = None
    if heldout:
        ho = {k: {"solved": v.get("mean", v)["solved"], "n": v["n"], "tp": v.get("mean", v).get("tests_passed"),
                  "tt": v.get("tests_total"), "runs": v.get("mean", {}).get("runs", 1), "tasks": {r["task"]: r["solved"] for r in v["results"]}}
              for k, v in heldout["evals"].items()}
    data = {"run": run, "rows": rows, "best": best["id"], "lineage": lineage, "heldout": ho}
    comparisons = "".join(
        f'<li><a href="comparisons/{html.escape(p.parent.name, quote=True)}/report.html">'
        f'{html.escape(p.parent.name)}</a></li>'
        for p in sorted((run_dir / "comparisons").glob("*/report.html")))
    comparison_section = ("<h2>同预算基线对照</h2><div class=\"card\"><ul>" + comparisons + "</ul></div>") if comparisons else ""
    out = run_dir / "report.html"
    out.write_text(TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
                   .replace("__RUN__", html.escape(run))
                   .replace("__COMPARISONS__", comparison_section)
                   .replace("__DEVN__", str(nodes[0]["eval"]["n"])).replace("__DEVT__", str(nodes[0]["eval"].get("tests_total", "?"))))
    return out


TEMPLATE = r"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Self-Improving Agent</title>
<style>
:root{color-scheme:light;--bg:#fcfcfb;--card:#ffffff;--line:#e4e3de;--text:#0b0b0b;--text2:#52514e;--muted:#8a8984;
--s1:#2a78d6;--s2:#eb6834;--grid:#eeede9;--bad:#e34948;--good:#008300;--code:#f5f4f0}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#1a1a19;--card:#222220;--line:#383835;
--text:#fff;--text2:#c3c2b7;--muted:#8f8e86;--s1:#3987e5;--s2:#d95926;--grid:#2c2c2a;--bad:#e66767;--good:#3fa33f;--code:#262624}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#1a1a19;--card:#222220;--line:#383835;--text:#fff;--text2:#c3c2b7;--muted:#8f8e86;
--s1:#3987e5;--s2:#d95926;--grid:#2c2c2a;--bad:#e66767;--good:#3fa33f;--code:#262624}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:32px 0 12px}.sub{color:var(--text2);margin:0 0 20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi .l{color:var(--text2);font-size:12px}.kpi .v{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums}.kpi .d{color:var(--text2);font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;overflow-x:auto}
svg text{fill:var(--text2);font-size:11px}.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--text2);font-size:12px;margin-bottom:8px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
#tip{position:fixed;pointer-events:none;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;
font-size:12px;max-width:320px;box-shadow:0 4px 16px rgba(0,0,0,.12);display:none;z-index:9}
table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--text2);font-weight:500}td.num{font-variant-numeric:tabular-nums;white-space:nowrap}tr.row{cursor:pointer}tr.row:hover{background:var(--code)}
.tag{font-size:11px;padding:1px 6px;border-radius:4px;border:1px solid var(--line);color:var(--text2);white-space:nowrap}
.tag.lin{border-color:var(--s2);color:var(--text)}
pre{background:var(--code);border-radius:8px;padding:12px;overflow:auto;font-size:12px;line-height:1.45;margin:6px 0 0;max-height:520px}
.add{color:var(--good)}.del{color:var(--bad)}
.steps{display:flex;flex-direction:column;gap:8px}.step{display:flex;gap:12px;align-items:baseline}
.step b{font-variant-numeric:tabular-nums;min-width:64px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:6px}
.cell{font-size:11px;padding:4px 6px;border-radius:5px;border:1px solid var(--line);color:var(--text2)}.cell.y{border-color:var(--good);color:var(--text)}
.cell.y::before{content:"✓ ";color:var(--good)}.cell.n::before{content:"✗ ";color:var(--bad)}
</style></head><body><main>
<h1>自我改进的 Coding Agent</h1>
<p class="sub">run: __RUN__ · 每个节点由 meta 模型读取父代源码后改写产生；纵轴 = 开发集测试通过率（__DEVN__ 题共 __DEVT__ 条测试），「整题」= 一道题的测试全部通过；复测过的节点为多次平均</p>
<div class="kpis" id="kpis"></div>
__COMPARISONS__
<h2>进化轨迹</h2>
<div class="card"><div class="legend"><span><i style="background:var(--s1)"></i>评测过的 Agent</span>
<span><i style="background:var(--s2)"></i>最佳 Agent 的谱系</span><span><i style="background:transparent;border:1.5px solid var(--muted)"></i>被安全层拒绝 / 写坏（画在 0%）</span>
<span>— 虚线：历史最佳</span></div><svg id="chart" width="100%" height="300"></svg></div>
<h2>最佳 Agent 是怎么一步步进化来的</h2><div class="card steps" id="lineage"></div>
<h2 id="hoh">留出集（进化中从未见过的题）</h2><div class="card" id="heldout"></div>
<h2>全部节点 <span class="sub" style="font-size:12px">点击行查看相对父代的代码 diff</span></h2>
<div class="card"><table><thead><tr><th>#</th><th>父代</th><th>测试 · 整题</th><th>LLM 调用</th><th>改动</th></tr></thead><tbody id="tbody"></tbody></table></div>
</main><div id="tip"></div>
<script>
const D=__DATA__;const R=D.rows,byId=Object.fromEntries(R.map(r=>[r.id,r]));const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const seed=byId[0],best=byId[D.best],nRej=R.filter(r=>r.status!=="ok").length;
const pct=(a,b)=>b?Math.round(100*a/b)+"%":"—",fmt=v=>Number.isInteger(v)?v:v.toFixed(1);
const kp=[["种子 Agent（开发集）",pct(seed.tp,seed.tt),`整题 ${fmt(seed.solved)}/${seed.n} · 只调用一次模型`],
 ["最佳 Agent（开发集）",pct(best.tp,best.tt),`整题 ${fmt(best.solved)}/${best.n} · node_${D.best} · 第 ${D.lineage.length-1} 代`]];
if(D.heldout){const a=D.heldout["0"],b=D.heldout[String(D.best)];kp.push(["留出集：种子 → 最佳",`${pct(a.tp,a.tt)} → ${pct(b.tp,b.tt)}`,`整题 ${fmt(a.solved)} → ${fmt(b.solved)}（共 ${a.n} 题，从未见过${a.runs>1?`，${a.runs} 次平均`:""}）`]);}
kp.push(["被拒绝 / 写坏的变体",String(nRej),`共 ${R.length-1} 次改写尝试`]);
$("#kpis").innerHTML=kp.map(([l,v,d])=>`<div class="kpi"><div class="l">${l}</div><div class="v">${v}</div><div class="d">${d}</div></div>`).join("");
// chart
const svg=$("#chart"),W=svg.clientWidth||900,H=300,m={l:44,r:16,t:12,b:32},N=100;
const val=r=>r.tt?100*r.tp/r.tt:0;
const x=i=>m.l+(R.length<2?0:i/(R.length-1))*(W-m.l-m.r),y=v=>m.t+(1-v/N)*(H-m.t-m.b);
let g="";for(let v=0;v<=N;v+=25){g+=`<line x1="${m.l}" x2="${W-m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)"/><text x="${m.l-8}" y="${y(v)+4}" text-anchor="end">${v}%</text>`;}
R.forEach((r,i)=>{if(R.length<=30||i%Math.ceil(R.length/15)===0)g+=`<text x="${x(i)}" y="${H-10}" text-anchor="middle">${r.id}</text>`;});
let run=0,pts=[];R.forEach((r,i)=>{if(r.status==="ok")run=Math.max(run,val(r));pts.push(`${x(i)},${y(run)}`);});
g+=`<polyline points="${pts.join(" ")}" fill="none" stroke="var(--muted)" stroke-width="1.5" stroke-dasharray="4 4"/>`;
const idx=Object.fromEntries(R.map((r,i)=>[r.id,i]));const yy=r=>r.status==="ok"||r.status==="broken"?y(val(r)):y(0);
R.forEach(r=>{if(r.parent===null)return;const p=byId[r.parent],lin=r.lineage&&p.lineage;
 g+=`<line x1="${x(idx[p.id])}" y1="${yy(p)}" x2="${x(idx[r.id])}" y2="${yy(r)}" stroke="${lin?"var(--s2)":"var(--line)"}" stroke-width="${lin?2:1}"/>`;});
R.forEach(r=>{const cx=x(idx[r.id]),cy=yy(r),okk=r.status==="ok";
 g+=`<circle cx="${cx}" cy="${cy}" r="${r.lineage?6:5}" fill="${okk?(r.lineage?"var(--s2)":"var(--s1)"):"var(--card)"}" stroke="${okk?"var(--card)":"var(--muted)"}" stroke-width="2"/>`;
 g+=`<circle cx="${cx}" cy="${cy}" r="14" fill="transparent" data-id="${r.id}"/>`;});
svg.setAttribute("viewBox",`0 0 ${W} ${H}`);svg.innerHTML=g;
const tip=$("#tip");svg.addEventListener("mousemove",e=>{const id=e.target.dataset?.id;if(id===undefined){tip.style.display="none";return;}
 const r=byId[id];tip.innerHTML=`<b>node_${r.id}</b>${r.parent!==null?` ← node_${r.parent}`:""}<br>${r.status==="ok"||r.status==="broken"?`测试 <b>${pct(r.tp,r.tt)}</b> · 整题 ${fmt(r.solved)}/${r.n}${r.runs>1?` · ${r.runs} 次评测平均`:""} · ${r.calls} 次调用${r.repairs?` · 修正 ${r.repairs} 次后过审`:""}<br>`:`<span style="color:var(--bad)">拒绝：${esc(r.reason)}</span><br>`}${esc(r.summary)}`;
 tip.style.display="block";tip.style.left=Math.min(e.clientX+14,innerWidth-340)+"px";tip.style.top=(e.clientY+14)+"px";});
svg.addEventListener("mouseleave",()=>tip.style.display="none");
// lineage
$("#lineage").innerHTML=D.lineage.map(id=>{const r=byId[id],p=byId[r.parent];const d=p?Math.round(val(r)-val(p)):null;
 return `<div class="step"><b>node_${id}</b><span class="tag lin">${pct(r.tp,r.tt)}${d!==null?` (${d>=0?"+":""}${d})`:""} · 整题 ${fmt(r.solved)}${r.runs>1?` · ×${r.runs}`:""}</span><span>${esc(r.summary)}</span></div>`;}).join("");
// heldout
if(D.heldout){const a=D.heldout["0"],b=D.heldout[String(D.best)];const cell=(t,v)=>`<div class="cell ${v?"y":"n"}">${t}</div>`;
 $("#heldout").innerHTML=`<p style="margin:0 0 6px;color:var(--text2)">种子 Agent：测试 ${pct(a.tp,a.tt)} · 整题 ${fmt(a.solved)}/${a.n}${a.runs>1?`（${a.runs} 次平均，下方格子为第 1 次）`:""}</p><div class="grid">${Object.entries(a.tasks).map(([t,v])=>cell(t,v)).join("")}</div>
 <p style="margin:14px 0 6px;color:var(--text2)">最佳 Agent（node_${D.best}）：测试 ${pct(b.tp,b.tt)} · 整题 ${fmt(b.solved)}/${b.n}</p><div class="grid">${Object.entries(b.tasks).map(([t,v])=>cell(t,v)).join("")}</div>`;}
else{$("#hoh").style.display="none";$("#heldout").style.display="none";}
// table
const fmtDiff=s=>esc(s).split("\n").map(l=>l.startsWith("+")&&!l.startsWith("+++")?`<span class="add">${l}</span>`:l.startsWith("-")&&!l.startsWith("---")?`<span class="del">${l}</span>`:l).join("\n");
$("#tbody").innerHTML=R.map(r=>`<tr class="row" data-id="${r.id}"><td class="num">${r.id}${r.lineage?' <span class="tag lin">谱系</span>':""}</td><td class="num">${r.parent??"—"}</td>
<td class="num">${r.status==="rejected"?'<span class="tag">拒绝</span>':r.status==="broken"?`<span class="tag">写坏</span> ${r.solved}/${r.n}`:`${pct(r.tp,r.tt)} · ${fmt(r.solved)}/${r.n}${r.runs>1?` <span class="tag">×${r.runs} 平均</span>`:""}`}${r.repairs?` <span class="tag">修正×${r.repairs}</span>`:""}</td>
<td class="num">${r.calls??"—"}</td><td>${esc(r.summary)}${r.reason?`<br><span style="color:var(--bad);font-size:12px">${esc(r.reason)}</span>`:""}</td></tr>
<tr hidden id="d${r.id}"><td colspan="5"><pre>${fmtDiff(r.diff)}</pre></td></tr>`).join("");
$("#tbody").addEventListener("click",e=>{const tr=e.target.closest("tr.row");if(tr){const d=$("#d"+tr.dataset.id);d.hidden=!d.hidden;}});
</script></body></html>"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="demo")
    print(build(ap.parse_args().run))
