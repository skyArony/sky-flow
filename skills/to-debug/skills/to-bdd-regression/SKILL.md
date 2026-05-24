---
name: to-bdd-regression
description: Sky Flow to-debug 的子能力。将真实线上 bug、客户反馈、日志 / 数据异常、时序问题、状态机问题或高风险回归转化为证据驱动的 BDD-style 回归测试，并用 Red / Green 验证修复。to-debug 已经确认的复现、假设、证据、incorrect path 和 correct path 必须复用；证据不足时回到 to-debug / to-infra 补证。
---

# to-bdd-regression

`to-bdd-regression` 把真实问题固化成可长期保护的 BDD-style 回归测试。这里的 BDD-style 指用 `Given / When / Then` 表达业务语义或系统边界，不要求引入 Cucumber。

它通常由 `to-debug` 推荐调用。`to-debug` 已经确认的信息不重复收集；本 Skill 只补足“测试化”所需的证据、fixture、行为边界、incorrect path、correct path 和验证节奏。

## 适用场景

使用本 Skill 处理这些请求：

- 线上 bug、客户反馈、日志异常、数据异常或支持工单已经有证据。
- 问题涉及时序、状态机、缓存、消息丢弃、历史补丁、延迟、跳过事件、重试、幂等或外部契约。
- 用户要求“用 BDD 固化 bug”“补一个贴近事故场景的测试”“修复后验证 correct path / incorrect path”。
- 需要证明同一个测试在修复前落入 incorrect path，修复后进入 correct path。

不适合的场景：

- 单纯格式化、类型修复、无业务语义的小改动。
- 没有可复现输入，也没有足够证据能定义正确行为的模糊问题。
- 只是普通测试 ROI、BDD 场景、stable seam 或替代验证判断，且没有真实事故或高风险回归背景；此时转 `to-test`。

## 与 `to-debug` / `to-infra` 配合

- 如果 `to-debug` 已提供 reproduction、confirmed hypothesis、evidence、incorrect path 和 correct path，直接复用，不重复查日志或重新列完整假设矩阵。
- 如果缺少会改变测试行为的证据，回到 `to-debug` 补复现或回到 `to-infra` 补日志、DB、缓存、Metrics、Dashboard 或告警证据。
- 如果发现 correct path 其实是产品 / 契约 / 数据口径问题，不直接写测试；回到上游 spec / plan / debug 流程确认。

## 输入包

从 `to-debug` 进入时，优先要求以下信息：

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

缺项不一定阻塞，但如果缺项会导致测试不知道保护什么，就必须补证或询问人类。

## 工作流

### 1. 还原事实

先把已有证据整理成测试可用的事实，而不是把整段日志塞进测试。

至少确认：

- Observed：真实系统实际错误表现。
- Expected：从业务规则、契约或人类确认推导出的正确表现。
- Inputs：触发错误的关键输入、状态、缓存、数据库记录或外部消息。
- Timeline：关键事件顺序和时间。
- Risk：如果不修复，会继续暴露什么错误结果。

### 2. 测试化假设

只把 `CONFIRMED` 或业务方明确确认的假设固化成回归测试。

```text
H1: [具体假设]
Evidence: [支持它的证据]
Incorrect path: [bug 存在时代码会做什么]
Correct path: [修复后代码应该做什么]
Observable assertions: [测试里能断言什么]
Status: CONFIRMED
```

`REJECTED` 假设不进测试；`INCONCLUSIVE` 假设先回到 `to-debug` / `to-infra`。

### 3. 设计 BDD-style 测试

测试描述和注释要准确表达事故场景、错误表现和修复方向。

推荐结构：

```ts
describe('BDD: <业务场景>', () => {
  it('Given <事故前状态>，When <触发输入>，Then <正确业务结果>', async () => {
    // Given: 从证据还原的关键状态。
    // When: 推入触发 bug 的输入。
    // Then: 断言 correct path 的可观察行为。
  });
});
```

断言优先级：

1. 用户可见结果、业务不变量、状态机结果或对外契约。
2. 对外副作用，例如发送消息、写入状态、发出请求或跳过操作。
3. 必要内部协作；只有它是唯一稳定可观察点时才使用。

不要只断言 mock 调用次数、私有 helper、日志文本或内部字段形状，除非它们本身就是事故边界。

### 4. Red: 证明 incorrect path

写好测试后，先运行定向测试。

期望结果：

- 如果生产逻辑还没修复，测试应失败，并且失败点对应 incorrect path。
- 如果测试已经通过，需要判断 bug 是否已被别的改动修复、测试是否没有打到真实路径、或断言是否太弱。

不要因为测试没有失败就放宽断言；先检查测试是否真的覆盖错误路径。

### 5. Green: 修复生产逻辑

修复时遵守：

- 修改生产逻辑，使同一个 BDD 测试进入 correct path。
- 保持测试语义稳定，不为了通过测试而删除关键断言、弱化 fixture 或改写事故事实。
- 修复必须落在可解释、可复用的业务规则、状态机转换或边界条件处理上。

修改测试允许条件：

- Red 阶段证明测试没有打到真实 incorrect path，需要收窄 seam、补齐 fixture 或修正断言方向。
- 新证据证明原始 expected / correct path 理解错误，且该证据来自 `to-debug`、`to-infra` 或人类确认。
- 生产修复揭示更稳定的可观察断言，但仍保护同一个事故行为和业务不变量。
- fixture 过宽、过窄或包含无关字段，导致测试脆弱或误报；可以整理为最小真实事实集。

禁止：

- hardcode 事故 fixture，如特判某个 user、task、id、时间戳或 payload。
- `NODE_ENV === 'test'`、spec-only 分支或测试环境专用业务路径。
- 绕开正在验证的核心判断逻辑，让测试变绿但真实路径仍可能错误。
- 为了让测试通过而删除 Given / When / Then 中的关键事故事实。
- 把原本应该失败的 incorrect path 改成跳过、宽松匹配或只断言 mock 调用次数。
- 在没有新证据的情况下改写 expected，把生产逻辑的当前行为当成正确行为。

### 6. Verify: 验证 correct path

至少运行：

- 新增或修改测试所在的定向测试。
- 与修复模块相关的相邻测试。
- 如果改动共享逻辑，运行更宽的 package 测试或构建检查。

验证后要能说明：

- 哪个 BDD case 固化了事故。
- bug 存在时会落入哪个 incorrect path。
- 修复后落入哪个 correct path。
- 还有哪些风险没有被当前测试覆盖。

## 输出格式

```text
Evidence
- [...]

BDD Regression
- Given: [...]
- When: [...]
- Then: [...]
- Incorrect path: [...]
- Correct path: [...]

Changes
- [...]

Verification
- [...]

Residual Risk
- [...]
```

如果只是做轻量分析，没有改代码，也按 `Evidence / BDD Regression / Residual Risk` 的缩短版输出。

## Checklist

- [ ] 已复用 `to-debug` 现有 reproduction、hypothesis 和 evidence，未重复取证。
- [ ] 已确认环境、时间范围和关键实体，或已说明为什么不需要。
- [ ] 已用 `to-infra` 或本地制品补齐必要证据。
- [ ] 已形成可测试的 confirmed hypothesis。
- [ ] BDD 测试描述准确表达事故场景。
- [ ] Given / When / Then 与证据事实一致。
- [ ] 测试断言业务可观察结果，而不是只测 helper 调用。
- [ ] 未修复时测试能覆盖 incorrect path，或已说明当前代码已经修复。
- [ ] 修复后同一测试进入 correct path。
- [ ] 没有为了让测试通过而削弱测试。
- [ ] 没有为了让测试通过而写 hardcode、test-only 分支或绕过核心逻辑的生产代码。
- [ ] 已运行定向测试和必要的相邻测试。
