# Thin Plan Working Set

本参考只在 `to-implement` 已判断 file-backed implementation working set 的恢复价值高于维护成本时读取。它是 thin plan 的唯一详细操作合同；物化门槛留在父 Skill。

## Discovery And Source

- 使用 `${SKY_FLOW_ROOT:-docs}/plan/<id>.md`，id 使用稳定描述性名称，不使用 `001-` / `001a-` 排序。
- 必须使用 `source_type: spec` 和稳定 `source_id`。
- 用户直接给出 plan path / id 时，只允许 `not_started` / `in_progress` plan 作为 resume locator；再解析 source spec 并确认仍 ready、unfinished，然后进入 `to-implement`。completed / abandoned plan 只能作为历史背景，plan 自身不拥有 goal 或 readiness。
- plan 没有 `draft` 阶段：恢复价值成立但尚未执行时用 `not_started`；开始实施后，plan 与 source spec 都使用 `in_progress`。
- 恢复时只寻找当前 source spec 的 active plan，不对 plan 做候选排名或 mtime 选择。
- 默认一份 spec 同时只有一份 active plan。多份时先收敛、废弃过期项，或确认 spec 是否应拆分；不建立 plan graph。
- spec 是规范性真相源。plan 中的代码事实在恢复时按风险做定点复核；与 spec 冲突时 spec 胜出。

## Shape

```markdown
---
id: <plan-id>
artifact_type: plan
status: not_started | in_progress | completed | abandoned
source_type: spec
source_id: <spec-id>
---

# <Title>

## Current Slice

<一段话说明当前实现目标，并引用 source spec；不复制长期需求。>

## Code Context

- <值得跨会话保留的模块、文件、symbol、数据流或兼容事实。>

## Approach

- <当前方向、实现 slice 与顺序理由；可随证据覆盖更新。>

## Decisions

- <局部、可逆工程选择> — <为什么，以及它会影响哪些后续实现。>

## Progress

- Done:
  - <已完成的实现 slice 与必要证据。>
- Active: <当前正在改变什么。>
- Next: <下一个可直接恢复的具体动作。>
- Blockers:
  - <none，或只影响当前 slice 的局部实施 blocker 与解除条件；目标级 blocker 只引用 spec Progress。>

## Verification

- <可复用验证入口>: <最近结论、未验证范围与残余风险。>
```

section 是推荐形状，不是为简单工作制造的模板 gate。省略无关内容，但 active plan 必须有可恢复的 `Progress`。

## Update And Promotion

- 只在 Current Slice、Code Context、Approach、Decision、Progress 或 Verification 发生有恢复价值的变化时更新。
- Progress 是覆盖快照，不按时间追加。删除过期事实和已失效动作。
- 保留能防止重复踩坑的 rejected direction，但不保留普通探索流水。
- 局部、可逆决策可留在 plan。任何会改变 material scope、stable constraint、no-touch、外部行为、contract、data semantics、authority、acceptance 或长期架构的事实或决定，都要暂停实现并先更新 spec。
- 只有当前 slice 的局部实施 blocker 留在 plan。阻塞整体 goal、涉及外部条件 / authority / durable constraint 的 blocker 写入 spec Progress，plan 只引用对应 blocker，不复制描述。
- 不在 plan 中存储 owner、Agent 消息、task / step graph、dependency / parallel fields、fan-in 批次、tool calls、完整 diff、长命令输出或微步骤。
- 不保存 secret / credential 值。未提交 diff、终端、临时环境和短期 credential state 属于用户授权时的 handoff，不属于 plan。

## Validation

- create、source / status 变化、decision promotion、closure，以及 plan 即将作为恢复 / handoff / commit 输入时，运行 deterministic `validate-flow`；有 warning 或规范性边界判断时再完成 focused semantic pass。
- 只改 body working-set snapshot 时可以批量到下一个恢复或提交边界，不要求每次覆盖更新都触发完整 validator / model pass。
- 最终 closure 前必须完成确定性校验和必要语义收口。

## Closure

plan 完成不自动完成 spec。收口顺序：

1. 把所有 durable / normative decision 提升到 spec 对应 section。
2. 把 semantic outcomes、关键 evidence、residual risk 和目标级 resume target 写回 spec Progress。
3. 将 plan 压缩为最小 completed 摘要，或在没有独立保留价值时删除。

`abandoned` 只表示丢弃当前 working set / approach，不表示放弃 source spec。先保留简短原因并提升仍有价值的教训，再压缩或删除；只有 source work 真正退出 active queue 时，才创建以 durable source spec 为来源的 backlog。

不移入 `plan/done`，不保留 task archive，不调用已归档的 `$to-plan`、`pick-plan`、`to-task` 或 `to-archive`。
