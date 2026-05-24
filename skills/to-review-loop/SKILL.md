---
name: to-review-loop
description: 'Run a Sky Flow review-fix-rereview loop only when the user explicitly asks for to-review-loop or review-fix-rereview; review, fix blocking or high-ROI issues, consolidate, and rereview until blocking issues are cleared or scope/design ambiguity requires upstream clarification.'
---

# to-review-loop

`to-review-loop` 是 Sky Flow 内的 review-fix-rereview 循环。它在已确认 scope 内协调 review、定向修复、收敛、验证和复审，用于清掉 blocking 或高 ROI 问题。

它只在用户明确要求 `to-review-loop`、review-fix-rereview，或明确要求“review、修复、再复审直到阻塞项清零”时使用。普通 review、blocking finding、handoff、acceptance 或 commit 前检查都不自动升级为这个循环；这些场景只输出 findings 和后续动作。

## Quick Path

1. 确认输入范围：
   - Sky Flow plan / task：读取 artifact、allowed write scope、no-touch scope、verification intent 和必要的关联 spec / issue。
   - Pending diff：检查当前 changed files 和用户指令；如果混入多个无关改动，先要求缩小 scope 或按逻辑范围拆循环。
2. 先做 review pass，优先使用 `to-review`，聚焦 correctness、spec alignment、行为回归、安全 / 可靠性、测试缺口和维护风险。
3. review 结果必须足够 final 才进入修复；如果 review 明确是 interim、未完成或等待 deep pass，停止并报告等待状态。
4. 把 findings 分为 blocking、高 ROI non-blocking、deferred。
5. 修复前逐条用当前代码、artifact 或 diff 核验 finding；review 输出是证据，不是自动修改指令。
6. 只修已确认 scope 内、ROI 清楚的问题；同文件或同验证路径的小修可以合并成一个 fix batch。
7. 修复 batch 后，对 changed scope 触发 `to-consolidation`，清理补丁式实现、临时代码、重复逻辑或 fan-in 残留。
8. 运行最小相关验证；如果修改 Sky Flow artifact，运行 `validate-flow`。
9. 再次 review，仍优先使用 `to-review`。
10. 重复直到 blocking findings 清零，或 scope、design、data、contract、ownership ambiguity 阻止安全修复。

## Finding Policy

blocking finding 包括：

- 会破坏 plan / task outcome。
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

遇到下面情况应 defer 或 stop，而不是直接修：

- 修复会超出 plan / task 或用户请求 scope。
- 存在多个合理设计，且选择会影响后续维护。
- 需要改变公共契约、数据模型、发布策略或 ownership 边界，但上游没有确认。
- 为低概率风险引入复杂 fallback、抽象、状态或兼容逻辑，且缺少具体证据。
- finding 不能从仓库事实或已提供 artifact 中确认。

未修复的 blocking finding 不能报告为 cleared。如果正确动作需要人类或上游设计输入，停止循环并明确写出 blocker。

## Sky Flow Coordination

- review pass 使用 `to-review`；`to-review-loop` 不另造一套 review 方法。
- 修复后需要清理 diff 熵值时使用 `to-consolidation`。
- 只有修改 Sky Flow artifact 时才用 `validate-flow`；它不替代代码 review 或 consolidation。
- 如果执行暴露 task 缺失、task topology 错误或实现策略变化，回到 `to-task` 或 `to-plan`。
- 如果 requirements、外部契约、数据语义、acceptance 行为或设计意图需要变化，回到 `to-spec`。
- 除非当前 loop scope 明确包含 artifact maintenance，否则不直接更新 plan / task status；只向调用方报告建议状态更新。

## Loop Discipline

- 所有编辑必须落在确认的 allowed write scope 内，并遵守 no-touch scope。
- 不 revert 无关的用户或其他 Agent 改动；基于当前 worktree 状态继续。
- 不为了满足 review 建议做大范围 refactor、格式化 sweep、依赖变更或命令 / 环境变更。
- 优先一到两个聚焦 fix batch；如果循环开始暴露无关工作，停止并建议新 plan / task。
- 复审必须检查修复后的 diff，而不是只确认文件发生过变化。
- clean loop 的定义是：最新 final review 对 scoped work 没有 blocking findings；non-blocking suggestion 可以保留，但必须报告清楚。

## Stop Conditions

成功停止条件：

- 最新 final review 对当前 scope 没有 blocking findings。

带 blocker 停止条件：

- 剩余 blocking issue 需要 scope、design、contract、data、ownership 或产品确认。
- 修复需要触碰 allowed scope 之外的文件，或违反 no-touch scope。
- 验证失败且存在多个合理修复路径。
- review 无法达到 final-enough，且缺失 review 可能影响 blocking finding。
- worktree 混入无关改动，导致无法可靠做 scoped review。

无文件变更停止条件：

- 所有 findings 都无法确认、已修复、超出 scope，或对当前 loop ROI 太低。需要明确写 `no file changes` 和停止原因。

## Output

最终输出保持短而有证据：

- Scope source：plan / task / pending diff / user-selected files。
- Review rounds：轮次数和最新 review 状态。
- Fixed issues：实际修复的 blocking 和高 ROI findings。
- Remaining blockers：severity、证据、为什么未修和所需上游动作。
- Deferred items：non-blocking suggestion 或低 ROI finding。
- Verification：执行过的命令或检查；跳过验证时写原因。
- Consolidation：`to-consolidation` 是否执行、是否发现或修改内容。
- Next action：继续 implementation、稍后 rerun review、更新 spec / plan / task，或交给人类决策。

如果没有文件变更，包含 `no file changes` 和停止原因。

## Boundaries

- 不替代 `to-review`；它围绕 review 结果协调循环。
- 不作为主实现流程；执行 plan / task 使用 `to-implement`。
- 不充当设计裁决者；上游 scope 或行为变化回 `to-spec`、`to-plan` 或 `to-task`。
- 不处理 commit；stage 和 commit 使用 `to-commit`。
- 不写死项目路径、命令、部署规则、业务术语或团队流程假设。
