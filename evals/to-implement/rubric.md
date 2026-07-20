# to-implement Thin Plan 评估量表

本量表用于比较 `runtime-only` 与 `runtime-first, plan-on-demand` 的执行质量。简单案例应证明新增 artifact 没有制造固定成本；长周期案例应证明恢复质量提高。复杂案例可重复运行并模拟一次 compaction / 新会话恢复。

## 质量维度

每项 0-2 分：0 为缺失或明显错误，1 为部分满足，2 为稳定满足。

| 维度 | 2 分标准 |
| --- | --- |
| 路由准确性 | 简单和低恢复成本工作保持 runtime-only；只有恢复价值超过维护成本时创建 plan。 |
| 物化时机 | 能在开始时或任务中途依据真实信号 materialize，不因为 spec、复杂度标签或 checklist 长度机械创建。 |
| 恢复质量 | 新会话可从 current slice、code context、decision、Next 和验证入口直接继续，并会定点复核易漂移事实。 |
| 边界清晰度 | spec 保持规范性；plan 不复制长期需求，不成为 acceptance / backlog / handoff 的权威 source。 |
| 直接恢复 | 直接给出 plan 时先解析并校验 source spec，把 plan 仅作为 resume locator，而不是独立 goal。 |
| 决策提升 | 外部行为、contract、data semantics、authority、acceptance 和长期架构变化及时提升回 spec。 |
| 拓扑抑制 | 不生成 task / step、owner、dependency、parallel lane、fan-in batch、Agent / tool 流水或 `plan/done`。 |
| Snapshot 质量 | plan Progress 覆盖更新，保留 Done / Active / Next / Blockers 与验证入口，删除过期事实和时间线。 |
| 收口质量 | durable semantics 与目标级证据先写回 spec，plan 随后压缩或删除，且不误报 spec 完成。 |

## 效率指标

同时记录：

- 简单任务的 plan 创建率；目标为 0。
- 长周期高恢复成本任务的正确 materialization 率，以及错误漏建率。
- 从新会话恢复到首次有效代码 / 验证动作所需的 token、墙钟时间和重复文件读取次数。
- 因遗失 code context、局部 decision 或验证入口造成的重新推导与返工次数。
- plan 与 spec 的重复内容比例、发现的 stale conflict 数量和 decision promotion 遗漏数。
- 直接 plan resume 中错误跳过 source spec / readiness 校验的次数。
- 每个 source spec 的 active plan 数量；默认应为 0 或 1。
- plan 维护写入次数与实现总时长，判断维护成本是否低于恢复收益。

优先比较同等或更高实现正确率下的恢复成本。不能为了减少 token 而跳过关键 contract 验证，也不能为了提高恢复感而把完整执行日志长期保存。

## 失败信号

- 每个 ready spec 都先生成 plan，或把 plan 当作 readiness gate。
- 仅因 checklist 有多步、存在多个文件或使用子代理便创建 plan。
- 应跨会话恢复的复杂任务没有 plan，导致重复探索、上下文丢失或错误继续。
- plan 复制 spec Requirements / Acceptance，或其决定与 spec 冲突仍继续实现。
- 把具体 owner、task graph、依赖边、并行 lane、Agent 消息、tool call、完整 diff 或命令输出写入 plan。
- plan 已完成但 durable decision / semantic outcome 未提升到 spec，或把文件移入 `plan/done`。
- 用 plan 代替 handoff 保存未提交 diff、终端、临时环境或凭证。
