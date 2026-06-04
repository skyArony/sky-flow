---
name: to-agent-review
description: 'Review agent decision-making inside Sky Flow by analyzing visible transcripts, execution records, tool calls, subagent ROI, fan-in, context management, runtime plan maintenance, and artifact writeback; output decision-chain issues, inefficiencies, and actionable workflow improvements.'
---

# to-agent-review

`to-agent-review` 是 Sky Flow 内部的 Agent 决策复盘入口。它分析可见会话、执行记录、工具调用、子代理产物、fan-in 结果、runtime plan 和 Sky Flow artifact 维护情况，定位决策链路问题、低效点和可落地改进项。

它不是普通代码 review，也不是项目私有复盘流程。默认产物写入 `${SKY_FLOW_ROOT}/backlog/agent-reivew/`，这是 Agent 复盘报告目录约定，不等同于调用 `to-backlog`，也不要求生成 `backlog` artifact。发现的改进可以进一步转入 Sky Flow `spec`、`plan`、`task` 或明确标记为暂不落地。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 如果输入是 Codex / Claude Code 原生 JSONL、agent-decision-log、昨日 / 指定日期日志或 automation 日报，先运行本目录 `scripts/preflight.py` 生成 compact manifest；不要默认手工扫全量 JSONL。
3. 默认用本目录 preflight helper 按 runtime、日期、当前项目根目录、compact 摘要和 Top session 生成 manifest；项目复盘必须过滤当前项目根目录，只有用户明确要求跨项目 / 全局复盘时才取消根目录过滤。
4. 先读 compact preflight 输出里的 `codex_cwd_filter`、`aggregate.decision_signals`、Top session 摘要、`candidate_bottlenecks` 和 `suggested_read_lines`，再决定需要精读哪些证据；只有诊断分歧或需要完整结构化输入时才去掉 `--compact`。
5. 精读 JSONL 行窗时优先使用 preflight helper 的行窗摘要能力；该摘要会遮蔽 hidden fields，并保留 `exit_code`、`original_token_count`、输出字符数和截断片段。
6. 确认输入范围：用户指定的 transcript、执行记录、日志片段、工具调用摘要、plan / task / handoff artifact、子代理输出或当前会话上下文；如果 preflight 后仍不足以复盘关键问题，先请求最小补充材料。
7. 建立证据地图：按时间线整理目标、关键决策、工具调用、失败 / 重试、等待、子代理派发、fan-in、验证、runtime plan 更新和 artifact 写回。
8. 按分析维度归类问题，区分必要等待、人类决策等待、基础设施等待、工具延迟和 Agent 低效；不要把 `expected no-match`、存在性探测、`git diff --no-index` 或轮询等待直接当作低效。
9. 填写固定量化信号清单；没有证据的项写 `unknown`，不要估算成事实。
10. 输出或更新 `${SKY_FLOW_ROOT}/backlog/agent-reivew/<yyyy-mm-dd>-<scope>.md`，默认采用 plain-language brief-first 结构：先用人话解释“问题是什么、为什么重要、下一步做什么”，再给指标和证据；每条建议必须有 ROI、落点、done-when 和 non-goal。
11. 需要改变长期 workflow 规则、计划或任务时，转入对应 Sky Flow 子能力：`to-spec`、`to-plan` 或 `to-task`。

## Preflight Helper

- `scripts/preflight.py` 是原生日志复盘的默认入口，用来在进入人工分析前完成项目归属过滤、成本聚合、失败 / 等待分类和安全行窗摘要。
- `--cwd` 默认过滤 Codex `session_meta.cwd`，防止把其他项目 session 写入当前项目日报；manifest 会保留 `excluded_by_cwd_count` 和 `excluded_by_cwd_top` 供跨项目判断。
- `--all-cwd` 只用于用户明确要求跨项目 / 全局 Agent 复盘的场景；这种报告必须在 Decision Brief 里说明跨项目范围。
- `--compact` 是 automation 日报默认输出，保留聚合判断和 Top evidence，但不展开完整 session 级嵌套 signal；需要完整机器输入时再去掉。
- `tool_output.high_output_context_read_count` / `top_high_output_context_read` 记录大输出上下文读取，按 `intent` 区分 `search`、`process`、`diff`、`helm`、`sqlite`、`transcript` 和 `other`；旧 `high_output_search_count` 只作为 search 子集兼容信号。
- 行窗摘要只输出结构化摘要，不输出完整 hidden reasoning / encrypted / thinking 字段；精读大型 transcript 时优先用它替代 raw JSONL 展开。

## Evidence Rules

- 只使用可见 transcript、工具调用、工具结果摘要、时间戳、子代理产物、runtime plan 状态和 Sky Flow artifact。
- 不引用、复述或重构隐藏 reasoning / thinking / encrypted 字段；如果日志中出现这类字段，只能作为事件计数或时间线锚点。
- 大型 transcript 优先抽取相关窗口和结构化摘要，不整段粘贴。
- 证据不足时写“证据不足”，并说明需要什么输入才能确认。
- 不把工具失败总数直接等同于低效；必须看失败后成功路径、等待类型和是否属于必要验证。

## Analysis Lenses

重点检查：

- 入口与路由：是否及时进入正确的 Sky Flow 子能力，是否漏读必要 artifact 或规范。
- 需求与假设：是否在关键歧义、scope 变化、契约不清时停止确认。
- 上下文管理：是否过早加载过多上下文、漏读关键来源、上下文包不完整，或 compaction / handoff 后恢复成本过高。
- 工具效率：是否重复搜索、重复读取、使用低效命令，或应脚本化而仍靠人工操作。
- 子代理 ROI：派发是否过早 / 过晚，任务包是否包含 mission、scope、no-touch、verification intent、output contract 和 stop condition。
- Fan-in：是否检查写入范围、冲突、验证证据、spec alignment、blocker 和状态回写。
- Runtime plan：是否及时维护运行时计划，是否记录并行批次、fan-in、blocker、next action 和动态 task 调整。
- Artifact 写回：plan / task / handoff / acceptance 是否记录稳定事实，而不是只留在聊天里。
- 验证与收敛：是否在合适阶段触发验证、`to-review`、`to-consolidation` 和 `validate-flow`。
- 决策质量：是否存在过早实现、过度设计、补丁式返工、未说明的 pushback 或低价值自动化。

## Quantitative Signals

复盘必须固定收集下面信号，但默认报告不逐项展开完整表。只使用可见 transcript、工具结果、runtime plan、子代理输出或 artifact 记录；不可见就写 `unknown`。默认只在 `Metrics Snapshot` 输出影响判断的 3-6 个指标，完整信号表只有在用户要求 full evidence mode、诊断分歧或后续自动化需要结构化输入时才展开到附录。

| Signal | Required Observation |
| --- | --- |
| `elapsed_time` | 总耗时、可见等待时间、明显空转时间。 |
| `tool_call_count` | 工具调用总数，并按 shell / file read / search / edit / validation / browser / subagent 等可见类别拆分。 |
| `failed_or_retried_calls` | 失败、超时、权限重试、无效命令和重复修正次数。 |
| `duplicate_context_reads` | 重复搜索、重复读取同一文件 / section、重复打开无新增信息的来源次数。 |
| `context_load_size` | 读取的大文件、长 transcript、批量输出或可能造成上下文压力的加载事件。 |
| `subagent_count` | 子代理数量、任务包完整度、完成 / blocked / needs-context 状态分布。 |
| `parallelism_efficiency` | 子代理是否真正并行、主会话等待时间、fan-in 是否阻塞关键路径。 |
| `fan_in_rounds` | fan-in 轮数、冲突次数、遗漏补传次数、是否检查 changed files / scope / evidence。 |
| `runtime_plan_updates` | runtime plan 更新次数、是否在 task start / completion / blocker / fan-in 后及时更新。 |
| `artifact_writebacks` | plan / task / acceptance / handoff / backlog / report 写回次数和遗漏点。 |
| `validation_evidence` | 验证命令 / 检查项、pass / fail / skipped、跳过理由。 |
| `blocker_and_question_count` | blocker、需要人类确认的问题、已解决 / 未解决数量。 |

## Recommendation Rules

每条建议必须包含 ROI：

- `High`：重复出现、影响明显、改动小，或能显著降低探索 / fan-in / 返工成本。
- `Medium`：有价值，但需要更多样本、跨 artifact 协调，或会增加维护面。
- `Low`：值得记录，但暂不建议马上执行。

每条建议必须给出落点：

- `spec`：Sky Flow 行为契约、artifact 规则或 workflow 语义需要澄清。
- `plan`：需要编排成阶段目标。
- `task`：可以直接拆成可执行工作。
- `agent-review-report`：只沉淀到 `${SKY_FLOW_ROOT}/backlog/agent-reivew/`，暂不转入正式 workflow artifact。
- `none`：明确不落地，并写明原因。

每条建议还必须给出 `Done when`：

- 说明完成条件或可观察验收信号，例如“模板不再生成冲突参数”“runner 写入 resolved path”“日报把 expected no-match 排除出失败榜”。
- 如果建议暂不落地，`Done when` 写“无需动作”，并在 non-goal 说明原因。

不要为了自动化而自动化。脚本化建议必须说明预期收益、触发频率、维护成本和暂不扩大的边界。

## Report Shape Rules

- 默认报告是给人做决策用的，不是给机器读的审计表。第一屏必须回答：昨天最值得关注什么、为什么重要、现在要做什么、什么不要误判。
- 用用户语言写主阅读路径；用户用中文时，主标题和字段名优先中文。避免只有 `F1` / `High` / `Impact` 这类内部标签而没有人话解释。
- `行动清单` 必须放在 `发现` 前面；不要让读者读完证据表才知道该做什么。
- `行动清单` 默认最多 3 条，表格最多 4 列：`优先级`、`做什么`、`何时算完成`、`落点`。复杂维护成本、ROI 细节放到发现卡片里，不要撑宽主表。
- 每条发现标题必须是可独立理解的短句，例如“远端诊断先读全量输出，挤占了上下文”，不要写成“F1. `High` high_output_context_read”。
- 每条发现第一行必须有 `一句话`，用非术语解释给没看过 transcript 的人听；如果这句话不能直接回答“这到底是什么意思”，重写。
- 不默认输出 `Signal Map`。需要保留信号映射时，把它放入 `证据附录`，不能位于主阅读路径。
- `指标依据` 最多 5 行，每行必须解释这个指标改变了什么判断；没有决策价值的固定信号只在附录或内部采集中保留。
- 每条发现默认最多 5 个 bullet：`一句话`、`为什么重要`、`怎么改`、`证据`、`落点 / 不做什么`。`证据` 最多 2 个锚点；长 UUID、完整路径和多段 line range 放到 `证据附录`。
- 写完报告后做一次通俗化自检：如果某个发现需要聊天里再解释一次才能懂，说明报告写得不够清楚，必须先改报告。

## Output Template

```markdown
# Agent Decision Review: <scope>

## 结论先说

- 一句话结论：<用人话说明这批会话最值得优化的问题。>
- 最大风险：<最大成本 / 风险，不堆指标名。>
- 下一步：<下一步最该落地的动作。>
- 不要误判：<明确不应优化或不应误判的方向。>

## 行动清单

| 优先级 | 做什么 | 何时算完成 | 落点 |
| --- | --- | --- | --- |
|  |  |  |  |

## 发现

### F1. <可独立理解的短句>

- 一句话：<不用术语解释这是什么意思。>
- 为什么重要：<影响成本、风险或返工。>
- 怎么改：<具体改法。>
- 证据：<最多 2 个锚点；长路径和完整 line range 放附录。>
- 落点 / 不做什么：<ROI、落点、non-goal。>

### F2. <可独立理解的短句>

- 一句话：
- 为什么重要：
- 怎么改：
- 证据：
- 落点 / 不做什么：

## 指标依据

| 指标 | 值 | 说明了什么 |
| --- | --- | --- |
|  |  |  |

## 不值得优化

| 项目 | 原因 |
| --- | --- |
|  |  |

## 证据附录

| 来源 | 行窗 | 用途 |
| --- | --- | --- |
|  |  |  |
```

## Output / Follow-up Rules

- 默认报告目录：`${SKY_FLOW_ROOT}/backlog/agent-reivew/`。
- 该目录只是复盘报告落点，不代表调用 `to-backlog`，也不自动创建 `backlog` artifact。
- 需要改变 Sky Flow 契约或 artifact schema 语义：进入 `to-spec`，不要在复盘报告里直接改规则。
- 需要实施一组改进：进入 `to-plan`，再由 `to-task` 拆 DAG。
- 已有 plan 下的明确小修：可建议新增 `task`，由 `to-implement` 调度。
- 复盘只形成观察和建议：保留在 `agent-review-report`。
- 只有创建或修改 Sky Flow artifact 时才运行 `validate-flow`；单纯写复盘报告不要求 artifact 校验。

## Boundaries

- 不做普通代码风险 review；实现风险交给 `to-review`。
- 不收敛 pending diff；补丁式实现和 fan-in 残留交给 `to-consolidation`。
- 不替代 `validate-flow` 检查 artifact/status 一致性。
- 除 `${SKY_FLOW_ROOT}/backlog/agent-reivew/` 这个通用复盘报告目录外，不写死项目路径、项目角色称呼、业务术语或运行时专属命令。
- 不自动修改 workflow 规则、routing、spec、plan 或 task；复盘只给建议，除非用户明确要求落地。

## Self-Review

- Hidden reasoning：是否避免引用或复述不可见 reasoning / thinking / encrypted 内容。
- Evidence：每个发现是否有可见证据和来源索引。
- Classification：是否区分必要等待、人类等待、基础设施等待、工具延迟和 Agent 低效。
- ROI：每条建议是否有优先级、预期收益、维护成本和落点。
- Sky Flow alignment：改进是否按性质进入 agent-review-report / spec / plan / task / none，而不是私有项目流程。
- Readability：第一屏是否不用解释就能看懂；每个 finding 是否有“这到底是什么意思”的人话版本。
- Brevity：是否合并重复问题，避免长篇粘贴 transcript。
