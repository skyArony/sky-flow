---
name: validate-flow
description: 'Validate the simplified Sky Flow artifact model with a deterministic TypeScript precheck and a focused semantic pass. Use after durable artifact changes, at thin-plan structure or recovery boundaries, and before committing artifact changes.'
---

# validate-flow

`validate-flow` 检查 Sky Flow artifact 的最小结构、来源和恢复语义。它保护长期状态，但不把 runtime 调度重新固化成文件约束。

当前 file-backed artifact 只有：`spec`、`plan`、`issue`、`acceptance`、`backlog`、`handoff`。plan 是复杂长周期实现的可选 thin working set；task / step、owner、依赖、并行与 fan-in 批次仍属于退休拓扑或 runtime，不进入有效 artifact。

## Quick Path

1. 确定 `SKY_FLOW_ROOT` 和 `SKY_FLOW_LANG`；未设置时默认 `docs` 和 `简体中文`。
2. 运行确定性预检：

```bash
node .agents/skills/sky-flow/scripts/validate_flow.ts [paths...]
```

仓库内开发时也可以运行：

```bash
node scripts/validate_flow.ts [paths...]
```

3. 先处理 `errors`，再判断 warnings 是否需要修复或人类确认。
4. 只对脚本不能判断的内容做语义收口；不要重新建立执行图。

不传路径时扫描 `${SKY_FLOW_ROOT}`；传入文件或目录时只检查显式范围。输出 JSON 包含：

- `summary`
- `checked_artifacts`
- `graph.source_links`
- `errors`
- `warnings`
- `llm_review_hints`

## Deterministic Checks

脚本只检查机器可以可靠判断的内容：

- frontmatter 是否存在且可解析。
- `id`、`artifact_type`、`status` 和各 artifact 最小必填字段。
- 文件 stem 是否等于 `id`，artifact 是否位于 `${SKY_FLOW_ROOT}`。
- spec 或 plan 是否错误使用旧数字编号前缀，plan 是否误放入已退休的 `plan/done`。
- completed issue 是否位于 `issue/fixed/`，以及未完成 issue 是否误放 fixed 目录。
- acceptance type 是否有效。
- plan 是否没有 pre-readiness `draft` 阶段，并严格 source 到 ready、unfinished spec；默认全量扫描中的孤儿 plan 直接失败，显式局部范围缺少来源时才 warning。in-progress plan 的 source spec 也必须已进入 in_progress。acceptance / backlog / handoff 继续使用各自单向 source，且 plan 不得成为其权威来源。
- 非 plan 的 abandoned artifact 是否有 linked backlog 或需要补充人类协商依据；abandoned plan 只丢弃 working set，不代表 source work 离队。
- ready / active / completed spec，以及 active plan 是否缺少对应 `Progress` 快照。
- 同一 spec 是否出现多个 active plan；这是 warning，由语义检查判断保留哪一个或合并。
- retired task / step artifact、legacy plan 字段、明确的 topology / append-log body section 或其他拓扑字段是否仍残留；不把普通 `Recovery` / `Milestones` heading 当成确定性错误。

旧执行拓扑不会兼容通过：legacy artifact 必须把长期设计、完成结果、目标级下一步、blocker 和证据迁移到 spec；仍有恢复价值的当前实施 working set 可以改写成 thin plan；真实人类 gate、长期延期和易失交接分别使用 acceptance、backlog、handoff。

## Semantic Pass

LLM 只判断：

- spec Intent、Scope、Requirements、Decisions、Acceptance Scenarios、Verification Intent 和 Implementation Readiness 是否一致。
- spec `Progress` 是否是紧凑语义恢复快照，包含 Checkpoint、Completed、Next、Blockers、Last verified；是否只保存结果、决策、证据、blocker、风险和目标级恢复入口，而没有代码行号、逐文件 diff、完整命令 / tool call、子代理过程、执行流水或文件化工作图。
- plan 是否只在跨会话 / compaction、昂贵代码事实、共享验证 slice、影响后续实现的局部 decision 或具体 checkpoint 恢复确有价值时存在；简单或低恢复成本工作是否错误创建 plan。
- plan 是否只保存当前 slice、code context、approach、局部可逆 decisions、Done / Active / Next / Blockers 和复用验证入口；是否与 spec 重复、越权为规范性决策或泄漏 task graph / owner / dependency / lane / Agent 流水。
- plan 中会改变 material scope、stable constraint、no-touch、external behavior、contract、data semantics、authority、acceptance 或长期架构的事实 / 决定是否已提升到 spec；plan 与 spec 冲突时是否以 spec 为准。
- plan Progress 是否是可覆盖的恢复快照，恢复后是否定点复核易漂移代码事实；slice-local blocker 与 spec goal-level / external / authority blocker 是否正确分层；完成时是否先提升 durable semantics，再压缩或删除，而不是进入 `plan/done`。
- Progress 的必要定位是否优先使用稳定模块、类、函数、公开接口或测试套件名称，而不是易漂移的具体代码行。
- no-touch、人类 gate、不可逆操作和独立 review 等真实 Execution Constraints 是否清楚，且没有预设 runtime owner。
- issue 是否保存了证据和有价值的下一决策，而不是实施脚本。
- acceptance 是否确实需要人类参与，证据和反馈轮次是否清楚。
- backlog 是否真的退出当前执行队列，阻塞、依赖和恢复条件是否可判定。
- handoff 是否只保存易失接力状态，没有复制 spec Progress。
- warning 是否需要升级为 blocker 或回到用户确认。

不要检查或要求 runtime worker 数量、依赖边、并行 lane、owner、微步骤或调度历史。

## Validation Timing

durable artifact 必须在创建 / 修改后运行；thin plan 使用分层时机：

- spec status、Implementation Readiness、Progress checkpoint / blocker / completion 发生稳定变化后。
- plan create、source / status 变化、decision promotion、closure，以及即将作为恢复 / handoff / commit 输入时，先运行确定性预检；有 warning 或规范性边界判断时完成 focused semantic pass。
- handoff / acceptance / backlog 交付前。
- staged diff 包含 workflow artifact 且准备 commit 前。

plan 只改 body working-set snapshot 时可批量到下一个恢复 / 提交边界，不要求每次覆盖都触发完整 validator / model pass。短暂 runtime checklist 更新、子代理派发和微步骤变化不需要 artifact 校验；也不应只为了触发 validator 而物化成 plan。

## Boundaries

- 只读检查，不自动修复。
- 不做代码 review；实现风险交给 `to-review`。
- 不收敛 pending diff；交给 `to-consolidation`。
- 不选择或执行普通测试；由 native runtime 根据风险完成。
- 不用另一个严格 schema 取代已经删除的执行拓扑。
- `html_interactive` 仍是保留枚举，默认 warning。

## 推荐关系

- spec 设计、readiness 或 Progress 不一致：`to-spec`。
- plan 创建边界、恢复内容、decision promotion 或关闭状态不一致：回 `to-implement`；若已触碰 durable semantics，再回 `to-spec`。
- acceptance 来源、证据或反馈轮次不清：`to-acceptance` / `to-next-acceptance`。
- backlog 阻塞或恢复条件不清：`to-backlog`。
- handoff 缺少可执行接力状态：`to-handoff`。
- 结构通过但实现风险、测试缺口或交付质量仍不确定：回到 native runtime 定向验证；用户明确要求专项 review 时使用 `to-review`。

## Dependencies

依赖和安装方式见 `../../references/dependencies.md`。validator 默认使用 Node.js 直接运行 TypeScript。
