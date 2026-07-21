---
name: to-handoff
description: 'Create or update a Sky Flow handoff artifact only when the user explicitly invokes $to-handoff for volatile cross-session or cross-agent transfer state such as uncommitted diffs, terminal state, temporary environments, or short-lived evidence.'
---

# to-handoff

`to-handoff` 保存下一轮无法从仓库、spec Progress 和 active thin plan 重建的易失状态。它不是聊天摘要、长期真相源或默认恢复入口。

长期设计、稳定 checkpoint、durable decision、blocker 和目标级验证结论必须先回写 spec；有恢复价值的当前 slice、code context、局部 decision 和验证入口留在 active plan；只有未提交 diff、当前终端、临时环境、短生命周期 evidence 或接手动作才进入 handoff。

handoff 默认写入 `${SKY_FLOW_ROOT}/handoff/`，并应由项目 `.gitignore` 排除。需要长期共享的事实不能只留在这里。

## Quick Path

1. 确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`。
2. 确认相关上下文：conversation、spec、issue、acceptance、backlog、plan 或已有 handoff。
3. 先判断信息是否已在 spec Progress、active plan、仓库文件或持久证据中；能重建的内容不要复制。
4. 收集易失事实：未提交范围、终端 / 进程、临时环境、短期凭据状态、未保存 evidence、接手动作和 stop conditions。
5. 创建或更新 `${SKY_FLOW_ROOT}/handoff/<id>.md`。
6. 如果 handoff 目录未被忽略，提醒用户；不要默认提交。
7. 修改 artifact 后由当前 Skill 直接对改动路径运行 deterministic validator，不进入 `validate-flow` Skill。

## Source And Naming

```yaml
---
id: <handoff-id>
artifact_type: handoff
status: draft
resume_from: <checkpoint-or-current-session>
---
```

- `source_type` / `source_id` 是可选 provenance；只有稳定上游能提高可发现性时写入，不参与全局关系校验。
- spec 只引用 path / id 和 checkpoint，不复制整个 Progress。
- acceptance / backlog 只保留当前人类反馈或恢复条件；active plan 放在 `Read First`，不赋予 handoff 新的权威来源。
- `resume_from` 必须是下一轮可定位的 checkpoint、文件、终端或当前会话入口。

## Body Template

```markdown
# Handoff: <Title>

最后更新：<YYYY-MM-DD>

## Resume Goal

<下一轮要继续达成什么。>

## Volatile State

- Uncommitted changes:
- Terminal / process state:
- Temporary environment:
- Short-lived evidence:

## Read First

- <spec / file / report>: <为什么必须先读>

## Scope

- Allowed:
- No Touch:

## Risks / Blockers

- <无法持久化到 spec 的当前风险或歧义>

## Next Actions

1. <可直接执行的接手动作>

## Stop Conditions

- <何时停止并回到人类、spec 或 backlog>
```

## Recovery Rules

- 下一轮按 `Read First` 先读相关 spec 和其 Progress；存在 active plan 时再读 plan，最后使用 handoff 补充易失信息。
- 更新已有 handoff 时删除已失效的临时状态，不累积历史流水。
- 验证证据已经稳定落盘时只引用路径，不复制长输出。
- 多个并行 lane 只有共享同一个 resume goal 且确有易失状态时才放同一 handoff。
- 接手成功后可以标记 `completed`，并删除 / 压缩不再需要的易失内容。

## Boundaries

- 不替代 spec Progress、acceptance 或 backlog。
- 不写聊天流水、完整 diff、长日志或长期设计正文。
- 不把可长期持久化的信息故意留在 handoff。
- 不写 secret、token、私钥或原始敏感数据。
- 当前工作长期无法推进时使用 `to-backlog`，不要伪装成 handoff。

## Self-Review

- 内容是否真的是易失状态，而不是重复 Progress。
- Read First、optional provenance 与 resume_from 是否可定位。
- 下一轮能否直接接手，且知道 allowed / no-touch。
- 风险、stop conditions 和缺失证据是否明确。
- handoff 是否保持本地、紧凑且无敏感数据。
- artifact 修改后是否直接对改动路径运行 deterministic validator。
