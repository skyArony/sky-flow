---
name: to-next-acceptance
description: 'Derive the next concise human acceptance round only when the user explicitly invokes $to-next-acceptance for an existing acceptance artifact; preserve only unresolved items that still require a real human gate.'
---

# to-next-acceptance

`to-next-acceptance` 处理已有 acceptance 的人工反馈，压缩已关闭轮次，并生成下一轮真正需要人类判断的最小范围。

## Quick Path

1. 读取 existing acceptance、人工反馈、related spec Progress（如有）和当前验证证据。
2. 把上一轮每项分类：pass、explicit fail、unmentioned、scope change、needs evidence。
3. 先过滤 Agent 可自行完成的验证；这些回 runtime 执行或作为 evidence，不继续占用人类 gate。
4. 只保留失败、争议、缺信息、需要风险决策或明确未完成的人类门控项。
5. `round` +1，旧轮次压缩到 Archive；有 related spec 时更新其 blocker / next / evidence。
6. 修改 artifact 后由当前 Skill 直接对改动路径运行 deterministic validator，不进入 `validate-flow` Skill。

## Feedback Classification

- `pass`：人类明确通过；归档结论与证据，不带入下一轮。
- `explicit fail`：明确失败、异常或待修；如果仍需人类复验，进入下一轮；否则先回 runtime 修复。
- `unmentioned`：不默认通过。判断它是否仍需要人类 gate；Agent 可自证的直接移出。
- `scope change`：反馈改变 requirement、contract、data semantics 或 acceptance behavior，暂停并回 `to-spec`。
- `needs evidence`：缺少证据；Agent 能补则先补，必须由人类提供则保留待补充。

## Inputs

- acceptance 当前轮次、反馈、未关闭项和 Archive。
- related spec Requirements、Acceptance Scenarios、Execution Constraints、Progress（如有）。
- runtime 新证据、失败验证、blocker 和残余风险。
- 人类新增范围或明确风险接受。

不能从以上来源证明的新 scope 不得凭空加入。

## Update Rules

- 当前轮只保留下一次需要人类判断、明确确认、接受风险、补信息或决策的内容。
- 已关闭项 Archive 保留：摘要、反馈结论、处理结果、关键证据、关闭日期。
- 未关闭项重写成可执行、可判断的简洁步骤，不复制长上下文。
- ordinary resume target 在 related spec 存在时写回其 Progress，不放在 acceptance；保持目标级，不写代码微任务。
- 能明确关联的 spec / commit 放在对应验收组；不能确认时省略。
- 所有 gate 关闭且无下一轮时设置 `completed`；有 related spec 时回写关键结论。

## Next Round Template

```markdown
## 验收组 1：<简短主题>

### 问题 / 需求

<本轮为什么仍必须由人类判断。>

### 验收步骤

1. <查看什么行为、环境、spec 或证据。>
2. <对比什么口径、体验、风险或选项。>
3. 确认 <通过、驳回、补材料、接受风险或调整范围。>

### 验收结论（人类填）

- 反馈：

### 关联

- Spec: <path / id；无可靠关联时省略>
- Commit: <hash + subject；无可靠关联时省略>

### 证据

- <支撑本轮判断的关键证据；没有时省略>

### 待补充

- <必须由人类补齐的材料或信息>

### 残余风险

- <仍需知情或会阻塞通过的风险>

## Next Round

- Scope:
- Human questions:
- Evidence gaps:

## Archive

- Round <N> closed on <YYYY-MM-DD>:
  - Outcome:
  - Evidence:
  - Notes:
```

## Boundaries

- 不把未提及项默认通过。
- 不把 Agent 可自证项继续包装成人工验收。
- 不把纯 FYI 或无需人类输出的结论带入下一轮；写入对话或 related spec Progress / evidence。
- 不在 acceptance 中修改长期设计；scope / contract 变化回 `to-spec`。
- 不把普通后续动作、runtime checklist 或调度状态写入 acceptance。
- 不把证据缺口包装成通过。

## Self-Review

- 每个旧项是否已分类。
- 下一轮每组是否仍是真实人类 gate。
- 失败和证据缺口是否先区分 Agent 可补与人类必须补。
- related spec Progress（如有）、acceptance round 和证据是否一致。
- 旧轮次是否压缩而不是复制。
- artifact 修改后是否直接对改动路径运行 deterministic validator。
