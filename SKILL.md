---
name: sky-flow
description: 'Sky Flow workflow suite for artifact-based collaboration across spec, issue, plan, task execution, testing, acceptance, backlog, handoff, knowledge notes, and completed-plan archive compression. Use when the user mentions Sky Flow, a to-* child workflow, pick-plan, validate-flow, workflow artifacts, skill migration, or asks to create, validate, progress, resume, execute a Sky Flow plan/task, test, accept, backlog, hand off, archive, review, consolidate, commit a file-backed workflow, or capture reusable technical knowledge.'
---

# Sky Flow

Sky Flow 是通用工作流 Skill 套件，覆盖 `spec`、`issue`、`plan`、`task`、`acceptance`、`backlog`、`handoff` 等 artifact 的创建、推进、校验、归档压缩与衔接，也提供通用技术知识沉淀入口。它用来把设计澄清、问题记录、实施编排、并行 fan-in、人类验收、跨会话交接和可复用开发知识沉淀成可恢复、可检索的状态。

它不是所有任务的默认入口，也不是单个巨型流程。简单任务直接使用 runtime；复杂或需要留痕的任务才进入 Sky Flow。入口 Skill 只负责判断是否进入套件、选择子能力、维护 artifact 纪律并触发校验；artifact 路径和输出语言可通过 `SKY_FLOW_*` 环境变量覆盖，项目提交规范和验证命令由本地规则承担。

## 使用方式

按下面顺序执行；这是入口 Skill 的必经短路径。

1. 先判断是否进入 Sky Flow：
   - 用户显式提到 Sky Flow、子能力名或 workflow artifact：进入。
   - 任务需要跨会话留痕、计划编排、验收、handoff、backlog 回收或通用技术知识沉淀：进入。
   - 只是简单代码修改、查询、解释或一次性命令，且不涉及 Sky Flow artifact：直接使用 runtime。
2. 一旦进入且需要读取、创建或修改 artifact，先确定 runtime 配置：
   - `SKY_FLOW_ROOT` 来自 runtime env；不存在则默认 `docs`。
   - `SKY_FLOW_LANG` 来自 runtime env；不存在则跟随用户语言，脚本默认 `简体中文`。
   - 不读取额外项目配置文件。
   - 默认值满足项目需求时不需要配置；如需覆盖，在项目 `.codex/config.toml` 的 `[shell_environment_policy.set]` 中设置 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`。
3. 选择子能力：
   - 用户显式点名子能力时，优先使用该能力。
   - 自动场景直接触发：debug、infra 查询 / 操作、BDD 回归固化、testing、review、commit、consolidation、acceptance、通用技术知识沉淀、completed plan 归档压缩、validate-flow、Sky Flow plan / task execution。
   - 没有明确子能力或需要完整清单时，读取 `references/routing.md`，它是子能力和触发规则的完整来源。
   - 执行已落地的子能力细节时，读取对应 `SKILL.md`；顶层子能力通常在 `skills/<name>/SKILL.md`，嵌套子能力可位于所属能力目录下。
   - 标注为 `project-provided adapter` 或项目级实现的子能力（例如 `to-infra`），必须优先使用当前会话 Skills 列表给出的路径，或项目 `.claude/skills/<name>/SKILL.md`；不要按 Sky Flow core 的 `skills/<name>/SKILL.md` 拼路径。
4. 维护 artifact 纪律：
   - 重要状态必须落到 artifact，不只留在聊天里。
   - 在 `SKY_FLOW_ROOT` 下创建、删除或移动 docs artifact 时，如果 `${SKY_FLOW_ROOT}/AGENTS.md` 或 `${SKY_FLOW_ROOT}/CLAUDE.md` 定义了 Table Of Content 维护规则，必须按本地规则同步 TOC。
   - Codex 执行 Sky Flow plan 时，主会话必须用内置 `update_plan` tool 维护 runtime plan；并行组用 `[并行 n]` 标记，主会话负责 fan-in。
   - 执行 Sky Flow plan 时，代码改动和 spec / plan / task / acceptance 等文档更新默认并行调度；可由多个子代理并行，也可由主会话维护文档、子代理写代码，前提是写集 single-writer 且最终由主会话 fan-in 对齐。
   - 创建或修改 Sky Flow artifact 后，必须触发 `validate-flow`，优先运行 `node .agents/skills/sky-flow/scripts/validate_flow.ts` 生成结构化报告。
   - 多 Agent fan-in、阶段状态更新、handoff / acceptance / commit 前，主会话负责运行 `validate-flow` 检查 artifact/status 一致性。

## 职责边界

- `validate-flow`：只检查 Sky Flow artifact 契约和状态一致性，包括 frontmatter、命名、DAG、相邻绑定、状态漂移、验收证据、backlog / handoff 归宿。它不做代码 review，也不收敛 pending diff。
- `to-test`：只判断测试策略、行为场景、测试 ROI、stable seam、Red / Green / Refactor 和替代验证。它不替代 debug 诊断或真实事故回归固化。
- `to-review`：只检查实现风险、行为回归、设计对齐、测试缺口和安全 / 可靠性问题。它可以读取 artifact 作为背景，但不修 artifact 状态，也不整理 diff。
- `to-consolidation`：只收敛目标 diff 中的补丁式实现、临时代码、重复逻辑、旧注释、debug 残留和 fan-in 半成品。它不判断 artifact/status 是否正确，也不替代 review。
- `to-knowledge`：只沉淀业务无关、项目无关、可跨项目复用的通用技术知识。它不替代 spec / issue / plan / backlog / handoff。
- `to-implement`：执行和维护已准备好的 Sky Flow plan / task DAG，协调主代理、子代理、runtime plan、验证、fan-in、动态 task 调整和状态回写。它不重做设计，也不替代 review / consolidation / acceptance / validate-flow。
- `to-archive`：只压缩已完成 plan 的执行期记录，把长期事实、关键决策和证据入口写回 completed plan；它不新增 archive artifact，也不替代 backlog / handoff / acceptance。

这些能力可以按阶段串联，但不能互相代偿：artifact/status 问题回 `validate-flow`，测试策略和测试 ROI 回 `to-test`，代码风险回 `to-review`，diff 熵值回 `to-consolidation`，人类验收回 `to-acceptance`。

子能力之间采用“推荐而非强制”的关系。某个子能力遇到非本领域流程时，应说明推荐 skill、原因、可传递输入和是否阻塞；除非触发表明确要求自动触发，推荐本身不等于强制切换。完整推荐关系以 `${SKY_FLOW_ROOT}/spec/tooling/sky-flow.md` 为设计真相源。

## 快速路由

| 场景                                 | 子能力                                             |
| ------------------------------------ | -------------------------------------------------- |
| 长期设计对齐、澄清或规格沉淀         | `to-spec`                                          |
| 问题 / 线索记录，暂不修复            | `to-issue`                                         |
| 排障、复现、root cause               | `to-debug` / `to-bdd-regression`                  |
| 基础设施查询 / 操作、日志 / 数据源取证 | `to-infra`（project-provided adapter）             |
| 测试策略、测试 ROI、BDD/TDD、替代验证 | `to-test`                                         |
| 通用技术知识、踩坑、库 / 工具选型笔记 | `to-knowledge`                                    |
| 实施计划、任务拆分、执行编排         | `to-plan` / `to-task` / `to-implement`             |
| 完成后归档压缩                     | `to-archive`                                       |
| 下一步 plan 选择和续跑提示           | `pick-plan`                                        |
| review、循环修复复审、Agent 决策复盘 | `to-review` / `to-review-loop` / `to-agent-review` |
| 人类验收、下一轮验收反馈             | `to-acceptance` / `to-next-acceptance`             |
| 阻塞回收或跨会话恢复                 | `to-backlog` / `to-handoff`                        |
| 提交、阶段收敛、artifact 校验        | `to-commit` / `to-consolidation` / `validate-flow` |

完整触发表和每个子能力的触发倾向只维护在 `references/routing.md`。

## Artifact 结构速记

命名：

- `spec`：文件名就是唯一 ID，不使用编号前缀。
- `plan`：standalone / parent 使用 `001-xxx-xxx.md`；child 使用 `001a-xxx-xxx.md`、`001b-xxx-xxx.md`，文件 stem 等于 `id`；未完成 plan 在 `plan/`，已完成 plan 在 `plan/done/`。
- `task`：`01-xxx-xxx.md`，必须位于 `tasks/<plan-id>/` 下，文件 stem 等于 `id`；完成 plan 经 `to-archive` 压缩后，默认可清空 `plan.tasks` 并删除该 plan 的 task 目录。
- 其他 artifact 要求文件 stem 与 `id` 一致。

关系：

- `spec.plans <-> plan.spec`
- `issue.plans <-> plan.issues`
- `plan.tasks <-> task.plan`，仅表示当前保留的展开 task DAG；completed plan 若已压缩为 summary-only，可为空。
- `plan.child_plans <-> plan.parent_plan`，仅用于超级巨大任务的父子 Plan；父 Plan 不直接绑定 task。
- `plan.acceptance <-> acceptance.plan`，仅当 acceptance 来源是 plan。
- 父子 artifact 只绑定相邻层级；`handoff` 和 `backlog` 可以引用来源 artifact，但不替代来源 artifact 的状态。

## Reference 加载

- `references/routing.md`：完整子能力清单、触发表和 runtime plan 规则；路由不确定或维护触发规则时读取。
- `references/dependencies.md`：脚本运行、setup 和外部 Skill 依赖；只有安装、运行环境或依赖问题时读取。
- `skills/<name>/SKILL.md` 或嵌套子能力 `SKILL.md`：可独立发现的子能力执行细节；只有进入对应子能力时读取。
- Artifact 结构规则：设计真相源在 `${SKY_FLOW_ROOT}/spec/tooling/sky-flow.md`；机器可执行约束在 `scripts/schema.ts` 和 `scripts/validate_flow.ts`。

`to-knowledge` 默认写入普通 knowledge note，不属于 workflow artifact；只有创建或修改真正的 Sky Flow artifact 时才按 artifact 规则运行 `validate-flow`。

项目提交规范、验证命令和环境限制由项目本地规则决定；Sky Flow core 不写死项目业务规则。
