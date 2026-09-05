# to-milestone 评估量表

本量表评估 milestone 是否提高大型 spec 的分阶段可实施性，同时避免恢复预先写死的执行拓扑。使用代表性 spec 重复运行时，应比较覆盖质量、恢复质量、人类决策成本和无效文档数量。

## 质量维度

每项 0-2 分：0 为缺失或明显错误，1 为部分满足，2 为稳定满足。

| 维度 | 2 分标准 |
| --- | --- |
| 逐层填充 | 每轮只创建当前节点的直接子层；没有未来占位目录或一次性完整树。 |
| Coverage | 直接子节点共同覆盖父级 required outcome，不遗漏 spec，也不新增未授权 scope。 |
| 粒度判断 | 以独立 outcome、边界和验收判断 branch / leaf，不按工时、文件或步骤数机械拆分。 |
| 意图对齐 | 从自然语言判断授权范围；一个清楚指令可关闭相邻 checkpoint，只有实质歧义、scope / 风险 / 权限变化才追问。 |
| 文档边界 | milestone 保持方向性；代码步骤、文件、命令、owner、lane 和调度留在 runtime。 |
| 验证质量 | executable leaf 明确核心行为、风险相关单元测试、其他证据和人类验收入口，不追求覆盖率。 |
| 并行纪律 | 只持久化硬依赖；实际并行由 runtime 根据共享 contract 与写冲突决定。 |
| Spec authority | 长期架构或外部语义决定先提升到 spec；变化只使受影响分支 stale。 |
| 状态汇总 | 人类接受后 leaf 才完成；branch 准确汇总 required children，不制造重复父级 gate。 |
| 归档压缩 | 只归档已验收且无 active descendant 的节点；长期事实进入 spec，实施细节回归代码，archive 只保留完成历史。 |
| show-me preflight | 每个 leaf 实现前有最小充分的可视化讲解；按主题选择内联图示或 HTML，HTML 验证可打开；已有实施授权时展示后继续。 |

## 失败信号

- 第一次运行就创建多层目录、完整 roadmap、task DAG 或固定并行 lane。
- 为显得完整而写空 acceptance、测试占位或未来子节点。
- 把文件清单、代码步骤、命令、commit、Agent owner 或 fan-in 写进 milestone。
- 仅因 milestone 很大、耗时长或文件多就拆分，拆出的节点没有独立 outcome。
- 人类只批准一个层级，却继续细化或开始编码。
- 人类已经说“开始实现”、指定执行分工或等价授权后，仍机械要求批准 runtime plan、show-me continue 或重复状态转换。
- 测试通过后自动完成 leaf，没有等待要求中的人类验收。
- Spec 改动导致全树重建，或受影响分支未标记 stale 仍继续实施。
- 使用 `parallel_with` 维护易漂移的全局关系，或把无硬依赖误解为必须并发。
- 把未验收或仍有 active descendant 的 milestone 归档，或让 archive 保存当前代码结构、API / schema 细节和实施过程。
- 在 show-me 可视化讲解交付前开始实现、混淆多个 leaf，或交付未验证可打开的 HTML；明明内联图示足够却机械要求 HTML 和 Web server。

## 效率指标

- 每轮创建但未被近期选择的文档数量；目标接近 0。
- 从新会话恢复到当前 frontier 所需的重复读取与重新推导次数。
- 人类每轮需要评审的节点数量和未解锁下游的问题比例。
- 因粒度过大导致的返工次数，以及因粒度过小导致的无独立验收节点数量。
- Spec 变化时被错误重建的无关节点数量。
- milestone 与 spec、runtime plan 的重复内容比例。
- active tree 中已关闭节点的残留数量，以及 archive 与代码 / spec 的重复事实数量。
