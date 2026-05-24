---
name: to-debug
description: Sky Flow 通用 Debug 诊断入口。定位问题、复现异常、分析 root cause、本地测试失败、线上异常、性能退化、间歇性 bug、用户描述坏了 / 报错 / 不稳定时必须使用；先建立可信反馈环，再复现、列假设、按 prediction 取证、修复、验证和清理。需要基础设施 / 数据源查询或操作时转项目级 to-infra；真实事故回归固化时转 to-bdd-regression。
---

# to-debug

`to-debug` 是 Sky Flow 的通用诊断循环。它负责把“坏了”转成可重复、可证伪、可验证的调查过程：先建立反馈环，再复现同一个现象，列出假设矩阵，按 prediction 取证，修复源头，验证并清理临时 instrumentation。

它不替代项目级基础设施 / 数据源查询能力，也不替代事故回归测试固化：

- 查询或操作环境、日志、数据库、缓存、Metrics、Grafana、AlertManager、部署、网络或外部系统时，转项目级 `to-infra`。
- 线上 bug、客户反馈、日志 / 数据异常、时序或状态机问题需要固化成回归测试时，转下级 `to-bdd-regression`。
- 普通测试 ROI、BDD 场景、stable seam、Red / Green / Refactor 或替代验证判断，转 `to-test`。
- 项目没有定义 `to-infra` 时，只能使用已知本地制品、公开文档或通用工具型 Skill；不能猜测环境命令、凭据、数据口径或外部契约。

## 入口边界

- 默认 Debug 入口是本 Skill：用户说 debug、排查、坏了、报错、不稳定、本地测试失败、线上异常、性能退化时，先建立反馈环。
- 用户明确要求查日志、查数据库、查 Redis、查 Metrics、查 Grafana、查告警或执行基础设施操作时，可以直接转 `to-infra`，但输出要说明这只是 infra / evidence 步骤，不等于完整诊断闭环。
- 排查过程中需要基础设施或数据源证据时，先在本 Skill 中说明 hypothesis、prediction、目标环境、时间范围和关键实体，再转 `to-infra`。
- 缺少复现环境、日志、trace、HAR、录屏或其他关键制品时，先说明已尝试路径和缺失输入，再向人类请求补齐。

## 总原则

- 反馈环第一。没有可运行、可重复、可验证的 pass / fail 信号时，不继续猜根因。
- 复现用户描述的同一个现象，不修附近另一个错误。
- 先列 3-5 个可证伪假设，再按概率和影响排序取证。
- 每个 probe 必须对应一个 hypothesis 和 prediction。
- 一次只改变一个变量。
- 先修源头，不在下游症状点堆补丁；只有入口或关键边界几行轻量保护能明显收住风险时才加保护。
- 临时 instrumentation 必须带唯一前缀，结束前清理。

## 工作流

### 1. 建立反馈环

优先级从高到低：

1. 失败测试：unit、integration、e2e，选择能打到真实 bug 的 seam。
2. HTTP / CLI / fixture：固定输入，观察输出、状态或副作用。
3. Browser / UI loop：驱动 UI，断言 DOM、console、network 或截图。
4. Trace replay：保存真实请求、payload、事件流或日志片段，在隔离路径回放。
5. Throwaway harness：最小化启动一个 service 或函数路径，mock 外部边界。
6. Differential / bisect loop：对比版本、配置、数据集或 commit。
7. HITL loop：最后手段，让人类按脚本复现并回填结果。

拿到初始反馈环后，先优化它本身：

- 更快：缩小测试范围、缓存 setup、跳过无关初始化。
- 更准：断言具体症状，不满足于“没有 crash”。
- 更稳：固定时间、随机种子、文件系统和网络边界。

一个慢且 flaky 的反馈环只能勉强使用；一个快速确定性的反馈环会显著提高排查速度。

### 2. 复现

- 确认反馈环复现的是用户描述的现象。
- 多次运行确认稳定；间歇性 bug 需要提高复现率，而不是追求一次性完美复现。
- 对间歇性 bug，可以循环触发、并行触发、加压、注入 sleep 或缩窄时序窗口，把复现率提升到可调试水平。
- 记录精确症状：错误信息、错误输出、异常状态、耗时或日志关键点。

### 3. Recent Changes 快速检查

复现后、进入假设矩阵前，先检查最近变化，避免跳过最常见根因：

- 当前工作区 diff 是否触碰同一模块、配置、依赖、环境变量或测试 fixture。
- 最近 commit 是否改变同一数据流、部署配置或外部契约。
- 当前环境、启动参数、缓存状态、依赖版本是否和成功路径不同。

这些变化只作为假设来源，不等于根因；仍必须用 prediction 和 evidence 验证。

### 4. 假设矩阵

测试假设前，先列出 3-5 个排序后的假设。人类暂时不在线时可以按当前排序推进，但输出中保留矩阵。

```text
H1: [具体假设]
Prediction: 如果它是根因，改变/观察 [X] 会导致 [Y]。
Status: PENDING / CONFIRMED / REJECTED
Evidence: [...]
```

### 5. 取证

- 每个 probe 必须对应一个假设和 prediction。
- 优先用现有测试、debugger、REPL 或边界日志，不要“到处打日志再 grep”。
- 优先找仓库中可工作的相似实现或相邻路径，对比好路径和坏路径的输入、状态、配置和输出差异。
- 对坏值、错误状态或异常输出，从使用点反向追到数据来源；如果根因在上游，不要只在下游调用点兜底。
- 跨组件链路使用边界 probe 收敛证据。每个边界记录：

```text
Boundary: [组件 A -> 组件 B]
Input: [进入边界的关键 payload / 参数 / 状态]
Output: [离开边界的关键 payload / 参数 / 状态]
Config: [影响边界行为的配置、模式或开关]
State: [边界前后的关键缓存、数据库或内存状态]
Prediction: [如果假设成立，这里应观察到什么]
Evidence: [实际观察]
```

- 需要临时日志时使用唯一前缀，例如 `[DEBUG-a4f2]`。
- 性能问题先建立 baseline measurement，再 profile 或 bisect；不要先凭感觉改代码。
- 需要基础设施、日志、DB、缓存或 Metrics 证据时转 `to-infra`，并带上 hypothesis、prediction 和范围约束。

### 6. 修复与回归

- 有正确测试 seam 时，先把最小复现转成失败测试，再修复。
- P0 / P1 行为才测试优先；普通测试 ROI、seam 或替代验证判断转 `to-test`。
- 真实事故、客户反馈、状态机、时序或线上数据异常转 `to-bdd-regression` 固化 BDD-style 回归。
- 同一问题连续 2 次修复尝试失败时，停止继续打补丁，回到假设矩阵并标记被证伪的假设。
- 连续 3 次失败时暂停，说明缺失证据、测试 seam 或架构边界；必要时转设计、计划或改进类能力。

### 7. 验证与清理

- 重跑原始反馈环。
- 重跑新增或相关测试。
- grep 并清理所有 `[DEBUG-...]` instrumentation。
- 删除 throwaway harness，或移动到明确标注的 debug 位置并说明原因。
- 在交付说明、commit 或 PR 中写清最终成立的 root cause 假设，让下一次排查可以复用。
- 复盘是否暴露架构问题；如是，记录为 issue、plan 或架构改进候选。

## `to-infra` 交接格式

转入 `to-infra` 前，尽量给出这个包：

```text
Hypothesis: [...]
Prediction: [...]
Environment: [...]
Time range: [...]
Entities: [...]
Data source: logs / database / cache / metrics / dashboard / alerting / infra operation
Read/write intent: read-only / requested operation
Expected evidence shape: [...]
```

## `to-bdd-regression` 交接格式

转入 `to-bdd-regression` 前，复用当前诊断信息，避免重复取证：

```text
Observed: [...]
Expected: [...]
Reproduction: [...]
Confirmed hypothesis: [...]
Evidence: [...]
Incorrect path: [...]
Correct path: [...]
Observable assertions: [...]
Residual risk: [...]
```

## 输出格式

```text
Feedback Loop
- [...]

Reproduction
- [...]

Hypotheses
- H1 [...]

Evidence
- [...]

Fix Strategy
- [...]

Verification
- [...]

Residual Risk
- [...]
```

## Checklist

- [ ] 已建立可信反馈环，或已停止并说明缺少什么制品。
- [ ] 已确认复现的是用户描述的同一现象。
- [ ] 已检查 Recent Changes，并只把它们作为可证伪假设来源。
- [ ] 已列 3-5 个可证伪假设。
- [ ] 跨组件问题已记录关键边界的 input / output / config / state。
- [ ] 需要基础设施 / 数据源查询或操作时已转 `to-infra`。
- [ ] 真实事故回归已转 `to-bdd-regression`。
- [ ] 临时 debug instrumentation 已清理。
