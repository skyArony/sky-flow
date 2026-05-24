---
name: pick-plan
description: 'Select the next Sky Flow plan worth continuing from unfinished plan artifacts and recently completed plans, then produce a prioritized plan list, one recommendation, concise recovery context, and two copyable prompts for Codex /goal continuation. Use when the user explicitly asks for pick-plan, choosing the next plan, recommending what Sky Flow plan to continue, resuming work from plan artifacts, or generating a /goal prompt from a plan.'
---

# pick-plan

`pick-plan` 从现有 Sky Flow `plan` artifact 中挑选下一步最值得继续推进的 plan，并输出可直接用于新会话续跑的提示词。它只做只读选择和上下文整理，不修改 plan、task、handoff 或代码。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取 `${SKY_FLOW_ROOT}/plan/` 下未完成的 Sky Flow plan，以及 `${SKY_FLOW_ROOT}/plan/done/` 下 `completed_at` 或文件 mtime 在 24 小时以内的 completed plan。
3. 优先运行只读 inventory 脚本生成候选清单：

```bash
node .agents/skills/sky-flow/skills/pick-plan/scripts/collect_plans.ts --root .
```

如果项目没有 `.agents` symlink，使用 `.claude/skills/sky-flow/skills/pick-plan/scripts/collect_plans.ts`。

4. 对候选按继续推进价值排序；脚本只提供事实清单，最终排序由 Agent 结合 plan 语义判断。
5. 推荐一个 plan，并输出背景、目标、进度、下一步、限制和验证方式。
6. 输出两个分开的可复制代码块：第一个只包含 `/goal ...`，第二个包含具体上下文和执行细节。

## Candidate Rules

纳入候选：

- `artifact_type: plan` 且 `status` 不是 `completed` / `abandoned`。
- `status: completed` 且位于 `plan/done/`，并且 `completed_at` 或文件 mtime 距今不超过 24 小时，用来发现刚完成后可承接的后续 plan。

单独列出但默认不推荐：

- 没有 Sky Flow frontmatter 的 legacy plan 文档：可以作为背景，但不能直接生成可靠 `/goal`。
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
- `goal` 太泛，无法作为 Codex `/goal` 契约。
- 当前 blocker 需要人类决策、外部系统权限或生产操作。
- plan 依赖的 spec / issue / task 状态明显漂移，继续前应先 `validate-flow` 或回到上游 skill。

## Output Contract

输出必须包含：

- 候选 plan list：按推荐优先级排列，说明状态、路径、推荐理由和风险。
- 推荐 plan：只推荐一个，并说明为什么它比其他候选更值得继续。
- 简明上下文：背景、目标、进度、下一步、限制、验证方式、何时停下问人。
- 两个分开的代码块。

第一个代码块只放 `/goal`，不要混入上下文：

```text
/goal <由推荐 plan frontmatter goal 生成的目标契约>
```

第二个代码块放具体执行上下文：

```text
工作区: <absolute or repo path>
Plan: <plan path>
当前状态: <status and recovery summary>
下一步: <one concrete next action>
限制: <scope, no-touch, env, approval or blocker boundaries>
验证方式: <from plan verification intent or local project rules>
停下问人: <blocking ambiguity / failed validation / scope change conditions>
```

两个代码块必须分开，因为 `/goal` 和细节混在同一个复制块时，Codex 可能无法稳定识别 `/goal`。

## Goal Prompt Rules

- 优先使用 `plan.frontmatter.goal` 原文；只做必要的代词、路径或状态补充，不改变目标范围。
- 如果 goal 缺失或明显不足，不要假装已准备好；输出“需要先回到 `to-plan` 补 goal”，并可给一个临时草案供人类确认。
- `/goal` 内容应包含期望终态、验证证据、约束、边界、迭代策略和阻塞停止条件。
- Codex Goals 官方参考保留为设计依据：https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex

## Boundaries

- 不修改任何 artifact；如果发现状态漂移，只报告并建议运行 `validate-flow`。
- 不替代 `to-implement` 执行 plan，不派发 task，不更新 runtime plan。
- 不替代 `to-handoff`；如果用户要求跨会话交接文档，转入 `to-handoff`。
- 不把 legacy plan 文档强行当成 Sky Flow plan；缺 frontmatter 时先说明限制。
