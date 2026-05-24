---
name: to-next-acceptance
description: "Derive the next concise Sky Flow acceptance round from an existing acceptance artifact and current plan/task runtime state; classify feedback, preserve unmentioned items, identify scope, confirmation steps, evidence gaps, blockers, residual risks, and update the acceptance artifact for the next human review."
---

# to-next-acceptance

`to-next-acceptance` 是 `to-acceptance` 的下级能力，用于从已有 `acceptance`、人类反馈和当前 plan / task runtime 状态推导下一轮验收。

它的核心职责是：分类反馈、关闭已明确完成的项、保留未提及项、提出下一轮验收范围、补齐证据缺口，并把需要人类确认的问题写回 artifact。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取 existing `acceptance`，再读取其 `source_type` / `source_id` 指向的 `plan`、`task`、`spec` 或会话上下文。
3. 读取当前 runtime 状态：已完成任务、验证证据、失败检查、残余风险、blocker、scope 变化和人类反馈。
4. 分类当前轮每个验收项：
   - 明确通过。
   - 明确失败或需要返工。
   - 需要澄清。
   - 有争议或证据不足。
   - 未被提及。
   - 应转入 `backlog` 或其他 artifact。
5. 关闭明确通过或明确放弃的项，压缩到 `Archive`；明确失败、未提及、证据不足和需澄清的项进入下一轮。
6. 推导下一轮验收范围、验收问题、证据缺口、待补充材料、残余风险和需要人类确认的点。
7. 更新 `round`、当前轮的问题 / 需求、验收步骤、验收结论（人类填）、`Next Round`、`待确认` / `Confirm With Human`、`待补充`、`Evidence` 和 `Archive`。
8. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Feedback Classification

先分类再行动，不要一边猜测一边改状态。

- `explicit pass`：人类明确通过，或明确说某项不再需要验收。压缩进 `Archive`。
- `explicit fail`：人类明确失败、异常、待修、继续跟进。写入下一轮验收项，并连接到相关 plan / task next action。
- `clarification needed`：反馈含糊，无法判断是否通过或失败。保留到 `待确认` / `Confirm With Human`。
- `disputed`：证据与反馈冲突、实现状态与验收口径冲突。保留到下一轮，写清冲突和需要决策的问题。
- `unmentioned`：人类没有提到。不得默认通过，继续保留到下一轮。
- `backlog candidate`：当前轮无法推进、依赖外部条件或超出当前 scope。建议转入 `backlog`，在 acceptance 中保留引用和原因。

## Deriving The Next Round

下一轮范围来自四类输入：

- 当前 acceptance 的未关闭项。
- 人类反馈中的失败、异常、补充要求和澄清问题。
- plan / task runtime 状态中的新证据、失败验证、blocker、scope 变化和残余风险。
- 来源 spec / plan / task 中尚未被验收覆盖的关键行为或交付边界。

推导时必须内部确认这些问题；写入 artifact 时只保留影响下一轮验收判断的短内容，不机械展开完整清单：

- Next scope：下一轮需要人类验收什么。
- Acceptance questions：人类需要判断哪些可判定问题。
- Evidence gaps：哪些证据缺失、过期或无法支撑完成声明。
- Required evidence：下一轮前 Agent 应补哪些验证、报告或观察结果。
- Residual risks：哪些风险仍然存在，是否阻塞通过。
- Stop points：哪些问题需要先问人，不能继续猜。

## Update Rules

- `round` 递增 1；正文写清上一轮结论和本轮目标。
- 当前轮只保留下一次需要判断的内容；旧轮次压缩到 `Archive`。
- 已关闭项归档时保留：原验收项摘要、反馈结论、处理结果、关键证据、关闭日期。
- 未关闭项不要复制长上下文；重写成下一轮可执行、可判断的简洁验收步骤。
- `Evidence` 只保留当前轮需要的证据入口和结论；完整长输出用路径或报告引用。
- `待确认` / `Confirm With Human` 只放需要人工判定的问题，并按背景、确认步骤、明确结论组织；普通后续行动放到 plan / task 或 `Next Round`。
- 固定核心单元是验收组，每组用 `## 验收组 <N>：<简短主题>` 作为二级标题；组内用三级标题连续出现「问题 / 需求」「验收步骤」「验收结论（人类填）」。其他 section 按实际验收价值保留，不要填低效占位。
- 能明确关联到某个验收组的 task artifact 或 commit，写入该组的 `关联` section；不能可靠关联时不要猜，也不要写占位。
- 与某个验收组相关的关联、证据、待确认、待补充或风险，放在该组验收结论之后、下一组验收组之前，并使用三级标题；文档级 `Next Round` / `Archive` 可放在全文末尾并使用二级标题。
- `关联` 只写可追溯引用：task artifact id / 路径、commit hash 和简短 subject；不要粘贴完整 commit diff 或长日志。
- 如果所有验收项都有明确结论且无下一轮动作，可把 `status` 设为 `completed`；否则保持 `in_progress` 或 `draft`。

## Next Round Template

可直接更新到原 acceptance 文档中，按实际内容裁剪空 section。下一轮也必须保持简洁，一个问题 / 需求 一组，每组用二级标题 `验收组` 承载，组内固定包含三级标题「问题 / 需求」「验收步骤」「验收结论（人类填）」。

```markdown
## 验收组 1：<简短主题>

### 问题 / 需求

<用 2-4 句话说明本轮要复验的问题、失败反馈或补充要求。>

### 验收步骤

1. <先做什么操作、打开什么页面、运行什么命令或查看什么 artifact。>
2. <再做什么操作或切到哪个状态。>
3. 观察 <预期看到的修复结果、剩余异常、字段、页面状态或验收口径。>

### 验收结论（人类填）

- 结论：
- 反馈：

### 关联

- Task: <能明确关联到本验收组的 task artifact id / 路径；不能可靠关联时省略>
- Commit: <能明确关联到本验收组的 commit hash 和简短 subject；不能可靠关联时省略>

### 证据

- <已有证据入口和结论；没有时省略>

### 待确认

<用 1-2 句话说明为什么需要人工确认；没有人工确认项时省略。>

1. <先查看什么信息、页面、artifact 或证据。>
2. <再对比什么口径、反馈或预期结果。>
3. 确认 <需要人类给出的明确结论，例如通过、驳回、补充证据或调整范围。>

### 待补充

- <缺少但需要补齐的背景、证据、artifact 链接或验收材料；没有明确补充项时省略。>

### 残余风险

- <仍需人类知情或阻塞通过的风险>

## Next Round

- Scope:
- Questions:
- Evidence gaps:
- Agent next action:

## Archive

- Round <N> closed on <YYYY-MM-DD>:
  - Passed:
  - Failed / carried forward:
  - Evidence:
  - Notes:
```

## Boundaries

- 不把未提及项默认通过。
- 不凭空创建新 scope；scope 变化必须来自来源 artifact、人类反馈或已确认 runtime 事实。
- 不在 acceptance 中修 plan / task DAG；需要调整执行计划时回到 `to-plan` / `to-task` / `to-implement`。
- 不把验收反馈写成聊天摘要；只保留可恢复的结论、证据、问题和下一步。
- 不把证据缺口包装成通过；缺口要显式列入下一轮。

## Self-Review

- Classification：每个旧验收项是否已分类，尤其是未提及项。
- Grouping：是否使用 `## 验收组 <N>：<简短主题>` 分组，且组内三级标题包含问题 / 需求、验收步骤和验收结论（人类填）。
- Brief：下一轮问题 / 需求 是否用几句话说清楚，没有复制长上下文。
- Steps：失败、未提及、争议和证据不足的项是否被整理成可执行、可观察的验收步骤。
- Evidence：下一轮完成声明需要的证据是否明确。
- Links：能关联到验收组的 task artifact / commit 是否已放在对应组内，且没有猜测性引用。
- Optional sections：非核心 section 是否都承载有效信息，没有低效占位。
- Questions：需要人类确认的问题是否按背景、确认步骤、明确结论组织。
- Runtime alignment：plan / task 状态、验证证据和 acceptance 轮次是否一致。
- Archive：已关闭项是否压缩归档而不是删除。
- Validation：修改 artifact 后是否运行 `validate-flow`。
