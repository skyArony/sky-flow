---
id: sky-flow
artifact_type: spec
status: draft
plans: []
---

# Sky Flow 工作流套件

最后更新：2026-05-25

## 定位

Sky Flow 是一套通用工作流 Skill 套件，用来承载从设计澄清、问题记录、实施计划、任务拆分、并行执行、
人类验收到 backlog 回收的完整协作链路。

它不是单个巨型 Skill，也不是所有任务的默认入口。它会形成多个职责清晰的子 Skill；每个子 Skill
可以被套件编排调用，也可以在合适场景下单独使用。

Sky Flow 不和任何单一项目耦合。项目差异通过 `SKY_FLOW_*` 环境变量覆盖和项目本地文档承载；套件核心只保留可跨项目复用的工作流抽象。

## SKY_FLOW 环境变量覆盖

`SKY_FLOW_*` 环境变量覆盖是 Sky Flow 唯一内置的项目级配置机制。它只负责少量 key/value 运行时覆盖，不承载业务规则、命令清单或项目流程。

Sky Flow 当前只定义两个变量：

- `SKY_FLOW_ROOT`：artifact 根目录，默认 `docs`。
- `SKY_FLOW_LANG`：artifact 和 Skill 输出语言，默认跟随用户语言；自动化脚本默认 `简体中文`。

解析规则：

- 只读取 runtime 已提供的环境变量，例如 Codex 启动环境、shell 环境继承、profile 注入，或 Codex 原生配置注入。
- 不解析额外项目配置文件。
- 没有环境变量时使用默认值。
- 任何读取、创建或修改 Sky Flow artifact 的任务，都先确定 artifact root 和输出语言；这是必经短路径，但不需要加载额外 reference。

需要覆盖默认值时，Codex 项目内定制推荐使用原生配置能力表达为 key/value：

- 长期项目默认值：在受信任项目的 `.codex/config.toml` 中配置。
- 单次运行覆盖：使用 `codex --config key=value`，值按 TOML 解析。
- 需要注入到子进程的环境变量：使用 `shell_environment_policy.set` 这种 `map<string,string>`。

默认值满足项目需求时不需要配置；只有需要改变 artifact 根目录或默认输出语言时，才设置 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`。

示例：

```toml
[shell_environment_policy.set]
SKY_FLOW_ROOT = "docs"
SKY_FLOW_LANG = "简体中文"
```

项目提交规范、验证命令、部署限制、领域术语和观测查询方式不进入 Sky Flow core。它们应由项目 `AGENTS.md` / `CLAUDE.md` 或项目本地工具说明。

## 通用枚举

### artifact_type

`artifact_type` 是文档 frontmatter 中的 artifact 层级枚举。

当前枚举：

- `spec`：设计文档。
- `issue`：问题和线索记录。
- `plan`：具体实施计划。
- `task`：归属于 plan 的具体任务。
- `step`：task 内部的可选串行阶段。
- `acceptance`：人机交互验收文档。
- `backlog`：当前阶段暂时无法推进的阻塞项。
- `handoff`：跨会话或换 Agent 的交接文档。

说明：

- `step` 属于 artifact 层级，但通常不单独成文档，因此一般不会出现在文档 frontmatter 中。
- 其他 artifact 都应在 frontmatter 中显式声明 `artifact_type`。

### status

`status` 是通用状态枚举。

当前枚举：

- `draft`：草稿。内容还在设计、澄清、拆解或确认中。
- `not_started`：未开始。已经确认，可以进入执行队列。
- `in_progress`：进行中。
- `completed`：已完成。
- `abandoned`：放弃。当前阶段不继续推进，通常需要对应 backlog 说明原因。

状态流转原则：

- 在 `plan` 没有被确定之前，`plan` 和它派生出的 `task` 初始状态都是 `draft`。
- 当整个 `plan` 被确定后，`plan` 以及该 plan 下已经确定的 `task` 全部转为 `not_started`。
- 后续 Agent 可以把 `not_started` 转为 `in_progress`，也可以在完成后转为 `completed`。
- `abandoned` 需要和人类协商后才能设置，不由 Agent 单方面决定。

### task_type

`task_type` 是 `task` 的有限类型枚举。类型要少而稳定，避免按项目或偶发场景无限膨胀。

当前枚举：

- `exploration`：探索。只读理解上下文、调研事实、确认风险、收集证据。
- `implementation`：实施。修改代码、文档、配置或其他正式产物。
- `review`：复审。检查实现、diff、设计对齐、风险和遗漏。
- `verification`：验证。执行测试、构建、手工验收辅助或可重复检查。
- `documentation`：文档。整理 spec、issue、plan、acceptance、handoff、backlog 等文档产物。
- `coordination`：协调。由主会话承担，维护依赖、fan-in、任务状态、handoff 衔接或多 Agent 分工。
- `consolidation`：收敛。阶段产物完成后，检查和收敛补丁式实现、临时代码、重复逻辑和 fan-in 残留。

特殊领域差异优先用 `tags` 或任务正文说明，不轻易新增 `task_type`。

`coordination` 不作为普通子代理任务派发。Sky Flow 的主会话负责 plan 级依赖维护、状态更新和 fan-in。
如果 runtime 支持嵌套子代理，task owner 可以在自己的 task scope 内继续派发二级子代理；二级结果由 task owner
先 fan-in，再回报给主会话维护 plan / task artifact。

### acceptance_type

`acceptance_type` 是 `acceptance` 的验收形态枚举。

当前枚举：

- `interactive`：需要人类逐项反馈的验收文档，默认使用 Markdown。
- `report`：只读、无需反馈的验收报告，可以使用 Markdown 或 HTML。
- `html_report`：包含样式、脚本或媒体资源的只读 HTML 报告。
- `html_interactive`：ToDo: 探索交互式验收页；当前仅作为未来候选。

选择规则：

- 先判断是否需要人类反馈。
- 再判断 HTML 是否比 Markdown 更可读、更适合展示信息结构或媒体资源。
- 需要反馈且 Markdown 足够清晰：使用 `interactive`。
- 不需要反馈且 Markdown 足够清晰：使用 `report`。
- 不需要反馈且 HTML 更可读：使用 `html_report`。
- 需要反馈且 HTML 更可读：使用 `interactive`，并可附带只读 `html_report` 辅助展示。
- ToDo: 评估并实现 `html_interactive`；当前先不实现，原因是纯静态 HTML 很难可靠写回 artifact，通常需要 server、外接 DB、
  浏览器扩展或 runtime 专用桥接。

## Skill 套件目录

Sky Flow 采用根 `SKILL.md` 加可独立发现的子能力 `SKILL.md`、内部说明文件和脚本的结构。
当前 runtime 以“目录内存在 `SKILL.md`”作为 skill 发现单元，可以递归发现嵌套目录；
普通 `.md` 文件只作为引用文档，不会被发现为 callable skill。

```text
.agents/skills/sky-flow/
├── SKILL.md
├── references/
│   ├── dependencies.md
│   └── routing.md
├── scripts/
│   ├── install_external_skills.sh
│   ├── schema.ts
│   ├── setup.sh
│   └── validate_flow.ts
├── skills/
│   ├── pick-plan/
│   │   ├── SKILL.md
│   │   ├── agents/
│   │   │   └── openai.yaml
│   │   └── scripts/
│   │       └── collect_plans.ts
│   ├── to-spec/
│   │   └── SKILL.md
│   ├── to-issue/
│   │   └── SKILL.md
│   ├── to-plan/
│   │   └── SKILL.md
│   ├── to-task/
│   │   └── SKILL.md
│   ├── to-implement/
│   │   └── SKILL.md
│   ├── to-acceptance/
│   │   ├── SKILL.md
│   │   └── skills/
│   │       └── to-next-acceptance/
│   │           └── SKILL.md
│   ├── to-backlog/
│   │   ├── agents/
│   │   │   └── openai.yaml
│   │   └── SKILL.md
│   ├── to-handoff/
│   │   └── SKILL.md
│   ├── to-debug/
│   │   ├── SKILL.md
│   │   └── skills/
│   │       └── to-bdd-regression/
│   │           └── SKILL.md
│   ├── to-test/
│   │   └── SKILL.md
│   ├── to-review/
│   │   ├── SKILL.md
│   │   └── reviewers/
│   │       ├── review-by-sanyuan/
│   │       │   └── SKILL.md
│   │       └── review-by-somestay/
│   │           └── SKILL.md
│   ├── to-review-loop/
│   │   └── SKILL.md
│   ├── to-agent-review/
│   │   └── SKILL.md
│   ├── to-commit/
│   │   └── SKILL.md
│   ├── to-consolidation/
│   │   └── SKILL.md
│   └── validate-flow/
│       └── SKILL.md
```

划分标准不是“是否属于 Sky artifact”，而是“是否有明确自动触发场景”。

- 有明确自动触发场景的能力，放入 Sky Flow 自动触发清单，并要求 `sky-flow` 或相关子能力确保触发。
- 没有明确自动触发场景的能力，默认需要人类显式触发。
- 即使自动触发，也应保持轻量，不能把所有任务都强行拉入 Sky Flow。

`to-infra` 是 Sky Flow 预留的项目级基础设施 adapter slot。Sky Flow core 只定义它的触发语义和边界，
不在 `skills/` 下提供具体实现。使用 Sky Flow 的项目如果需要查询或操作基础设施、日志、数据库、缓存、
指标、告警、部署环境或外部系统，应在项目级定义自己的 `to-infra` Skill，并由该项目负责环境、权限、
命令、只读 / 写入边界和安全审批细节。

## 渐进式披露

Sky Flow 使用渐进式披露控制入口成本，避免每次触发都加载完整子能力细节。

层级划分：

- Frontmatter `description` 是常驻触发层，只描述能力范围和触发口径，不列完整子能力细节。
- `SKILL.md` 是必经短路径，只保留进入判断、runtime env 读取、子能力选择、artifact 纪律和快速路由。
- 内部说明文件可以按路由、schema、依赖等主题拆分，作为执行层摘要和索引，降低每次触发的上下文成本。
- 子能力 `SKILL.md` 只承载具体流程执行细节，不替代本 spec 的设计真相。

必须触发的规则必须出现在必经短路径上，并保持短小，例如 artifact 操作前确定 artifact root、写入 artifact 后触发 `validate-flow`。完整设计必须在本 spec 中自洽，执行产物只能做拆分摘要，不能成为唯一设计来源。

## 自动触发与显式触发

触发顺序：

- 显式点名优先：用户提到具体子能力时，直接进入对应能力。
- 自动场景必须触发：debug、infra 查询 / 操作、BDD 回归固化、testing、review、commit、consolidation、acceptance、validate-flow、Sky Flow plan / task execution 命中时，不等待用户再次点名。
- Artifact 操作前必须先确定 artifact root 和输出语言。
- 简单任务快速退出：不需要 workflow artifact、不需要跨会话状态、不命中自动场景时，直接使用 runtime。

完整触发表：

| Skill                | 触发倾向 | 进入场景                                                                                               | 注意事项                                            |
| -------------------- | -------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `to-spec`            | 显式     | 生成或更新长期留存的设计文档；系统化设计澄清。                                                         | 不强制立刻进入 plan。                               |
| `to-issue`           | 显式     | 记录近期问题、现象、证据和线索，尚不进入修复。                                                         | 不替代 debug 或 plan。                              |
| `to-debug`           | 自动     | 定位问题、复现异常、分析 root cause。                                                                  | 调试循环入口；基础设施查询 / 操作转 `to-infra`，真实事故回归转 `to-bdd-regression`。 |
| `to-infra`           | 自动     | 查询或操作基础设施、环境、日志、数据库、缓存、Metrics、Grafana、AlertManager、部署或外部系统。            | Project-provided adapter slot；Sky Flow core 不实现具体环境细节。 |
| `to-bdd-regression`  | 自动     | 线上 bug、客户反馈、日志 / 数据异常、时序或状态机问题需要固化为 BDD-style 回归。                         | `to-debug` 子能力；复用已有诊断信息，不重复取证。   |
| `to-test`            | 自动     | 新增 / 修改测试、写 Given / When / Then、判断测试 ROI、选择 stable seam、决定 Red / Green / Refactor 或替代验证。 | 不替代 `to-debug`；真实事故回归转 `to-bdd-regression`；项目命令由本地规则决定。 |
| `to-plan`            | 显式     | 从 spec、issue 或当前会话生成实施计划；承载目标、范围、阶段、进度、恢复入口和 handoff。                 | 文件化 plan 是长期状态；task DAG 和执行模型分别交给 `to-task` / `to-implement`。 |
| `to-task`            | 显式     | 从 plan 拆出 task、依赖、并行关系、owner、write scope、no-touch 和可选 step。                          | 必须以 task-ready plan 作为输入；不执行 task。      |
| `to-implement`       | 自动     | 执行和维护指定 Sky Flow plan / task artifact / task DAG，协调主代理、子代理、runtime plan、动态 task 调整、验证、fan-in 和状态回写。 | 日常任务不用；仅显式指定，或执行已制定 Sky Flow plan / task 时触发。 |
| `to-review`          | 自动     | 小型 review、明确 review 指令，或流程阶段需要复审。                                                    | 查代码风险，不做 artifact 校验或 diff 收敛；不自动升级为 `to-review-loop`。 |
| `to-review-loop`     | 显式     | review-fix-review 循环。                                                                               | 成本较高，必须有明确意图。                          |
| `to-agent-review`    | 显式     | Agent 决策链路、工具调用、子代理 ROI 和流程低效点复盘；常见自动场景是 runtime 自动化在固定时间点触发。 | 普通会话只在明确 Agent 复盘场景中自动触发；报告默认写入 `${SKY_FLOW_ROOT}/backlog/agent-reivew/`。 |
| `pick-plan`          | 显式     | 从未完成 plan 和近期完成 plan 中挑选下一步推荐项。                                                     | 输出推荐 plan 和可复制续跑提示。                    |
| `to-acceptance`      | 自动     | 出现需要人类验收的点，或人类补充验收点 / 验收要求。                                                    | 完成声明前必须有验证证据。                          |
| `to-next-acceptance` | 显式     | 处理已有 acceptance 的人类反馈并推进下一轮；作为 `to-acceptance` 的子能力维护。                         | 未提及项不默认通过。                                |
| `to-backlog`         | 显式     | 当前阶段无法推进、被阻塞、延期或需要回收。                                                             | 说明阻塞原因、依赖和建议恢复时机。                  |
| `to-handoff`         | 显式     | 跨会话继续、换 Agent、保存可执行恢复状态。                                                             | 不写聊天摘要式 handoff。                            |
| `to-commit`          | 自动     | 用户要求 stage、commit、commit message 或拆分提交。                                                    | 遵守项目本地提交规范和验证要求；staged diff 含 workflow artifact 时先推荐 `validate-flow`。 |
| `to-consolidation`   | 自动     | 阶段产物完成、多 Agent fan-in 后、task 显式安排收敛或用户要求收敛 diff。                               | 只收敛当前 pending diff，不查 artifact/status；不作为 `to-commit` 固定前置。 |
| `validate-flow`      | 自动     | 创建或修改 Sky Flow artifact 后、plan 主会话 fan-in 后，或提交 workflow artifact 前。                  | 只检查 artifact 契约和状态一致性。                  |

`to-review-loop` 和 `to-spec` 类似，需要明确意图后再进入。它会带来循环修复成本，不能因为出现普通 review
就自动升级。

`to-agent-review` 默认显式触发。普通会话只在明确 Agent 复盘场景中自动触发；更常见的自动场景是 runtime
自动化在固定时间点触发。它不作为常规 Sky Flow 自我迭代入口。

## 子能力职责说明

Sky Flow 的 Skill 命名优先围绕 artifact 和状态转换，而不是围绕具体 runtime。

### 职责边界速记

- `validate-flow` 只管 Sky Flow artifact：frontmatter、枚举、命名、相邻绑定、DAG、状态流转、验收证据、backlog / handoff 归宿，以及 fan-in 后 plan / task / acceptance 是否互相漂移。它只读输出报告，不做代码 review，也不替代代码收敛。
- `to-test` 只管测试策略：行为场景、测试 ROI、stable seam、Red / Green / Refactor、characterization 和替代验证。它不替代 debug 诊断、事故回归固化或人类验收。
- `to-review` 只管 review：实现风险、行为回归、设计对齐、测试缺口和安全 / 可靠性问题。它可以引用 artifact 作为背景，但不负责修 artifact 状态，也不把 diff 整理成一体化实现。
- `to-consolidation` 只管收敛：清理当前目标 diff 中的补丁式实现、临时代码、重复逻辑、旧注释、debug 残留和 fan-in 半成品。它不是 review，也不检查 Sky Flow artifact/status 一致性。

这些能力可以串联，但不能互相代偿：artifact/status 问题回 `validate-flow`，测试策略和测试 ROI 回 `to-test`，代码风险回 `to-review`，diff 熵值回 `to-consolidation`。

### Skill 推荐关系机制

Sky Flow 子 skill 之间采用“推荐而非强制”的协作机制。某个 skill 在执行中遇到非本职责领域时，应明确指出有专门 skill 负责，并给出推荐 skill、推荐原因、输入摘要和是否阻塞当前流程；除非该场景在触发表中是必须自动触发，推荐本身不等于强制跳转。

推荐关系的目的：

- 保持职责边界清晰，避免一个 skill 代偿另一个 skill 的专业判断。
- 降低遗漏：例如运行环境证据归 `to-infra`，测试策略归 `to-test`，artifact 状态归 `validate-flow`。
- 允许主会话或人类按成本、时机和当前 scope 决定是否接受推荐。

推荐输出至少包含：

- `Recommended skill`: 目标 skill。
- `Why`: 当前流程遇到的非本领域问题。
- `Input to pass`: 已确认事实、相关 artifact / diff / evidence、时间范围或关键实体。
- `Blocking`: yes / no；只有不处理会阻断当前 artifact、阶段或交付时才写 yes。

默认推荐关系：

| 当前 skill | 遇到的领域 | 推荐 skill |
| --- | --- | --- |
| `to-spec` | 设计已 ready，需要拆实施路径 | `to-plan` |
| `to-spec` / `to-plan` / `to-implement` | 环境、日志、数据库、缓存、Metrics、Dashboard、告警或部署证据 | 项目级 `to-infra` |
| `to-plan` | task DAG、并行、single writer、阶段 review / consolidation 安排 | `to-task` |
| `to-task` | 执行已准备好的 task DAG | `to-implement` |
| `to-task` / `to-implement` | 测试策略、测试 ROI、BDD/TDD、stable seam 或替代验证 | `to-test` |
| `to-debug` / `to-test` / `to-implement` | 真实事故或客户反馈需要回归固化 | `to-bdd-regression` |
| `to-task` / `to-implement` | 普通 code / artifact review | `to-review` |
| `to-task` / `to-implement` | 阶段产物完成、fan-in 后或 diff 熵值风险高 | `to-consolidation` |
| 任意创建 / 修改 workflow artifact 的 skill | artifact contract / status 校验 | `validate-flow` |
| `validate-flow` | 发现语义归属问题 | 按 artifact 类型推荐 `to-spec` / `to-plan` / `to-task` / `to-acceptance` / `to-backlog` / `to-handoff` |

如果 review 输出中存在会阻止 handoff、acceptance、commit 或 plan / task 完成的 `P0` / `P1` / blocked / failed / scope-violation 问题，只在当前 review / fan-in 结果中输出为 blocking finding，并说明影响、证据和需要人类或后续显式流程处理的动作；不推荐、不自动转入 `to-review-loop`。`to-review-loop` 只能由用户显式触发。

### sky-flow

`sky-flow` 是套件入口和使用纪律 Skill。

它更接近 `superpowers/using-superpowers` 的定位：提醒 Agent 在合适场景下选择和调用套件能力，并建立
“该用 Skill 时必须用 Skill”的工作流纪律。简单 / 中等任务的 H0 / H1 / H2 分层保留在根 `AGENTS.md`；
当任务需要 durable artifact、跨会话恢复、阶段验收或任务 DAG 时，Agent 应先推荐 Sky Flow，是否使用由人类决定。

`sky-flow` 不负责写所有 artifact 正文。它只负责：

- 判断任务是否适合进入 Sky Flow。
- 判断从 `spec`、`issue`、`plan`、当前会话还是原生 runtime 开始。
- 在需要读取、创建或修改 artifact 时，先确定 artifact root 和输出语言。
- 推荐应该使用的子 Skill。
- 在需要时触发 `validate-flow` 检查 artifact 状态。

### to-spec

`to-spec` 用于生成或更新 `spec`。

它先做仓库事实校准，再做设计收敛，最后把稳定意图、事实、术语、范围、acceptance scenarios、可测试且无歧义的要求、关键决策和
`to-plan` handoff 写入长期设计真相源。

`to-spec` 自身承担事实校准和设计澄清职责。它先读相关 docs、代码、schema、历史 artifact 和 recent commits，
建立已确认事实、未知点、冲突点和术语口径；能从仓库确认的事实不问人，用户描述与代码 / docs 冲突时直接指出证据来源。

需要人类决策时，`to-spec` 一次只问一个高价值问题，并给出已确认事实、歧义点、`2-3` 个互斥候选、推荐项和影响面。
需要让用户在选项中决策时，若 `functions.request_user_input` 可用且当前 runtime 允许调用，应优先调用；否则只问一个简洁的纯文本问题。

设计收敛前，`to-spec` 用具体场景压力测试关键行为和边界，澄清模糊或过载术语，并主动发掘用户未显式说出、但会影响
scope、行为、契约、验证或计划拆分的隐含问题。发现的问题按 repo 可确认、blocking、non-blocking、low-value 分类处理。
对真实设计分叉，它给出 `2-3` 个互斥方案、取舍和推荐项，再把稳定结论写入 `Decisions`。

`to-spec` 输出的是长期留存的设计文档，不强制立刻进入 `plan`。spec 阶段明确限制 implementation details：
requirements 必须可测试、无歧义，acceptance scenarios 必须保护用户可见行为、业务不变量、系统边界或外部契约。
模板保持轻量；必要时可以新增承载长期关键信息的 section，但不能为了完整感添加空标题，也不能把实现细节、实现步骤、task 列表或命令清单提前写进 spec。

`Ready for to-plan` 表示 `to-plan` 只需要拆实施路径、阶段、任务和验证证据，不需要替 spec 决定“到底要什么”。
只有 intent、scope、pressure pass、blocking questions、requirements、acceptance scenarios 和 implementation details 边界都满足约束时，
`Plan Handoff` 才能标记为 ready。否则 spec 停在 `Open Questions` 和下一个最高价值问题上。

### to-issue

`to-issue` 用于在本地 docs issue 目录创建或更新 `issue` artifact。

它不进入修复环节，也不创建 GitHub Issue、Linear Issue 或其他外部 tracker 条目。它只沉淀现象、证据、
影响面、相关上下文、后续可能切入点，或从 spec / plan / 讨论中拆出的可独立认领 vertical slice。

`to-issue` 写入 `${SKY_FLOW_ROOT}/issue/`。如果 `${SKY_FLOW_ROOT}/AGENTS.md` 或
`${SKY_FLOW_ROOT}/CLAUDE.md` 存在并定义 Table Of Content 维护规则，新增、删除或移动 issue artifact
时必须按本地规则同步 TOC；两者是同一文件或软链接时维护一次即可。

issue 和 backlog 的边界：issue 记录“值得追踪但尚未进入实施”的问题或机会；backlog 记录“当前阶段已经无法继续、
需要恢复条件”的阻塞。issue 和 plan 的边界：issue 可以作为 plan 输入，但不写实施计划、task DAG 或命令清单。

### to-debug

`to-debug` 用于定位问题、复现异常和分析 root cause。

它是调试思路入口，不是基础设施查询入口。`to-debug` 负责建立反馈环、复现同一个现象、列出可证伪假设、
按 prediction 取证、收敛 root cause、执行最小修复策略、重跑验证并清理临时 instrumentation。

`to-debug` 必须和基础设施 / 数据源查询分离：

- 需要查询或操作环境、日志、数据库、缓存、Metrics、Grafana、AlertManager、部署、网络或外部系统时，转入项目级 `to-infra`。
- 进入 `to-infra` 前，`to-debug` 应说明要验证的假设、prediction、目标环境、时间范围和关键实体；不要把“查一下”当成无目标搜索。
- `to-infra` 返回证据后，`to-debug` 继续负责更新假设矩阵、确认或证伪根因，并决定是否修复、补测试、回滚或暂停询问人类。
- 如果当前项目没有定义 `to-infra`，`to-debug` 只能使用已知本地制品、外部知识型 Skill 或询问人类补齐环境入口，不能编造环境命令或数据口径。

`to-debug` 必须和回归固化分离：

- 真实事故、客户反馈、日志 / 数据异常、时序问题或状态机问题已经具备足够证据时，推荐调用 `to-bdd-regression`。
- 调用 `to-bdd-regression` 时，把 `to-debug` 已确认的 reproduction、hypotheses、evidence、incorrect path、correct path 和 residual risk 作为输入。
- `to-bdd-regression` 不重复 `to-debug` 已完成的取证；只有证据缺口会改变测试行为或正确性时，才回到 `to-debug` / `to-infra` 补证。
- 普通测试 ROI、BDD 场景、stable seam、Red / Green / Refactor 或替代验证判断，推荐调用 `to-test`。

`to-debug` 输出应优先保留：

- Feedback loop：用于判定 pass / fail 的稳定信号。
- Reproduction：复现步骤和确认的症状。
- Hypotheses：3-5 个可证伪假设、prediction、状态和证据。
- Evidence：按假设组织的本地或 `to-infra` 证据。
- Fix strategy：最小修复方向或停止原因。
- Verification：原始反馈环、相关验证和清理结果。
- Residual risk：未覆盖风险、需要人类确认的问题或可转入 `to-bdd-regression` 的回归候选。

### to-infra

`to-infra` 是 Sky Flow 的项目级基础设施 adapter slot。它属于 Sky Flow 的工作流边界，但具体实现不进入
Sky Flow core。

Sky Flow core 只约定触发语义：

- 查询基础设施状态、环境配置、服务、网络、日志、数据库、缓存、对象存储、队列、Metrics、Dashboard、告警或外部系统时使用。
- 执行基础设施操作、环境维护、port-forward、dashboard / alert 维护、部署前检查或其他 infra 变更时使用。
- `to-debug`、`to-implement`、`to-acceptance` 或其他子能力需要运行环境事实、观测证据或基础设施操作时，可以推荐进入 `to-infra`。

项目级 `to-infra` 必须自己声明：

- 支持的环境、系统、数据源和访问方式。
- 默认只读规则、允许写入的操作类型、安全审批和禁止事项。
- 查询必须携带的范围约束，例如环境、时间范围、namespace、service、用户、任务、trace id 或资源名。
- 具体应该分流到哪些知识型 / 工具型 Skill，例如 PromQL、Grafana、VictoriaLogs、VictoriaMetrics、AlertManager 或云厂商 Skill。
- 证据输出格式，确保调用方能把结果回填到 `to-debug`、`to-implement`、`to-acceptance` 或其他 workflow artifact。

如果项目没有提供 `to-infra`，Sky Flow 不能猜测环境细节。调用方只能使用用户提供的制品、公开文档或通用工具型 Skill，
并在缺少项目入口时停下询问。

### to-bdd-regression

`to-bdd-regression` 是 `to-debug` 的下级能力，用于把真实 bug、客户反馈、日志 / 数据异常、时序问题或状态机问题固化为
BDD-style 回归测试。

它的输入优先来自 `to-debug`：

- 已确认的事故场景、环境、时间范围和关键实体。
- reproduction 和反馈环。
- confirmed / rejected / inconclusive hypotheses。
- `to-infra` 或本地取证得到的关键 evidence。
- incorrect path、correct path、observable assertions 和 residual risk。

`to-bdd-regression` 只补足“测试化”所需的信息，不重复诊断循环。它应把证据摘成最小 fixture 或场景事实，
再用 Given / When / Then 描述业务行为、系统边界或用户可观察结果。测试应该保护 correct path，而不是复制日志、
mock 调用顺序或私有 helper 细节。

如果证据不足以定义正确行为，`to-bdd-regression` 不直接写测试；它应回到 `to-debug` 补复现或回到 `to-infra` 补证据。
如果问题并非真实事故或高风险行为，只需要普通测试 ROI、BDD 场景、stable seam 或替代验证判断，应转交 `to-test`，而不是强行创建回归测试。

### to-test

`to-test` 是 Sky Flow 的通用测试工作流入口，用于新增 / 修改测试、写 `Given / When / Then` 行为场景、判断测试 ROI、选择 stable seam、决定 Red / Green / Refactor，或记录替代验证。

它只保留跨项目可复用的测试策略，不写死项目命令、测试框架、包名、环境名或业务术语。项目级测试命令、watch 禁止规则、框架约定和领域优先级由本地 `AGENTS.md` / `CLAUDE.md` 承载。

`to-test` 的核心顺序：

- 先读取相关 spec / issue / plan / task / debug 证据和当前变更上下文，确认行为边界，不问 repo 可确认的问题。
- 用业务或系统语言写 `1-3` 个高价值 `Given / When / Then` 场景，保护用户可见结果、业务不变量、系统边界或外部契约。
- 通过 ROI Gate 判断 `P0` / `P1` / `P2` / `Skip`：高风险行为测试优先，低价值覆盖率补丁默认不测。
- 选择最小稳定 test seam：pure function / state machine、service / domain rule、API / contract、database / storage、UI / workflow。
- `P0` / `P1` 默认使用 Red / Green / Refactor；characterization test 必须标注不是 TDD。
- `P2` / `Skip` 必须记录替代验证、跳过理由和残余风险。

`to-test` 的边界：

- Debug 尚未复现或根因不清时，先用 `to-debug`。
- 真实事故、客户反馈、日志 / 数据异常、时序或状态机问题需要固化回归时，转 `to-bdd-regression`。
- 人类验收、sign-off 或反馈文档由 `to-acceptance` 处理；`to-test` 只提供测试策略和验证证据。
- 不测试 mock 调用次数、私有 helper、日志文本、内部字段形状或纯实现路径，除非它们本身就是稳定外部契约或安全边界。
- 不为测试向生产代码加入 test-only method、测试环境分支或 spec-only 行为。

### to-plan

`to-plan` 用于生成或更新 `plan`。

它可以从 `spec`、`issue` 或当前会话进入，也可以独立存在。`to-plan` 输出的是可长期留存的实施计划
artifact，不是 runtime 内存里的临时计划。

`plan` 不只是计划，也是进度和编排中心。它基于 task 编排记录当前推进方式、并行关系、阶段产物、
验收意图和恢复入口；执行时由主会话负责把文件化 `plan` 映射为 runtime 任务清单。

`to-plan` 和 runtime plan 的承接关系：

- runtime plan 适合当前会话内的短期执行状态，生命周期短，通常不作为长期真相源。
- Sky Flow `plan` 是文件化 artifact，适合跨会话、多人协作、任务拆分、验收和 backlog 回灌。
- 执行时可以从 Sky Flow `plan` 派生 runtime plan，但 runtime plan 不能替代 Sky Flow `plan`；主会话需要把关键进度、fan-in 结论和编排决策回写到文件化 `plan`。

`to-plan` 吸收编排经验时只保留对 plan 有直接价值的部分：

- Scope Check：如果输入 spec / issue 覆盖多个独立子系统，`to-plan` 不硬塞进一个 standalone plan；应拆成多个 plan，或升级 parent / child plan。
- 进度追踪：`plan` 可以在执行中记录当前阶段、已完成项、阻塞项、下一步、关键决策、fan-in 结论和验证证据入口。
- 恢复入口：`plan` 至少能说明 resume from、next action、current blocker 和 last validated state，让下一轮不依赖聊天历史恢复。
- 子代理 ROI 判定：只要并行时间收益、上下文隔离收益、专业化收益、质量 / review 收益任一成立，且 fan-in 成本可控，就应该派发子代理；如果从其他角度能说明派发子代理有明确正向收益，也应该派发。该判断必须和后续 `task.depends_on` / `task.parallel_with` 对齐。
- 并行优先：plan 应表达阶段级串行关系和可并行 lane，`to-task` 再把它收敛为具体 task DAG；能并行的任务尽量并行，不无故串行化。
- 实施承接：`to-plan` 只记录进入执行前必须知道的执行边界；完整主代理 / 子代理分工、上下文 fork、fan-in 和状态回写规则归 `to-implement`。
- Execution Safety：`to-plan` 只记录进入执行前必须知道的 gate、风险和停止条件；执行期是否继续推进由 `to-implement` 根据 task 状态、验证结果和 scope 风险判断。
- 停止条件：范围扩大、验证失败且修复路径不唯一、公共契约 / DB / 部署等风险升级、产品 / 设计取舍不明时，plan 必须记录 blocker，执行期必须暂停并询问人类。

`to-plan` 需要维护 `goal` 字段。`goal` 是当前 plan 的完成契约，用于生成 Codex 续跑提示词。
它应符合 Codex Goals 的官方写法：包含期望终态、验证证据、约束、边界、迭代策略和阻塞停止条件。
`goal` 字段只保存正文，不包含 `/goal` 前缀。

Codex Goals 官方参考：

- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex

Plan Mode 参考：

- Claude Code Plan Mode 将计划阶段定位为只读分析代码库、规划复杂变更和交互式确认方向。
- Codex Plan Mode 要求先探索环境、区分可发现事实和偏好取舍，最终输出 decision-complete 的计划。
- Sky Flow `to-plan` 继承“先探索、先提案、再执行”的精神，但输出是文件化 `plan` artifact，而不是只存在于聊天中的计划。

超级巨大 Plan 分拆规则：

- 只有系统判定任务已经大到单个 Plan 难以承载时，`to-plan` 才自动拆成父 Plan 和多个子 Plan。典型信号是：构建一整个系统、重做一个巨型模块、跨多个独立交付域、需要多轮反馈后才能继续细化。
- 普通和中等复杂度任务仍使用单个 `001-xxx-xxx.md`，不要为了显得完整而拆子 Plan。
- 父 Plan 使用 `001-xxx-xxx.md`，只做总纲、边界、阶段顺序和恢复入口；它不直接生成或绑定 task。
- 子 Plan 使用 `001a-xxx-xxx.md`、`001b-xxx-xxx.md`，按父 Plan 的 `child_plans` 顺序串行推进。
- 初始规划时可以先列出每个子 Plan 的方向，但只把第一个子 Plan 细化到可生成 task 的程度；后续子 Plan 根据实际推进、反馈和验收结果再动态细化。
- 父子 Plan 之间通过 frontmatter 双向绑定：父 Plan 写 `child_plans`，子 Plan 写 `parent_plan`。兄弟顺序只由父 Plan 的 `child_plans` 表达，不新增 `previous_plan` / `next_plan`。

`to-plan` 和 task / implementation step 的边界：

- Sky Flow `to-plan` 只负责计划层，重点是 summary、范围、阶段、task handoff、进度追踪和恢复入口。
- `to-plan` 不写 step-by-step implementation，不写命令清单为主，也不替 `to-task` 拆内部 step。
- `to-task` 负责把 `task_ready` plan 拆成可执行 task，包括依赖、并行关系、single writer、fan-in 和 task-level step。
- `to-plan` 可以记录模块边界、ownership、single writer / no-touch、阶段级并行 lane 和验证意图；具体文件路径、代码片段、测试命令、red-green step 和 commit 粒度留给 `to-task`。

执行承接规则：

- 当 `plan` 进入执行时，主会话应维护当前 runtime 的任务清单。
- 如果 runtime 是 Codex，必须使用 Codex 内置的 `update_plan` tool 维护任务清单。
- 执行任务时，任务清单由主会话负责维护；主会话要根据 `task` 状态变化及时使用 `update_plan` 更新任务清单。
- 若存在并行组，runtime 任务清单中用 `[并行 n]` 标记同一并行批次。
- 当进入父 Plan 时，runtime plan 只承接当前可执行子 Plan；父 Plan 本身只作为总纲和子 Plan 顺序来源。

示例：

```text
- task A
- [并行 1] task B-1
- [并行 1] task B-2
- task C
- [并行 2] task C-1
- [并行 2] task C-2
- task D
```

### to-task

`to-task` 用于从 `plan` 生成或更新 `task`。

它必须以 `plan` 文档作为输入。它负责拆分 task、定义 task 类型、依赖、被依赖、并行关系和外部 plan
依赖。它根据复杂度和阶段性特征决定是否在 task 内部拆 `step`。

父 Plan 不能直接进入 `to-task`。当输入 Plan 的 `plan_role` 是 `parent` 时，`to-task` 必须先切换到
`child_plans` 中当前可执行的子 Plan；如果没有可执行子 Plan，应回到 `to-plan` 先细化第一个子 Plan。

并行派发安全规则：

- 依赖已满足、写集不冲突、fan-in 方式清楚的 `task`，应尽量并行派发。
- task 一般由子代理承接，也可以由当前主会话或新会话主代理承接；owner 是执行时选择，不是 task 的固定身份。
- 如果 runtime 支持二级子代理，task owner 可以在自己的 task scope 内继续派发二级子代理；如果 task 由主会话承接，主会话也可以继续为该 task 派发子代理。
- 二级子代理不直接修改 plan / task status；task owner 先 fan-in 二级结果，再向主会话汇报最终结果、验证证据、changed files 和 blocker。
- 主会话继续负责 coordination、状态更新和 fan-in；这与 `coordination` 类型不派给普通子代理的规则一致。
- `to-task` 应预估哪些 task 会产生正式产物；对有产物的阶段，根据必要程度穿插 `consolidation` 类型 task
  和阶段 review。
- 当 `task_type: review` 时，task 应推荐执行时使用 `to-review`，并写清 review target、focus、evidence input、output contract 和 escalation hint；修复不混入 review task。
- 当 `task_type: verification`，或 task 需要新增 / 修改测试、写 `Given / When / Then`、判断测试 ROI、选择 stable seam、决定 Red / Green / Refactor 或替代验证时，task 应推荐执行时使用 `to-test`，并写清 behavior、ROI、seam、execution mode、verification evidence 和 artifact writeback。
- 真实事故回归的测试化 task 推荐 `to-bdd-regression`，并复用 `to-debug` 的 reproduction、evidence、incorrect path 和 correct path；普通测试策略不强行走事故回归入口。
- `to-task` 可以在不改变 plan goal / scope / milestone intent 的前提下调整 task DAG；如果执行策略、milestone 边界、plan shape、scope 分解或 task handoff 需要变化，回到 `to-plan`；如果目标、scope、外部契约、数据口径、业务行为或 requirements 需要变化，回到 `to-spec`。

### to-implement

`to-implement` 用于执行 Sky Flow `plan` / `task` DAG，是 Sky Flow 的执行协调器。

它倾向自动触发，但不是日常任务入口。只有用户显式指定 `to-implement`，或要求执行 / 继续 / 推进某个已制定的
Sky Flow plan / task artifact，或当前会话已经进入文件化 Sky Flow plan / task 的执行阶段时，才自动进入。

它不重做设计、不无根据重写 plan / task、不默认直接写业务代码。它负责读取已准备好的 plan / task，选择下一批可执行 task，
决定主代理和子代理分工，管理上下文、验证、fan-in、runtime plan、状态回写和必要的执行期计划调整。没有指定 Sky Flow plan / task artifact，
且任务本身可以日常直接完成时，不要为了使用 Sky Flow 而触发 `to-implement`。

`to-implement` 和相邻能力的边界：

- `to-plan` 负责计划层：目标、范围、阶段、恢复入口和进入 `to-task` / `to-implement` 的 handoff。
- `to-task` 负责拆 task DAG：task 类型、依赖、并行关系、single writer、fan-in 意图和 task-level step。
- `to-implement` 负责执行层：读取 task DAG、派发 / 执行 task、维护 runtime plan、验证、review、收敛、验收 gate、fan-in、状态回写和执行期 plan / task 调整。
- `to-test` 只负责测试策略、测试 ROI、stable seam、Red / Green / Refactor 和替代验证判断；`to-implement` 可以触发它，但不替代它。
- `to-consolidation` 只在阶段产物完成后收敛 diff 熵值；`to-implement` 可以触发它，但不替代它。
- `to-acceptance` 只在人类验收、sign-off、争议确认或反馈节点创建 / 更新验收文档；`to-implement` 可以触发它，但不替代它。
- `validate-flow` 只检查 artifact/status；`to-implement` 负责在修改 plan / task 后触发它。

核心流程：

1. Load and review：读取 plan、tasks、关联 spec / issue，确认 artifact 状态可执行；如果 plan / task 有缺口、依赖不满足或 scope 不清，先停，不猜。
2. Select executable task：根据 `depends_on`、status、parent / child plan 顺序选择下一批 task；parent plan 不直接执行，task 缺失时回到 `to-task`。
3. Decide execution mode：主代理默认是 coordinator，不直接写业务代码；实现型 task 默认派 worker。
4. Dispatch packet：每个子代理必须拿到 mission、source artifact、task text、allowed write scope、no-touch、context policy、verification intent、output contract 和 stop condition。
5. Fan-in and verify：主代理读取子代理结果，检查 changed files、task 要求、spec alignment 和验证结果；必要时触发 test / review / consolidation / acceptance / validate-flow。
6. Update runtime and artifacts：主代理维护 runtime plan；Codex runtime 必须调用内置 `update_plan` tool 同步 task status、并行批次、fan-in 和 next action。
7. Artifact writeback：主代理更新 task status、plan progress / recovery / decision / blocker。
8. Acceptance gate：到达人类验收、sign-off、争议确认或反馈节点时，调用 `to-acceptance` 创建或更新验收文档。
9. Dynamic maintenance：执行事实要求拆分 task、调整依赖 / 并行关系或补充验证 / 收敛 task 时，在已确认 scope 内按 `to-task` 规则更新 artifact 并运行 `validate-flow`。
10. Stop on blockers：遇到关键歧义、验证反复失败、scope / contract / 数据口径变化或高风险操作时，停止并询问人类。

执行模型：

- 主代理是 plan owner、coordinator、fan-in reviewer 和 artifact maintainer。
- 主代理默认不直接写业务代码；如果确实需要主代理承担实现，应优先 full-context fork 一个“主代理替身” worker 去写。
- 实现型 worker / 主代理替身优先 full fork；explorer / reviewer / docs researcher / verifier 优先最小上下文包。
- 一个子代理通常对应一个 task，或一组明确同 owner、同写集边界的并行 task。
- task 一般由子代理承接，也可以由当前主会话或新会话主代理承接；主代理承接会话、维护 plan runtime 进度和 artifact 状态。
- 只要并行时间收益、上下文隔离收益、专业化收益、质量 / review 收益任一成立，且 fan-in 成本可控，就应该派发子代理；其他明确正向收益也可以成立。
- runtime 支持二级子代理时，task owner 可以在自己的 task scope 内继续派发二级子代理，并负责二级 fan-in。
- 子代理不直接修改 plan；主代理 fan-in 后回写进度、决策、阻塞和恢复入口。
- 子代理状态至少能表达 `DONE`、`DONE_WITH_CONCERNS`、`NEEDS_CONTEXT`、`BLOCKED`。
- spec compliance review 应先于测试策略和 code quality review；不接受“close enough”的 spec 偏差。
- 执行中涉及测试策略、BDD/TDD、测试 ROI、stable seam 或替代验证时，必须触发 `to-test`；真实事故回归固化继续交给 `to-bdd-regression`。

并行规则：

- 依赖满足、写集不冲突、上下文可隔离、fan-in 成本可控时，必须尽量并行派发实现型 task。
- explorer / reviewer / verifier 的并行门槛可以低于 worker，但必须有明确 output contract。
- 不把 coordination task 派给普通子代理；coordination 默认由主代理承担。
- task owner 的二级并行必须保持在自己的 task scope 内，不能绕过主代理维护 plan / task status。
- 如果任务强耦合、共享核心文件多 writer、或 review / 返工需要跨多轮，不在 `to-implement` 中硬并行；应拆小 task、串行化共享写集，或暂停并回到 `to-task` / `to-plan` 重新表达执行边界。

子代理 ROI 执行规则：

- `to-implement` 是最终执行调度点，必须在选择 task owner 和并行批次时主动判断子代理 ROI。
- 只要并行时间收益、上下文隔离收益、专业化收益、质量 / review 收益或其他明确正向收益任一成立，且 fan-in 成本可控，就应该派发子代理。
- 如果收益不成立、fan-in 成本超过收益、共享写集无法 single writer，或需要主会话直接决策高风险取舍，可以由主会话承接 task，但必须记录原因。

执行期计划维护：

- `to-implement` 参考 `to-plan` 的计划层约束，同时维护 runtime plan 和文件化 plan / task artifact。
- runtime plan 是当前会话执行投影，可以更细、更临时；Codex runtime 必须使用内置 `update_plan` tool 维护任务清单。file artifacts 是长期真相源，只记录稳定进度、task status、依赖变化、关键决策、blocker、验证证据和恢复入口。
- 下游动态调整不能和上游定义冲突；任何策略或设计重决策都必须回到对应上游 skill 更新 artifact，再继续执行。
- 如果只是状态推进、blocker、验证证据或恢复入口变化，主代理直接更新 task / plan 对应 section；Codex 中同步调用 `update_plan`。
- 如果实现事实显示 task 过大、遗漏、依赖方向错误、并行关系可以释放，或需要新增 review / verification / consolidation task，主代理可在原 goal / scope 内按 `to-task` 规则维护 task DAG，并同步 runtime plan。
- 如果执行策略、milestone 边界、plan shape、scope 分解或 task handoff 需要变化，必须暂停执行并调用 `to-plan` 更新 plan。
- 如果目标、scope、外部契约、数据口径、业务行为或 requirements 需要变化，必须暂停执行并调用 `to-spec` 更新 spec。
- 子代理只能提出 plan / task 调整建议；文件化 artifact 状态由主代理 fan-in 后维护。

参考取舍：

- 参考 `executing-plans` 的批判性读 plan、逐 task 推进、验证 checkpoint、遇 blocker 不猜。
- 参考 subagent-driven 模式的 fresh subagent、上下文控制、状态回报、spec compliance review 和 code quality review。
- 吸收主代理管理、子代理 ROI、进度真相源、恢复入口和续跑提示的有价值理念，但只保留对执行层有直接价值的约束。
- 不照搬强制 worktree、每 task commit、所有任务默认 TDD、2-5 分钟 step 粒度或无停顿连续执行。

### to-review

`to-review` 用于小型 review 或明确 review 指令。

它可以自动触发，但不自动升级为 `to-review-loop`。它关注的是代码、artifact、设计和行为风险：是否存在 bug、回归、测试缺口、安全 / 可靠性风险、实现与需求不一致、验收证据不足或可维护性问题。

`to-review` 的输出必须 findings-first：先列问题，再给简短总结。问题按严重度排序，尽量给文件 / 行号、
证据、影响和建议修复方向；没有发现问题时明确说没有 blocking findings，并说明剩余风险或未覆盖验证。
它优先降低误报，不为了凑数量输出弱问题。

`to-review` 可以使用内部 reviewer profile：

- `review-by-somestay`：中等深度、高信号 review，适合多数非平凡 diff 或 artifact 复审。
- `review-by-sanyuan`：深度 review，只在跨模块、契约、安全、共享状态、架构或高风险 fan-in 场景升级。

内部 reviewer profile 不作为 Sky Flow 顶层流程入口。它们只服务 `to-review` 的审查深度分层。

`to-review` 不负责整理 pending diff 的补丁痕迹；这属于 `to-consolidation`。它也不负责 Sky Flow artifact 的 frontmatter、状态、DAG 或验收归宿；这属于 `validate-flow`。

### to-review-loop

`to-review-loop` 用于 review-fix-review 循环。

它需要显式触发，避免普通 review 被自动升级成高成本修复循环。循环过程是：先用 `to-review` 找出 blocking /
high-ROI findings，再在已确认 scope 内修复，然后重新 review，直到 blocking findings 清零、剩余问题被记录为
non-blocking，或遇到 scope / design / contract ambiguity 必须停下询问人类。

`to-review-loop` 不能借修复 review 问题私自扩大范围。修复后应根据产物形态触发必要验证、`to-consolidation`
和 `validate-flow`；如果发现计划、任务或规格需要改变，应回到 `to-plan`、`to-task` 或 `to-spec` 更新上游 artifact。

### to-agent-review

`to-agent-review` 用于分析 Agent 历史行为和 Sky Flow 执行链路。

它分析 Agent 决策链路、工具调用、子代理 ROI、上下文管理、fan-in、runtime plan 维护、artifact 状态回写和流程低效点，目标是找出可复现的问题线索和可落地的流程改进项。

它默认需要显式触发。普通会话中，只有明确要求 Agent 决策链路复盘时才自动触发；runtime 自动化可以在固定
时间点定期触发，用于沉淀长期的 Agent 行为质量和流程改进线索。

输出默认落到 `${SKY_FLOW_ROOT}/backlog/agent-reivew/`，保留足够上下文、证据、影响、建议和可恢复入口。这个目录是 Agent 复盘报告落点，不等同于调用 `to-backlog`，也不要求生成 `backlog` artifact。如果结论会改变 Sky Flow 的长期设计、计划策略或任务拆分规则，不在复盘内直接改写上游真相源，而是转交 `to-spec`、`to-plan` 或 `to-task` 更新对应 artifact。

复盘必须包含固定量化信号清单；不可见的数据写 `unknown`，不能估算成事实。固定信号包括：总耗时、工具调用分类、失败 / 重试调用、重复上下文读取、上下文加载压力、子代理数量和状态、并行效率、fan-in 轮次、runtime plan 更新、artifact / report 写回、验证证据、blocker 和人类问题数量。

它不做这些事：

- 不调用 `to-backlog`。
- 不输出到 `handoff`。
- 不直接回灌 `spec`。
- 不直接回灌 Sky Flow Skill 文档。
- 不把自身定位为 Sky Flow 套件的自我迭代机制。
- 不替代 `to-review`、`to-review-loop` 或 `to-consolidation`。

### pick-plan

`pick-plan` 用于从现有 plan 中挑选下一步最值得继续推进的 plan。

它需要显式触发，不自动运行。

`pick-plan` 的设计需要包含 Codex Goals 官方参考：

- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex

触发后执行：

1. 读取未完成的 plan，以及 1 天以内完成的 plan。
   - 实现应优先用只读 inventory 脚本生成候选清单；脚本只负责事实收集，不替代 Agent 做语义排序和推荐。
2. 输出 plan list，并按继续推进价值排布优先级。
3. 推荐一个 plan。
4. 输出推荐 plan 的简明上下文：背景、目标、进度和下一步。
5. 输出一个可复制代码块，供开发者在新会话中继续推进。

代码块内放完整续跑提示词，不带 `/goal` 前缀：

```text
目标: <由 plan.frontmatter.goal 生成的目标契约>
工作区: <absolute or repo path>
Plan: <plan path>
当前状态: <status and recovery summary>
下一步: <one concrete next action>
限制: <scope, no-touch, env, approval or blocker boundaries>
验证方式: <from plan verification intent or local project rules>
停下问人: <blocking ambiguity / failed validation / scope change conditions>
```

这个代码块必须完整可用，用户复制后即可在新会话中继续推进。

开发者看到推荐后，可以选择：

- 继续补充并完善提示词。
- 换一个 plan。
- 手动指定 plan。

### to-acceptance

`to-acceptance` 用于创建或更新 `acceptance`。

它不只由 `sky-flow` router 检测触发。Agent 在完成某个任务、阶段、临时工作或只读调查后，应自行判断
是否需要人类验收；`to-implement` 在 plan / task 执行到验收 gate、sign-off、争议确认或人类反馈节点时，
必须调用 `to-acceptance` 创建或更新验收文档。

`to-acceptance` 是 Sky Flow 通用验收能力，不绑定移动设备、截图矩阵或任何项目专属验收场景。它把 plan /
task / spec 中需要人类判断的内容转成可反馈的验收项，记录验证证据、观察结果、残余风险、需要确认的问题和下一轮动作。

轻量自检门禁：

- 声明完成前必须有对应验证证据。
- 验收项要能映射到实际产物、行为场景、观察结果或验证命令。
- 验收项不能验证私有实现细节；它应保护用户可见行为、业务不变量、artifact 契约、外部接口或交付边界。
- 人类需要确认的项要写成可判定的问题，而不是泛泛总结。

### to-next-acceptance

`to-next-acceptance` 是 `to-acceptance` 的子能力，用于把已有 `acceptance` 推进到下一轮。

它不会把人类没提及的验收项默认视为通过。未被提及的项继续保留到下一轮，直到人类明确通过、明确失败、
明确放弃，或转入 backlog。

当当前请求明确是在处理已有 `acceptance` 的人类反馈时，使用 `to-next-acceptance` 推进轮次。
处理人类反馈时，先分类再行动：明确通过、明确失败、需要澄清、争议项、未提及项。争议项不自动改，
应保留到下一轮或转入 backlog。未提及项继续保留，不默认通过。

### to-backlog

`to-backlog` 用于创建或更新 `backlog`。

它可以从当前会话、`plan` 或 `task` 进入。核心要求是补足上下文，说明为什么当前阶段无法推进、依赖什么、
什么时候适合捞回。

### to-handoff

`to-handoff` 用于创建或更新 `handoff`。

它可以从当前会话、`plan`、`task`、`acceptance` 或 `backlog` 进入。核心要求是保存可执行恢复状态，而不是聊天摘要。

`to-handoff` 写出的内容必须让下一轮 Agent 只读 handoff 和引用的 artifact / 文件，就能知道目标、当前状态、
已完成项、未完成项、验证证据、风险、阻塞、允许范围、禁止范围、下一步和停止条件。它不能依赖聊天历史作为唯一上下文。

`to-handoff` 不替代来源 artifact 的状态真相。长期设计事实回 `spec`，计划和任务进度回 `plan` / `task`，
验收反馈回 `acceptance`，无法推进但值得保留的阻塞回 `backlog`；handoff 只做恢复入口和交接索引。

### to-commit

`to-commit` 用于处理明确提交指令。

它可以自动触发，但必须遵守项目本地提交规范、允许范围和验证要求。提交阶段如果 staged diff 包含 workflow artifact，可以先推荐运行 `validate-flow`；如果 staged diff 不包含 workflow artifact，不为了形式运行 artifact 校验。

`to-commit` 不执行 `to-consolidation`。diff 收敛应由 `to-task` 像 review task 一样根据阶段风险、fan-in 复杂度和产物形态提前插入，或由用户显式触发。

### to-consolidation

`to-consolidation` 用于阶段产物完成后的收敛检查。

它可以自动触发，触发条件是阶段任务完成且有产物产出、`to-task` 显式安排 consolidation task、多 Agent fan-in 后，或用户要求收敛。它只检查当前目标 diff 是否干净、统一、可交付，重点是补丁式实现、临时代码、重复逻辑、旧注释、debug 残留和 fan-in 半成品。默认范围是当前工作区 pending diff，明确包括 unstaged、staged 和 untracked files。

它不做 code review，不判断实现是否有业务 bug；这属于 `to-review`。它也不检查或修正 Sky Flow artifact/status 漂移；这属于 `validate-flow`。

### validate-flow

`validate-flow` 用于检查 Sky Flow artifact 是否符合规范。

它不是普通的完成前自检，也不主要依赖 LLM 逐项阅读。它负责 artifact 契约和状态一致性，包括 fan-in 后 plan / task / acceptance / backlog / handoff 是否互相漂移。校验采用“脚本预检 + LLM 收口”的两段式流程：

1. 脚本先做确定性预检，快速发现 frontmatter、枚举、命名、依赖和 DAG 问题。
2. LLM 再基于脚本报告做语义收口，检查上下文是否充分、状态说明是否合理、artifact 之间的意图是否一致。

脚本预检范围：

- frontmatter 是否存在必需字段。
- `artifact_type`、`status`、`task_type`、`acceptance_type` 是否使用合法枚举。
- `spec`、`plan` 和 `task` 文件名 / 编码是否符合规则。
- `completed` Plan 是否位于 `plan/done/`，以及未完成 Plan 是否误放到 `plan/done/`。
- task 是否位于所属 plan 名称目录下。
- plan 的 `plan_role`、`planning_depth` 和父子命名是否符合层级约定。
- 父子 artifact 是否只绑定相邻层级，且双向绑定是否一致。
- 父 Plan 的 `child_plans` 和子 Plan 的 `parent_plan` 是否双向一致。
- 父 Plan 是否错误绑定了 task，或子 Plan 是否和父 Plan 数字前缀不一致。
- `plan -> task` DAG 是否存在缺失节点、悬空依赖、循环依赖或非法外部依赖。
- `task.depends_on`、`task.depended_by`、`task.parallel_with` 是否互相一致。
- plan 来源 `acceptance` 是否被对应 `plan.acceptance` 反向列出，避免 `plan.acceptance` 为空时漏掉验收漂移。
- plan / task / acceptance 状态是否存在低误报的机械冲突。
- 后序子 Plan 是否在前序子 Plan 未完成时已经进入 `in_progress` / `completed`。
- `backlog` / `handoff` 的来源 artifact 是否可追溯。
- `abandoned` 是否有对应 backlog 或明确人工协商记录。
- artifact 路径是否落在 `SKY_FLOW_ROOT` 指定或默认的根目录下。

LLM 收口范围：

- dependency / parallel 关系是否符合任务语义，而不只是格式合法。
- `plan.goal` 是否足以作为 Codex 续跑契约。
- fan-in 后状态是否与实际产物、验证证据和剩余工作一致。
- `acceptance` 是否能说明自身来源。
- `backlog` 是否讲清主题、阻塞原因、依赖和建议恢复时机。
- `handoff` 是否保留可执行状态，而不是只写聊天摘要。
- 脚本无法判断的争议项是否需要回到人类确认。

脚本应优先放在 `scripts/` 下，由 `validate-flow` Skill 调用。校验器使用 TypeScript 表达 schema 和
校验逻辑：`scripts/schema.ts` 存放枚举、必填字段和命名规则，`scripts/validate_flow.ts` 负责扫描和输出报告。
脚本输出应是结构化报告，至少包含
`errors`、`warnings` 和 `checked_artifacts`，方便 LLM 用较少 token 做最终判断。

`validate-flow` 可以被 Agent 在交付前主动调用，也可以被其他子 Skill 在写入 artifact 后推荐调用。

## 层级定义

Sky Flow 当前定义八个 artifact 层级：`spec`、`issue`、`plan`、`task`、`step`、`acceptance`、
`backlog`、`handoff`。

它们通过 frontmatter 记录状态、归属和依赖关系。

父子依赖文档需要双向绑定，但只绑定相邻层级。例如 `spec` 绑定直接关联的 `plan`，`plan` 绑定直属
`task`；`spec` 不直接绑定 `task`，`task` 也不直接绑定跨层级的长期设计文档。

### Spec

`spec` 是设计文档。

它通常通过 `to-spec` 与人类持续对话、校准事实、澄清取舍、收敛设计后得到，可以长期留存，作为后续
计划和实现的设计参考。

命名规则：

- 文件名就是唯一 ID。
- 不使用编号前缀。
- 示例：`sky-flow.md`。

定位规则：

- 一个 `spec` 可以关联多个 `plan`。
- `plan` 可以不属于任何 `spec`。
- 如果某个 `plan` 与 `spec` 强关联，必须在相邻层级双向绑定：`spec.plans` 记录该 `plan`，
  `plan.spec` 记录该 `spec`。

推荐 frontmatter：

```yaml
id: sky-flow
artifact_type: spec
status: draft
plans: []
```

### Issue

`issue` 是最近发现的问题、搜集到的线索，或尚未进入实施的可独立认领工作单元。

它还没有进入修复环节，只负责记录现象、证据、线索、影响面、vertical slice 和后续可能的切入点。
`issue` 不等同于 `plan`；只有当人类或 Agent 决定进入修复、实现或系统化分析时，才从 `issue` 派生或关联 `plan`。

命名规则：

- 可以使用短语义文件名。
- 不强制编号；项目可以选择自己的排序规则。

定位规则：

- `issue` 可以长期保留为线索记录。
- `issue` 可以记录一个 problem record，也可以记录一个可独立认领、可验证的 vertical slice。
- `issue` 可以关联一个或多个 `plan`。
- 如果某个 `plan` 是为处理该 `issue` 创建的，必须双向绑定：`issue.plans` 记录该 `plan`，
  `plan.issues` 记录该 `issue`。
- `issue` 默认写入 `${SKY_FLOW_ROOT}/issue/`；它不是外部 tracker issue。
- 若本地 `${SKY_FLOW_ROOT}/AGENTS.md` / `${SKY_FLOW_ROOT}/CLAUDE.md` 声明 issue 目录纳入 TOC，
  issue 增删移动时必须同步维护对应 TOC。

推荐 frontmatter：

```yaml
id: example-issue
artifact_type: issue
status: draft
plans: []
```

推荐正文模板保持轻量：

```markdown
# <Issue Title>

最后更新：<YYYY-MM-DD>

## Summary

<问题、机会或 slice 目标。>

## Source Context

- Source:
- Related artifacts:
- Current state:

## Evidence

- <日志、验证结果、用户反馈、review finding、代码位置、artifact section 或观察结论>

## Impact

- <影响范围、风险、为什么值得保留或处理>

## Proposed Slice

- Type: AFK / HITL
- Outcome:
- Verification:
- Blocked by:

## Open Questions

- <进入 plan 前必须澄清的问题；无则省略>

## Notes

- <关键约束、已知非目标、相关决策或后续建议>
```

可选 section：

- `Dependency Order`：一次拆出多个 issue 且存在依赖时。
- `Acceptance Notes`：已有可观察验收口径，但还没进入 plan 时。
- `Related Backlog`：由 backlog 恢复出的 issue 或与阻塞有关时。

### Plan

`plan` 是具体实施计划，也是进度和编排中心，一般由主会话负责创建和维护。

它不只描述“准备做什么”，还负责承载 task 编排、当前进度、并行批次、阶段产物、验收意图和恢复入口。
在 Codex runtime 中，主会话需要把 plan 的 task 编排同步到 `update_plan` tool，并随着 task 状态变化持续更新。

命名规则：

- 使用符合字母序的编号前缀。
- standalone / parent Plan 格式：`001-xxx-xxx.md`。
- child Plan 格式：`001a-xxx-xxx.md`、`001b-xxx-xxx.md`。
- child Plan 必须和 parent Plan 共享三位数字前缀，例如 `001-example.md` 的子 Plan 使用 `001a-*`、`001b-*`。
- 编号用于稳定排序，不表达优先级本身。

目录规则：

- 未完成、正在实施或可恢复的 Plan 保存在 `${SKY_FLOW_ROOT}/plan/`。
- 已实现完成且 `status: completed` 的 Plan 必须移入 `${SKY_FLOW_ROOT}/plan/done/`。
- `plan/done/` 下的完成 Plan 仍是 Sky Flow plan artifact，可被 `validate-flow` 校验，也可被 `pick-plan` 在近期完成窗口内作为后续承接背景读取。
- 非 `completed` 状态的 Plan 不应放在 `plan/done/`，避免 active plan 清单和历史完成计划混在一起。

定位规则：

- `plan` 可以独立存在，不强制绑定 `spec`。
- 如果 `plan` 与某个 `spec` 强关联，必须绑定该 `spec`。
- 如果 `plan` 是为处理某个 `issue` 创建的，必须绑定该 `issue`。
- `plan` 通过 frontmatter 绑定直属 `task` 列表。
- `plan` 可以绑定一个主 `acceptance` 文档，但不是所有 `acceptance` 都必须来自 `plan`。
- `plan` 不直接绑定 `step`；`step` 只存在于 `task` 文档内部。
- `plan_role` 默认为 `standalone`；只有超级巨大任务才使用 `parent` / `child`。
- `planning_depth` 表示当前计划细化程度：`outline` 只到方向和边界，`task_ready` 可以进入 `to-task`。
- parent Plan 必须是 `planning_depth: outline`，`tasks: []`，并通过 `child_plans` 维护串行子 Plan 列表。
- child Plan 必须通过 `parent_plan` 指向 parent Plan；初始阶段只把第一个 child Plan 细化到 `task_ready`。

推荐 frontmatter：

```yaml
id: 001-example-plan
artifact_type: plan
status: draft
goal: Complete the example plan, verified by the linked acceptance artifact, while preserving the declared scope and constraints. Use only the files and tasks listed in this plan. Between iterations, update task status and runtime plan state. If blocked or no defensible path remains, stop with evidence, blockers, and the next input needed.
spec: sky-flow
issues: []
plan_role: standalone
planning_depth: task_ready
parent_plan:
child_plans: []
tasks: []
acceptance: 001-example-plan-acceptance
completed_at:
```

父 Plan frontmatter 示例：

```yaml
id: 001-example-system
artifact_type: plan
status: draft
goal: Coordinate the example system build through the listed child plans. Keep this parent as the outline and sequencing source; execute only the active child plan. Update child plan status after each iteration and stop with evidence if the next child cannot be safely detailed.
spec: sky-flow
issues: []
plan_role: parent
planning_depth: outline
parent_plan:
child_plans:
  - 001a-example-foundation
  - 001b-example-runtime
tasks: []
acceptance:
completed_at:
```

子 Plan frontmatter 示例：

```yaml
id: 001a-example-foundation
artifact_type: plan
status: draft
goal: Complete the foundation slice for the parent plan, with tasks and validation scoped to this child plan only.
spec: sky-flow
issues: []
plan_role: child
planning_depth: task_ready
parent_plan: 001-example-system
child_plans: []
tasks: []
acceptance:
completed_at:
```

推荐正文模板保持轻量。必备 section 只放 plan 层需要长期维护的信息；frontmatter 已表达的字段不要在正文机械重复。

```markdown
# <Plan Title>

最后更新：<YYYY-MM-DD>

## Summary

<3-6 句说明本 plan 要达成什么、从哪里来、当前处于什么阶段。>

## In Scope

- <明确包含的工作>

## Out of Scope

- <明确不做的工作>

## Execution Model

- Ready for `to-task`: yes / no
- Ready for `to-implement`: yes / no
- Task topology:
  - <阶段级串行顺序、可并行 lane 或 no-task execution reason>
- Execution Notes:
  - <执行前必须知道的边界、owner 或验证意图；不写完整执行模型>

## Milestones

1. <阶段名>
   - Outcome:
   - Agent / Owner:
   - Verification:
   - Handoff to `to-task`:

## Progress Log

- <YYYY-MM-DD>: <关键进展、决策、阻塞或 fan-in 结果>

## Recovery

- Resume from:
- Next action:
- Blockers:
```

可选 section 只在确有长期价值时添加：

- `Agent Lanes`：多子代理 / 多 task lane 时。
- `Dependencies / Parallelism`：依赖或并行关系复杂时；必须表达阶段级串行关系和可并行 lane。
- `Risks / Blockers`：存在真实阻塞或高影响风险时。
- `Decision Log`：有多个会影响后续维护的取舍时。
- `Validation Evidence`：已有验证结果需要长期保留时。
- `Parent / Child Plan Notes`：只有 parent / child plan 才需要。

Plan self-review：

- Spec coverage：spec 的关键 requirements / acceptance scenarios 是否至少映射到一个 milestone、task handoff 或 verification intent。
- Placeholder scan：不得出现无意义的 `TBD`、`TODO`、`handle edge cases`、`add appropriate validation` 等空泛计划语言；允许 `[NEEDS CLARIFICATION: ...]`，但必须标明是否 blocking。
- Scope check：输入是否仍适合单个 standalone plan；如已覆盖多个独立子系统，应拆分或升级 parent / child plan。
- Dependency check：阶段前置依赖、可并行关系、single writer / no-touch 和 blocker 是否足够支持后续 `to-task`。
- Parallelism check：是否把可并行阶段和 lane 表达清楚；不要把无真实依赖的工作串行化。
- Recovery check：下一轮能否只读本 plan 恢复 current phase、next action、blockers 和 last validated state。
- Boundary check：是否提前写入 implementation details、step-by-step code、命令清单或 commit 粒度；这些应留给 `to-task`。

### Task

`task` 是不大不小的具体任务，必须归属于某个 `plan`。

它通常由主会话拆出，并一般由子代理承接执行；也可以在某个新会话由主代理承接。主会话主要维护 plan runtime
进度、artifact 状态和 fan-in。
长期目标是让 `task` 成为并行执行的主要调度单元，也可以定义专门 Agent 来负责不同类型的 `task`。
如果 runtime 支持二级子代理，task owner 可以在自己的 task scope 内继续派发二级子代理；如果 task 由主会话承接，
主会话也可以继续为该 task 派发子代理。

命名规则：

- 与 `plan` 类似，使用编号前缀和名称。
- 格式：`01-xxx-xxx.md`。
- 编号只在所属 `plan` 范围内保证排序。
- `task` 必须以所属 `plan` 名作为目录名存放，目录下再放具体 task 文档。
- 示例：`tasks/001-example-plan/01-example-task.md`。

定位规则：

- `task` 必须记录所属 `plan`。
- `task` 可以依赖同一 `plan` 下的其他 `task`。
- `task` 可以依赖外部 `plan` 下的 `task`，但必须写清外部 `plan` 和外部 `task` ID。
- `task` 需要显式记录：
  - 它依赖哪些 `task`。
  - 哪些 `task` 依赖它。
  - 它能和当前所属 `plan` 下哪些 `task` 并行。
  - 它是否允许 task owner 在 task scope 内继续派发二级子代理。

推荐 frontmatter：

```yaml
id: 01-example-task
artifact_type: task
task_type: exploration
status: draft
plan: 001-example-plan
depends_on: []
depended_by: []
parallel_with: []
external_depends_on: []
```

推荐正文模板保持轻量。固定的是核心必要信息，不是完整标题清单；标题可以按 task 形态调整。

```markdown
# <Task Title>

## Summary

<任务目标、来源 milestone、期望产物。>

## Scope

- Allowed Write Scope:
- No Touch:

## Dependencies

- Depends on:
- Can run in parallel with:
- Blocks:

## Execution Handoff

- Recommended owner:
- Context policy:
- Delegation policy:
- Output contract:
- Stop condition:

## Verification Intent

- <应保护的行为、不变量或证据类型。>
```

核心必要信息：

- `Summary`：任务目标、来源 milestone、期望产物。
- `Scope`：allowed write scope 和 no-touch scope。
- `Dependencies`：depends on、can run in parallel with、blocks。
- `Execution Handoff`：owner、context policy、delegation policy、output contract、stop condition。
- `Verification Intent`：应保护的行为、不变量或证据类型。

常见可选 section：

- `Steps`：task 自身复杂、需要 checkpoint 或明确阶段顺序时。
- `Context Notes`：需要保留关键背景、事实来源或读取入口时。
- `Interface / Data Notes`：task 涉及契约、数据口径或外部接口时。
- `Risks / Blockers`：存在真实风险或阻塞时。
- `Decision Log`：执行中形成会影响后续维护的取舍时。
- `Fan-in Notes`：多子代理或二级子代理需要汇总时。
- `Validation Evidence`：已有验证证据需要长期保留时。

允许在模板不足以承载关键执行信息时新增自定义 section。不要为了完整感添加空 section；frontmatter 已表达的信息不要在正文机械重复。

### Step

`step` 是 `task` 文档内部的可选阶段。

不是所有 `task` 都需要拆 `step`。只有较复杂的任务，或本身明确需要分阶段推进的任务，才应该在
`task` 内部定义 `step`。

定位规则：

- `step` 不单独成文档。
- `step` 只存在于 `task` 文档内部。
- 同一个 `task` 内的 `step` 一定是串行关系。
- `step` 通常表示阶段性任务完成点，而不是任意细碎操作。

推荐写法：

```md
## Steps

1. <阶段一>
2. <阶段二>
3. <阶段三>
```

### Acceptance

`acceptance` 是人机交互的验收文档。

Agent 完成的任务需要交给人类验收；`acceptance` 用来记录验收项、执行结果、人类反馈、剩余问题和下一轮
修订动作。它是一个不断循环迭代的文档，而不是一次性报告。

定位规则：

- `acceptance` 可以绑定 `plan`。
- `acceptance` 也可以游离存在，用于没有走 `plan` 的临时任务、小任务、只读调查或验收报告。
- 一个 `plan` 通常最多对应一个主 `acceptance` 文档，但游离态 `acceptance` 不受这个限制。
- `acceptance` 可以记录多个验收轮次。
- Agent 应自行判断某项工作是否需要人类验收；这不是必须由 `sky-flow` router 才能触发的能力。
- `acceptance` 不替代 `task` 状态；它记录人类验收视角下的通过、失败、阻塞和反馈。
- 未被人类提及的验收项不能默认通过，必须保留到下一轮。

验收形态：

- 具体枚举和选择规则以 `acceptance_type` 小节为准。
- 如果选择 `html_report`，涉及 JS、CSS 或媒体资源时，应以目录组织。

HTML 验收建议：

- 为节省 token 和降低样式复杂度，优先使用轻量 CSS，例如 Pico.css。
- 如果需要 JS / CSS / 媒体资源，使用目录形式，例如
  `acceptance/001-example-plan/index.html`、`acceptance/001-example-plan/assets/`。
- HTML 可以提升阅读和交互体验，但状态真相源仍应回写到 `acceptance` frontmatter 或 Markdown 正文。

推荐 frontmatter：

```yaml
id: 001-example-plan-acceptance
artifact_type: acceptance
status: draft
acceptance_type: interactive
source_type: plan
source_id: 001-example-plan
plan: 001-example-plan
round: 1
```

### Backlog

`backlog` 是实现过程中发现当前阶段暂时无法推进的阻塞点。

它可以来自当前会话，也可以来自 `plan` 或 `task`。转入 backlog 的内容必须保留充分上下文，让后续会话
可以独立判断为什么当时不继续、依赖什么、什么时候适合捞回推进。

定位规则：

- `backlog` 可以对应一个状态为 `abandoned` 的 `plan`。
- `backlog` 可以对应一个状态为 `abandoned` 的 `task`。
- `backlog` 可以直接基于当前会话创建，不要求一定来自 `plan` 或 `task`。
- `backlog` 必须说明主题、阻塞原因、依赖条件、推荐恢复时机和来源 artifact。
- 如果来源是当前会话，必须在正文中补足上下文，不能依赖聊天记录本身作为唯一来源。

推荐 frontmatter：

```yaml
id: example-blocker
artifact_type: backlog
status: draft
source_type: conversation
source_id: current-session
depends_on: []
recommended_resume: after-dependency-ready
```

### Handoff

`handoff` 是跨会话、换 Agent 或多 Agent 接手时的交接文档。

它保留可执行状态，而不是聊天摘要或长期设计真相源。`handoff`
应该让下一轮 Agent 能直接知道先读什么、当前状态是什么、允许做什么、禁止做什么、如何验证、何时停下问人。

`handoff` 是本地恢复态，默认写入 `${SKY_FLOW_ROOT}/handoff/`，该目录应由项目 `.gitignore`
排除，不进入版本库。需要长期保留、跨团队共享或进入 review / commit 边界的事实，必须回写到 `spec`、
`plan`、`task`、`acceptance` 或 `backlog`，不能依赖 handoff 作为唯一真相源。

定位规则：

- `handoff` 可以直接基于当前会话创建，不要求一定来自 `plan` 或 `task`。
- `handoff` 可以关联当前正在推进的 `plan`。
- `handoff` 可以关联某个具体 `task`。
- `handoff` 可以引用相关 `acceptance` 或 `backlog`，但不替代它们。
- 如果来源是当前会话，必须在正文中补足恢复上下文，不能依赖聊天记录本身作为唯一来源。
- `handoff` 通常是恢复入口；长期设计事实应沉淀回 `spec`，实施状态应沉淀回 `plan` / `task` / `acceptance`。
- handoff 可以记录多个并行 lane 的当前状态，但不能把无关进度混到同一个恢复入口里。

推荐 frontmatter：

```yaml
id: example-handoff
artifact_type: handoff
status: draft
source_type: conversation
source_id: current-session
plan:
task:
resume_from: current-session
```

推荐正文模板保持紧凑：

```markdown
# Handoff: <Title>

最后更新：<YYYY-MM-DD>

## Resume Goal

<下一轮要继续达成什么。>

## Current State

- Completed:
- In progress:
- Not started:

## Read First

- <artifact / file / URL>: <为什么下一轮必须先读>

## Scope

- Allowed:
- No Touch:

## Evidence

- <验证命令、检查结果、报告路径或观察结论>

## Risks / Blockers

- <未解决问题、阻塞、歧义或残余风险>

## Next Actions

1. <可执行下一步>

## Stop Conditions

- <何时停止并询问人类或回到上游 artifact>
```

可选 section：

- `Decision Log`：只记录会影响恢复和后续维护的关键取舍。
- `Parallel Lanes`：存在多 Agent / 多 task 并行进度时。
- `Tried And Failed`：只有能避免下一轮重复试错时。
- `Validation Gaps`：证据缺口会影响继续推进或验收时。

不要为了完整感添加空 section；不要复制大段 diff、日志、spec、plan 或聊天内容，只引用路径和关键结论。

## 关键原则

### 套件优先，不做巨型 Skill

Sky Flow 是工作流 Skill 套件，不是单个巨型 Skill。它会拆成多个子 Skill，每个子 Skill 负责一个清晰
阶段或能力，例如澄清、计划、任务展开、执行、验收、backlog、恢复和质量门禁。

子 Skill 可以被完整工作流编排，也可以独立使用。缺少某个推荐依赖时，子 Skill 应说明影响和降级方式，
而不是直接失效。

### 通用核心，SKY_FLOW 环境变量覆盖与项目本地文档

Sky Flow 核心不和任何项目耦合。通用层只定义 artifact、状态、依赖、路由和反馈闭环。

项目层只能通过 `SKY_FLOW_*` 环境变量覆盖少量 Sky Flow 运行时参数，例如 artifact 根目录和输出语言。技术栈、验证命令、环境限制、领域词汇和专属能力由项目本地文档或本地工具描述，不进入 Sky Flow core。

### 分入口使用

Sky Flow 不是所有任务的入口。

- 系统化任务：从 `spec` 进入，先澄清设计，再进入计划和任务拆分。
- 稍复杂但不需要长期设计沉淀的任务：可以从 `plan` 进入。
- 简单任务：不走 Sky Flow，直接使用原生 runtime 开始执行。

### Artifact 驱动，而不是聊天驱动

重要状态必须落到 artifact，而不是只留在聊天里。`spec`、`issue`、`plan`、`task`、`acceptance`、
`backlog` 和 `handoff` 共同承担跨会话恢复和人机协作的上下文。

当 artifact 位于本地 docs 树下时，Sky Flow 必须尊重本地 docs 入口规则。如果 `${SKY_FLOW_ROOT}/AGENTS.md`
或 `${SKY_FLOW_ROOT}/CLAUDE.md` 声明某些目录纳入 Table Of Content，创建、删除或移动这些目录下的 artifact
时同步维护 TOC；如果两者是同一文件或软链接，维护一次即可。未纳入 TOC 的过程目录不强行添加。

### 依赖显式化

`spec`、`issue`、`plan`、`task`、`acceptance`、`backlog`、`handoff` 的状态和依赖关系通过
frontmatter 表达。

父子依赖需要双向绑定，但只绑定相邻层级；跨层级信息通过相邻层级逐级追踪，避免一个文档承担过多关系。
