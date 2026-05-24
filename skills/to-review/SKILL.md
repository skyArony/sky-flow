---
name: to-review
description: 'Review code diffs and Sky Flow artifacts such as spec, plan, task, acceptance, backlog, or handoff outputs. Use to find bugs, regression risks, missing verification, scope drift, artifact boundary problems, and implementation/design alignment issues. Default to read-only review; delegate to internal review-by-somestay or review-by-sanyuan profiles only when depth requires it.'
---

# to-review

`to-review` 是 Sky Flow 内的通用 review 入口。它检查实现风险、行为回归、设计对齐、测试缺口、安全 / 可靠性问题，以及 Sky Flow artifact 的边界和输出质量。默认只读，不修代码、不改 artifact。

它不替代：

- `validate-flow`：结构化校验 artifact schema、状态一致性和相邻绑定。
- `to-consolidation`：收敛 pending diff 中的临时代码、重复逻辑和 fan-in 残留。
- `to-implement`：执行 plan / task、维护状态和调度 fan-in。

## Quick Path

1. 确认 review 范围：默认审当前 pending diff；用户指定文件、目录、artifact、commit range 或 task 输出时，以指定范围为准。
2. 整理 `review_context`：需求 / artifact 来源、预期行为、已知偏离、已跑验证、非目标、base / head 或输入输出路径。
3. 选择 `review_focus`：`spec-compliance`、`code-quality` 或 `general`；artifact 输出优先看 scope、边界、依赖、验收和验证证据。
4. 选择深度：小范围低风险走 `fast`；非平凡 diff 或 artifact 输出走 `medium`；命中共享边界或系统性风险才走 `deep`。
5. 只有进入 `medium` 时读取 `reviewers/review-by-somestay/SKILL.md`。
6. 只有 `medium` 明确建议深挖时读取 `reviewers/review-by-sanyuan/SKILL.md`。
7. 输出 findings-first 报告；无问题时明确写 `no findings`、检查范围和未验证点。

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

## Review Heuristics

- Findings 必须按严重度排序，先问题后摘要。
- 每条 finding 必须有文件 / 行或 artifact section 定位、触发场景、影响面、推荐修复和 confidence。
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

输出应保持 findings-first。建议结构：

```text
Findings
1. [P1] <title> - <file:line 或 artifact section>
   Evidence: <触发路径 / 证据>
   Impact: <影响面>
   Recommendation: <小而具体的修复>
   Confidence: high|medium|low

Checked Areas
- <已检查范围>

Unverified Areas
- <未验证或证据不足范围>

Residual Risks
- <低 ROI 或需后续确认风险>

Outcome
- review_depth: fast|medium|deep
- review_focus: spec-compliance|code-quality|general
- deep_review_state: not-requested|recommended-but-disabled|in-progress|completed
- suggested_outcome: pass|no-change|blocked|failed|scope-violation
- no file changes
```

无 findings 时第一行写 `No findings.`，并列出 checked / unverified / residual risk。不要把 “看起来没问题” 当作替代证据。
