---
name: to-spec
description: 'Align, create, or maintain a durable Sky Flow spec only when the user explicitly invokes $to-spec for long-lived design, requirement clarification, implementation readiness, execution constraints, or a compact Progress recovery snapshot.'
---

# to-spec

`to-spec` 先建立共同底座，再把已经稳定的设计真相写入 Sky Flow `spec`。spec 是长期设计与目标级恢复状态的规范性载体；ready 后由 `to-implement` 直接执行，不要求先创建 plan，也不生成 task / step。只有执行期出现真实恢复价值时，`to-implement` 才按需维护非规范性的 thin plan。

简单、一次性且不需要长期设计沉淀的工作直接交给 runtime。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户；判断当前是只做对齐，还是用户已授权创建 / 更新 spec。
2. 只读检查相关代码、docs、schema、issue、现有 spec、近期变更和其他可信证据。
3. 完成`底座对齐`，区分事实、冲突、未知与用户真正要保护的结果。
4. 为每个实质分叉判断`决策归属`，只向用户询问真正属于人类的决策。
5. 沿`决策前沿`逐个关闭会改变下游设计的问题；一次只问一个，并给出推荐、影响和它将解锁什么。
6. 对真实分叉给出 2-3 个互斥方案及取舍；没有真实分叉时直接说明判断，不机械凑选项。
7. 分段呈现设计并及时校准；只把稳定结论写入 spec，不记录问答过程或决策树。
8. 用`就绪证明`判断是否可执行；ready 后让 Progress `Next` 指向目标级恢复入口。
9. 创建或修改 spec 后由当前 Skill 直接对改动路径运行 deterministic validator，不进入 `validate-flow` Skill。spec 语义一致性由本 Skill 的就绪证明和 Self-Review 收口；只要求设计产物时请用户 review，用户已明确要求继续实现且没有人类决策未关闭时可直接进入 `to-implement`。

## 底座对齐

先确认设计赖以成立的核心底座，而不是象征性问几个问题：

- `根因与动机`：为什么现在要做，现状在哪个可观察点失效。
- `成功边界`：什么结果算成功，什么明确仍算失败。
- `不变量`：无论采用哪种实现都必须保持什么。
- `系统边界`：谁发起、谁拥有状态、谁做最终裁决、影响到哪里为止。
- `关键契约`：外部行为、数据语义、权限、兼容、迁移和运维约束。
- `非目标`：哪些合理但不属于本轮的扩展明确不做。

同时维护四类运行时视图：仓库已确认事实、无法从仓库确认的未知、证据之间的冲突、必须统一的关键术语。它们用于对齐，不要求成为固定 spec section。

复杂设计至少检查正常路径、边界路径和反例路径。场景关注可见行为、业务不变量与系统边界，不写 mock、私有 helper 或调用顺序。

## 决策归属

| 类别 | 处理方式 |
| --- | --- |
| 仓库事实 | Agent 从代码、docs、schema、历史或运行证据查明，不转问用户。 |
| 人类决策 | 产品 / 业务口径、风险偏好、外部行为、权限边界、重大 scope 或不可逆选择由用户决定。 |
| Agent 决策 | 已确认边界内的架构与工程选择由 Agent 取证、权衡并决定；影响长期架构或后续约束的重要结论写入 spec。 |
| runtime 选择 | 工具、顺序、局部可逆实现、调度和验证组合由执行时决定，不进入 spec；需要跨会话恢复时可暂存于 thin plan。 |
| 外部未知 | 当前任何一方都不能确认时，记录影响、owner 和解除条件；实质阻塞则保持未就绪。 |

实质性判断：如果答案不同会改变成功标准、外部行为、数据语义、权限、兼容 / 迁移、重大 scope、不可逆风险或验收口径，它才值得成为 spec 决策或问题。

## 决策前沿

`决策前沿`是当前最靠近根部、且会解锁多个下游判断的未决问题，只存在于对话或 runtime 中：

1. 先查仓库事实和已有约束。
2. 找出仍会改变设计方向的根问题，并按依赖顺序处理。
3. 若属于 Agent 决策，直接给出结论、依据和主要取舍。
4. 若属于人类决策，一次只问一个：先给推荐，再说明其他选择的影响和此答案将解锁什么。
5. 用户回答后立即检查哪些下游分叉已自动关闭，再推进新的前沿。

不要持久化问题树、问答时间线、被自动关闭的分支或“已经问过什么”。只写最终决策和仍然真实开放的问题。

出现以下任一情况时，完整读取 [decision-alignment.md](references/decision-alignment.md)：用户要求 grill / stress test；存在多个相互依赖的实质决策；涉及跨系统、数据、外部契约、安全、权限、迁移或不可逆动作；仓库证据与用户口径仍冲突。

## Writing Rules

- spec 保存长期设计真相与紧凑目标级 Progress，不保存代码步骤、文件 / symbol 级落地上下文、命令清单、runtime 拓扑或子代理过程；这些内容只有具备恢复价值时才进入 thin plan。
- requirements 必须可测试、无歧义；未知内容使用 `[NEEDS CLARIFICATION: ...]`，不要用模板制造伪完整。
- acceptance scenarios 保护行为、不变量或外部契约。
- `Execution Constraints` 只写真实 no-touch、人类 gate、不可逆操作、独立 review、安全或兼容约束。
- 设计变化更新 Requirements / Decisions；实现结果、证据、blocker 和下一恢复目标更新 Progress。
- 一个 spec 覆盖多个可独立演进、没有共同成功边界的系统时拆分 spec，不用 thin plan 或其他执行层 artifact 掩盖过大 scope。

稳定决策可按需记录归属：

```markdown
## Decisions

- 决策: <稳定结论>
  - 归属: 人类 | Agent（已确认边界内）
  - 理由: <结论赖以成立的核心依据>
  - 放弃方案: <仅保留仍有解释价值的主要替代方向>
```

仍开放的实质问题应说明为什么必须回答，而不是只列问号：

```markdown
## Open Questions

- 问题: <尚未解决的问题>
  - 负责人: 人类 | 外部
  - 重要性: <答案会改变什么>
  - 推荐: <当前最佳建议；外部未知可写待证据>
  - 解锁: <回答后可确认的设计范围>
```

字段按需使用；不要为了格式完整给每个普通决定添加元数据。

## 推荐形状

spec 不要求每个可选 section 都存在，但直接创建时至少保持可发现 frontmatter，并覆盖完成判断所需语义：

```markdown
---
id: <spec-id>
artifact_type: spec
status: draft | not_started | in_progress | completed | abandoned
---

# <标题>

## Intent
## Context
## Scope
## Acceptance Scenarios
## Requirements
## Decisions
## Verification Intent
## Implementation Readiness
## Progress
```

`Execution Constraints`、`Open Questions`、迁移、安全、运维、外部契约和风险 section 只在确有内容时增加。section 名称不是执行前置 schema；高可读、可测试和语义完整比模板一致更重要。

## 就绪证明

`Ready: yes` 表示执行层不需要重新决定“到底要什么”，至少能够证明：

- Intent、Scope、Requirements、Acceptance Scenarios 和 Verification Intent 互相一致。
- 底座中的成功边界、不变量、系统边界和关键契约已经足够清楚。
- 没有未关闭的实质人类决策或 blocking `[NEEDS CLARIFICATION: ...]`。
- 重要 Agent 决策已有可信依据；runtime 选择没有泄漏进 spec。
- 正常路径、边界路径和反例路径遵循同一组不变量。
- 实现者无需猜测产品口径、数据语义、权限边界或如何判断完成。
- 必要 Execution Constraints 已表达，Progress `Next` 是清楚的目标级恢复入口。
- readiness 不依赖 plan 是否存在；plan 是执行期按需 materialize 的 working set。

不满足时保持 `draft`、`Ready: no`，并明确 blocking question 或外部未知的解除条件。

## Progress

Progress 是覆盖更新的语义恢复快照，只回答：当前稳定成立什么、已经完成哪些能力或行为、下一目标级恢复入口、真实 blocker 及解除条件、最近验证结论与残余风险。

不得记录执行时间线、具体代码行号、逐文件 diff、完整命令、tool call 或子代理过程。必要定位可引用稳定模块、类、函数、公开接口或测试套件。新内容合并或替换过期状态，不持续追加。

长期延期或退出活动队列转 `to-backlog`；只有易失本地状态跨会话接力时转 `to-handoff`。

## Self-Review

- 底座：根问题、成功边界、不变量、系统边界和非目标是否清楚。
- 归属：仓库事实是否被误问用户，Agent / runtime 决策是否被误升级，人类决策是否被遗漏。
- 前沿：根问题是否先于依赖问题，是否还有会推翻下游设计的未决项。
- 一致性：Intent、Scope、Requirements、Scenarios、Decisions、Readiness 是否互相支持。
- 可验证性：要求和证据是否足以判断完成，且没有绑定脆弱实现细节。
- 约束：只保留真实约束，没有预设 runtime 调度。
- Progress：是否高可读、语义化、可恢复，且没有代码行 / 命令 / Agent 流水。

## 推荐关系

- ready spec 执行或继续：`to-implement`，由它决定 runtime-only 或按需 thin plan；从多个 spec 选择 / 恢复目标：`pick-goal`。
- 尚未进入设计的问题证据：`to-issue`；bug / root cause 与事故回归：`to-debug`；普通测试策略和验证组合由 native runtime 决定。
- 真正人类 gate：`to-acceptance`；长期离队：`to-backlog`；易失接力：`to-handoff`。

创建或更新 spec 后直接运行局部 deterministic lint 并明确就绪状态。是否停下来等 review 取决于用户当前请求和仍存在的人类决策，不设置额外固定 gate。
