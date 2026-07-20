---
name: pick-goal
description: 'Select an unfinished Sky Flow spec and derive a concise portable runtime goal only when the user explicitly invokes $pick-goal. Selection stays read-only; an explicit start routes a ready goal to to-implement and leaves a blocked goal unstarted.'
---

# pick-goal

`pick-goal` 是 spec 与当前 runtime goal 之间的只读选择器。它从 durable spec 编译当前目标投影；若所选 spec 已有 source-linked active thin plan，可把其中仍有效的实施恢复上下文带入投影。它不创建或更新 workflow artifact，也不拥有后续执行。

```text
spec = durable goal source
Progress = resume cursor
active thin plan = optional implementation resume context
runtime goal = current execution projection
```

## Selection

- 用户指定 spec 路径、id 或紧邻引用时，只解析该 spec，不比较其他候选。
- 未指定时，从 `${SKY_FLOW_ROOT:-docs}/spec/` 中寻找 unfinished specs，结合用户当前意图、readiness、恢复连续性、blocker 和可验证价值做语义判断。
- 不使用固定评分、mtime、最近完成窗口或机械状态排序。候选确实不可比较时，给出少量清晰选项，不虚构唯一答案。
- completed / abandoned spec 默认是背景，不作为 implementation goal；draft 或 unready spec 只能派生 alignment goal；有 blocker 时必须保留解除条件。
- 选定 spec 后可查找其唯一 active thin plan；plan 只补充当前 slice、code context 和具体 resume action，不参与 spec 排名，也不改变 readiness 或权威边界。

一个 coherent spec 可以随 Progress 推进连续派生多个 runtime goal，但每次只输出一个当前 goal projection，不持久化 sibling goal graph。只有多个 outcome 彼此无关、可独立演进且不共享成功标准时才由 `to-spec` 考虑拆分；`pick-goal` 不把 Requirements 或 `Progress.Next` 挖成隐藏 task 图。

## Goal Projection

从相关语义派生目标，而不是要求固定 section 名称：

- 目标：spec 希望最终成立的结果。
- 成功边界：可观察的 requirements / acceptance / verification evidence。
- 关键约束：scope、no-touch、权限、真实人类 gate 和其他稳定 constraints。
- 相关契约：与当前目标直接相关的外部行为、数据、权限或兼容边界；没有时省略。
- 当前事实：spec Progress 中仍成立的 checkpoint、outcome、blocker 和 evidence；active plan 存在时，加入经定点复核仍有效的 code context、current slice 和具体 resume action。
- 恢复目标：下一轮优先推进的目标级入口；它不是 goal 本身，也不是具体代码操作。

输出保持紧凑，按相关性包含来源 spec、可选 active plan、目标、成功边界、关键约束、相关契约、当前事实、恢复目标和需要停下问人的条件。不预写实现步骤、子代理数量、runtime checklist 或固定验证顺序。

## Native Goal Boundary

- 选择和投影始终只读；默认只输出 portable goal packet。
- 用户明确要求“选择并启动 / 创建 goal”时，按 readiness 交接：implementation-ready goal 进入 `to-implement`；draft / unready spec 派生的 alignment goal 进入 `to-spec`；仍有 blocker 的 goal 只报告解除条件，不启动。
- runtime 原生 goal 能力只承载已经选定的目标。创建后 `pick-goal` 立即结束职责，由接收方拥有执行、spec Progress 和可选 active plan 的状态写回。
- 启动前尊重现有 unfinished goal；不静默替换，也不推断 token budget。
- runtime 没有原生 goal 工具时，仍输出 goal packet，并按相同 readiness 规则路由。
- native goal 的过程状态不逐项同步回 spec；只有稳定语义变化才进入 Progress。

## Boundaries

- 不创建 `artifact_type: goal` 或其他 goal 文件。
- 不修改 spec、plan、Progress、代码或安装状态。
- 不实现 goal，不替代 `to-spec` 或 `to-implement`；显式启动只负责原生 goal 创建与职责交接。
- 不把 `Progress.Next` 当成 goal，不选择 plan 代替 spec，也不恢复 legacy plan/task/DAG 语义。
- 不复制旧 `pick-plan` 的 collector、task gate、owner、mtime ranking 或长 continuation prompt。
