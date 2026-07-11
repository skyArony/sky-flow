---
name: sky-flow
description: 'Lightweight artifact-based workflow suite centered on durable specs, spec-derived runtime goal selection, compact semantic Progress snapshots, and native execution. Use for Sky Flow, to-* workflows, pick-goal, spec design and progress, issue capture, implementation, testing, review, acceptance, backlog, handoff, validation, commits, or reusable technical knowledge.'
---

# Sky Flow

Sky Flow 是轻量、spec-direct 的通用工作流套件。长期设计、稳定约束、实现 readiness、关键进度和验证证据集中在 `spec`；执行拆解、owner、依赖、并行和子代理调度交给原生 runtime 动态处理。

它不是所有工作的默认入口。简单工作直接执行；只有需要长期设计、跨会话恢复、人类 gate、长期阻塞、易失交接或可复用知识时才创建对应 artifact。

## Quick Path

1. 判断是否进入 Sky Flow：
   - 用户显式提到 Sky Flow、子能力或 workflow artifact：进入。
   - 需要长期设计、文件化进度、人类验收、backlog、handoff 或知识沉淀：进入。
   - 简单查询、解释、局部修改或一次性命令：直接使用 runtime。
2. 需要读取、创建或修改 artifact 时确定 runtime 配置：
   - `SKY_FLOW_ROOT` 默认 `docs`。
   - `SKY_FLOW_LANG` 默认跟随用户语言；脚本默认 `简体中文`。
   - 不读取额外项目配置文件。
3. 选择子能力：
   - 用户显式点名时优先使用。
   - debug、testing、review、commit、consolidation、acceptance、knowledge、validate-flow 和 ready spec execution 按触发规则自动进入。
   - 路由不明确或需要完整清单时读取 `references/routing.md`。
4. 维护 artifact 纪律：
   - 重要长期状态必须落到 artifact，不只留在聊天里。
   - spec 是默认设计和进度真相源；`Progress` 只保存稳定恢复快照。
   - runtime 调度拓扑、子代理消息、owner、依赖边和微步骤不写入 artifact。
   - 同一文件或共享状态避免并发多写；完成交接后可以动态更换 writer，主会话负责 fan-in。
   - 创建或修改 artifact 后运行 `validate-flow`。
   - 本地 docs 入口定义 TOC 规则时，创建、删除或移动 artifact 必须同步维护。

## Core Model

```text
spec（长期设计 + readiness + Progress）
  ↓ 可选 pick-goal（只读目标投影与 readiness 交接）
ready spec / implementation-ready goal
  ↓
native runtime execution + dynamic subagents
  ↓
test / review / consolidation（按风险触发）
  ↓
spec Progress 写回
```

只在真实边界出现时创建旁路 artifact：

- `issue`：值得长期保留的问题、证据、机会或 unresolved finding；不是执行 slice。
- `acceptance`：Agent 无法自证、需要人类判断的 gate。
- `backlog`：工作退出当前执行队列，等待长期外部条件。
- `handoff`：未提交 diff、临时环境、终端状态等易失接力信息。

## Responsibility Boundaries

- `to-spec`：对齐并维护长期设计、readiness、Execution Constraints 和 Progress。
- `pick-goal`：只读选择 unfinished spec 并派生 portable runtime goal；显式启动时把 ready goal 交给 `to-implement`、alignment goal 交给 `to-spec`，blocked goal 不启动。
- `to-implement`：执行 ready spec 或其派生的 implementation-ready goal，动态调度 runtime，验证、fan-in 并压缩写回 Progress。
- `validate-flow`：只检查轻量 artifact schema、来源和状态一致性，不检查 runtime 拓扑。
- `to-test`：测试策略、行为场景、ROI、stable seam 和替代验证。
- `to-review`：实现风险、行为回归、设计对齐、测试缺口和可靠性问题。
- `to-consolidation`：只收敛 pending diff 的临时代码、重复逻辑和 fan-in 残留。
- `to-acceptance`：只承载真实人类 gate，不包装 Agent 可自行验证的检查。
- `to-backlog`：长期阻塞和恢复条件。
- `to-handoff`：易失接力状态，不替代 spec Progress。
- `to-knowledge`：只沉淀业务无关、项目无关、可跨项目复用的技术知识。

这些能力不能互相代偿：结构问题回 validate-flow，设计变化回 to-spec，代码风险回 review，diff 熵值回 consolidation，人类判断回 acceptance。

## Quick Routing

| 场景 | 子能力 |
| --- | --- |
| 长期设计、需求澄清、spec/Progress 维护 | `to-spec` |
| 从一个或多个 spec 选择、恢复或生成 runtime goal | `pick-goal` |
| 执行或继续 ready spec / implementation-ready goal | `to-implement` |
| 问题 / 证据记录，暂不进入长期设计 | `to-issue` |
| 排障、复现、root cause | `to-debug` / `to-bdd-regression` |
| 基础设施、日志、数据源取证 | `to-infra`（project-provided adapter） |
| 测试策略、BDD/TDD、替代验证 | `to-test` |
| review、循环复审、Agent 决策复盘 | `to-review` / `to-review-loop` / `to-agent-review` |
| 人类验收或下一轮反馈 | `to-acceptance` / `to-next-acceptance` |
| 长期阻塞或易失交接 | `to-backlog` / `to-handoff` |
| 提交、diff 收敛、artifact 校验 | `to-commit` / `to-consolidation` / `validate-flow` |
| 通用技术知识 | `to-knowledge` |

完整触发表只维护在 `references/routing.md`。

## Artifact Model

当前 file-backed artifact：

- `spec`：长期设计、实现 readiness、稳定约束、Progress 和证据。
- `issue`：问题与线索；completed issue 位于 `issue/fixed/`。
- `acceptance`：人类 gate 与反馈轮次。
- `backlog`：长期阻塞与恢复条件。
- `handoff`：易失跨会话接力状态。

所有 artifact 文件 stem 等于 frontmatter `id`。关系默认使用单向 `source_type` / `source_id`；不维护反向绑定图。

通用状态：`draft`、`not_started`、`in_progress`、`completed`、`abandoned`。

## Spec Progress

Progress 是覆盖更新的恢复快照：

```markdown
## Progress

- Checkpoint: <稳定状态>
- Completed:
  - <语义结果和必要证据>
- Next: <目标级恢复入口，不是代码微任务>
- Blockers:
  - <none，或原因与恢复条件>
- Last verified:
  - <日期、证据、结论和残余风险>
```

Progress 只保存能力 / 行为结果、关键决策、可信 evidence、真实 blocker、residual risk 和 resume target。不得写入具体代码行号、逐文件 diff、完整命令过程、tool call、子代理身份 / 消息、runtime 工作清单、owner、并行批次或逐轮时间线；必要时可以引用少量稳定模块、类、函数、公开接口或测试套件名称。每次写回覆盖或合并旧快照，不持续追加。

## Retired Model

文件化执行拓扑及其创建、选择和压缩能力已归档到 `archive/skills/`，不属于 active skill 或安装范围。legacy artifact 必须迁移：长期设计和稳定进度进入 spec；真实人类 gate、长期延期和易失交接分别进入 acceptance、backlog、handoff。

## Reference Loading

- `references/routing.md`：完整子能力清单与触发规则。
- `references/dependencies.md`：安装、运行环境和依赖。
- `skills/<name>/SKILL.md`：进入对应 active 子能力时读取。
- `docs/spec/tooling/sky-flow.md`：设计真相源。
- `scripts/schema.ts` / `scripts/validate_flow.ts`：机器可执行的轻量 artifact 约束。

项目验证命令、部署限制、业务规则和专属工具由项目本地文档承担，不写入 Sky Flow core。
