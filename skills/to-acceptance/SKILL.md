---
name: to-acceptance
description: 'Create or update a durable Sky Flow acceptance artifact only when the user explicitly invokes $to-acceptance for a real human gate: behavior the agent cannot self-verify, a significant decision or risk, missing human input, or multi-round sign-off.'
---

# to-acceptance

`to-acceptance` 只在用户显式调用时，为需要长期保留或多轮跟踪的真实人类门控创建 artifact。普通一次性问题直接在对话中询问。Agent 能通过代码、命令、测试、lint、build、渲染或静态 review 自行判断的事项必须先自行验证，最多作为支撑人类判断的简短 evidence。

## Quick Path

1. 确认用户显式要求 durable acceptance artifact；一次性 gate 直接在对话中处理。
2. 确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`。
3. 读取来源：优先 spec，也可以是 conversation、issue、backlog、handoff 或 existing acceptance；active thin plan 只能作为实施 evidence 上下文读取，不能成为 acceptance source。
4. 过滤候选项：只保留真实设备 / 账号 / 环境 / 体验、产品或风险决策、缺失人类输入、明确 sign-off。
5. 如果所有内容都可由 Agent 自证，不创建 acceptance；直接报告并写回 spec Progress / evidence。
6. 创建或更新 `${SKY_FLOW_ROOT}/acceptance/<id>.md`，不覆盖人工反馈。
7. 每个验收组保持「问题 / 需求 → 验收步骤 → 验收结论（人类填）」。
8. 修改 artifact 后运行 `validate-flow`。

## Source And Metadata

推荐来源：

- spec：`source_type: spec`、`source_id: <spec-id>`。
- conversation：`source_type: conversation`、`source_id: current-session`，正文必须自包含。
- issue / backlog / handoff：写对应 source type 和稳定 id。
- 实现从 active plan 到达人类 gate 时仍 source 到 durable spec；plan Progress 可指向 acceptance blocker，但 acceptance 不反向以 plan 为权威来源。

```yaml
---
id: <acceptance-id>
artifact_type: acceptance
status: draft
acceptance_type: interactive
source_type: spec
source_id: <source-id>
round: 1
---
```

`acceptance_type`：

- `interactive`：默认，需要人类反馈。
- `report`：无需逐步操作，但仍要求人类明确 acknowledgement、sign-off 或风险接受；纯 FYI 不创建 acceptance。
- `html_report` / `html_interactive`：只有媒体或复杂布局明显提升真实 gate 的判断效率时使用；同样必须产生明确的人类结论。

状态：draft 表示整理中；in_progress 表示等待或处理反馈；completed 表示所有 gate 已有明确结论；abandoned 必须有人工依据并建议关联 backlog。

## Human Gate Filter

应该进入：

- 真实设备、账号、浏览器 profile、外部平台、生产 / 测试环境、权限、网络或人工体验。
- 产品、业务、运维、兼容性、部署时机、风险接受或 scope 决策。
- 需要人类提供材料、口径、凭据、截图、操作结果或 sign-off。
- spec 明确声明的 Required Human Gate。

不应该进入：

- test、typecheck、lint、build、schema、template render、静态搜索或文件检查。
- 普通 diff review、finding triage、verifier closure 或 Agent 能自行判断的完成证明。
- mock、私有 helper、调用顺序、变量名、低价值文案或格式偏好。

Agent 自证结果可以压缩到验收组 `证据`，不能拆成独立验收组。

## Body Template

```markdown
# <Acceptance Title>

最后更新：<YYYY-MM-DD>

## 验收组 1：<简短主题>

### 问题 / 需求

<为什么必须由人类判断、批准、接受风险或补信息。>

### 验收步骤

1. <先查看什么真实环境、行为、spec 或证据。>
2. <再对比什么口径、体验、风险或选项。>
3. 确认 <明确结论：通过、驳回、补材料、接受风险或调整范围。>

### 验收结论（人类填）

- 反馈：

### 关联

- Spec: <相关 spec path / id；无可靠关联时省略>
- Commit: <hash + subject；无可靠关联时省略>

### 证据

- <Agent 已完成且支撑人类判断的关键证据；没有时省略>

### 待补充

- <缺少的人工材料、口径或结果；没有时省略>

### 残余风险

- <影响人工判断的风险；没有时省略>

## Feedback

- <人类反馈或补充要求>

## Next Round

- <仍需重新验收的点>

## Archive

- <已关闭轮次的短结论和关键证据>
```

## Conciseness Rules

- 一个问题 / 需求形成一个验收组。
- 每组默认约三步，最后一步要求明确结论。
- `验收结论（人类填）` 只保留 `反馈`，Agent 不代填通过 / 失败。
- 不能可靠关联 spec 或 commit 时直接省略，不写占位。
- 长日志和完整报告只引用路径与关键结论。
- 没有高价值内容的 optional section 直接省略。

## Runtime Interaction

- Agent gate 前的可验证工作继续由 `to-implement` 动态执行。
- 到达人类 gate 时，spec Progress `Blockers` 指向 acceptance 和解除条件。
- 人类反馈返回后由 `to-next-acceptance` 分类；设计变化回 `to-spec`，可继续执行时让 Progress `Next` 指向目标级恢复入口。
- acceptance 完成后，关键结论和 evidence 回写 source spec，避免 acceptance 成为长期执行中心。

## Boundaries

- 不替代 spec Progress 或 runtime 执行。
- 不替代 native runtime 测试、`to-review` 或 `validate-flow`。
- 不把普通 review triage 写成人工验收。
- 不为纯 FYI、完成播报或无需人类输出的重大结论创建 acceptance；写入对话或 spec Progress / evidence。
- 不把未验证内容包装成通过。
- 不记录 runtime 调度、owner、并行批次或微步骤。

## Self-Review

- 每组是否真的需要人类参与。
- 问题是否简洁自包含。
- 步骤是否可观察、可判断。
- Agent 可自证项是否已执行并只作为 evidence。
- 人工反馈是否未被覆盖或代填。
- source、round、links 和 status 是否一致。
- artifact 修改后是否运行 `validate-flow`。

## Next Round

已有 acceptance 的反馈和下一轮范围交给嵌套 Skill `skills/to-next-acceptance/SKILL.md`。
