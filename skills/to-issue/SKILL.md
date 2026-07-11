---
name: to-issue
description: 'Create or update a local Sky Flow issue artifact only when the user explicitly invokes $to-issue for a durable problem, evidence set, opportunity, or unresolved finding that should be understood before runtime work or long-lived spec design.'
---

# to-issue

`to-issue` 把值得长期保留的问题、证据、线索和改进机会写入本地 `${SKY_FLOW_ROOT}/issue/`。它不创建 GitHub Issue 或调用外部 tracker。

issue 是问题记录，不是聊天摘要或实施脚本。后续如果需要长期设计，转 `to-spec`；如果目标清楚且工作很小，可以直接 runtime 执行并把 resolution / evidence 写回 issue。

## Quick Path

1. 确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`。
2. 读取本地 docs 入口中的目录与 TOC 规则。
3. 确认来源：conversation、spec、acceptance、backlog、handoff、review finding、debug evidence 或用户材料。
4. 一个独立 root cause 或决策问题对应一个 issue；不要按执行顺序、模块、owner 或依赖拆成工作图。
5. 未完成 issue 写入 `${SKY_FLOW_ROOT}/issue/<id>.md`；completed issue 移入 `${SKY_FLOW_ROOT}/issue/fixed/<id>.md`。
6. 同一 root cause 的完成结论被新证据推翻时移回 active 目录、改为 `in_progress` 或 `not_started`，并记录 `Reopen Evidence` / `Reopen Reason`。
7. 修改 artifact 后运行 `validate-flow`。

## Issue Shape

issue 是 `problem record`：保留现象、证据、影响、上下文、未知项和下一决策。它可以在问题解决后记录 outcome 与验证证据，但不定义执行 slice、依赖图或分工。

## Metadata

```yaml
---
id: <issue-id>
artifact_type: issue
status: draft
---
```

- `id`：短横线命名，表达主题。
- `status`：draft / not_started / in_progress / completed / abandoned。
- completed issue 必须位于 `issue/fixed/`。
- abandoned 必须有事实或人类依据，并建议关联 backlog。

## Body Template

```markdown
# <Issue Title>

最后更新：<YYYY-MM-DD>

## Summary

<问题、机会或待澄清结论。>

## Source Context

- Source:
- Related artifacts:
- Current state:

## Evidence

- <日志、验证、用户反馈、finding、代码位置或观察结论>

## Impact

- <影响范围、风险和为什么值得处理>

## Recommended Direction

- Next decision:
- Why:
- Constraints:

## Open Questions

- <会影响直接执行或是否需要 spec 的问题；无则省略>

## Resolution

- Outcome:
- Evidence:
- Residual risk:
- Follow-up:
```

只保留有价值 section。active issue 可以省略 Resolution；fixed issue 应压缩为短结论。

## Recording Rules

- 按独立 root cause、证据边界或人类决策拆分，而不是按依赖、执行阶段或技术层拆分。
- `Recommended Direction` 只描述下一决策和稳定约束，不写实施 outcome、verification contract 或 blocker graph。
- 不写 step-by-step implementation、命令清单、代码片段、owner、依赖边或并行分工。
- 目标和边界已经明确的小修直接 runtime；需要长期 contract 的工作先转 `to-spec`。

## Routing

- 目标、scope、行为或契约需要长期对齐：`to-spec`。
- 单一清晰、无需长期设计的修复：直接 runtime。
- 当前问题需要 root cause：`to-debug`。
- 工作长期等待外部条件：`to-backlog`。
- 易失状态需要接力：`to-handoff`。
- 需要人类判断：`to-acceptance`。

## Docs TOC Rules

- 本地 `AGENTS.md` / `CLAUDE.md` 声明 issue 目录纳入 TOC 时，创建、移动或删除后同步维护。
- 两个入口是同一文件或软链接时只维护一次。
- 本地规则明确不纳入索引的目录不要强行添加。
- 只更新当前 artifact 对应条目，不重排无关内容。

## Boundaries

- 不创建外部 tracker item。
- 不替代 spec 的长期设计真相。
- 不把可执行工作伪装成 backlog。
- 不把新症状或新 root cause 写回旧 fixed issue；新建并引用。
- 不记录 runtime 拆解、owner、并行批次或子代理消息。

## Self-Review

- Source 和 evidence 是否可追溯。
- 是否是独立问题记录，而不是执行 slice 或任务换皮。
- scope 是否没有泄漏 implementation steps 或 runtime topology。
- fixed / reopen 路径与状态是否正确。
- 本地 TOC 规则是否遵守。
- artifact 修改后是否运行 `validate-flow`。
