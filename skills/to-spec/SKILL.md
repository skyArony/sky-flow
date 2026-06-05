---
name: to-spec
description: 'Run Sky Flow spec alignment and, when approved, create or update durable spec artifacts. Use when the user asks for to-spec, wants to brainstorm/refine a long-lived design/spec, needs systematic requirement clarification before planning, wants to turn current discussion into a spec, or a plan needs a missing/incomplete spec before to-plan.'
---

# to-spec

`to-spec` 先做人类对齐，再在确认后生成或更新 Sky Flow `spec` artifact。它把当前讨论、仓库事实、术语口径、设计取舍和行为要求沉淀为长期设计真相源，为后续 `to-plan` 提供稳定输入。

核心顺序：先校准仓库事实，再追问真实意图和成功标准，然后提出可比较的设计选择、获得人类确认，最后才写出高效扼要、可验证、可交给 `to-plan` 的 spec。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 判断当前是 `alignment-only` 还是 `artifact-write`：
   - 用户只是在探索、brainstorm、澄清需求或问“怎么看 / 如何优化”时，先停留在对话对齐，不急着写文件。
   - 用户指定现有 spec 时，读取该 spec，但只有确认后的设计变化才写回。
   - 用户明确要求创建 / 更新 spec，且输入已经足够稳定时，可以进入写入；否则先完成对齐门禁。
3. 只读探索相关 docs、代码、schema、历史 spec / issue / plan / design / recent commits。
4. 运行人类对齐循环，直到事实、术语、真实目标、范围、成功标准、关键行为、隐含模糊点和设计决策足够稳定。
5. 对真实设计分叉提出 `2-3` 个互斥方案、取舍和推荐项；把推荐设计按复杂度分段展示并获得确认。
6. 确认后写入或更新 spec artifact，只保留长期设计信息；未确认时不要用 artifact 代替对齐。
7. 自检 spec；如果不 ready，停在 `Open Questions` 和下一个高价值问题。
8. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后请用户 review 写好的 spec；不要自动进入 `to-plan`。

## Alignment Contract

`to-spec` 的首要交付物是共享理解，不是文件。spec artifact 只是把已经对齐的设计结论长期留存。

- 不把模板填充当作澄清；先确认“为什么要做、为谁做、什么算成功、什么不做、哪些行为必须被保护”。
- 不为了显得有进展而把未决问题写成完整 spec；阻塞问题继续问，非阻塞问题进入 `Open Questions`。
- 不把用户初始表述直接规格化为结论；要主动寻找隐藏前提、反例、边界和真正的设计分叉。
- 对话还在 brainstorm 时，输出当前理解、候选方向和下一个最高价值问题；只有用户要求或确认写入时才创建 / 更新 artifact。
- 复杂设计必须先展示设计摘要并获得确认。简单、机械的现有 spec 更新可以把确认视为用户的明确修改请求，但写完后仍需 review gate。

对齐门禁：

1. Context Gate：仓库事实、历史 artifact 和用户目标没有明显未解释冲突。
2. Intent Gate：problem、outcome、audience、success criteria 和非目标足够清楚。
3. Option Gate：真实分叉已用 `2-3` 个互斥方案比较，并给出推荐项。
4. Design Gate：推荐设计的 scope、关键行为、边界场景、契约 / 数据影响和风险已经展示并被用户接受，或未接受部分已回到澄清循环。
5. Artifact Gate：只有通过 Design Gate，或用户明确要求记录一个仍带 blocking questions 的 draft，才写入 spec。
6. Review Gate：写入后请用户 review spec；用户要求修改时更新 artifact 并重新自检 / validate。

## Clarification Loop

### 1. Ground Facts First

先建立工作视图，写作时再决定放入哪个 section：

- `Confirmed Facts`：来自代码、docs、schema、日志、已确认讨论或现有 artifact。
- `Unknowns`：仓库无法确认、但会影响边界、行为、验证或计划的问题。
- `Conflicts`：用户描述、docs、代码或历史决策互相矛盾的地方。
- `Terms`：容易混用、过载或需要 canonical term 的领域词。

规则：

- 能从仓库确认的事实不要问用户。
- 用户陈述和代码 / docs 不一致时，直接指出冲突来源，并要求确认哪个口径为准。
- 不猜测关键协议、数据口径、外部契约或业务行为；缺口用 `[NEEDS CLARIFICATION: ...]` 标出。
- 如果任务大到包含多个独立子系统，先要求拆分 spec；不要在一个 spec 中继续细化全部细节。

### 2. Root The Intent

像 brainstorm 一样追到设计根部，而不是只收集字段：

- 目的：用户到底想改变什么现状，为什么现在要做。
- 成功：什么可观察结果表示这件事做对了，什么结果表示失败。
- 受众：谁会读这个 spec，谁会使用 / 维护 / 验收结果。
- 约束：时间、兼容、数据、权限、外部契约、运维和组织边界。
- 非目标：哪些诱人的扩展现在不做，避免 scope creep。

如果用户只给了解法，反问它要解决的问题；如果用户只给了问题，追问可接受的结果和边界；如果两者都有，检查它们是否匹配。

### 3. Tighten Language

- 用户使用模糊词时，提出 precise canonical term，并说明候选含义。
- 术语冲突会影响理解或后续维护时，必须澄清；稳定后写入 `Context`，必要时新增 `Glossary`。
- 不把术语写成实现细节；只记录领域专家、维护者或后续规划者需要共享的语言。

### 4. Ask One High-Value Question

只问会改变方案、边界、验证方式或后续 plan 的问题。一次只问一个，等待反馈后再继续。

问题必须包含：

- 已确认事实。
- 当前歧义或冲突。
- 2-3 个互斥候选解释或选择。
- 推荐项。
- 影响面。

如果需要让用户在选项中决策，且 `functions.request_user_input` 可用并且当前 runtime 允许调用，就调用它。否则只问一个简洁的纯文本问题。

不要提供明显无效或只是凑数的选项。无法形成高质量选项时，先继续只读探索；探索后仍无法形成选项，再问一个开放但具体的问题。

### 5. Pressure-Test With Scenarios

用具体场景检验概念边界和需求行为：

- 正常路径：目标用户或系统如何成功完成关键行为。
- 边界路径：权限、状态、时间、数据缺失、兼容或外部契约如何影响行为。
- 反例路径：明确哪些行为不应该发生。

这些场景用于澄清和保护行为，最终可沉淀为 `Acceptance Scenarios`。不要把 mock、私有方法、调用顺序或文件路径写成场景重点。

### 6. Pressure Pass Before Convergence

进入方案收敛前，必须主动发掘用户未显式说出、但会影响 scope、行为、契约、验证或计划拆分的隐含问题。不要只处理用户已经意识到的歧义。

至少扫一遍：

- 术语是否过载或缺少 canonical term。
- scope 是否有隐藏边界、未声明的 out-of-scope 或过大子系统。
- actor / owner / reader 是否漏掉。
- 状态生命周期、数据口径、权限、时间窗口或幂等边界是否完整。
- 外部契约、兼容 / 迁移、安全 / 隐私、运维或回滚是否可能改变设计。
- failure path、反例路径和 acceptance scenarios 是否足以暴露模糊点。

把发现的问题分类处理：

- repo 可确认：继续只读探索，不问用户。
- blocking：一次问一个高价值问题。
- non-blocking：写入 `Open Questions`，标明影响。
- low-value：明确不展开，不阻塞收敛。

### 7. Converge Decisions

对真实设计分叉给出 2-3 个互斥方案、取舍和推荐项。先展示推荐项和理由，再展示其他可行路径，不要只给一个看似确定的答案。

设计展示按复杂度缩放：

- 简单事项：一个简洁设计摘要即可。
- 中等事项：分段展示 problem / outcome、scope、关键行为、acceptance scenarios、decisions、risks。
- 复杂事项：每个主要 section 后询问是否符合预期；用户不同意时回到对应事实、术语、场景或方案分支。

方案稳定并通过 Design Gate 后，写入 `Decisions`：

- `Decision`：最终选择。
- `Why`：为什么适合当前目标和约束。
- `Alternatives`：被放弃方案和原因。

没有通过 Design Gate 时，不写最终 spec；只输出当前设计摘要、剩余问题和下一个最高价值问题。

## Writing Rules

- spec 是长期设计真相源，不是 PRD、实现计划、task 列表或命令清单。
- 写 artifact 是对齐后的记录动作，不是澄清的替代动作。
- spec 阶段禁止写 implementation details、文件级修改步骤、私有 helper、具体函数拆分、测试 mock 形状或执行命令。
- requirements 必须可测试、无歧义；做不到时使用 `[NEEDS CLARIFICATION: ...]`，不要用模糊句子掩盖缺口。
- acceptance scenarios 必须保护用户可见行为、业务不变量、系统边界或外部契约。
- 保持高效扼要；只写会影响长期理解、计划拆分、行为验证或维护决策的信息。
- 不强制所有 creative work 都走 spec，不强制自动 commit，不强制立刻进入 `to-plan`。

## 推荐关系

`to-spec` 遇到非 spec 职责时只做推荐，不强制跳转：

- spec 已 ready，需要拆实施路径、阶段、任务和验证证据：推荐 `to-plan`。
- 讨论中出现尚不进入实施的问题、线索或独立 slice：推荐 `to-issue`。
- 需要定位 bug、复现异常或分析 root cause：推荐 `to-debug`。
- 需要查询运行环境、日志、数据库、缓存、Metrics、Dashboard、告警或部署事实：推荐项目级 `to-infra`。
- 需要设计测试策略、BDD 场景、测试 ROI 或验收证据类型：推荐 `to-test`。
- 需要人类 sign-off、验收轮次或反馈处理：推荐 `to-acceptance`。
- 设计问题暂时无法推进且需要恢复条件：推荐 `to-backlog`。

## Spec Template

模板是最小充分结构。只填有价值内容；不需要为了完整感保留空 section。

```markdown
---
id: <spec-id>
artifact_type: spec
status: draft
plans: []
---

# <Spec Title>

最后更新：<YYYY-MM-DD>

## Intent

- Problem: <要解决的问题>
- Outcome: <期望终态 / 用户可感知结果>
- Audience: <主要读者，如实现 Agent、维护者、产品决策者>

## Context

- Confirmed Facts:
  - <来自代码、docs、日志或已确认口径的事实>
- Constraints:
  - <技术、业务、流程、兼容或环境限制>
- Source Notes:
  - <可选：关键参考文档或证据>

## Scope

### In Scope

- <本 spec 明确覆盖什么>

### Out of Scope

- <明确不做什么，防止 scope creep>

## Acceptance Scenarios

1. <保护用户可感知行为、业务不变量或外部契约的场景>
   - Given <初始状态>
   - When <动作>
   - Then <期望结果>

## Requirements

- R1: <可测试、无歧义的要求>
- R2: <可测试、无歧义的要求>
- R?: [NEEDS CLARIFICATION: <具体缺口>]

## Decisions

- Decision: <已选方向>
  - Why: <选择理由>
  - Alternatives: <被放弃方案和原因>

## Interface / Data Notes

仅在涉及契约、数据模型、状态机或跨模块边界时填写。

- Interface: <稳定调用 / 文档契约>
- Data: <关键实体、字段、状态，不写实现细节>
- Ownership: <模块或边界归属>

## Verification Intent

- Must Protect:
  - <P0 / P1 行为或关键不变量>
- Suggested Evidence:
  - <后续 plan / task 应提供的验证证据类型>

## Open Questions

- <不阻塞 / 阻塞后续 plan 的问题，标明影响>

## Plan Handoff

- Ready for `to-plan`: yes / no
- Blocking Questions: <none 或阻塞项>
- Planning Notes:
  - <进入 plan 前必须注意的边界、顺序或风险，不写实现步骤>
```

## Template Extension

模板不足以承载关键长期信息时，可以新增 section，但要谨慎。新增 section 必须满足至少一个条件：会改变方案、边界、验证方式或计划顺序；放入现有 section 会明显降低可读性；具有长期设计价值而不是过程记录。

常见可选 section：

- `Glossary`：领域术语容易混用时。
- `Compatibility / Migration`：涉及旧行为兼容、数据迁移或协议演进时。
- `Security / Privacy`：涉及权限、敏感数据、审计或合规时。
- `Operational Notes`：涉及部署、监控、告警、回滚或 SLO 时。
- `External Contracts`：涉及第三方 API、WS、文件格式或平台协议时。
- `Risks`：存在明确高影响风险，但尚不能完全消化进 requirements 时。

避免新增：

- 空的 `Security` / `Performance` / `Rollout` 等占位 section。
- 已能放入 `Constraints`、`Decisions`、`Verification Intent` 的重复内容。
- 实现步骤、task 列表、命令清单；这些进入 `to-plan` 或 `to-task`。

## Self-Review

写完后优先交给 fresh 子代理检查。子代理只接收 spec 路径、本自检清单和必要背景；不要传入写作者自己的结论、辩护或预期答案。

- Placeholder：是否还有无意义的 `TBD`、`TODO`、空 section 或未解释占位。
- Consistency：Intent、Scope、Requirements、Decisions、Plan Handoff 是否互相矛盾。
- Scope：是否已经大到需要拆成多个 spec。
- Language：是否存在模糊、过载或未定义的关键术语。
- Requirements：每条是否可测试、无歧义。
- Scenarios：是否保护行为或关键不变量，而不是实现细节。
- Leakage：是否提前写入 implementation details、task、命令或文件级步骤。
- Handoff：`Ready for to-plan` 是否与 `Open Questions` 一致。

能直接修的就修；涉及设计取舍或事实缺口时，不猜测，回到澄清循环。

## User Review Gate

写入或更新 spec 后，必须请用户 review artifact，再推荐后续 `to-plan`。推荐表述保持简洁：

```text
Spec 已写入 `<path>`。请 review 设计口径；如果需要调整，我会更新 spec 并重新自检 / validate。确认后再进入 `to-plan`。
```

如果用户要求修改，更新 spec、重新 Self-Review、重新运行 `validate-flow`。只有用户确认或明确要求继续时，才推荐进入 `to-plan`。

## Plan Handoff Gate

`Ready for to-plan` 表示 `to-plan` 只需要拆实施路径、阶段、任务和验证证据，不需要替 spec 决定“到底要什么”。只有满足下面条件时，才把 spec 标记为可进入 `to-plan`：

- Intent 稳定：问题、期望结果和主要读者明确。
- Scope 稳定：`In Scope` / `Out of Scope` 足以支持拆阶段。
- Pressure pass 已完成：发现的隐含问题已被确认、降级为 non-blocking、记录为 blocking，或明确判断为 low-value。
- Design Gate 已通过：关键设计结论已经展示并被接受，或用户明确要求记录为仍需确认的 draft。
- Blocking questions 清零：没有会影响架构方向、业务行为、数据口径、外部契约、验收标准或计划拆分的 `[NEEDS CLARIFICATION: ...]`。
- Requirements 可测试、无歧义。
- Acceptance scenarios 能保护关键成功路径、核心边界和不变量。
- spec 没有 implementation details。

不满足时，`Plan Handoff` 写 `Ready for to-plan: no`，并停在一个下一个最高价值问题上。

## References

- https://github.com/ninehills/mattpocock-skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
- https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
