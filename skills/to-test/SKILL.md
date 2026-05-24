---
name: to-test
description: 'Design or update Sky Flow testing strategy for behavior changes. Use when adding or changing tests, writing Given / When / Then scenarios, judging test ROI, choosing a stable test seam, deciding Red / Green / Refactor, or documenting alternative verification without project-specific commands.'
---

# to-test

`to-test` 是 Sky Flow 的通用测试工作流入口。它回答四个问题：

1. 要保护的行为是什么？
2. 这个行为值不值得测试？
3. 应该测在哪个稳定 seam？
4. 应该用 Red / Green / Refactor，还是用替代验证？

它不绑定任何项目命令、测试框架或业务术语。具体测试命令、包名、环境限制和本地执行方式由项目规则决定。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言。
2. 读取相关 spec / issue / plan / task / debug 证据和当前变更上下文；不要问能从仓库确认的问题。
3. 用业务或系统语言写 `1-3` 个高价值 `Given / When / Then` 行为场景。
4. 通过 ROI Gate 判断 `P0` / `P1` / `P2` / `Skip`。
5. 选择最小稳定 test seam。
6. `P0` / `P1` 默认使用 Red / Green / Refactor；characterization test 必须明确标注。
7. `P2` / `Skip` 记录替代验证和残余风险。
8. 如果需要长期留痕，把测试计划、验证证据或跳过理由回写到对应 plan / task / acceptance。
9. 创建或修改 Sky Flow artifact 后运行 `validate-flow`。

## Boundaries

- Debug 尚未复现或根因不清时，先用 `to-debug` 建立反馈环。
- 真实事故、客户反馈、日志 / 数据异常、时序问题或状态机问题需要固化回归时，转 `to-bdd-regression`。
- 人类验收、sign-off 或反馈文档由 `to-acceptance` 处理；`to-test` 只提供测试策略和验证证据。
- 不为覆盖率补低价值测试。
- 不测试 mock 调用次数、私有 helper、日志文本、内部字段形状或纯实现路径，除非它们本身就是稳定外部契约或安全边界。
- 不为了测试向生产代码加入 test-only method、测试环境分支或 spec-only 行为。

## Behavior Boundary

先定义行为，再决定怎么测。场景描述只写发生什么和正确结果，不写 mock、调用顺序、私有实现或日志文案。

```gherkin
Scenario: Given <前置状态>，When <触发行为>，Then <可观察正确结果>
```

规则：

- 一个场景只保护一个用户可见结果、业务不变量、系统边界或外部契约。
- 优先保护最可能回归、最难人工发现、影响最大的行为。
- 行为边界能从 repo 确认时先只读探索；仍不清楚时只问一个高价值问题。
- 如果问题不是“行为是什么”，而是“实现怎么做”，不要把它写进测试场景。

## ROI Gate

按风险和长期价值决定测试投入。

- `P0 必测`：数据正确性、安全 / 隐私 / 权限、计费或关键业务不变量、外部契约、关键状态机、并发、幂等、重试、真实事故回归。
- `P1 建议测`：复杂业务分支、跨模块映射、高频变更共享逻辑、重要 API / service 行为链路、近期不稳定路径。
- `P2 可不测`：简单 glue code、低风险展示、类型 / schema / lint 已直接约束的内容、小范围重命名、文档或 Skill 规则调整。
- `Skip 默认不测`：日志 / 告警文案、mock 调用次数、私有 helper 调用路径、内部字段形状、coverage-only 断言。

`P0` / `P1` 才进入测试优先。`P2` / `Skip` 必须写清替代验证，例如类型检查、schema 校验、编译、定向 smoke、review、轻量保护或人工验收证据。

## Test Seam

选择能保护行为的最小稳定 seam：

1. 纯函数 / state machine：优先单元测试。
2. Service / domain rule：通过稳定业务接口测试，mock 外部边界。
3. API / controller / contract：只在鉴权、状态码、参数解析、响应包装或 contract 本身有风险时测。
4. Database / storage：只有事务、约束、迁移兼容、查询语义或持久化副作用是核心风险时测。
5. UI / workflow：只保护关键用户流程、状态展示、提交边界或可见错误处理。

如果 mock / fixture setup 明显大于业务断言，先重新评估 seam 是否选错，或该行为是否应降级为替代验证。

## Mock / Fixture Gate

Mock 和 fixture 只用于隔离外部依赖，不能绕开正在验证的业务判断。

- Mock 只能隔离数据库、缓存、网络、时间、消息发送、文件系统或外部服务等边界。
- Fixture 应保持最小但真实的字段集合，不只填当前断言字段。
- 测试必须通过公开接口或稳定 seam 观察行为，能承受内部重构。
- 不为测试削弱生产逻辑、删除关键断言、硬编码 fixture 或加入测试专用路径。

## Execution Mode

### P0 / P1: Red / Green / Refactor

```text
RED: 写一个行为测试，确认它因为目标行为缺失而失败。
GREEN: 写刚好足够的生产代码让同一个测试通过。
REFACTOR: 相关测试为绿后，再整理重复、命名或边界。
```

规则：

- 一次只写一个行为测试。
- Red 失败原因必须对应目标行为缺失，不能是 import、fixture、mock、语法或环境错误。
- 如果第一次就是 Green，判断它是 characterization、测试没打到真实路径，还是断言太弱；不要误报为 Red。
- Characterization test 可以从 Green 开始，但必须标注它保护的是既有正确行为，不声称是 TDD。
- Never refactor while RED.

### P2 / Skip: Alternative Verification

不新增测试时，输出必须写清：

- 为什么不测。
- 用什么替代验证。
- 是否有残余风险或后续观察点。

## Output Contract

```text
Testing Plan
- Behavior: [...]
- Scenarios:
  1. Given [...]，When [...]，Then [...]
- ROI: P0 / P1 / P2 / Skip, reason[...]
- Seam: [...]
- Execution: Red / Green / Refactor / Characterization / Alternative verification
- Verification: [...]
- Artifact writeback: [...]
- Open Questions: [...]
```

## Checklist

- [ ] 行为场景保护的是可观察行为、系统边界或关键不变量。
- [ ] 场景没有描述 mock、调用顺序、私有实现或日志文案。
- [ ] ROI 已明确为 `P0` / `P1` / `P2` / `Skip`。
- [ ] `P0` / `P1` 已优先使用 Red / Green / Refactor，或说明为什么只能 characterization。
- [ ] Red 失败原因对应目标行为缺失。
- [ ] Test seam 足够稳定，能承受内部重构。
- [ ] Mock / fixture 没有绕开核心业务判断。
- [ ] `P2` / `Skip` 已记录替代验证和残余风险。
- [ ] 真实事故回归已转 `to-bdd-regression`。
