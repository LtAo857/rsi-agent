# rsi-demo：会改写自己的 Coding Agent

迷你版 [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954)：一个很弱的种子 Agent，由 meta 模型阅读它的**源码 + 失败案例**，
改写出新 Agent；新 Agent 评测后入档，再被继续改写。被改进的对象就是「解题者」本身，这是它区别于普通 prompt 优化的地方。

```
            ┌──────────── 档案库（所有版本 + 分数） ◄──────────┐
            │  按「分数高 + 子代少」采样父代                    │
            ▼                                                │
  meta 模型 读源码+失败案例+历史尝试 ─► 新 Agent 源码 ─► 安全层 ─► 开发集评测
                                                       │ 拒绝也入档
            最终：种子 vs 最佳 在 留出集 上对比（检验泛化）
```

## 运行

支持自动读取项目根目录 `.env`（`KEY=value` 格式，参见 `.env.example`）；已设置的环境变量优先。

```bash
uv sync
export DASHSCOPE_API_KEY=sk-...           # 或 LLM_API_KEY + LLM_BASE_URL（任意 OpenAI 兼容接口）
export AGENT_MODEL=qwen-turbo             # 被进化的 Agent 用的模型：弱一点才有提升空间
export META_MODEL=qwen3-max               # 负责改写 Agent 的模型：越强越好（弱 meta 会很快让进化进入平台期）
uv run python -m rsi.evolve --run demo --iterations 15    # 续跑：同一个 --run 再执行一次
uv run python -m rsi.report --run demo                    # 生成 runs/demo/report.html
```

不花钱先看效果（假 LLM，秒级跑完）：

```bash
uv run python scripts/fake_llm.py &
LLM_BASE_URL=http://127.0.0.1:18765/v1 LLM_API_KEY=x AGENT_MODEL=fake-agent META_MODEL=fake-meta \
  uv run python -m rsi.evolve --run fake --iterations 5 && uv run python -m rsi.report --run fake
```

## 同预算强基线对照

用同一个解题模型比较四种固定策略，默认在 16 道留出题上分别设置每题 1、4、8 次调用上限，每组复测 3 次：

| 策略 | 行为 |
|---|---|
| `seed` | 该实验保存的初始 Agent，一次生成 |
| `repair` | 生成 → 可见样例测试 → 根据错误修复，样例全过即停止 |
| `best_of_n` | 用完调用预算独立生成候选，按可见样例通过数选择，同分保留最早候选 |
| `evolved` | 仅根据开发集成绩选定最佳已复测版本，保持原策略 |

```bash
# 检查计划，不调用模型；默认完整实验最多 2016 次策略调用（服务重试另计）
uv run python -m rsi.compare --run demo4 --plan

# 配好 API Key、AGENT_MODEL 后运行；同名命令可续跑
uv run python -m rsi.compare --run demo4 --name baselines --budgets 1 4 8 --repeats 3
uv run python -m rsi.report --run demo4
```

结果保存在 `runs/demo4/comparisons/baselines/`：`results.json` 含每题结果、模型、预算、题库与源码哈希；
`agents/` 保存本次参评源码；`report.html` 展示通过率、实际调用数、输入加输出 token 数以及进化版本相对各基线的配对胜负。
重新生成主报告后会附上对照报告入口。配置或源码变化时必须换一个 `--name`，避免不同实验混在一起。
各组评测随机排序，完成一组即保存。API 错误单独写入 `last_error.json` 并中止，恢复后重跑该组。

无需真实 API 的流程验证（先按上文启动 `scripts/fake_llm.py`）：

```bash
LLM_BASE_URL=http://127.0.0.1:18765/v1 LLM_API_KEY=x AGENT_MODEL=fake-agent \
  uv run python -m rsi.compare --run demo4 --name smoke --budgets 1 4 --repeats 1 --limit 2
uv run python -m unittest discover -s tests -v
```

**如何解读**：这是相同调用上限对照，实际调用数和 token 成本仍可能不同；每次生成上限为 4096 tokens、
每题总时间上限为 300 秒。1 次调用档位也用于观察已有进化策略在低预算下是否退化，未针对每个档位重新进化。
假模型或 `--limit` 子集运行会明确标为流程验证。复测范围不是置信区间；一次进化实验也不能代表跨实验稳定性。
报告只计推理开销，未计入进化搜索成本。若根据留出集结果继续调整策略，最终验证需要另外准备未见题目。
在此基础上，还需扩充题库、做多次独立进化实验，才能更有力地判断自动进化是否优于人工设计。

进化本身也有平台期：弱 meta 模型（如 flash 级）往往在十几代内就停止进步——demo4 的最佳出现在第 5 代，之后连续
5 代无一代突破，并伴随退化/写坏/被拒。遇到平台期时，优先换更强的 `META_MODEL` 而非盲目增加 `--iterations`。

## 结构

| 文件 | 作用 |
|---|---|
| `seed_agent.py` | 第 0 代：只问一次模型，取第一个代码块 |
| `rsi/evolve.py` | 进化循环、父代采样、meta prompt、留出集评估 |
| `rsi/tasks.py` 🔒 | 48 道题（32 开发 / 16 留出），每题有可见样例 + 隐藏边界测试 |
| `rsi/runner.py` 🔒 | 子进程里加载 Agent，只暴露 `tools.llm / run_tests / log`，隐藏测试不进这个进程 |
| `rsi/sandbox.py` 🔒 | 独立子进程 + 超时 + 随机 nonce 执行代码和测试 |
| `rsi/guard.py` 🔒 | 静态检查：import 白名单、禁 `open/exec/eval`、禁私有属性、禁写死题目名 |
| `rsi/evaluate.py` 🔒 | 评测；启动时对 🔒 文件做 sha256，改动即中止 |
| `rsi/report.py` | 进化曲线、最佳谱系、留出集对比、每代 diff |
| `rsi/compare.py` | 同调用上限基线对照、实验快照、续跑与独立报告 |
| `baselines/` | 人工编写的测试修复、多候选选择策略 |
| `scripts/check_tasks.py` | 用参考实现校验题库本身正确 |

## 防作弊设计（demo 里值得讲的点）

- **Agent 看不到隐藏测试**：只能用 `run_tests` 跑可见样例；隐藏测试只在评测进程里出现。
- **Agent 改不了评测**：它只能输出自己的源码；评测文件有哈希锁；import 白名单拦掉 `os/subprocess/socket`。
- **不能针对题目写死**：源码里出现题目函数名即拒绝。
- **留出集**：meta 模型从没见过这 16 题。开发集涨而留出集不涨 = 过拟合，这本身就是一个好的讨论点。
- 每题 8 次 LLM 调用、300 秒预算，防止「靠堆调用刷分」。

> 注：候选代码在本机子进程里执行，没有网络/文件系统隔离。要更严格可以把 `sandbox.run_tests` 换成 `docker run --network none`。
