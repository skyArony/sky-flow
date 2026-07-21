---
name: to-review
description: 'Run a dedicated read-only review only when the user explicitly invokes $to-review for code diffs or active Sky Flow artifacts. Find bugs, regression risks, missing verification, scope drift, artifact boundary problems, and implementation/design misalignment; routine diff sanity stays in the native runtime.'
---

# to-review

`to-review` 只在用户显式调用时运行，默认只读，检查实现风险、行为回归、设计对齐、测试缺口、安全 / 可靠性问题，以及 artifact 边界。普通任务的 diff sanity 和定向验证由 native runtime 直接完成。它不替代 deterministic artifact lint、`to-consolidation` 或 `to-implement`。

## Quick Path

1. 确认具体范围：默认 pending diff；也可使用用户指定的文件、artifact、commit range 或实现输出。
2. 获取 source spec / runtime goal、可选 source-linked active thin plan、预期行为、known deviations、non-goals 和已跑验证。plan 只提供实施上下文，不能覆盖 spec。意图只能从 diff 推断时明确标注。
3. 选择最小充分深度：小而低风险用 `fast`；非平凡变更默认 `medium`；有系统性高风险线索才进入 `deep`。
4. 默认只使用当前 reviewer；只有用户明确要求，或 source spec 明确要求且一个结论不足时才使用多个独立 reviewer。
5. 同一个 reviewer 同时给出`设计 / spec 符合性`与`代码质量`两个结论，并列出无法验证项；不要机械拆成两轮 review。
6. findings-first 输出；无 finding 时说明检查范围、证据、未验证范围与残余风险。
7. 用户要求收敛修复范围或判断优先级时，对 confirmed findings 再做 ROI 裁决：合并同根问题，只保留当前值得修的最小集合，其余明确标为顺手带上、暂缓、不修或接受残余风险。不要用 finding 数量代替决策。

同一稳定 diff 默认只做一轮完整 review。finding 修复后只验证对应 hunk、真实触发路径和必要测试 / 静态证据；只有修复改变公共契约、资金 / 状态机语义、显著扩大 scope、引入新的跨模块路径，或首次 review 明确留下系统性未知时，才重开完整 review。

## Review Context

小范围 review 直接读文件和 diff。大 diff 可先用 stat / numstat 建立 change map，按领域和风险选择文件；模型根据复杂度和证据需要自行决定读取范围。用户显式要求多个 reviewer 时，默认避免重复覆盖同一文件组，确需独立裁决时除外。

只有 diff 很大、多个 reviewer 需要相同上下文，或明确需要跨会话复审时，才运行：

```bash
python3 skills/to-review/scripts/prepare_review_context.py --output-dir <临时目录> --spec <source-spec>
```

脚本在仓库外的临时目录生成可复用 `review-context.md` 与 `changes.diff`。也可用 `--base` / `--head` 指定范围，使用 `--goal` 代替 `--spec`，并重复传入 `--known-deviation`、`--non-goal`、`--evidence`。context 必须引用 source spec 或 runtime goal，不能只给 diff；active plan 如有则作为独立只读上下文一并提供。优先让 reviewer 读取文件，不在消息中粘贴大段内容。

该目录是 runtime 临时输入，不是 Sky Flow artifact，不得写入 spec Progress。

## Depth And Independence

- `fast`：小 diff、单文件或低风险文案，本地 review 即可。
- `medium`：默认主力路径；按需读取 `reviewers/review-by-somestay/PROFILE.md`，追求高信号和低误报。
- `deep`：仅在 medium 暴露跨模块 / 共享契约 / 状态机 / 安全 / 并发 / 权限 / 数据 / 迁移等系统性线索时，读取 `reviewers/review-by-sanyuan/PROFILE.md` 深挖该线索，不重做整轮 medium。

多个 reviewer 必须拿到相同 source、known deviations、验证和 non-goals，但优先按不重叠文件组分配 scope。只有需要独立裁决同一高风险结论时才重复覆盖相同代码。合成时只合并语义相同的问题；独有 finding 仍按触发路径、影响、信心和修复成本判断，不能因缺少共识而丢弃。

## Review Focus

- 行为是否满足 source spec / goal 的 intent、requirements、scenarios 和 constraints。
- active plan 的 approach、局部 decisions 和 Progress 是否仍与 spec / code 一致，是否存在应提升到 spec 的 durable semantics、失效 code context 或 legacy topology。
- 错误路径、边界状态、数据 / 权限 / 安全 / 并发 / 兼容风险是否有真实触发路径。
- 实现是否越过 scope、no-touch 或 authority，是否遗漏必要验证。
- artifact 是否保持设计、readiness、spec / plan Progress 和来源一致，且没有 runtime topology 泄漏；plan 是否确有恢复价值且没有变成规范性真相源。
- 多来源产物是否存在冲突、重复、临时残留或相互矛盾的假设。

结构字段问题由 owning Skill 直接运行 deterministic validator；用户要求全量 / migration audit 时使用 `$validate-flow`。补丁式实现和 diff 熵值交 `to-consolidation`；目标、外部契约、数据语义或验收行为变化回 `to-spec`。

## Finding Quality

- 按严重度排序，给出紧凑定位、真实触发场景、影响、证据、建议修复、修复成本和信心。
- 严重度描述最坏影响，修复优先级由 ROI 决定；P0 / P1 不自动等于“现在修”，P2 / P3 也不自动等于“忽略”。
- 只有能说明真实触发路径与影响时才升为 P0-P2；理论风险降为 P3 / Suggestion 或 residual risk。
- 区分稳定复现 / 已发生事故、正常业务路径、单一常见故障和多个独立故障叠加；没有频率证据时明确不确定性，不凭直觉声称高概率。
- 计算幂等、重试、后续补偿、人工门禁和降级后的剩余影响；不能只写未经折减的最坏后果。
- 同一根因或同一个最小 patch 能闭合的问题合并裁决，避免把一项修复拆成多个优先级噪声。
- 修复建议优先局部且明确，不为低概率风险引入复杂状态、fallback、兼容层或抽象。
- known deviation 先判断是否合理；日志措辞、mock 次数和私有 helper 路径通常不构成 blocking finding。

严重度：`P0` 破坏关键行为或数据 / 资金 / 权限 / 隐私 / 安全边界；`P1` 高概率或高影响回归；`P2` 真实局部问题；`P3` 低概率、低影响或证据不足；`Suggestion` 为改进建议；`Nit` 不影响结果。

## ROI Triage

用户问“哪些值得修”、要求去掉边角问题，或 review 需要给执行顺序时，对 confirmed findings 做第二层裁决：

1. **现实触发**：正常输入就会命中、稳定失败或已有事故证据，还是需要多个低概率故障同时发生。
2. **剩余影响**：经过现有补偿、幂等、重试和人工操作后，是否仍会破坏资金、数据、契约或关键可用性。
3. **最小成本**：修复是局部条件 / 排序 / 断言，还是会扩成新状态机、公共抽象、迁移或高风险回归面。
4. **机会成本**：修复是否会制造重试风暴、增加正常空路径负载、扩大兼容面，或让实现复杂度超过风险本身。

裁决使用以下语义：

- `fix-now`：真实路径或确定性失败，剩余影响高，且修复收益明显大于风险。
- `bundle`：多个 finding 同根、可由同一最小 patch 和回归闭合，合并处理。
- `piggyback`：触发低概率但修复极小；不单独立项，只在相邻代码已被修改时顺手带上。
- `defer/no-fix`：需要故障组合、已有充分补偿，或修复会引入不成比例的状态与回归成本。
- `accepted-residual`：用户或 spec 已明确接受；保留边界和重新评估条件，不继续提出修复。

确定性失败的测试 / CI 即使不是运行时 Bug，也应按确定性维护成本计入 ROI。死代码、重复 helper 和抽象机会只有在已产生漂移、缺陷或显著修改摩擦时才进入修复集合；不要把纯清理包装成 Bug。最终建议可以只保留少数高 ROI 项，但必须列出其余 confirmed findings 的不修理由。

## Verification

Verifier 只验收已选择 finding 是否修复，不用于重新发现需求或重做完整 review。能够用聚焦测试、静态检查或明确代码路径确定修复时，由当前执行者定点验证即可。只有 P0、证据冲突、高风险安全 / 资金 / 权限 / 迁移且定点证据不足，或用户明确要求独立验收时，才启动一个独立 verifier；严重度为 P1 本身不构成强制独立复审理由。

只有独立 verifier 仍存在证据冲突、P0 安全边界需要双重确认，或用户明确要求时，才使用两个不同模型 / 供应商。

没有文件变化、没有 confirmed finding，或只需核对现有证据时，不启动 verifier；由当前 review 给出可追溯结论。运行时无法满足所需独立性时如实标注，不能宣称 gate 已完成。

## Output

每个 finding 先回答真实触发、补偿后的影响和修复代价；需要执行建议时再给 ROI 裁决。推荐结构：

```markdown
## Findings

### RV-001 [P1] <标题> - <定位>

> **实际会出 Bug 吗？** high|medium|low|unknown - <正常路径、稳定复现或故障组合及证据>
>
> **补偿后影响？** critical|high|medium|low - <现有幂等、重试、补偿或门禁后的剩余后果>
>
> **修复代价？** low|medium|high - <最小 patch、测试范围与 blast radius>
>
> **ROI 裁决？** fix-now|bundle|piggyback|defer/no-fix|accepted-residual - <一句理由>

- **证据**：<证据>
- **影响**：<影响面>
- **建议修复**：<小而具体的方向>
- **信心**：high|medium|low

## 综合结论

- **建议修复集**：<只列当前值得修的最小集合与顺序；同根项合并>
- **明确不修**：<低概率、已有补偿、纯清理或成本不成比例的项及理由>
- **设计 / spec 符合性**：pass|fail|unknown - <依据>
- **代码质量**：pass|fail|unknown - <依据>
- **检查范围**：<范围>
- **未验证范围**：<缺口>
- **残余风险**：<风险>
- **文件改动**：no file changes
```

无 findings 时第一行写 `No findings.`，再给出上述综合结论。多个 reviewer 或 verifier 场景可增加 reviewer agreement、模型独立性和 finding closure 状态，但不要求所有单 reviewer 输出固定长模板。

`to-review` 不自动修复，也不自动升级 `to-review-loop`。用户明确要求 review-fix-rereview 时才进入循环。
