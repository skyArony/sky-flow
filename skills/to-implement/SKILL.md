---
name: to-implement
description: 'Execute or continue a ready Sky Flow spec or a runtime goal derived from it. Preserve user intent, real constraints, authority boundaries, and completion evidence while leaving decomposition, delegation, tools, sequencing, and verification tactics to the native runtime. Write back only a compact semantic Progress recovery snapshot.'
---

# to-implement

`to-implement` 是 ready spec 或其派生的 implementation-ready runtime goal 与原生 runtime 之间的薄桥。spec 提供目标、边界和成功依据；runtime 自主选择实现、探索、调度、验证和 fan-in 方式。

## Must Preserve

- 用户目标、外部行为、已确认 scope、no-touch 和权限边界。
- 只执行 implementation-ready 目标；alignment goal 回 `to-spec`，仍有未解除 blocker 的目标保持未启动。
- 需要人类决定的产品 / 业务口径、真实环境 gate、发布、删除、生产写入和其他不可逆操作。
- 同一文件或共享状态不得并发多写；完成交接后可以动态更换 writer。
- 用户或 spec 明确要求的独立评估不能由 implementation owner 自行清除。
- 完成声明必须有与风险匹配的可信证据，未验证范围必须明确。
- 不创建 plan/task/step artifact，不把 runtime 拆解、owner、消息或执行时间线写入 artifact。

除这些边界外，执行方法保持开放。scope 内的 implementation design、探索顺序、工具、子代理角色、并行度和验证组合由 runtime 根据当前事实决定。

## Operating Guidance

- 从 ready spec 或派生 goal 读取足以理解目标、成功标准、当前真相、真实 constraints 和恢复入口的语义；section 名称和完整模板不是执行前置 schema。
- 简单工作可以直接完成；复杂工作可以使用 runtime checklist、子代理或其他原生协调能力。
- 派发只提供完成 mission 所需的最小上下文。Mission 必须清楚；write scope、no-touch、evidence 或 stop condition 只在相关时提供，不形成固定 packet。
- explorer、worker、reviewer、verifier 等只是可能角色，不是必须枚举或预先分配的 lane。
- 测试、review、consolidation、acceptance 和 validation 根据证据缺口与风险选用，不构成固定流水线。
- 探索推翻早期拆解、验证出现多个方向或 fan-in 发生冲突时，优先继续取证、调整、重派或收敛；只有触碰 Must Preserve 且现有事实无法安全裁决时才询问人类。

## Completion And Fan-in

完成前按实际风险确认：

- 结果支持当前 goal 和相关成功条件。
- 写入没有越过 scope、no-touch 或 authority。
- 多来源产物不存在未处理的冲突、重复、临时残留或相互矛盾的假设。
- evidence 足以支持结论，blocker 和 residual risk 没有被隐藏。
- material goal、contract、data semantics 或 acceptance behavior 发生变化时，先回 `to-spec`；scope 内实现策略变化无需升级。

## Progress Writeback

`Progress` 是覆盖更新的语义恢复快照，不是执行日志：

```markdown
## Progress

- Checkpoint: <当前稳定成立的能力、行为或状态>
- Completed:
  - <已完成的语义结果和必要 evidence>
- Next: <下一轮优先推进的目标级恢复入口>
- Blockers:
  - <none，或阻塞原因与解除条件>
- Last verified:
  - <日期、证据结论、未验证范围和残余风险>
```

写回只保留长期恢复有用的信息：能力或行为结果、关键决策、可信 evidence、真实 blocker、residual risk 和 resume target。必要时可以引用少量稳定模块、类、函数、公开接口或测试套件名称。

不得写入具体代码行号、逐文件 diff、完整命令过程、tool call、子代理身份 / 消息、调度批次或逐轮时间线。`Next` 不是代码级微任务。新 checkpoint 必须合并或替换过期内容，不能持续追加。

spec 只有在整个 durable scope、必要验证和真实人类 gate 都结束时才标记 `completed`；单个 runtime goal 完成不自动完成 spec。长期离队使用 backlog，只有易失本地状态需要接力时才使用 handoff。

## Ask Human When

- 必须改变用户拥有的目标、产品 / 业务口径、外部契约或重大 scope。
- 需要新权限、未授权外部写入、发布、删除、生产操作或其他不可逆动作。
- 真实人类 gate 尚未关闭。
- 多个高影响方向在补充合理证据后仍无法从既有 intent 安全裁决。

其他实现不确定性由 runtime 自主处理，不为了使用 Sky Flow 而制造额外流程。
