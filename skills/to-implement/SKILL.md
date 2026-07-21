---
name: to-implement
description: 'Execute or continue a ready Sky Flow spec, derived runtime goal, or active thin-plan resume locator. Keep simple work runtime-only; materialize optional implementation working memory only when recovery value justifies it, without persisting task topology.'
---

# to-implement

`to-implement` 是 ready spec、其派生 goal 或 active plan resume locator 与原生 runtime 之间的薄桥。plan locator 必须先解析回 source spec；spec 始终给出目标、边界与成功依据，runtime 自主选择探索、实现、调度、验证和 fan-in 方式。

## 快速就绪检查

开始时只做一次轻量检查：目标、成功边界、关键约束、当前 spec Progress、blocker，以及 source-linked active plan（如有）是否互相一致。直接从 plan 恢复时先验证其 source spec 仍 ready 且 unfinished。能够从 spec 或仓库补齐的事实直接补齐；规范性边界存在实质缺口时回 `to-spec`，不要在执行层猜设计。

这不是重复完整 spec review，也不是固定 gate。简单且清楚的目标应立即执行。

## 必须保持

- 用户目标、外部行为、已确认 scope、no-touch 和权限边界。
- alignment goal 回 `to-spec`；未解除 blocker 的 goal 不启动。
- 产品 / 业务决策、真实环境 gate、发布、删除、生产写入及其他不可逆操作仍由相应 authority 决定。
- 同一文件或共享状态避免并发多写；交接完成后可动态更换 writer。
- 用户或 spec 要求的独立评估不能由 implementation owner 自行清除。
- 完成声明必须有与风险匹配的证据，未验证范围必须明确。
- 只有符合物化边界并完整读取 thin-plan 参考后才创建 / 更新 plan；任何情况下都不创建 task / step artifact。

除此之外，scope 内的 implementation design、探索顺序、工具、角色、并行度和验证组合由 runtime 根据当前事实决定。

## Runtime Context

简单工作直接从 spec 执行。复杂但当前会话可连续完成、且重新推导成本低的工作也可只用 runtime checklist。只有任务复杂或上下文容易在交接中失真时，才在 runtime 内做一次紧凑投影：

- `目标`
- `成功边界`
- `关键约束`
- `相关契约`
- `当前事实`

这五项是语义提示，不是固定 packet 或必填 schema；可省略无关项，并复用于后续派发和 review，避免每次重新拼接或复制整段聊天。它不自动写回 artifact；只有其中的 implementation context 真正满足下面的物化边界时才创建 plan。

## Plan Materialization

只有当实现预期跨会话 / compaction、上下文重建昂贵，或必须从具体 checkpoint 恢复时，才完整读取 `references/thin-plan.md`。该参考是 plan discovery、shape、update、promotion、validation 与 closure 的唯一详细合同。然后：

1. 先寻找当前 source spec 的 active thin plan；存在时定点复核可能漂移的代码事实后继续。
2. 不存在且恢复价值已经成立时，在 `${SKY_FLOW_ROOT:-docs}/plan/` 创建 source-linked plan。不因为 spec 存在或 checklist 步骤多就创建。
3. 工作开始时可以不创建 plan；执行中扩大、中断或出现高成本上下文时可中途 materialize，不重启 workflow。
4. 按参考中的分层校验规则处理高频 snapshot 与结构 / 恢复边界。

默认由当前 Agent 执行。只有用户显式要求 delegation / subagent，或 source spec 明确要求独立评估时才派发；派发只补充 mission 所需的 write scope、no-touch、evidence 或 stop condition，不建立固定 lane。

若 runtime 支持模型选择，清楚、局部、可验证的工作优先使用满足要求的最小模型；高歧义、高风险、跨契约裁决或最终冲突仲裁使用更强模型。模型选择是运行时优化，不是 artifact 约束。

## 执行与收敛

- 简单工作直接完成；复杂工作可使用轻量 runtime checklist，只有符合 Plan Materialization 时才增加 file-backed plan。subagent 只按上面的显式条件使用。
- 日常测试、typecheck、lint、build、真实路径检查和 diff sanity 由 native runtime 直接完成；artifact 写回后由当前执行者直接对改动路径运行 deterministic validator，不进入 `validate-flow` Skill。
- 对可观察的高风险行为、关键不变量、外部契约和真实回归补测试；不要为覆盖率测试日志、mock 次数、私有 helper，或已由类型、schema、lint 直接约束的内容。
- `$to-review`、`$to-review-loop`、`$to-consolidation`、`$to-acceptance`、`$to-knowledge` 和 provider second opinion 只在用户显式调用时使用，不构成固定流水线。
- finding 修复后默认做定点验证，不自动重开完整 review 或 consolidation。只有用户显式要求多 Agent / 多 reviewer，或 source spec 明确要求独立评估时，才建立满足任务所需的最小 change map 和 fan-in 结构。
- 探索推翻早期判断、fan-in 冲突或验证暴露新方向时，继续取证和调整；只有触碰必须保持的边界且无法安全裁决时才询问人类。
- 结束前确认结果支持当前 goal，未越过 authority，多来源产物无冲突 / 重复 / 临时残留，证据足以支撑结论。
- 任何事实或决定会改变 source spec 的规范性边界时暂停并建议 `$to-spec`；边界内局部、可逆实现决策在 active plan 存在且具有恢复价值时写入 plan，否则留给 runtime。

## State Writeback

spec Progress 是覆盖更新的语义恢复快照，只保存：稳定成立的能力或行为、长期关键决策、可信证据、真实 blocker 与解除条件、残余风险、下一目标级恢复入口。

不得记录具体代码行号、逐文件 diff、完整命令、tool call、子代理身份 / 消息、调度批次或逐轮时间线。必要定位可引用少量稳定模块、类、函数、公开接口或测试套件；新 checkpoint 合并或替换过期内容。

active plan 的写回与收口完全遵循 `references/thin-plan.md`。只有当前 slice 的局部实施 blocker 留在 plan；阻塞整体 goal、涉及外部条件 / authority / durable constraint 的 blocker 写入 spec Progress，plan 只保留引用，避免双份真相。

spec 只有在整个 durable scope、必要验证和真实人类 gate 都结束时才标记 `completed`；plan 或单个 runtime goal 完成不自动完成 spec。长期离队使用 backlog，易失本地接力才使用 handoff。

## 询问人类的条件

- 必须改变用户拥有的目标、产品 / 业务口径、外部契约或重大 scope。
- 需要新权限、未授权外部写入、发布、删除、生产操作或其他不可逆动作。
- 真实人类 gate 尚未关闭。
- 多个高影响方向在合理取证后仍无法从既有 intent 安全裁决。

其他实现不确定性由 runtime 自主处理，不为了使用 Sky Flow 制造额外流程。
