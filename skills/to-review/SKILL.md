---
name: to-review
description: 'Review code diffs and Sky Flow artifacts such as spec, plan, task, acceptance, backlog, or handoff outputs. Use to find bugs, regression risks, missing verification, scope drift, artifact boundary problems, and implementation/design alignment issues. Default to read-only review; delegate to internal review-by-somestay or review-by-sanyuan profiles only when depth requires it, and synthesize multi-review findings when risk justifies independent reviewers.'
---

# to-review

`to-review` 是 Sky Flow 内的通用 review 入口。它检查实现风险、行为回归、设计对齐、测试缺口、安全 / 可靠性问题，以及 Sky Flow artifact 的边界和输出质量。默认只读，不修代码、不改 artifact。高风险或大范围变更可以进入 multi-review lane：多个 reviewer 独立发现问题，再 synthesize 成一份可人工 triage 的清单。

它不替代：

- `validate-flow`：结构化校验 artifact schema、状态一致性和相邻绑定。
- `to-consolidation`：收敛 pending diff 中的临时代码、重复逻辑和 fan-in 残留。
- `to-implement`：执行 plan / task、维护状态和调度 fan-in。

## Quick Path

1. 确认 review 范围：默认审当前 pending diff；用户指定文件、目录、artifact、commit range 或 task 输出时，以指定范围为准。
2. 整理 `review_context`：需求 / artifact 来源、预期行为、已知偏离、已跑验证、非目标、base / head 或输入输出路径。
3. 选择 `review_focus`：`spec-compliance`、`code-quality` 或 `general`；artifact 输出优先看 scope、边界、依赖、验收和验证证据。
4. 选择深度和 lane：小范围低风险走 `fast`；非平凡 diff 或 artifact 输出走 `medium`；命中共享边界或系统性风险才走 `deep`；大 diff、跨模块、高 blast radius 或用户要求多 Agent review 时进入 `multi-review` lane。
5. 单 reviewer lane 按深度加载对应 reviewer profile：`medium` 读取 `reviewers/review-by-somestay/SKILL.md`；只有 `medium` 明确建议深挖时读取 `reviewers/review-by-sanyuan/SKILL.md`。
6. `multi-review` lane 必须让 reviewer 独立产出 findings，再 synthesize 为一份排序清单；不要让后一个 reviewer 继承前一个 reviewer 的结论。
7. 如果目标是验证修复是否解决已选 review findings，进入 verifier stage；至少使用两个独立 verifier，模型必须不同。
8. 输出 findings-first 报告；无问题时明确写 `no findings`、检查范围和未验证点。

## Scope Rules

- Review scope 必须具体到文件、目录、artifact、commit range、task 输出或 pending diff；不要只写模糊摘要。
- 只能基于用户请求、artifact 内容、diff、commit message 和相邻代码推断意图。需求不明时标注 `intent inferred from diff/artifact`，不要把推断写成已确认事实。
- artifact review 可以读取相邻 spec / plan / task / acceptance 作为背景，但不直接修改它们。
- 发现 scope drift、write scope 越界、no-touch 违规、状态和产物不匹配时，按 review finding 报告；结构字段校验交给 `validate-flow`。
- 默认只读。只有父级 workflow 明确切到修复环节，才可以把 findings 交给实现或 `to-review-loop`。

## Depth Routing

### fast

用于小 diff、单文件、低风险 artifact 文案或明显局部变更。

- 当前会话本地 review 即可。
- 仍然按 findings-first 输出。
- 不默认加载内部 reviewer profile。

### medium

默认主力路径，用于非平凡 diff、实现完成后的阶段 review、task 输出 review、artifact 边界 review 或验证缺口检查。

- 加载 `reviewers/review-by-somestay/SKILL.md`。
- 优先高信号、低误报、具体修复建议。
- 必须判断是否需要升级 `deep`，并说明理由。

### deep

只在 medium 发现高价值线索或不确定性时进入。

典型触发：

- 跨模块、共享契约、公共 schema、共享状态或状态机风险。
- 安全、并发、事务、权限、数据迁移、回滚或删除风险。
- plan / task / spec / acceptance 之间存在可能影响执行或验收的边界错配。
- medium findings 分布在多个区域，或高影响 finding 需要系统级证据。

`deep` 不是重做 medium；它只验证线索、深挖系统性风险并纠偏误报。

## Multi-Review And Synthesis

`multi-review` 不是 `deep` 的替代品。`deep` 深挖系统性风险；`multi-review` 用独立 reviewer 扩大覆盖面并交叉验证发现。只有风险或范围值得付出额外成本时才使用。

触发倾向：

- 单次 diff 横跨多个模块、应用、数据库 schema、状态机、权限边界或外部契约。
- 变更影响 P0 / P1 行为、资金 / 隐私 / 权限 / 数据完整性、部署或迁移路径。
- 多 Agent fan-in 后需要独立视角检查整合风险。
- 用户要求多模型 / 多 Agent review，或 review 结果将进入人工 triage / acceptance。

执行规则：

- 每个 reviewer 必须拿到相同的 review scope、context、known deviations、已跑验证和非目标。
- reviewer 之间尽量使用不同模型或不同 reviewer profile；如果运行时只能使用同一模型，也必须保持独立上下文，并在输出中标注 `model_diversity: limited`。
- reviewer 原始报告可存在临时上下文、子代理输出或调用方 artifact 中；`to-review` 的最终输出必须包含 synthesize 后的清单。
- synthesize 只合并语义相同的 finding，不把不同触发路径粗暴归并。多个 reviewer 命中同一真实问题时，提高 `reviewer_agreement` 和 confidence。
- 单 reviewer 独有 finding 不能因为没有共识就丢弃；必须根据真实触发路径、影响和修复成本排序。
- 合成清单是 decision input，不是自动修复指令；进入修复前由调用方、`to-review-loop` 或当前对话直接 triage，不写 `acceptance` artifact。

Synthesis 排序优先级：

1. 已有真实触发路径、用户可见影响或数据 / 权限 / 安全影响的问题。
2. 多 reviewer 独立命中的高影响问题。
3. 修复成本低且能保护 P0 / P1 行为的问题。
4. 证据不足但影响很高、需要补证据的问题。
5. 低概率、低影响或修复成本明显高于收益的问题。

## Verifier Stage

Verifier stage 用于验收已选 review findings 是否被修复，不用于发现新需求。典型入口是 review-fix-rereview、修复后复审或 review closure。

规则：

- 至少运行两个独立 verifier；二者必须使用不同模型。优先不同供应商；如果只有一个供应商，使用该供应商最新模型和次新模型。
- 如果运行时无法实际选择模型或派发第二 verifier，必须在输出中写明 `dual_verifier: unavailable`，不能宣称完成双 verifier 验收。
- verifier 只检查 selected findings、相关回归面、验证证据和修复后 diff；不要重新扩大 scope 成普通 review。
- 两个 verifier 都确认 cleared，且验证证据匹配，才把 finding 标为 `cleared`。
- verifier 意见不一致时，保留为 `disputed`，写清分歧、证据缺口和下一步；不要用多数投票掩盖真实不确定性。
- verifier 发现新的 blocking 问题时，作为新 finding 输出，但要标注 `found_during_verification`。

## Review Heuristics

- Findings 必须按严重度排序，先问题后摘要。
- 每条 finding 必须有文件 / 行或 artifact section 定位、触发场景、影响面、真实 bug 风险、修复成本、推荐修复和 confidence。
- 能说明真实触发路径和影响时才升为 `P0 / P1 / P2`；纯理论风险降级为 `P3 / Suggestion` 或放入 `residual_risks`。
- 修复建议优先小而明确：几行 guard、补验证、补注释、收窄 scope、修正 artifact 边界。不要为了低概率边界建议复杂状态机、兼容层或额外抽象。
- 对已声明的 `known_deviations` 先判断是否合理；不要直接当 bug。
- 不把日志措辞、mock 调用次数、私有 helper 路径等低价值细节当阻塞项，除非它们承载对外契约、安全或真实事故回归。

## Artifact Review Focus

审查 Sky Flow artifact 或执行输出时，重点看：

- spec 是否把目标、非目标、术语、外部契约和验收口径说清楚。
- plan 是否保持 goal / scope / milestones / progress / recovery 一致，不把实施细节塞进计划层。
- task 是否有清晰 allowed write scope、no-touch、依赖、owner 建议、验证意图和输出契约。
- acceptance 是否有可复核证据，不把未验证内容写成已通过。
- handoff / backlog 是否能恢复上下文，且没有替代原 artifact 的状态真相。
- 实现输出是否符合对应 artifact，不扩大 scope，不遗漏 P0 / P1 验证。

## 推荐关系

`to-review` 默认只读，不直接修复。发现问题后按归口推荐，不强制跳转：

- review 发现 artifact frontmatter、DAG、状态或相邻绑定问题：推荐 `validate-flow`。
- review 发现补丁式实现、临时代码、重复逻辑、debug 残留或 fan-in 半成品：推荐 `to-consolidation`。
- synthesize 后需要人类决定哪些 finding 值得修、哪些接受风险或延后：直接在对话或 review 报告中输出 triage 清单和两个 ROI 问题，不创建 `acceptance` artifact。
- review 发现 blocking 或高 ROI finding：只输出 finding、证据、影响和建议修复方向；不推荐、不自动进入 `to-review-loop`。`to-review-loop` 只能由用户显式触发。
- review 发现测试策略、BDD 场景、测试 ROI、stable seam 或替代验证不清：推荐 `to-test`。
- review 发现真实事故回归需要固化：推荐 `to-bdd-regression`。
- review 发现目标、scope、契约、数据口径或 requirements 需要变化：推荐 `to-spec`；执行策略或 task 拆分变化推荐 `to-plan` / `to-task`。

## Severity

- `P0`：已确认会破坏关键行为、数据安全、资金 / 权限 / 隐私、安全边界或阻断交付。
- `P1`：高概率或高影响回归，必须在当前轮修复或明确阻塞。
- `P2`：真实可触发问题，但影响局部或有合理缓解；建议当前轮修。
- `P3`：低概率、低影响或证据不足；记录但不阻塞。
- `Suggestion`：改进建议、测试补强或可维护性提升。
- `Nit`：细小一致性问题，不影响结果。

## Output Contract

输出应保持 findings-first。用户可见标题和字段 label 默认使用中文，必要术语、枚举值、模型名、finding id 和 mode 保留英文。字段 label 用 `**加粗**`，主要区块用二级标题，单个 finding 用三级标题。每个 finding 最前面必须放 `#### 决策核心`，用显眼的加粗问题句回答“这个问题在实际场景下会出 Bug 吗？”和“修它的代价是什么？”。单 reviewer 可以省略不适用字段；`multi-review` 或 verifier stage 必须使用扩展结构。

```markdown
## 待决策问题

### RV-001 [P1] <标题> - <file:line 或 artifact section>

#### 决策核心

> **这个问题在实际场景下会出 Bug 吗？** high|medium|low - <实际触发场景和判断依据>
>
> **修它的代价是什么？** low|medium|high - <预计修复范围 / 风险>

- **Reviewer 共识**：<1/3|2/3|3/3>（<reviewer ids>）
- **证据**：<触发路径 / 证据>
- **影响**：<影响面>
- **建议修复**：<小而具体的修复>
- **建议决策**：fix-now|ask-human-in-dialogue|needs-evidence|defer|reject-false-positive
- **信心**：high|medium|low
- **来源 finding**：<reviewer ids / finding ids>

## Verifier 结果

- **双 Verifier 状态**：complete|unavailable|not-applicable
- **Verifier 模型**：<model A>, <model B>
- **RV-001**：cleared|not-cleared|disputed|not-checked
- **证据**：<测试、命令、diff 检查或 artifact 证据>

## 已检查范围

- <已检查范围>

## 未验证范围

- <未验证或证据不足范围>

## 残余风险

- <低 ROI 或需后续确认风险>

## 结论

- **Review 深度**：fast|medium|deep
- **Review 模式**：single-review|multi-review|verifier
- **Review 重点**：spec-compliance|code-quality|general
- **Reviewer 数量**：<n>
- **模型多样性**：full|limited|unknown
- **Deep review 状态**：not-requested|recommended-but-disabled|in-progress|completed
- **建议结果**：pass|no-change|blocked|failed|scope-violation
- **文件改动**：no file changes
```

无 findings 时第一行写 `No findings.`，并用中文标题列出 `已检查范围`、`未验证范围`、`残余风险` 和 `结论`。不要把 “看起来没问题” 当作替代证据。
