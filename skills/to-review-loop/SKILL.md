---
name: to-review-loop
description: 'Run a Sky Flow review-fix-rereview loop only when the user explicitly asks for to-review-loop or review-fix-rereview; review, triage, fix blocking or high-ROI issues, consolidate, rereview, and require final consolidation plus a dual-model verifier gate before clean closure.'
---

# to-review-loop

`to-review-loop` 是 Sky Flow 内的 review-fix-rereview 循环。它在已确认 scope 内协调 review、定向修复、收敛、验证和复审，用于清掉 blocking 或高 ROI 问题。

它只在用户明确要求 `to-review-loop`、review-fix-rereview，或明确要求“review、修复、再复审直到阻塞项清零”时使用。普通 review、blocking finding、handoff、acceptance 或 commit 前检查都不自动升级为这个循环；这些场景只输出 findings 和后续动作。

`to-review-loop` 不创建 acceptance 文档，也不等待人工审核来决定每个 review finding 是否修复。循环内由 Agent 基于真实 bug 风险和修复成本自行 triage；clean closure 前必须触发最终 `to-consolidation`，然后进入 verifier gate，用至少两个不同模型 verifier 验收 selected findings 是否 cleared。

## Quick Path

1. 确认输入范围：
   - Sky Flow spec：读取 scope、requirements、Execution Constraints、Progress、verification intent 和必要的 issue / acceptance。
   - Pending diff：检查当前 changed files 和用户指令；如果混入多个无关改动，先要求缩小 scope 或按逻辑范围拆循环。
2. 先做 review pass，优先使用 `to-review`，聚焦 correctness、spec alignment、行为回归、安全 / 可靠性、测试缺口和维护风险；大 diff、跨模块或高风险 scope 使用 `to-review` 的 multi-review / synthesize lane。
3. review 结果必须足够 final 才进入修复；如果 review 明确是 interim、未完成或等待 deep pass，停止并报告等待状态。
4. 把 findings 分为 blocking、高 ROI non-blocking、deferred；分类时必须回答两个 ROI 问题：这个问题在实际场景下会出 bug 吗？修它的代价是什么？
5. 修复前逐条用当前代码、artifact 或 diff 核验 finding；review 输出是证据，不是自动修改指令。
6. 只修已确认 scope 内、ROI 清楚的问题；同文件或同验证路径的小修可以合并成一个 fix batch。
7. 修复 batch 后，对 changed scope 触发 `to-consolidation`，清理补丁式实现、临时代码、重复逻辑或 fan-in 残留。
8. 运行最小相关验证；如果修改 Sky Flow artifact，运行 `validate-flow`。
9. 进入 Final Consolidation Gate：clean closure 前必须再次触发一次 `to-consolidation`，即使本轮没有修复、前面已经 consolidation 过，或当前只需要确认 `no file changes`。Scope 是当前 loop scope / pending diff / selected findings touched files，不允许顺手清理无关历史问题。
10. 如果 Final Consolidation Gate 修改了文件，重新运行相关最小验证，再进入最终 review；否则直接进入最终 review。最终 review 仍优先使用 `to-review`，并只验证当前 loop scope 和 selected findings。
11. 进入 verifier gate：至少两个独立 verifier 使用不同模型确认 selected findings 是否 cleared；优先不同供应商，单供应商时用最新模型和次新模型。
12. 重复直到 blocking findings 清零、Final Consolidation Gate 已完成且 verifier gate 通过，或 scope、design、data、contract、ownership ambiguity 阻止安全修复。

## Finding Policy

blocking finding 包括：

- 会破坏 spec outcome、requirement 或 acceptance scenario。
- 违反 spec requirement 或 acceptance scenario。
- 回归用户可见行为。
- 造成数据丢失、安全风险或权限 / 隐私边界问题。
- 让必需验证失败。
- 让当前产物不适合 handoff、acceptance 或 commit。

高 ROI 修复通常是：

- 有直接证据的小型 correctness fix。
- 简单且局部的 guard。
- 保护 P0 / P1 行为或已声明 acceptance scenario 的测试 / 验证补强。
- 清理由当前 diff 引入的临时代码、debug 残留或重复实现。
- 解释非显而易见不变量、约束或取舍的必要注释。

Agent triage 每条 finding 时必须显式判断：

1. 这个问题在实际场景下会出 bug 吗？
2. 修它的代价是什么？

真实触发概率低且修复成本高的问题默认 defer；触发路径明确、影响高、修复局部的问题优先进入当前 fix batch。

遇到下面情况应 defer 或 stop，而不是直接修：

- 修复会超出 spec 或用户请求 scope。
- 存在多个合理设计，且选择会影响后续维护。
- 需要改变公共契约、数据模型、发布策略或 ownership 边界，但上游没有确认。
- 为低概率风险引入复杂 fallback、抽象、状态或兼容逻辑，且缺少具体证据。
- finding 不能从仓库事实或已提供 artifact 中确认。

未修复的 blocking finding 不能报告为 cleared。如果正确动作需要人类或上游设计输入，停止循环并明确写出 blocker。

## Sky Flow Coordination

- review pass 使用 `to-review`；`to-review-loop` 不另造一套 review 方法。
- 非平凡或高风险 scope 优先复用 `to-review` 的 multi-review / synthesize 输出；Agent 在 loop 内自行 triage，不写 acceptance 文档。
- 修复后需要清理 diff 熵值时使用 `to-consolidation`。
- clean closure 前必须有一次最终 `to-consolidation`。这次 final pass 不能被 batch-level consolidation、review、validate-flow 或 verifier gate 替代；如果它发现并修改内容，必须重新验证和复审后才能关闭 loop。
- 只有修改 Sky Flow artifact 时才用 `validate-flow`；它不替代代码 review 或 consolidation。
- 如果执行暴露拆解、owner 或并行方式不合适，由 `to-implement` 动态调整 runtime；这些变化不写入 artifact。
- 如果 requirements、外部契约、数据语义、acceptance 行为或设计意图需要变化，回到 `to-spec`。
- 除非当前 loop scope 明确包含 artifact maintenance，否则不直接更新 spec Progress；只向调用方报告建议写回。

## Verifier Gate

Verifier gate 是 `to-review-loop` 的修后验收环节。它和普通 review 不同：目标不是重新寻找全部问题，而是确认 selected findings 已修复、修复没有引入相关回归、验证证据足够支撑 closure。

规则：

- 至少两个 verifier，且必须使用不同模型。优先不同供应商；当前只有一个供应商时，用该供应商最新模型和次新模型。
- fixer 和 verifier 必须分离；同一个 Agent / 模型刚完成修复时，不能单独判定自己 cleared。
- verifier 输入包含 selected finding id、原始证据、修复 diff、已跑验证和 non-goals；不要给 verifier 全量聊天历史或让它扩大 scope。
- 两个 verifier 都确认 cleared，且没有证据冲突，finding 才算 cleared。
- 任一 verifier 判定 not-cleared 或两者分歧时，finding 进入下一轮；如果分歧需要 scope / design / contract 决策，停止并报告 blocker。
- 如果运行时无法选择两个不同模型，必须输出 `dual_verifier: unavailable` 和原因；不能把 loop 报告成 clean closure。

## Loop Discipline

- 所有编辑必须落在确认的 allowed write scope 内，并遵守 no-touch scope。
- 不 revert 无关的用户或其他 Agent 改动；基于当前 worktree 状态继续。
- 不为了满足 review 建议做大范围 refactor、格式化 sweep、依赖变更或命令 / 环境变更。
- 优先一到两个聚焦 fix batch；如果循环开始暴露无关工作，停止并建议新 issue 或独立 spec。
- 复审必须检查修复后的 diff，而不是只确认文件发生过变化。
- clean loop 的定义是：Final Consolidation Gate 已完成且没有未处理收敛项，最新 final review 对 scoped work 没有 blocking findings，且 verifier gate 对 selected findings 通过；non-blocking suggestion 可以保留，但必须报告清楚。

## Stop Conditions

成功停止条件：

- Final Consolidation Gate 已触发且没有未处理收敛项，最新 final review 对当前 scope 没有 blocking findings，且两个不同模型 verifier 确认 selected findings cleared。

带 blocker 停止条件：

- 剩余 blocking issue 需要 scope、design、contract、data、ownership 或产品确认。
- 修复需要触碰 allowed scope 之外的文件，或违反 no-touch scope。
- 验证失败且存在多个合理修复路径。
- review 无法达到 final-enough，且缺失 review 可能影响 blocking finding。
- 无法完成双 verifier gate，且缺失 verifier 会影响 closure 可信度。
- worktree 混入无关改动，导致无法可靠做 scoped review。

无文件变更停止条件：

- 所有 findings 都无法确认、已修复、超出 scope，或对当前 loop ROI 太低。需要明确写 `no file changes` 和停止原因。

## Output

最终输出保持短而有证据：

- Scope source：spec / pending diff / user-selected files。
- Review rounds：轮次数和最新 review 状态。
- Verifier gate：verifier 数量、模型、每个 selected finding 的 cleared / not-cleared / disputed 状态；无法双 verifier 时写 `dual_verifier: unavailable`。
- Fixed issues：实际修复的 blocking 和高 ROI findings。
- Remaining blockers：severity、证据、为什么未修和所需上游动作。
- Deferred items：non-blocking suggestion 或低 ROI finding。
- Verification：执行过的命令或检查；跳过验证时写原因。
- Consolidation：batch-level `to-consolidation` 和 Final Consolidation Gate 是否执行、是否发现或修改内容；如果没有文件变更，也要写明 final pass 的 no-op / no file changes 结论。
- Next action：继续 implementation、稍后 rerun review、更新 spec，或交给人类决策。

如果没有文件变更，包含 `no file changes` 和停止原因。

## Boundaries

- 不替代 `to-review`；它围绕 review 结果协调循环。
- 不创建或更新 acceptance 文档；Review triage 和 closure 在 loop 内由 Agent 自行处理，只有 scope / design / contract / risk 需要人类决策时才停止报告。
- 不作为主实现流程；执行 ready spec 使用 `to-implement`。
- 不充当设计裁决者；scope、行为、契约或数据语义变化回 `to-spec`。
- 不处理 commit；stage 和 commit 使用 `to-commit`。
- 不写死项目路径、命令、部署规则、业务术语或团队流程假设。
