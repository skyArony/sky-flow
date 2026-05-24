---
name: to-backlog
description: 'Create or update Sky Flow backlog artifacts when current work is blocked, deferred, abandoned, or needs recovery later; capture source context, blocker reason, dependencies, recommended resume timing, and links back to plan/task/conversation sources.'
---

# to-backlog

`to-backlog` 创建或更新 Sky Flow `backlog` artifact。它把当前阶段暂时无法推进的阻塞点沉淀成可恢复的长期记录：主题、来源、为什么现在不能继续、依赖什么、什么时候适合捞回，以及后续恢复时必须读取的上下文。

backlog 不是聊天摘要，也不是 issue / plan 的替代品。它只记录当前阶段无法推进但仍值得保留的工作；如果目标已经可以执行，回到 `to-plan` / `to-task` / `to-implement`。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 确认来源：当前会话、已有 `plan`、已有 `task`，或被验收 / 执行流程转入 backlog 的争议项。
3. 只读来源 artifact 和必要上下文，提取主题、当前状态、已尝试动作、阻塞原因、依赖条件和恢复信号。
4. 判断是否应创建 backlog：只有当前阶段确实无法继续、被延期、需要人工输入、外部依赖未满足或已协商放弃时才写。
5. 创建或更新 `${SKY_FLOW_ROOT}/backlog/<id>.md`；如果项目已有 backlog 目录约定，沿用现有路径。
6. 如来源 plan / task 已被人类确认放弃，可把对应 artifact 状态更新为 `abandoned`，并在 backlog 中反向说明；没有人工协商依据时不要单方面改成 `abandoned`。
7. 自检上下文是否足以让后续会话不依赖聊天记录恢复判断。
8. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Backlog Metadata

frontmatter 使用 Sky Flow schema：

```yaml
id: example-blocker
artifact_type: backlog
status: draft
source_type: conversation
source_id: current-session
depends_on: []
recommended_resume: after-dependency-ready
```

字段规则：

- `id`：使用短横线命名，表达阻塞主题；不要使用空泛的 `backlog-1`。
- `status`：新建默认 `draft`；被确认仍需保留但尚未恢复时可转为 `not_started`；已被恢复并纳入 plan / task 后可转为 `completed`。
- `source_type`：使用 `conversation`、`plan` 或 `task`。
- `source_id`：如果来自 plan / task，写 artifact id；如果来自当前会话，写 `current-session` 或更具体的会话来源标识。
- `depends_on`：写恢复前必须满足的 artifact、外部决策、账号、环境、数据、权限或人工输入；没有时用 `[]`，但正文仍要说明为什么暂时不能继续。
- `recommended_resume`：写可判定的恢复时机，例如 `after-dependency-ready`、`after-human-decision`、`after-environment-evidence`、`after-plan-scope-change`。

## Body Template

正文保持轻量，但必须补足恢复上下文。frontmatter 已表达的字段不要机械重复。

```markdown
# <Backlog Title>

最后更新：<YYYY-MM-DD>

## Summary

<3-5 句说明阻塞主题、来源、当前阶段为什么停下，以及这件事为什么仍值得保留。>

## Source Context

- Source type:
- Source artifact:
- Related artifacts:
- Current state when backlogged:

## Blocker

- Reason:
- Evidence:
- Impact if forced now:

## Dependencies

- Required before resume:
- Owner / input needed:
- Unknowns:

## Recommended Resume

- Resume when:
- First action after resume:
- Validation or acceptance needed:

## Notes

- <关键决策、已尝试但不应重复的路径、后续注意点。>
```

可选 section：

- `Decision Log`：存在人类协商、放弃依据或重要取舍时。
- `Attempted Work`：已经做过探索、实现、验证或 fan-in，且后续恢复需要避免重复时。
- `Recovery Prompt`：需要给后续 Codex /goal 或新会话一段明确续跑提示时。
- `Acceptance Link`：从验收轮次转入 backlog，且后续需要回到 acceptance 时。

## Source Rules

- 来自 `plan`：读取 plan 的 goal、scope、current milestone、progress / recovery / blockers；只记录导致当前 plan 停下的部分，不复制整个 plan。
- 来自 `task`：读取 task 的 scope、dependencies、verification intent、fan-in / blocker notes；说明该 task 是否阻塞 plan 后续任务。
- 来自当前会话：必须把关键上下文写进正文，不能依赖聊天记录作为唯一事实来源。
- 来自 acceptance：保留人类反馈原意，区分明确失败、争议项、需要澄清和延期项；不要把未提及项默认转入 backlog。

## Update Rules

- 更新已有 backlog 时，追加 `最后更新`、新证据、依赖变化和恢复建议；不要覆盖掉仍有恢复价值的历史原因。
- 当依赖已满足但还没恢复执行时，把 `Recommended Resume` 改成下一步动作，而不是直接关闭。
- 当 backlog 已恢复进 plan / task 时，设置 `status: completed`，并写清恢复到哪个 artifact。
- 当确认不再需要时，可设置 `status: abandoned`，但必须写清人工确认或事实依据。
- 如果 backlog 对应 abandoned plan / task，确保来源关系能被 `validate-flow` 找到。

## Boundaries

- 不把可执行工作伪装成 backlog；能继续就回到执行链路。
- 不写完整 implementation plan、task DAG、命令清单或验收报告。
- 不替代 `handoff`；需要保存可执行恢复状态时使用 `to-handoff`。
- 不替代 `issue`；发现新的独立问题但未阻塞当前阶段时使用 issue 或 plan 后续项。
- 不单方面把 plan / task 改为 `abandoned`；`abandoned` 需要人类协商依据。
- 不创建空泛 backlog，例如“后续优化”“处理边界情况”；必须有具体阻塞原因和恢复条件。

## Self-Review

- Source：`source_type` / `source_id` 是否准确，相关 artifact 是否可追溯。
- Context：后续会话能否不看聊天记录就理解为什么停下。
- Blocker：阻塞原因是否具体，有证据或明确未知项。
- Dependencies：恢复前需要满足的条件是否可判定。
- Resume：`recommended_resume` 和正文第一步动作是否足够明确。
- Status：是否避免未经确认的 `abandoned`。
- Boundary：是否没有写成 plan、task、handoff、acceptance 或普通 issue。
