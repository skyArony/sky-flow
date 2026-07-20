---
name: to-review-loop
description: 'Run a Sky Flow review-fix-rereview loop only when the user explicitly invokes $to-review-loop; triage and fix confirmed blocking or high-ROI issues, verify proportionately, and finish with an integrated rereview.'
---

# to-review-loop

`to-review-loop` 在已确认 scope 内执行 review、triage、定向修复、验证和复审，只清理 confirmed blocking 或高 ROI 问题。

仅当用户显式调用 `$to-review-loop` 时使用。普通 review、自然语言提到 review-fix-rereview 或出现 blocking finding 都不自动升级。

## Quick Path

1. 明确 source spec / goal、可选 source-linked active plan、pending diff 或用户指定范围，并保护无关 worktree 改动。plan 只提供实施决策与恢复上下文，不能覆盖 spec。
2. 完成首轮一体化 review；默认由当前 executor 同时检查设计 / spec 符合性和代码质量，只有用户明确要求或出现真实高风险证据缺口时才增加独立 reviewer。
3. 逐条核验 finding，回答“实际会不会出 Bug”和“修复代价”，分为 blocking、当前轮高 ROI、deferred / rejected。
4. 只修 scope 内且证据充分的问题；优先一到两个聚焦 batch。
5. 运行与改动风险匹配的最小验证；durable artifact 或 plan 结构 / 恢复边界变化时运行 `validate-flow`，plan body-only snapshot 遵循其批量时机。
6. 直接检查重复 / 临时代码、补丁感和明显 diff 熵值；只有用户同时显式调用 `$to-consolidation` 时才进入专项收敛流程。
7. 修复完成后做一次整合复审，同时给出设计 / spec 符合性与代码质量结论，避免为同一范围机械叠加重复 review。
8. 默认用定向测试和修复后 diff 完成 closure；只有用户明确要求、P0 证据冲突或真实高风险证据缺口时才增加一个独立 verifier。

## Triage Policy

优先修复：

- 破坏 spec outcome、requirement、acceptance scenario 或用户可见行为。
- 造成数据丢失、安全、资金、权限、隐私或可靠性问题。
- 让必要验证失败，或让当前产物不适合交付。
- 有直接证据且修复局部的 correctness guard、回归保护或当前 diff 引入的临时残留。

defer、reject 或 stop：

- finding 无法从代码、artifact、diff 或运行证据确认。
- 修复超出 scope，或需要改变公共契约、数据语义、产品口径、权限 / ownership 边界。
- 为低概率风险引入明显高成本的 fallback、状态、兼容逻辑或抽象。
- 多个合理方向在取证后仍需要人类拥有的决策。

review 输出是证据输入，不是自动修改指令。未修复的 blocking finding 不能标为 cleared。

## Consolidation And Verification

`to-consolidation` 不是每个 batch 或 clean closure 的固定 gate。当前循环直接报告收敛迹象；只有用户显式调用 `$to-consolidation` 时才使用专项收敛流程，典型迹象包括：

- 多 Agent / 多来源 fan-in 后需要统一实现。
- 当前 diff 出现重复逻辑、临时代码、debug 残留或互相矛盾的局部修复。
- 多轮 fix 使实现明显补丁化。
- 用户明确要求 consolidation。

Verifier 只检查 selected findings、相关回归面和修复证据：

- confirmed blocking / 高 ROI finding 被修改后，默认由当前 executor 运行定向验证并检查修复后 diff。
- 只有用户明确要求、P0 证据冲突或真实高风险证据缺口时才增加一个独立 verifier。
- 第二个模型或供应商只用于用户明确要求，或第一个独立 verifier 无法裁决的 P0 安全结论。
- 没有文件变化、没有 confirmed finding，或全部 finding 被证据否定 / defer 时，不运行 verifier；整合复审说明依据。
- fixer 不能在需要独立验证的情形下单独宣称自己 cleared。独立性不可用时如实报告，不伪造 closure。

## Loop Discipline

- 不 revert 无关用户改动，不为了 review 建议做无关重构、格式化 sweep 或依赖升级。
- 复审必须看修复后 diff 与行为证据，而不是只确认文件发生变化。
- scope 内 implementation strategy 可动态调整；任何 source spec 规范性边界变化回 `to-spec`。
- 循环开始扩散到无关工作时停止，建议新 issue 或独立 spec。
- 除非 scope 包含 artifact maintenance，否则只向调用方报告建议写回，不直接改 spec / plan Progress。报告必须区分 durable outcome / decision / blocker（spec）与当前 slice、局部 decision、resume / verification context（active plan），避免修复后 plan 过期。

## Stop Conditions

成功：最新整合复审无 blocking finding，selected findings 已按风险充分验证，且没有未处理的收敛迹象。

带 blocker：安全修复需要新的 scope / product / contract / data / permission / ownership 决策，验证存在无法裁决的冲突，或 worktree 无法可靠隔离。

无文件变化：findings 均无法确认、已经修复、超出 scope 或 ROI 太低；明确报告 `no file changes` 与证据。

## Output

- Scope source 和 review 轮数。
- 实际修复的 findings，以及 deferred / rejected 项及理由。
- 验证证据、独立 verifier 数量与适用理由。
- 是否触发 consolidation、触发迹象及结果。
- 最新整合复审的设计 / spec 符合性和代码质量结论。
- 调用方需要执行的 spec / active plan 分层写回。
- remaining blockers、residual risks 和下一动作。

不处理 commit；stage / commit 使用 `to-commit`。不创建 acceptance artifact，除非另有真实人类 gate 需要 `to-acceptance`。
