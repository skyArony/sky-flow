---
name: to-handoff
description: 'Create or update Sky Flow handoff artifacts for cross-session continuation, agent transfer, recovery checkpoints, or plan/task/acceptance/backlog resume points; preserve executable state, evidence, scope, blockers, next actions, and stop conditions without writing a chat summary.'
---

# to-handoff

`to-handoff` 创建或更新 Sky Flow `handoff` artifact。它把当前工作整理成可执行恢复状态，让下一轮 Agent 不依赖聊天历史也能继续：目标、当前状态、先读入口、允许范围、禁止范围、验证证据、风险 / 阻塞、下一步和停止条件。

handoff 不是聊天摘要，也不是长期设计真相源。长期设计事实回 `to-spec`，计划 / 任务进度回 `to-plan` / `to-task` / `to-implement`，验收反馈回 `to-acceptance`，暂时无法推进的阻塞回 `to-backlog`。

handoff 是本地恢复态，默认写入 `${SKY_FLOW_ROOT}/handoff/`，该目录应由项目 `.gitignore` 排除，不进入版本库。需要长期保留、跨团队共享或进入 review / commit 边界的事实，必须回写到 `spec`、`plan`、`task`、`acceptance` 或 `backlog`，不能依赖 handoff 作为唯一真相源。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 确认 handoff 来源：当前会话、`plan`、`task`、`acceptance`、`backlog`，或用户指定的既有 handoff。
3. 只读收集恢复事实：目标、当前状态、相关 artifact / 文件、已完成项、未完成项、验证证据、风险、阻塞、scope、no-touch 和下一步。
4. 判断创建还是更新：
   - 用户指定已有 handoff，或当前工作明确延续同一个恢复入口时，更新已有文档。
   - 否则创建新的 `${SKY_FLOW_ROOT}/handoff/<handoff-id>.md`。
   - 如果项目没有忽略 `${SKY_FLOW_ROOT}/handoff/`，提醒用户补 `.gitignore`；不要把 handoff 当作默认提交内容。
5. 写入 frontmatter、恢复目标、当前状态、先读入口、scope、证据、风险 / 阻塞、下一步和停止条件。
6. 自检 handoff 是否自包含、可恢复、可验证，且没有复制大段聊天、diff、日志或外部 artifact 正文。
7. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Source And Naming

handoff 可以来自 `conversation`、`plan`、`task`、`acceptance` 或 `backlog`。

- `conversation` 来源：id 使用稳定短 slug；frontmatter 写 `source_type: conversation`、`source_id: current-session`、`resume_from: current-session`；正文必须补足上下文。
- `plan` 来源：id 推荐 `<plan-id>-handoff`；frontmatter 写 `source_type: plan`、`source_id: <plan-id>`、`plan: <plan-id>`。
- `task` 来源：id 推荐 `<task-id>-handoff`；frontmatter 写 `source_type: task`、`source_id: <task-id>`、`task: <task-id>`；正文说明所属 plan。
- `acceptance` 来源：id 推荐 `<acceptance-id>-handoff`；正文保留当前轮次、反馈状态和下一轮入口。
- `backlog` 来源：id 推荐 `<backlog-id>-handoff`；正文保留阻塞原因、恢复条件和第一步动作。

推荐 frontmatter：

```yaml
id: <handoff-id>
artifact_type: handoff
status: draft
source_type: conversation
source_id: current-session
plan:
task:
resume_from: current-session
```

字段规则：

- `id`：短横线命名，表达恢复主题；不要使用空泛的 `handoff-1`。
- `status`：新建默认 `draft`；可恢复但尚未接手时可转为 `not_started`；已被下一轮成功恢复并纳入执行时可转为 `completed`。
- `source_type` / `source_id`：必须能追溯来源；当前会话来源必须在正文补齐事实。
- `resume_from`：写可恢复入口，例如 artifact id、当前阶段、当前 task、`current-session` 或明确 checkpoint。

## Body Template

正文保持紧凑。固定的是核心恢复信息，不是完整标题清单；已有信息不要机械重复。

```markdown
# Handoff: <Title>

最后更新：<YYYY-MM-DD>

## Resume Goal

<下一轮要继续达成什么。>

## Current State

- Completed:
- In progress:
- Not started:

## Read First

- <artifact / file / URL>: <为什么下一轮必须先读>

## Scope

- Allowed:
- No Touch:

## Evidence

- <验证命令、检查结果、报告路径或观察结论>

## Risks / Blockers

- <未解决问题、阻塞、歧义或残余风险>

## Next Actions

1. <可执行下一步>

## Stop Conditions

- <何时停止并询问人类或回到上游 artifact>
```

常见可选 section：

- `Decision Log`：只记录会影响恢复和后续维护的关键取舍。
- `Parallel Lanes`：存在多 Agent / 多 task 并行进度时。
- `Tried And Failed`：只有能避免下一轮重复试错时。
- `Validation Gaps`：证据缺口会影响继续推进或验收时。
- `Recovery Prompt`：需要给新会话一段明确续跑提示时。

不要为了完整感添加空 section；不要复制大段 diff、日志、spec、plan 或聊天内容，只引用路径和关键结论。

## Recovery Rules

- handoff 必须自包含：下一轮 Agent 可以只读 handoff 和 `Read First` 引用，恢复当前状态。
- 区分事实和建议；没有证据的内容写成未知项，不包装成已确认。
- 验证证据只写影响可信度的命令、报告路径、观察结果和结论；未运行验证时说明原因。
- 多个并行 lane 可以写在同一个 handoff 中，但必须属于同一个恢复目标；无关进度不要混写。
- 更新已有 handoff 时，删除或压缩过期内容，保留仍影响恢复的决策、风险和证据。
- 如果发现状态真相源缺失或过期，先更新对应 plan / task / acceptance / backlog，再写 handoff 引用。

## Handoff Quality

handoff 至少能回答：

- 下一轮要达成什么。
- 当前已经完成什么，正在做什么，还没开始什么。
- 下一轮必须先读哪些 artifact / 文件，以及为什么。
- 当前允许修改什么，禁止触碰什么。
- 哪些验证已经运行，结果是什么；哪些验证缺失。
- 当前风险、阻塞、歧义和停止条件是什么。
- 下一步动作是否可以直接执行。

## Boundaries

- 不写聊天流水账、对话摘要或情绪化说明。
- 不替代 `spec`、`plan`、`task`、`acceptance` 或 `backlog` 的状态真相源。
- 不写完整 implementation plan、task DAG、命令清单或验收报告。
- 不把 secret、token、凭证、私钥或原始敏感数据写入 handoff。
- 不写死本地固定路径、本地目录索引规则、运行命令、角色称呼、业务术语或团队流程假设。
- 不把无法继续推进的阻塞伪装成 handoff；如果当前阶段需要长期回收，使用 `to-backlog`。

## Self-Review

- Source：frontmatter 是否能追溯来源 artifact 或当前会话上下文。
- Resumability：下一轮是否不看聊天记录也能恢复。
- Scope：allowed / no-touch 是否清楚。
- Evidence：验证证据是否具体，缺口是否说明原因。
- Risks：阻塞、歧义和残余风险是否足够明确。
- Next action：下一步是否可执行，stop conditions 是否清楚。
- Boundary：是否没有写成聊天摘要、plan、task、acceptance、backlog 或项目私有流程。
- Validation：修改 artifact 后是否运行 `validate-flow`。
