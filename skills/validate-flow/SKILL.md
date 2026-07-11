---
name: validate-flow
description: 'Validate the simplified Sky Flow artifact model with a deterministic TypeScript precheck and a focused semantic pass. Use after creating or modifying spec, issue, acceptance, backlog, or handoff artifacts, and before committing those artifact changes.'
---

# validate-flow

`validate-flow` 检查 Sky Flow artifact 的最小结构、来源和恢复语义。它保护长期状态，但不把 runtime 调度重新固化成文件约束。

当前 file-backed artifact 只有：`spec`、`issue`、`acceptance`、`backlog`、`handoff`。执行拆解、owner、依赖、并行与 fan-in 批次属于 runtime，不进入 validator。

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
- spec 是否错误使用数字编号前缀。
- completed issue 是否位于 `issue/fixed/`，以及未完成 issue 是否误放 fixed 目录。
- acceptance type 是否有效。
- acceptance / backlog / handoff 的单向 source 是否可解析；部分校验范围缺少来源时只 warning。
- abandoned artifact 是否有 linked backlog 或需要补充人类协商依据。
- ready / active / completed spec 是否缺少 `Progress` 快照。
- retired artifact type 或拓扑字段是否仍残留。

旧执行拓扑不会兼容通过：legacy artifact 必须把长期设计、完成结果、下一步、blocker 和证据迁移到 spec；真实人类 gate、长期延期和易失交接分别使用 acceptance、backlog、handoff。

## Semantic Pass

LLM 只判断：

- spec Intent、Scope、Requirements、Decisions、Acceptance Scenarios、Verification Intent 和 Implementation Readiness 是否一致。
- spec `Progress` 是否是紧凑语义恢复快照，包含 Checkpoint、Completed、Next、Blockers、Last verified；是否只保存结果、决策、证据、blocker、风险和目标级恢复入口，而没有代码行号、逐文件 diff、完整命令 / tool call、子代理过程、执行流水或文件化工作图。
- Progress 的必要定位是否优先使用稳定模块、类、函数、公开接口或测试套件名称，而不是易漂移的具体代码行。
- no-touch、人类 gate、不可逆操作和独立 review 等真实 Execution Constraints 是否清楚，且没有预设 runtime owner。
- issue 是否保存了证据和有价值的下一决策，而不是实施脚本。
- acceptance 是否确实需要人类参与，证据和反馈轮次是否清楚。
- backlog 是否真的退出当前执行队列，阻塞、依赖和恢复条件是否可判定。
- handoff 是否只保存易失接力状态，没有复制 spec Progress。
- warning 是否需要升级为 blocker 或回到用户确认。

不要检查或要求 runtime worker 数量、依赖边、并行 lane、owner、微步骤或调度历史。

## Validation Timing

必须运行：

- 创建或修改 Sky Flow artifact 后。
- spec status、Implementation Readiness、Progress checkpoint / blocker / completion 发生稳定变化后。
- handoff / acceptance / backlog 交付前。
- staged diff 包含 workflow artifact 且准备 commit 前。

短暂 runtime checklist 更新、子代理派发和微步骤变化不需要 artifact 校验。

## Boundaries

- 只读检查，不自动修复。
- 不做代码 review；实现风险交给 `to-review`。
- 不收敛 pending diff；交给 `to-consolidation`。
- 不选择测试策略；交给 `to-test`。
- 不用另一个严格 schema 取代已经删除的执行拓扑。
- `html_interactive` 仍是保留枚举，默认 warning。

## 推荐关系

- spec 设计、readiness 或 Progress 不一致：`to-spec`。
- acceptance 来源、证据或反馈轮次不清：`to-acceptance` / `to-next-acceptance`。
- backlog 阻塞或恢复条件不清：`to-backlog`。
- handoff 缺少可执行接力状态：`to-handoff`。
- 结构通过但实现风险、测试缺口或交付质量仍不确定：`to-review` / `to-test`。

## Dependencies

依赖和安装方式见 `../../references/dependencies.md`。validator 默认使用 Node.js 直接运行 TypeScript。
