---
name: to-acceptance
description: 'Create or update concise Sky Flow acceptance artifacts when work reaches a human acceptance gate, stage confirmation, sign-off, feedback checkpoint, or completion claim; group each problem or request with acceptance steps and a human-filled acceptance conclusion, record only necessary evidence, risks, confirmations, round state, and handoff to to-next-acceptance.'
---

# to-acceptance

`to-acceptance` 创建或更新 Sky Flow `acceptance` artifact。它把已经完成、阶段性完成、只读调查完成或需要人工判断的工作，整理成可反馈的验收文档。

验收文档不是测试报告的替代品，也不替代 `plan` / `task` 状态。它记录人类验收视角下的范围、证据、行为场景、残余风险、待确认问题、反馈结论和下一轮动作。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取来源：优先使用用户指定的 `plan` / `task` / `spec` / existing `acceptance`；否则从当前会话提取验收主题、交付范围和证据。
3. 判断创建还是更新：
   - 已有 `acceptance` 时，先读取现有轮次、反馈和未关闭项，追加或整理，不覆盖人工结论。
   - 来源是 `plan` 且该 plan 已绑定 `acceptance` 时，更新绑定文档。
   - 未指定文档时，根据来源生成 stable id，并写入 `${SKY_FLOW_ROOT}/acceptance/<acceptance-id>.md`。
4. 选择 `acceptance_type`：需要人类反馈默认 `interactive`；只读总结用 `report`；HTML 只在信息结构或媒体展示明显更清晰时使用。
5. 写入或更新 frontmatter、当前轮次，以及一组或多组「问题 / 需求 → 验收步骤 → 验收结论（人类填）」。
6. 自检：每个问题 / 需求 是否都有成组的验收步骤和验收结论，且步骤明确说明先做什么、再做什么、最后观察什么。
7. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Source And Naming

`acceptance` 可以来自 `plan`、`task`、`spec` 或当前会话。

- `plan` 来源：id 推荐 `<plan-id>-acceptance`，frontmatter 写 `source_type: plan`、`source_id: <plan-id>`、`plan: <plan-id>`；如果更新 plan artifact，应同步 `plan.acceptance`。
- `task` 来源：id 推荐 `<task-id>-acceptance`，frontmatter 写 `source_type: task`、`source_id: <task-id>`；正文中说明所属 plan。
- `spec` 来源：id 推荐 `<spec-id>-acceptance`，frontmatter 写 `source_type: spec`、`source_id: <spec-id>`。
- 会话来源：id 使用稳定短 slug，frontmatter 写 `source_type: conversation`、`source_id: current-session`，正文补足上下文，不能依赖聊天记录作为唯一来源。

推荐 frontmatter：

```yaml
id: <acceptance-id>
artifact_type: acceptance
status: draft
acceptance_type: interactive
source_type: plan
source_id: <source-id>
plan: <plan-id>
round: 1
```

状态规则：

- `draft`：验收草稿仍在整理。
- `in_progress`：已进入人工反馈或下一轮确认。
- `completed`：所有验收项都有明确通过、放弃或转入其他 artifact 的结论。
- `abandoned`：必须有人工协商依据，并建议转入 `backlog`。

## Acceptance Body

正文必须简洁扼要，最多写到二级标题。固定核心单元是验收组，每组必须按顺序成组出现：「问题 / 需求」→「验收步骤」→「验收结论（人类填）」。一个问题 / 需求 就是一组；多个问题重复整组三段。其他 section 按实际验收价值保留，不强制填写。

```markdown
# <Acceptance Title>

最后更新：<YYYY-MM-DD>

## 问题 / 需求

<用 2-4 句话说明要验收的问题、需求或阶段成果；只写人类判断需要知道的背景。>

## 验收步骤

1. <先做什么操作、打开什么页面、运行什么命令或查看什么 artifact。>
2. <再做什么操作或切到哪个状态。>
3. 观察 <预期看到的行为、结果、字段、页面状态或验收口径。>

## 验收结论（人类填）

- 结论：
- 反馈：

## 关联

- Task: <能明确关联到本验收组的 task artifact id / 路径；不能可靠关联时省略>
- Commit: <能明确关联到本验收组的 commit hash 和简短 subject；不能可靠关联时省略>

## 证据

- <验证命令、检查结果、报告路径、产物路径或观察结论；无必要证据时省略。>

## 待确认

<用 1-2 句话说明为什么需要人工确认；没有人工确认项时省略。>

1. <先查看什么信息、页面、artifact 或证据。>
2. <再对比什么口径、反馈或预期结果。>
3. 确认 <需要人类给出的明确结论，例如通过、驳回、补充证据或调整范围。>

## 待补充

- <缺少但需要补齐的背景、证据、artifact 链接或验收材料；没有明确补充项时省略。>

## 残余风险

- <已知风险、限制或未覆盖范围；无高价值风险时省略>

## Feedback

- <人类反馈、结论或补充要求>

## Next Round

- <下一轮需要重新验收、补证或确认的点>

## Archive

- <已关闭轮次的压缩摘要、结论和关键证据>
```

## Conciseness Rules

- 每个问题 / 需求 必须形成一组，且同组内必须连续出现「问题 / 需求」「验收步骤」「验收结论（人类填）」。
- 问题 / 需求必须用几句话说清楚；不要复述 plan / task 的长背景、实现过程或完整聊天摘要。
- 验收步骤默认 3 步左右：第一步做什么，第二步做什么，最后一步观察什么。
- 验收结论留给人类填写；除非来源里已有明确人工反馈，否则 Agent 不替人类写通过、失败或放弃结论。
- 除每组固定三段外，其他 section 都不是强制必填；不要为了模板填 `无`、`暂无`、`不涉及` 等低效占位。
- 能明确关联到某个验收组的 task artifact 或 commit，写入该组的 `关联` section；不能可靠关联时不要猜，也不要写占位。
- 与某个验收组相关的关联、证据、待确认、待补充或风险，放在该组验收结论之后、下一组问题 / 需求之前；文档级 `Next Round` / `Archive` 可放在全文末尾。
- `关联` 只写可追溯引用：task artifact id / 路径、commit hash 和简短 subject；不要粘贴完整 commit diff 或长日志。
- 每个步骤都必须是人类能执行或判断的动作 / 观察点；不要写 mock、私有 helper、调用顺序或内部实现偏好。
- 待确认也使用类似组织方式：先说明为什么要确认，再列确认步骤，最后写清需要人类给出的结论。
- 待补充只记录明确缺口，例如缺少的验收材料、证据路径、业务口径或人工反馈；没有明确补充项时省略。
- 证据、待确认、待补充、风险、下一轮只写会影响验收判断的信息；没有高价值内容时直接省略。
- 长日志、长输出、完整报告、抓包样本只放路径和关键结论，不粘贴全文。

## Item Rules

- 验收步骤必须描述可观察结果：用户可见行为、业务不变量、artifact 契约、外部接口、交付边界或阶段 gate。
- 不写 mock、私有 helper、调用顺序、内部实现偏好等低价值细节，除非它本身就是公开契约或安全边界。
- `scenario`、`evidence`、`expected feedback` 只在它们能让验收更清楚时写入，不要机械展开成子项。
- 人类需要确认的项必须有可判定结论，不写泛泛总结；复杂确认按步骤组织，避免散列问题清单。
- 声明完成前必须有验证证据；没有证据时写入 `待确认` / `Confirm With Human` 或 `Next Round`，不要包装成已完成。

## Round Rules

- `round` 从 1 开始递增。新文档默认第 1 轮；处理反馈进入下一轮时交给 `to-next-acceptance`。
- 当前轮只保留下一次人类需要判断的信息；已关闭内容压缩到 `Archive`，保留结论、处理结果和关键证据。
- 未被人类提及的验收项不能默认通过，必须继续保留到下一轮，直到明确通过、明确失败、明确放弃或转入 `backlog`。
- 大段日志、输出、报告或样本不要堆在当前轮；正文只保留来源、关键字段、结论和可追溯路径。
- 下一轮也必须延续简洁分组格式，优先给出新的「问题 / 需求 → 验收步骤 → 验收结论（人类填）」三段，不恢复成完整测试报告。

## Handoff To to-next-acceptance

当请求是在处理已有 `acceptance` 的反馈、推进下一轮验收或从 plan / task runtime 状态推导下一轮范围时，使用子 skill：

`skills/to-next-acceptance/SKILL.md`

该子 skill 当前放在 `to-acceptance` 目录内，保持作为 `to-acceptance` 的下级能力。它负责分类反馈、保留未提及项、识别证据缺口，并更新下一轮验收范围。

## Boundaries

- 不替代 `to-plan` / `to-task` / `to-implement` 的状态维护。
- 不替代 `to-test` 的测试策略、测试 ROI、stable seam 或替代验证判断。
- 不替代 `validate-flow` 的 artifact 契约检查。
- 不把验收文档写成 PRD、长期设计文档、实现计划或完整测试报告。
- 不把项目专属命令、业务术语或环境限制写入 Sky Flow core；这些由项目本地规则或来源 artifact 承载。

## Self-Review

- Source：frontmatter 是否能追溯来源 artifact 或当前会话上下文。
- Grouping：每个问题 / 需求 是否都有紧随其后的验收步骤和验收结论（人类填）。
- Brief：问题 / 需求 是否用几句话说清楚，没有复述长背景。
- Steps：验收步骤是否明确说明做什么、做什么、观察什么。
- Evidence：完成声明是否有证据，证据是否可追溯。
- Links：能关联到验收组的 task artifact / commit 是否已放在对应组内，且没有猜测性引用。
- Optional sections：非核心 section 是否都承载有效信息，没有低效占位。
- Items：验收项是否可由人类判断，且不依赖私有实现细节。
- Confirmations：需要人类判断的问题是否按背景、确认步骤、明确结论组织。
- Rounds：未提及项是否继续保留，已关闭项是否压缩归档。
- Validation：修改 artifact 后是否运行 `validate-flow`。
