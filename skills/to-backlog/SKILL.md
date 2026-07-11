---
name: to-backlog
description: 'Create or update Sky Flow backlog artifacts only when work leaves the active execution queue because it is blocked, deferred, abandoned, or waiting on a long-lived external condition; preserve source, evidence, dependencies, and a concrete resume condition.'
---

# to-backlog

`to-backlog` 保存长期阻塞或延期状态。短期 blocker 留在 spec `Progress`；只有工作退出当前执行队列、需要未来恢复时才创建 backlog。

## Quick Path

1. 确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`。
2. 确认来源：conversation、spec、issue、acceptance、handoff 或已有 backlog。
3. 读取来源与证据，提取 current state、已尝试动作、阻塞原因、外部依赖和恢复信号。
4. 判断是否真的需要长期回收；如果现在仍可安全推进，回到 runtime 或 `to-implement`。
5. 创建 / 更新 `${SKY_FLOW_ROOT}/backlog/<id>.md`。
6. abandoned 来源必须有事实或人类依据；不要单方面放弃。
7. 修改 artifact 后运行 `validate-flow`。

## Metadata

```yaml
---
id: <backlog-id>
artifact_type: backlog
status: draft
source_type: spec
source_id: <source-id>
depends_on: []
recommended_resume: after-dependency-ready
---
```

- `source_type`：`conversation`、`spec`、`issue`、`acceptance`、`backlog` 或 `handoff`。
- `source_id`：当前会话使用 `current-session`；artifact 来源写稳定 id。
- `depends_on`：恢复前必须满足的外部条件、决策、账号、环境、数据、权限或人工输入。
- `recommended_resume`：必须可判定，例如 `after-human-decision`、`after-environment-evidence`。

## Body Template

```markdown
# <Backlog Title>

最后更新：<YYYY-MM-DD>

## Summary

<为什么现在停下，以及为什么仍值得保留。>

## Source Context

- Source:
- Current state when backlogged:
- Stable evidence:

## Blocker

- Reason:
- Evidence:
- Impact if forced now:

## Dependencies

- Required before resume:
- External input needed:
- Unknowns:

## Recommended Resume

- Resume when:
- First action:
- Spec / validation / acceptance update needed:

## Notes

- <关键决定、已尝试但不应重复的路径、风险。>
```

## Update Rules

- 更新时保留仍有恢复价值的历史原因，压缩已经过期的过程细节。
- 依赖满足但尚未恢复时，把 Recommended Resume 改成下一动作。
- 恢复执行后设置 `completed`，写清恢复到哪个 spec checkpoint 或 runtime outcome。
- 确认不再需要时可设为 `abandoned`，但必须写明依据。
- 恢复后的稳定状态回写 spec Progress；backlog 不成为新的执行中心。

## Boundaries

- 不把短期 blocker 或仍可执行的工作移入 backlog。
- 不写完整实现步骤、runtime checklist、owner、并行分工或命令清单。
- 不替代 handoff；易失接力状态使用 `to-handoff`。
- 不替代 issue；未阻塞当前工作的新问题使用 `to-issue`。
- 不复制 spec 的长期设计和完整 Progress。

## Self-Review

- Source 是否准确可追溯。
- blocker 与 evidence 是否具体。
- depends_on 和 resume condition 是否可判定。
- 后续会话是否不看聊天也能判断何时恢复。
- 是否确实已退出当前执行队列。
- artifact 修改后是否运行 `validate-flow`。
