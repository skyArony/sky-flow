---
name: validate-flow
description: 'Validate Sky Flow artifacts with a deterministic TypeScript precheck and an LLM semantic pass. Use whenever creating or modifying Sky Flow spec, issue, plan, task, acceptance, backlog, or handoff artifacts, or before committing workflow artifact changes.'
---

# validate-flow

`validate-flow` 用于检查 Sky Flow artifact 是否符合规范。

它不是普通完成前自检，也不是 LLM 逐项读文档的 review。Sky Flow artifact 的结构、状态、依赖、验收证据、backlog / handoff 归宿和 fan-in 后状态漂移都归它负责；`to-review` 只检查代码风险，`to-consolidation` 只处理代码 / 产物 diff 收敛。

创建或修改 Sky Flow artifact 后必须运行；执行 plan 的主会话在多 Agent fan-in、阶段状态更新、handoff / acceptance / commit 前负责运行它并处理报告，不把 artifact 状态校验下放给普通 worker。

校验采用两段式：

1. 脚本预检：确定性检查 frontmatter、枚举、命名、artifact root、相邻绑定、DAG 和依赖一致性。
2. LLM 收口：基于脚本结构化报告判断语义是否合理、上下文是否充分、状态是否漂移、争议项是否要问人。

## 脚本预检

运行：

```bash
node .agents/skills/sky-flow/scripts/validate_flow.ts [paths...]
```

不传路径时，脚本扫描 `${SKY_FLOW_ROOT}` 下带 Sky Flow frontmatter 的 Markdown artifact。传入文件或目录时，只检查指定范围。

脚本输出 JSON，包含：

- `summary`
- `checked_artifacts`
- `graph`
- `errors`
- `warnings`
- `llm_review_hints`

有 `errors` 时退出码为 1；只有 warnings 时退出码为 0。

脚本预检覆盖这些机器可判断的状态 / 关系问题：

- `plan.acceptance` 与 plan 来源 `acceptance` 是否缺失、类型错误或互相指错。
- plan 来源 `acceptance` 是否反向列入对应 `plan.acceptance`；即使 `plan.acceptance` 为空也必须报错，避免验收状态漂移。
- `plan_role` / `planning_depth` 是否使用合法枚举。
- `completed` plan 是否位于 `plan/done/`，以及非 `completed` plan 是否误放到 `plan/done/`。
- `completed` issue 是否位于 `issue/fixed/`，以及非 `completed` issue 是否误放到 `issue/fixed/`。
- 父 Plan 的 `child_plans` 与子 Plan 的 `parent_plan` 是否缺失、类型错误或互相指错。
- 父 Plan 是否直接绑定 task，或子 Plan 是否没有复用父 Plan 的三位数字前缀。
- 后序子 Plan 是否在前序子 Plan 未完成时已经进入 `in_progress` / `completed`。
- task 是否使用合法 `task_role`，plan-scoped task 是否固定于 `tasks/<plan-id>/` 且不进入 `done/` 子目录，standalone task 是否位于 `tasks/standalone/` 或完成后的 `tasks/standalone/done/`。
- standalone task 是否显式设置 `task_role: standalone` 和 `goal`，以及是否错误声明本地 `depends_on` / `depended_by` / `parallel_with`。
- `backlog` / `handoff` 的 artifact 来源是否能找到。
- `completed` plan 是否仍有未完成 task，或缺少 `completed_at`。
- `completed_at` 是否和 plan 的 `completed` 状态不一致。
- `not_started` plan 下是否已有 `in_progress` / `completed` task。
- task 是否在依赖 task 未完成时已经进入 `in_progress` / `completed`。
- `abandoned` artifact 是否有对应 backlog 或人工协商线索。

## LLM 收口

脚本通过后，LLM 只处理脚本不能可靠判断的语义问题：

- dependency / parallel 关系是否符合任务语义。
- `plan.goal` 是否足以作为 Codex 续跑契约。
- fan-in 后 plan / task / acceptance 状态是否与实际阶段产物、验证证据和剩余工作一致。
- task 是否都能由 Agent 独立完成；如果 task 的核心完成条件是人工操作、真实设备 / 账号、外部环境、审批或人工体验判断，应建议转入 acceptance。
- standalone task 是否仍然只是单一可恢复任务；如果出现多个 peer task、milestone、长期验收 gate 或 plan 级恢复需求，应建议升级为 plan。
- 捞回后的 plan / issue 是否已经移回 active 目录、改掉 `completed` 状态，并写清 `Reopen Evidence` / `Reopen Reason`。
- completed plan 若已清空 `tasks` 或声称 summary-only 归档，归档摘要是否保留必要事实、关键决策、踩坑、证据入口和 follow-up。
- `acceptance` 是否说清来源、轮次、验证证据和未提及项处理。
- `backlog` 是否讲清主题、阻塞原因、依赖条件和推荐恢复时机。
- `handoff` 是否保留可执行恢复状态，而不是聊天摘要。
- `abandoned` 是否确实有人类协商依据。
- warning 是否需要升级为阻塞或回到用户确认。

LLM 不应重新做脚本已经确定的机械校验。

## 校验边界

- 只读检查，不自动修复。
- `SKY_FLOW_ROOT` / `SKY_FLOW_LANG` 只来自 runtime env；未设置时使用默认值。
- 外部 task 依赖缺失先 warning，不直接阻塞。
- `html_interactive` 是保留枚举，默认给 warning。

## 推荐关系

`validate-flow` 只报告 artifact 契约和状态一致性问题；修复或后续动作按问题归口推荐，不强制跳转：

- `spec` 语义、requirements、acceptance scenarios 或设计边界不一致：推荐 `to-spec`。
- `plan` goal、scope、milestone、progress、parent / child plan 或 recovery 不一致：推荐 `to-plan`。
- `task` DAG、depends_on / depended_by / parallel_with、write scope 或 verification intent 不一致：推荐 `to-task`。
- completed plan 的 task 压缩、归档摘要或 retention 策略不清：推荐 `to-archive`。
- `acceptance` 来源、轮次、证据或未提及项处理不清：推荐 `to-acceptance` 或 `to-next-acceptance`。
- `backlog` 来源、阻塞原因、依赖或恢复时机不清：推荐 `to-backlog`。
- `handoff` 恢复状态不足：推荐 `to-handoff`。
- 脚本报告显示 artifact 结构无问题，但实现风险、测试缺口或交付质量仍不确定：推荐 `to-review`，不要让 `validate-flow` 代替 review。

## 依赖

依赖和安装方式见 `../../references/dependencies.md`。脚本默认使用 Node.js 直接运行 TypeScript。
