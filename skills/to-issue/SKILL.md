---
name: to-issue
description: 'Create or update Sky Flow issue artifacts under the local docs issue directory, not GitHub Issues; use when recording problems, evidence, opportunities, unresolved findings, vertical slices, or work candidates that should be tracked before entering to-plan.'
---

# to-issue

`to-issue` 创建或更新 Sky Flow `issue` artifact。它把问题、证据、线索、未进入实施的改进候选，或从 spec / plan / 讨论中拆出的可独立认领工作单元，写入本地 `${SKY_FLOW_ROOT}/issue/`；已修复且 `status: completed` 的 issue 移入 `${SKY_FLOW_ROOT}/issue/fixed/`。它不创建 GitHub Issue，不调用外部 issue tracker。

issue 是可追踪的工作单元或问题记录，不是聊天摘要，也不是实施计划。只有当人类或 Agent 决定进入修复、实现或系统化分析时，才从 issue 派生或关联 `to-plan`。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取项目 docs 入口规则：如果 `${SKY_FLOW_ROOT}/AGENTS.md` 或 `${SKY_FLOW_ROOT}/CLAUDE.md` 存在，读取其中与目录边界和 Table Of Content 相关的规则。
3. 确认来源：当前会话、`spec`、`plan`、`task`、`acceptance`、`backlog`、`handoff`、review finding、debug 证据或用户指定材料。
4. 判断写入形态：
   - 单一问题或线索：创建 / 更新一个 issue。
   - 多个可独立认领 slice：先列出拆分建议和依赖顺序；需要人类确认粒度时先问一个高价值问题。
5. 创建或更新 `${SKY_FLOW_ROOT}/issue/<issue-id>.md`；fixed issue 使用 `${SKY_FLOW_ROOT}/issue/fixed/<issue-id>.md`，且必须是 `status: completed`。如果项目 docs 入口声明了 issue TOC 或索引规则，按本地规则执行。
6. 如果本地 docs 入口要求维护 TOC，创建、删除或移动 issue artifact 后同步更新 `${SKY_FLOW_ROOT}/AGENTS.md` / `${SKY_FLOW_ROOT}/CLAUDE.md` 中对应目录的 TOC。
7. fixed issue 被同一 root cause 的新证据推翻时，移回 `${SKY_FLOW_ROOT}/issue/`，把 `status: completed` 改成 `in_progress` 或 `not_started`，并写入 `Reopen Evidence` / `Reopen Reason`。新症状或新 root cause 新建 issue，并引用旧 fixed issue。
8. 创建、移动或修改 Sky Flow artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Issue Shape

issue 可以有两种常见形态：

- `problem record`：记录现象、证据、影响、上下文、未决问题和后续切入点。
- `vertical slice`：从 spec / plan / 讨论中拆出的窄而完整、可独立认领、可验证工作单元。

优先使用 vertical slice，而不是纯水平拆分。不要把一个大目标机械拆成“只改 schema / 只改 API / 只改 UI”这类无法独立验证的片段；除非它本身就是独立可验证的准备工作。

## Metadata

推荐 frontmatter：

```yaml
id: <issue-id>
artifact_type: issue
status: draft
plans: []
```

字段规则：

- `id`：文件 stem，使用短横线命名，表达问题或 slice 主题；不要使用空泛的 `issue-1`。
- `status`：新建默认 `draft`；确认可进入计划但尚未规划时可转为 `not_started`；已被 plan 处理或明确关闭后可转为 `completed`；放弃必须有人工或事实依据。
- `plans`：只记录直接关联 plan id。若 issue 后续进入 `to-plan`，必须与 plan 的 `issues` 双向绑定。

目录规则：

- 非 `completed` issue 位于 `${SKY_FLOW_ROOT}/issue/<issue-id>.md`。
- `status: completed` 的 fixed issue 位于 `${SKY_FLOW_ROOT}/issue/fixed/<issue-id>.md`。
- fixed issue 捞回时必须移回 `${SKY_FLOW_ROOT}/issue/`，并把 status 改成 `in_progress` 或 `not_started`。

fixed issue 正文应压缩为短结论，保留 resolution、fixed by、verification、residual risk 和 follow-up。fixed issue 被捞回时必须新增 `Reopen Evidence` / `Reopen Reason`，说明新证据和原完成结论为什么不再成立。

## Body Template

正文保持轻量。固定的是核心信息，不是完整标题清单；按 issue 形态裁剪空 section。

```markdown
# <Issue Title>

最后更新：<YYYY-MM-DD>

## Summary

<3-5 句说明问题、机会或 slice 目标。>

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

## Vertical Slice Rules

拆分多个 issue 时：

- 每个 slice 应交付一个窄但完整、可观察、可验证的结果。
- 每个 slice 应能被独立认领，且写清 `Blocked by`。
- 优先把能自动推进的 slice 标为 `AFK`；需要人类产品 / 设计 / 架构决策的 slice 标为 `HITL`。
- 依赖顺序必须清楚；不要把有真实依赖的 slice 写成并行。
- 不把 implementation steps、命令清单、代码片段或 commit 粒度写进 issue；这些属于后续 `to-plan` / `to-task`。

拆分展示建议：

```text
Issue Breakdown
1. <Title>
   Type: AFK / HITL
   Blocked by: <None / issue title>
   Outcome: <完成后能观察到什么>
   Verification: <如何证明这个 slice 完成>
```

## Docs TOC Rules

Sky Flow core 不硬编码项目文档索引，但必须尊重本地 docs 入口。

- 如果 `${SKY_FLOW_ROOT}/AGENTS.md` 或 `${SKY_FLOW_ROOT}/CLAUDE.md` 存在，且声明某些 docs 子目录纳入 Table Of Content，创建、删除或移动这些目录下的 artifact 时必须同步维护 TOC。
- 如果两者都是同一文件或软链接，维护一次即可。
- 如果本地规则明确某目录不纳入 TOC，例如 handoff / progress 类过程目录，不要为了完整感强行加入。
- 只更新当前 artifact 对应目录的 TOC 条目；不要顺手重排或清理无关条目。

## Boundaries

- 不创建 GitHub Issue、Linear Issue 或其他外部 tracker 条目。
- 不替代 `to-spec`：目标、外部契约、数据口径或行为要求仍不清时，回到 spec 澄清。
- 不替代 `to-plan`：已经决定进入实施时，用 issue 作为输入创建 plan。
- 不替代 `to-backlog`：当前阶段已经阻塞且需要恢复条件时，使用 backlog。
- 不替代 `to-handoff`：需要跨会话可执行恢复状态时，使用 handoff。
- 不写项目专属命令、业务术语、提交规范或目录规则；这些来自本地 docs 入口或来源 artifact。
- 不把新症状或新 root cause 写回旧 fixed issue；这类情况应新建 issue 并引用旧 fixed issue。

## Self-Review

- Local docs rules：是否读取并遵守 `${SKY_FLOW_ROOT}/AGENTS.md` / `${SKY_FLOW_ROOT}/CLAUDE.md` 的 TOC 规则。
- Local-only：是否只写本地 docs issue artifact，没有创建外部 tracker。
- Source：来源、证据和相关 artifact 是否可追溯。
- Slice：如果拆分 issue，是否是可验证 vertical slice，而不是纯水平层级拆分。
- Scope：是否没有提前写 implementation steps、命令清单或 commit 粒度。
- TOC：新增、删除或移动纳入 TOC 的 issue 时，是否同步本地 TOC。
- Fixed / reopen：completed issue 是否位于 `issue/fixed/`；捞回 issue 是否移回 active 目录、改掉 `completed` status 并写清 reopen 证据。
- Validation：创建或修改 artifact 后是否运行 `validate-flow`。
