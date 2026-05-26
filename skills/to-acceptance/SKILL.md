---
name: to-acceptance
description: "Create or update concise Sky Flow acceptance artifacts only when work reaches a real human acceptance gate: something the agent cannot self-verify, a significant decision humans must know or approve, missing information humans must provide, or a feedback/sign-off checkpoint. Filter out agent-verifiable checks, reference them only as supporting evidence, and hand off feedback rounds to to-next-acceptance."
---

# to-acceptance

`to-acceptance` 创建或更新 Sky Flow `acceptance` artifact。它只把已经到达人类验收门的工作整理成可反馈文档，例如 Agent 无法自行验证的真实环境行为、重大口径 / 范围决策、需要人类补齐的信息、需要人类知晓并确认的风险或阶段 sign-off。

验收文档不是测试报告、验证清单或完成证明的替代品，也不替代 `plan` / `task` 状态。Agent 可以通过代码阅读、命令、测试、模板渲染、lint、类型检查或本地页面自行验证的事项，不应单独包装成验收组；这些内容最多作为支撑人类判断的简短证据出现。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取来源：优先使用用户指定的 `plan` / `task` / `spec` / existing `acceptance`；否则从当前会话提取验收主题、交付范围和证据。
3. 先做人类验收价值过滤：
   - 保留：Agent 无法自行验证的真实环境 / 用户体验 / 权限 / 账号 / 设备 / 线上数据事项；重大产品、业务、运维、范围、兼容性或风险决策；需要人类补充的材料、口径、凭据或反馈；需要人类明确 sign-off 的阶段 gate。
   - 剔除：Agent 可自行完成的文件检查、命令验证、测试 / lint / build / Helm template 结果、静态 diff 审核、实现细节核对、mock / 私有 helper / 调用顺序验证。
   - 如果候选项全都可由 Agent 自行验证，默认不要创建或扩写 acceptance；在交付说明里报告验证结果，必要时写回 `plan` / `task` / `handoff`，而不是制造验收文档。
4. 判断创建还是更新：
   - 已有 `acceptance` 时，先读取现有轮次、反馈和未关闭项，追加或整理，不覆盖人工结论。
   - 来源是 `plan` 且该 plan 已绑定 `acceptance` 时，更新绑定文档。
   - 未指定文档时，根据来源生成 stable id，并写入 `${SKY_FLOW_ROOT}/acceptance/<acceptance-id>.md`。
5. 选择 `acceptance_type`：需要人类反馈默认 `interactive`；只读 `report` 只用于人类需要知晓的重大结论、风险或决策记录；HTML 只在信息结构或媒体展示明显更清晰时使用。
6. 写入或更新 frontmatter、当前轮次，以及一组或多组「问题 / 需求 → 验收步骤 → 验收结论（人类填）」。
7. 自检：每个验收组是否真的需要人类参与，且步骤明确说明人类先看什么、再对比什么、最后需要给出什么判断。
8. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

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

## Human Gate Filter

创建或更新验收文档前，先把来源里的候选内容按“是否需要人类参与”分类。验收组只承载人类门控项；Agent 自证项不应凑数。

应该进入 acceptance 的内容：

- Agent 无法自行验证的行为：真实设备、真实账号、浏览器 profile、外部平台、生产 / 测试环境、权限、网络、人工操作体验、客户反馈或线上数据口径。
- 需要人类拍板的决策：产品口径、业务规则、运维取舍、部署时机、风险接受、兼容性范围、是否继续推进下一阶段。
- 需要人类知晓的重大变化：架构路径变化、对外入口变化、默认行为变化、安全 / 合规 / 成本 / 可用性风险、需要后续团队配合的事项。
- 需要人类补全的信息：缺少的验收材料、业务定义、账号 / 权限、真实环境操作结果、截图、反馈、审批结论。

不应该单独进入 acceptance 的内容：

- Agent 可以直接运行并判断的验证：单元测试、类型检查、lint、build、schema 校验、Helm template、静态搜索、文件存在性或 diff 核对。
- 纯实现细节：mock、私有 helper、调用顺序、内部变量名、日志文案、低价值格式偏好；除非它本身是公开契约、安全边界或人类明确要求验收的内容。
- 已经由 `to-test`、测试报告、CI、commit 记录或 `plan` / `task` 状态清楚覆盖的完成证明。

Agent 自行验证的结果如果能支撑人类判断，可以压缩到对应验收组的 `证据` section，例如“Agent 已通过 `helm template ...` 确认模板可渲染”。不要把这些结果扩写成独立验收组，也不要要求人类重复跑 Agent 已能完成的机械检查。

如果已有 acceptance 里混入了 Agent 自证项，更新时优先把它们合并为相关人类门控项下的证据、压缩到 `Archive`，或在不覆盖人工结论的前提下移除低价值占位；保留真正需要人类判断、知晓、补信息或决策的内容。

## Acceptance Body

正文必须简洁扼要，最多写到三级标题。二级标题用于区分验收组，格式为 `## 验收组 <N>：<简短主题>`；组内用三级标题，并必须按顺序成组出现：「问题 / 需求」→「验收步骤」→「验收结论（人类填）」。一个问题 / 需求 就是一组；多个问题重复整个验收组，不要在文档顶层反复写一串 `## 问题 / 需求`。其他 section 按实际验收价值保留，不强制填写。

```markdown
# <Acceptance Title>

最后更新：<YYYY-MM-DD>

## 验收组 1：<简短主题>

### 问题 / 需求

<用 2-4 句话说明为什么这个事项需要人类验收、知晓、补信息或决策；只写人类判断需要知道的背景。>

### 验收步骤

1. <先查看什么页面、真实环境、artifact、证据或背景。>
2. <再对比什么业务口径、用户体验、风险说明、反馈或决策选项。>
3. 确认 <需要人类给出的明确结论，例如通过、驳回、补充材料、接受风险或调整范围。>

### 验收结论（人类填）

- 结论：
- 反馈：

### 关联

- Task: <能明确关联到本验收组的 task artifact id / 路径；不能可靠关联时省略>
- Commit: <能明确关联到本验收组的 commit hash 和简短 subject；不能可靠关联时省略>

### 证据

- <Agent 已完成的验证命令、检查结果、报告路径、产物路径或观察结论；只写支撑人类判断的关键证据，无必要证据时省略。>

### 待确认

<用 1-2 句话说明为什么需要人工确认；没有人工确认项时省略。>

1. <先查看什么信息、页面、artifact 或证据。>
2. <再对比什么口径、反馈或预期结果。>
3. 确认 <需要人类给出的明确结论，例如通过、驳回、补充证据或调整范围。>

### 待补充

- <缺少但需要补齐的背景、证据、artifact 链接或验收材料；没有明确补充项时省略。>

### 残余风险

- <已知风险、限制或未覆盖范围；无高价值风险时省略>

## Feedback

- <人类反馈、结论或补充要求>

## Next Round

- <下一轮需要重新验收、补证或确认的点>

## Archive

- <已关闭轮次的压缩摘要、结论和关键证据>
```

## Conciseness Rules

- 每个问题 / 需求 必须形成一组，使用 `## 验收组 <N>：<简短主题>` 作为该组二级标题；组内用三级标题连续出现「问题 / 需求」「验收步骤」「验收结论（人类填）」。
- 每个验收组都必须能回答“为什么这件事需要人类参与”；答不出来就不要写成验收组。
- 不要把每组的「问题 / 需求」「验收步骤」「验收结论（人类填）」都写成二级标题；它们是验收组内部结构，必须用三级标题。
- 问题 / 需求必须用几句话说清楚；不要复述 plan / task 的长背景、实现过程或完整聊天摘要。
- 验收步骤默认 3 步左右：第一步让人类看什么，第二步对比什么，最后一步给出什么结论。
- 验收结论留给人类填写；除非来源里已有明确人工反馈，否则 Agent 不替人类写通过、失败或放弃结论。
- 除每组固定三段外，其他 section 都不是强制必填；不要为了模板填 `无`、`暂无`、`不涉及` 等低效占位。
- 能明确关联到某个验收组的 task artifact 或 commit，写入该组的 `关联` section；不能可靠关联时不要猜，也不要写占位。
- 与某个验收组相关的关联、证据、待确认、待补充或风险，放在该组验收结论之后、下一组验收组之前，并使用三级标题；文档级 `Next Round` / `Archive` 可放在全文末尾并使用二级标题。
- `关联` 只写可追溯引用：task artifact id / 路径、commit hash 和简短 subject；不要粘贴完整 commit diff 或长日志。
- 每个步骤都必须是人类能执行或判断的动作 / 观察点；不要写 mock、私有 helper、调用顺序或内部实现偏好。
- 待确认也使用类似组织方式：先说明为什么要确认，再列确认步骤，最后写清需要人类给出的结论。
- 待补充只记录明确缺口，例如缺少的验收材料、证据路径、业务口径或人工反馈；没有明确补充项时省略。
- 证据、待确认、待补充、风险、下一轮只写会影响验收判断的信息；没有高价值内容时直接省略。
- Agent 可自行验证的命令结果只写在 `证据`，且必须支撑某个人类门控项；不要把命令结果、文件检查或模板渲染拆成独立验收组。
- 长日志、长输出、完整报告、抓包样本只放路径和关键结论，不粘贴全文。

## Item Rules

- 验收步骤必须描述可观察结果：用户可见行为、业务不变量、artifact 契约、外部接口、交付边界或阶段 gate。
- 验收项必须指向 Agent 无法自行完成的判断、需要人类知晓的重大变化、需要人类补信息的缺口，或需要人类拍板的决策。
- 对 Agent 可自行验证的完成项，先执行验证并在交付说明或证据中记录；不要把它包装成等待人类验收的事项。
- 不写 mock、私有 helper、调用顺序、内部实现偏好等低价值细节，除非它本身就是公开契约或安全边界。
- `scenario`、`evidence`、`expected feedback` 只在它们能让验收更清楚时写入，不要机械展开成子项。
- 人类需要确认的项必须有可判定结论，不写泛泛总结；复杂确认按步骤组织，避免散列问题清单。
- 声明完成前必须有 Agent 自证材料或明确的人类确认需求；Agent 能验证但尚未验证的内容，先补验证，不要转嫁到 acceptance。

## Round Rules

- `round` 从 1 开始递增。新文档默认第 1 轮；处理反馈进入下一轮时交给 `to-next-acceptance`。
- 当前轮只保留下一次人类需要判断的信息；已关闭内容压缩到 `Archive`，保留结论、处理结果和关键证据。
- 未被人类提及的验收项不能默认通过；只有仍需要人类验收、知晓、补信息或决策的项才继续保留到下一轮，直到明确通过、明确失败、明确放弃、转入 `backlog`，或被确认只是 Agent 自证项。
- 大段日志、输出、报告或样本不要堆在当前轮；正文只保留来源、关键字段、结论和可追溯路径。
- 下一轮也必须延续简洁分组格式，优先给出新的 `## 验收组 <N>：<简短主题>`，组内包含「问题 / 需求 → 验收步骤 → 验收结论（人类填）」三段，不恢复成完整测试报告。

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
- Human gate：每个验收组是否都需要人类验收、知晓、补信息或决策；Agent 可自行验证的事项是否已被剔除或压缩为证据。
- Grouping：是否使用 `## 验收组 <N>：<简短主题>` 分组，且组内三级标题包含问题 / 需求、验收步骤和验收结论（人类填）。
- Brief：问题 / 需求 是否用几句话说清楚，没有复述长背景。
- Steps：验收步骤是否明确说明人类看什么、对比什么、给出什么结论。
- Evidence：完成声明是否有证据，证据是否可追溯。
- Links：能关联到验收组的 task artifact / commit 是否已放在对应组内，且没有猜测性引用。
- Optional sections：非核心 section 是否都承载有效信息，没有低效占位。
- Items：验收项是否可由人类判断，且不依赖私有实现细节。
- Confirmations：需要人类判断的问题是否按背景、确认步骤、明确结论组织。
- Rounds：未提及项是否继续保留，已关闭项是否压缩归档。
- Validation：修改 artifact 后是否运行 `validate-flow`。
