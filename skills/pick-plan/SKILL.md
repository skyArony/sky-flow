---
name: pick-plan
description: 'Select the next Sky Flow plan worth continuing from unfinished plan artifacts and recently completed plans, then produce a prioritized plan list, one recommendation, concise recovery context, and one copyable Codex continuation prompt. Use when the user explicitly asks for pick-plan, choosing the next plan, recommending what Sky Flow plan to continue, resuming work from plan artifacts, or generating a continuation prompt from a plan.'
---

# pick-plan

`pick-plan` 从现有 Sky Flow `plan` artifact 和 standalone task 清单中挑选下一步最值得继续推进的工作，并输出一个可直接用于新会话续跑的完整提示词代码块。它只做只读选择和上下文整理，不修改 plan、task、handoff 或代码。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取 `${SKY_FLOW_ROOT}/plan/` 下未完成的 Sky Flow plan，`${SKY_FLOW_ROOT}/plan/done/` 下 `completed_at` 或文件 mtime 在 24 小时以内的 completed plan 作为后续承接背景，以及 `${SKY_FLOW_ROOT}/tasks/standalone/` 下 active standalone task。
3. 优先运行只读 inventory 脚本生成候选清单：

```bash
node .agents/skills/sky-flow/skills/pick-plan/scripts/collect_plans.ts --root .
```

如果项目没有 `.agents` symlink，使用 `.claude/skills/sky-flow/skills/pick-plan/scripts/collect_plans.ts`。

4. 对候选按继续推进价值排序；脚本只提供事实清单，最终排序由 Agent 结合 plan / task 语义判断。
5. 推荐一个 plan 或 standalone task，并输出背景、目标、进度、下一步、限制和验证方式。
6. 输出一个可复制代码块，代码块内放完整续跑提示词，不带 `/goal` 前缀，并默认包含按需使用子代理的授权边界。

## Candidate Rules

纳入候选：

- `artifact_type: plan` 且 `status` 不是 `completed` / `abandoned`。
- `status: completed` 且位于 `plan/done/`，并且 `completed_at` 或文件 mtime 距今不超过 24 小时，用来发现刚完成后可承接的后续 plan；这不是自动捞回。
- `artifact_type: task`、`task_role: standalone` 且 `status` 不是 `completed` / `abandoned`。
- `status: completed` 且位于 `tasks/standalone/done/`，并且 `completed_at` 或文件 mtime 距今不超过 24 小时，用来发现刚完成后可承接的后续 task / plan；这不是 task 捞回。

单独列出但默认不推荐：

- 没有 Sky Flow frontmatter 的 legacy plan 文档：可以作为背景，但不能直接生成可靠续跑提示。
- 缺少 `goal` 的 plan：除非用户明确指定，否则先建议回到 `to-plan` 补全目标契约。
- `abandoned` plan：只有用户明确要求恢复时才考虑，并先检查 backlog / 人类协商依据。

## Ranking Heuristics

排序以“下一轮继续推进价值”为准，不以文件编号或最近修改时间机械决定。

优先级通常是：

1. `in_progress` 且 `Recovery / Next action` 清楚、没有 blocking blocker。
2. `not_started` 且 `goal`、scope、task handoff 或 tasks 已经足够明确。
3. `draft` 但只差少量澄清即可进入 `to-task` / `to-implement`。
4. 24 小时内刚完成的 plan，如果它明显指向下一阶段、验收、handoff 或后续 plan。

降低优先级：

- `Recovery` 缺失且只能靠聊天历史恢复。
- `goal` 太泛，无法作为 Codex 续跑契约。
- 当前 blocker 需要人类决策、外部系统权限或生产操作。
- plan 依赖的 spec / issue / task 状态明显漂移，继续前应先 `validate-flow` 或回到上游 skill。
- completed plan / standalone task 只能作为后续新 plan / 新 task 的背景；`pick-plan` 不执行捞回，也不把 plan-scoped task 当候选。

## Output Contract

输出必须包含：

- 候选 plan list 和 standalone task list：按推荐优先级排列，说明状态、路径、推荐理由和风险。
- 推荐 plan 或 standalone task：只推荐一个，并说明为什么它比其他候选更值得继续。
- 简明上下文：背景、目标、进度、下一步、限制、验证方式、何时停下问人。
- 一个完整的可复制代码块。

代码块内必须包含目标契约和具体执行上下文，不带 `/goal` 前缀。排版使用清晰分段，每段只保留必要事实，避免长篇叙述：

```text
目标:
- <由推荐 plan frontmatter goal 生成的目标契约，说明完成后应当为真的状态>

依据:
- 工作区: <absolute or repo path>
- Plan: <plan path>
- 当前状态: <status and recovery summary>
- 下一步: <one concrete next action>

完成标准:
- <auditable done condition>
- <specific evidence that proves completion>

约束与边界:
- <scope, no-touch, env, approval or blocker boundaries>
- 不扩大 plan 目标，不修改未授权 artifact 或代码区域。

子代理:
- 默认授权 Codex 按需使用子代理来并行探索、实现、测试或复核；每个子代理必须带明确任务、路径/边界和预期输出，继承当前 sandbox/approval 策略，并遵守同一 scope/no-touch。主代理等待结果后统一汇总和决策。

迭代策略:
- <how Codex should choose the next best action between attempts>
- <what evidence to record after each meaningful attempt>

验证方式:
- <from plan verification intent or local project rules>

停下问人:
- <blocking ambiguity / failed validation / scope change conditions>
```

代码块必须是一个完整提示词，用户复制后即可在新会话中使用。

## Continuation Prompt Rules

- 优先使用 `plan.frontmatter.goal` 原文；只做必要的代词、路径或状态补充，不改变目标范围。
- 如果 goal 缺失或明显不足，不要假装已准备好；输出“需要先回到 `to-plan` 补 goal”，并可给一个临时草案供人类确认。
- 续跑提示应包含期望终态、验证证据、约束、边界、迭代策略和阻塞停止条件；这些字段对应 Codex Goals 的可审计完成契约，不要删减成只有任务说明。
- 默认加入“子代理”段，授权按需派发子代理。该授权是允许而非强制：只有在并行探索、复核、测试或拆分实现能提高确定性时才使用；如果推荐 plan 明确禁止委派或当前环境没有子代理能力，写明“不授权/不可用”及原因。
- 子代理授权不得扩大权限或 scope：子代理必须继承当前 sandbox/approval 策略，遵守相同 no-touch 和停下问人条件，不能自行请求生产操作、破坏性操作或计划外文件修改。
- Codex Goals 官方参考保留为设计依据：https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- Codex Subagents 官方参考保留为授权和继承策略依据：https://developers.openai.com/codex/subagents

## Boundaries

- 不修改任何 artifact；如果发现状态漂移，只报告并建议运行 `validate-flow`。
- 不替代 `to-implement` 执行 plan，不派发 task，不更新 runtime plan。
- 不替代 `to-handoff`；如果用户要求跨会话交接文档，转入 `to-handoff`。
- 不把 legacy plan 文档强行当成 Sky Flow plan；缺 frontmatter 时先说明限制。
