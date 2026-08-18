# Deep Consolidation Method

## Contents

1. Candidate recon
2. Change and replacement maps
3. Vertical responsibility trace
4. Six audit matrices
5. Deletion proof
6. Finding classification
7. Cross-project evidence adapters
8. Output template

## 1. Candidate Recon

先广后深地建立候选清单，候选只是调查入口，不能单独证明替代、无消费者或可自动修改。优先查看：

- 新不变量已接管后仍保留的重复 guard、fallback 或错误包装；
- 可由语言标准库或已批准依赖等价替代的目标内手写工具；
- 仅服务旧入口、旧字段或已删除行为的测试、fixture、mock、注释和文档；
- 当前 diff 暴露出的半废弃 wiring、临时 probe、注释掉代码或未消费结果；
- 对同一领域事实、调度或副作用的重复 owner。

新第三方依赖、跨范围历史残留和任何可能改变契约的候选直接标为人类决策，不扩展为自动清理。

## 2. Change And Replacement Maps

先按业务能力建立 change map，而不是按文件扩展名罗列 diff。每个切片记录：入口、领域决策、数据模型、IO、调度、消费者、观测和测试。

从 source intent 和 diff 提取 replacement map：

| Old symbol / design | New owner | Replaced responsibility | Evidence status |
| --- | --- | --- | --- |
| 旧入口 | 新入口 | 启动同一能力 | complete / partial / unknown |
| 旧字段 / 状态 | 新模型 | 表达同一事实 | complete / partial / unknown |
| 旧 timer / retry | 新调度 | 控制执行时机 | complete / partial / unknown |

replacement 必须有以下至少一种证据：明确设计决策、调用迁移、写读链变化、测试行为变化。名字相似或代码相似不能单独证明替代关系。

对 map 中的精确旧符号允许 repository-wide 搜索；搜索范围只用于确认其声明、调用、生产、消费、注册和文档证据，不扩展为泛化清理。

## 3. Vertical Responsibility Trace

对每个主要能力追踪：

```text
Trigger
→ Entry
→ Domain decision
→ Scheduler / concurrency
→ IO / persistence
→ State transition
→ Consumer
→ Side effects
→ Observability
```

逐层回答：

- 当前 owner 是谁？
- 是否仍有旧 owner？
- 输入事实来自哪里？
- 输出由谁消费？
- 失败、超时、取消和重试由哪一层决定？
- 查询是否夹带业务推进或通知副作用？
- 新旧路径是否可能同时执行？

如果某层没有消费者、存在两个 owner，或下一层必须理解上一层内部细节，记录为候选并继续取证，不立即发明抽象。

## 4. Six Audit Matrices

### 4.1 Entry And Call Matrix

检查：

- 同一能力是否有多个入口；
- 新旧入口是否同时被调用；
- wrapper 是否只转发且没有领域命名价值；
- 多层是否重复手拼同一参数组；
- 参数是否永远固定、可从上下文推导或与另一参数重复；
- 精确单条查询是否误用 Batch；
- 返回分支和字段是否仍有真实消费者。

不要只统计调用次数。一个单调用 helper 可能是有价值的领域命名或测试 seam；多个调用方也可能只是重复暴露了错误入口。

### 4.2 Data Lifecycle Matrix

对本轮新增、改名、合并或准备删除的字段和状态追踪：

```text
declare → construct → write → persist → read → branch → return → expire / delete
```

重点识别：

- 只写不读、只读不写；
- 永远固定或可从上下文推导；
- 两个字段 / 状态表达同一事实；
- 一个字段混合多个正交维度；
- 非法组合、互相覆盖或到达顺序依赖；
- persisted 字段没有运行时消费者；
- 状态已迁移但 fixture、schema、mock 或文档仍使用旧值。

持久化字段即使 TTL 很短也不是 TS-only 符号。没有兼容要求可以建议删除，但必须进入人类 gate，除非用户已经明确授权无兼容发布。

### 4.3 Responsibility Ownership Matrix

为以下职责各确定一个主 owner：

- 判断是否执行；
- fetch / query；
- normalize / map；
- persist；
- scan / repair；
- 推进领域状态；
- retry / timeout / cancel；
- 发布消息、通知或告警；
- 输出 Metrics 和日志。

同一职责有两个 owner，通常表示新旧并存或职责泄漏。查询层顺便推进业务状态、Repository 决定重试、Controller 维护领域状态，都需要记录并判断是否由本次变更造成。

### 4.4 Concurrency And Scheduling Matrix

按真实业务身份比较：

- dedupe key；
- debounce；
- in-flight reuse；
- queue；
- retry；
- timeout；
- breaker / cooldown；
- durable due scheduling；
- shutdown / drain ownership。

检查 key 粒度是否与能力一致，以及相邻层是否重复控制同一件事。重点发现：

- Batch retry 外又包一层同语义 retry；
- timer debounce 与 queue delay 重叠；
- caller timeout 与 transport timeout 互相遮蔽；
- 单条查询错误共享用户级 Batch dedupe；
- 新旧 scheduler 同时触发；
- in-flight 完成后 queued intent 被静默丢弃。

合并控制机制可能改变时序，默认进入人类 gate。

### 4.5 Side-effect And Consumer Matrix

对返回值、事件、缓存、落表结果和日志字段检查：

- 谁消费，消费是否改变行为；
- 是否只为旧测试、人工脚本或历史观测保留；
- 主事务成功后的后置副作用是否仍阻塞主链；
- 查询方法是否顺便落表、推进状态、发送通知或修复数据；
- 同一结果是否在两处落表或触发两次状态推进；
- ignored return 是否意味着接口已经过宽。

如果删除观测字段会改变 Dashboard、告警或事故排查口径，即使不改变业务结果，也必须进入人类 gate。

### 4.6 Evidence Synchronization Matrix

检查现行实现与以下证据是否一致：

- 测试名称、fixture、mock 和 snapshot；
- 当前 spec、设计文档和模块说明；
- 历史 plan、issue、task 和回滚文档；
- 配置示例、环境变量和 feature flag；
- Metrics HELP、label、Dashboard 和 Alert；
- 日志、注释、一次性脚本和人工操作说明。

当前规范应更新为现行口径。历史证据不重写；在仍可能误导时标记 superseded，并链接现行真相源。

测试是证据消费者，不是旧设计的永久护身符。仅当删除证明显示其覆盖的行为已消失、没有其他契约消费者且验证仍成立时，才可同步删除测试、fixture 或 mock。

## 5. Deletion Proof

删除、内联或停止写入任何 symbol 前，收集以下证据：

1. **Declaration**：声明、导出和注册位置。
2. **Producers**：构造、写入、发布和序列化位置。
3. **Consumers**：读取、分支、调用、反序列化和查询位置。
4. **Persistence**：DB、Redis、文件、消息、缓存、配置和 TTL。
5. **External boundary**：HTTP、WS、CLI、插件、SDK、部署和人工脚本。
6. **Runtime discovery**：反射、decorator、DI token、字符串注册、框架扫描和动态 import。
7. **Evidence consumers**：测试、fixture、Dashboard、告警、日志查询和文档。
8. **Replacement completeness**：新 owner 覆盖旧职责、错误路径和生命周期。
9. **Verification**：删除后能执行的最小类型、编译、测试或真实路径验证。

缺少第 3、4、5、6 或 8 项证据时，不得自动删除。

按边界分类：

- private / compile-time-only symbol：证据完整时可直接处理；
- exported package symbol：检查仓库内外消费者和发布边界；
- framework-discovered symbol：检查注册和运行时扫描；
- persisted field / enum：检查数据生命周期和兼容窗口；
- external contract field：检查 schema、版本和调用方；
- observability field：检查 Metrics、Dashboard、Alert 和运维查询。

## 6. Finding Classification

每个 finding 都说明预期行为差异。默认应为行为不变；不触及 P0 Boundary 的微小且合理差异可纳入 C1 / C2，但必须写明实际差异与简化理由。涉及契约、兼容、持久化、状态、并发、错误或观测取舍，或边界不清时，直接进入 C3。

### C1 Direct Delete

无消费者、无兼容边界、替代职责完整，且行为不变或只包含已说明的微小且合理差异。

### C2 Direct Merge Or Inline

行为等价，或只包含已说明的微小且合理差异；顺序等价、不丢失领域命名 / seam / 观测价值，且不会产生 caller-specific flag。

### C3 Human Decision

涉及契约、持久化、状态、并发、错误、观测语义或多个合理维护方向。

### C4 Explicit Keep

看似重复但承担领域命名、公共契约、测试 seam、框架边界、观测边界或明确兼容职责。记录未来重新评估条件，避免后续重复清理。

## 7. Cross-project Evidence Adapters

核心方法保持语言无关。根据仓库技术栈选择最小证据工具：

- 静态语言：符号引用、类型检查、编译、导出图；
- 动态语言：调用搜索之外检查字符串查找、注册表、反射和 monkey patch；
- Web / API：schema、路由注册、序列化、客户端生成物；
- 数据库：schema、migration、读写查询、历史数据和 rollout 约束；
- 缓存 / 消息：key / topic、生产者、消费者、TTL、幂等和版本；
- Worker / scheduler：注册入口、去重粒度、重试、shutdown 和跨进程恢复；
- 可观测性：metric 定义、HELP、label、Dashboard、Alert 和日志查询。

项目级 `AGENTS.md`、模块规则和真实协议证据优先于通用方法。不要把某个项目的框架、命名或兼容策略写回通用 Skill。

## 8. Output Template

```markdown
## 收敛结论

- 范围：
- 新设计接管状态：complete / partial / unknown
- 自动收敛：N 项
- 需确认：N 项
- 明确保留：N 项

## 建议立即收敛

### C-001 标题
- 位置：
- 当前问题：
- 新旧职责：
- 证据：
- 建议改法：
- 行为差异与理由：
- 风险：
- 验证：

## 只能 deprecated / 留待后续

### C-002 标题
- 位置：
- 为什么不能直接处理：
- 兼容对象：
- 推荐方向：
- 更小替代：
- 删除前置条件：

## 明确保留

### C-003 标题
- 位置：
- 看似冗余：
- 实际价值：
- 未来重新评估条件：

## 最小实施阶段

- Stage 1：纯删除 / 无行为变化
- Stage 2：接口、字段和职责收敛
- Stage 3：命名与文件归属
- Stage 4：文档、归档和验证
```

只列有证据的 finding。没有 finding 时，报告检查范围、职责接管结论、未验证边界和残余风险，不输出空区块。
