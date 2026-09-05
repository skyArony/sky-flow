---
name: to-milestone
description: 'Explicitly turn a stable Sky Flow spec into a human-reviewed, progressively elaborated milestone tree; deepen selected branches, hand executable leaves to runtime, and compact accepted work into milestone archives.'
---

# to-milestone

`to-milestone` 把稳定 spec 转换为一棵按需展开、与人类逐层对齐的交付里程碑树。它持久化阶段边界、层级、硬依赖、验收目标和完成状态；当前叶子的代码步骤、工具、顺序和调度仍属于 runtime plan。

本 Skill 只在用户明确选择 milestone 流程时进入，可通过 `$to-milestone` 或等价自然语言表达；继续或恢复此前已选择的流程无需重复授权。简单工作、一次性实现和无需长期分阶段交付的 ready spec 直接交给 `to-implement`。

创建、细化、恢复或收口 milestone 文档前，完整读取 [milestone-docs.md](references/milestone-docs.md)。

## Quick Path

1. 确定 `${SKY_FLOW_ROOT:-docs}`、语言和 source spec；spec 尚未稳定到足以判断阶段 outcome、边界与验收时回 `$to-spec`。
2. 读取现有 milestone 树，只恢复已存在的 approved frontier、硬依赖、stale 分支和完成证据；不重新规划未受影响的分支。
3. 没有树时，只从 spec 提议一级 milestone。每个节点创建一个目录和同名文档，不创建第二级占位目录。
4. 向人类展示本层的 coverage、边界、硬依赖、建议顺序和可并行节点；从人类最新指令判断哪些节点已对齐。只有仍存在会改变 scope、行为、风险或优先级的实质歧义时才追问。
5. 从已批准且硬依赖满足的节点中推荐下一 frontier。人类可以选择一个节点，也可以批准多个互不冲突的节点并行推进。
6. 对选中节点只细化一层：如果仍包含多个不可独立验收的 outcome，创建直接子 milestone；如果已满足叶子标准，将其定义为 executable leaf。
7. executable leaf 的 outcome、边界、验收、核心行为测试、单元测试意图和其他证据明确后，从人类指令判断是否已授权实施；普通 Agent plan 不单独制造批准 gate。
8. 任何实现动作开始前，调用内嵌 `eli5` 为当前 leaf 生成 HTML 图解，启动本地 Web 服务器，验证页面可访问并把 URL 交给人类。若此前已经获得实施授权，展示 URL 后直接交给 `to-implement`；只有人类要求先看讲解，或讲解暴露实质问题时才等待。
9. 实现跨会话且恢复价值成立时，thin plan 仍以 spec 为 source，并在 Current Slice 中引用当前 milestone。
10. Agent 完成确定性验证后按当前 acceptance authority 收口：默认请求人类验收；若人类已明确委托 Agent 验收，则由独立于实现者的 Agent 按约定标准裁决。通过后把 leaf 标记 `completed`，向父节点汇总并推荐下一 frontier。
11. 已关闭且没有 active descendant 的 milestone 可以归档：先把规范性结论提升到 spec，再将实施期文档压缩成完成摘要并移出 active tree。代码是实现事实，spec 是规范性事实，archive 只保存交付历史。
12. 规范性事实或长期架构决定发生变化时，先写回 spec；只把受影响节点标记 stale 并重新评审，不重建整棵树。

## Progressive Elaboration

每轮只创建或重写当前节点的直接子层。目录中没有尚未讨论的未来分支，也没有为了显得完整而生成的空文档。

一个层级得到批准，只表示当前切分和边界成立，不表示所有后代已经设计完成。选中节点后重新检查仓库事实、已完成兄弟节点产生的约束和 source spec，再决定它是 branch 还是 executable leaf。

直接子节点必须共同覆盖父节点的 required outcome：

- 不遗漏父节点承接的 spec requirement、scenario 或 constraint。
- 不把父节点之外的新 scope 偷渡进子节点；需要扩大 scope 时先回 spec。
- 允许共享跨切约束，但要明确由谁建立、由谁消费，避免重复实现。
- 不要求互斥分区；确有交叉时说明交叉原因与最终验收位置。

## Executable Leaf

达到以下条件时停止细化：

- 只有一个连贯 outcome，能够作为一个 runtime goal 推进。
- 边界清楚，完成后可独立验证和接受，不依赖未定义的兄弟结果才能判断正确性。
- 没有仍会改变外部行为、数据语义、权限、兼容、重大 scope 或验收口径的人类决策。
- 硬依赖和共享契约已知；尚未满足的依赖会阻止执行，但不阻止把叶子定义清楚。
- 验收标准可观察，Verification Intent 能区分“已经成立”与“看起来可用”。
- 已明确最高价值的核心行为测试、风险相关的单元测试意图，以及必要的集成、端到端或人工证据；不适用项说明理由。

叶子大小不按工时、文件数、commit 数或固定步骤判断。无法独立验收通常意味着仍需细化；拆开后每个部分都没有独立 outcome，则说明切得过细。

## Intent-Aware Alignment

以下边界需要人类拥有最终意图，但不要求逐项重复说“批准”：

- 一级 milestone 划分。
- 每个被选 branch 的直接子层划分。
- executable leaf 的定义与验收合同。
- 会改变 scope、外部行为、关键风险或执行授权的 runtime 方向。
- 当前叶子的 ELI5 Web 讲解必须在实现前交付；是否等待再次回复取决于已有授权和人类要求。
- 实现后的最终验收。

一个清楚的人类指令可以同时关闭多个相邻 checkpoint。例如“可以，让子代理实现，你来验收”同时授权当前 leaf 实施、指定 runtime 分工，并把该 leaf 的 acceptance authority 委托给主 Agent；不得再要求形式化 runtime-plan 批准。

从自然语言和上下文判断意图：选择节点、要求开始、指定执行者、说“按这个做 / 可以 / 继续”，或对完整提案给出等价肯定，都可作为对其覆盖范围的授权。只讨论部分节点、要求修改、条件性同意或未回复不自动扩大授权范围。

只有以下情况才追问：多个高影响方案仍待选择；最新指令与 spec / 已批准边界冲突；需要扩大 scope、改变外部契约、接受新增风险或取得新权限；无法判断授权覆盖哪个 leaf。不要为了记录 `review: approved`、生成普通 Agent plan、展示已要求的分工或重复上一轮结论而询问。

父节点默认在所有 required child 完成后自动汇总；只有父节点存在无法由子节点证据覆盖的整体行为、体验或风险接受时，才增加独立父级验收。

一次性人类确认留在对话中。只有用户显式要求跨会话、多轮或可审计的验收记录时，才交给 `$to-acceptance`。

## Dependencies And Parallelism

- 文档只记录真实硬依赖；偏好、建议顺序和资源便利不伪装成 dependency。
- 不维护 `parallel_with`。没有未完成硬依赖只表示具备并行资格，不代表必须并行。
- 多个 executable leaf 可以同时 active，但 runtime 必须检查共享文件、schema、公共 contract、部署配置和 single-writer 状态，避免并发多写。
- 并行调度、owner、Agent lane、fan-in 和具体顺序只存在于 runtime，不写进 milestone 文档。

## ELI5 Leaf Preflight

每个 executable leaf 获得实施授权后，完整读取并调用 Sky Flow 内嵌的 [`eli5`](../eli5/SKILL.md)，把当前 leaf 讲成不需要技术背景也能理解的 HTML 图解。讲解聚焦：要解决的问题、系统会发生什么变化、关键数据或交互如何流动、完成后人类能看到什么，以及主要风险；使用大图、流程图或简单类比，少字，不展示代码和逐文件计划。

- 把 HTML 写到 repo 外的临时目录，例如 `${TMPDIR}/sky-flow-eli5/<spec-id>/<leaf-id>/index.html`；它是交互产物，不写入 milestone、spec 或 Git。
- 用可持续跨当前人类 gate 的 runtime session 启动静态 Web server。默认绑定 `127.0.0.1`，动态选择空闲端口；不要启动项目 dev server，也不要占用固定端口。
- 在输出前实际请求页面并确认成功响应。向人类提供完整可点击 URL，例如 `http://127.0.0.1:<port>/`，同时用一句话说明该页面对应哪个 leaf。
- 页面不可访问、内嵌 `eli5` 不可读取或 runtime 无法维持服务器时停止，不得用文字摘要冒充已完成 preflight。
- 如果最新指令已经明确要求开始实施，交付 URL 后直接继续，不再请求“请确认继续”。只有人类明确要求 review-before-run，或讲解暴露新的规范性问题时才暂停。
- 服务器在该 leaf 开始后可按 runtime 需要保留；人类确认不再需要、leaf 完成、切换 leaf 或任务结束时停止进程并清理临时目录。

多个并行 leaf 各自生成独立页面和 URL，不用一个页面混合多个 leaf，也不共享可相互覆盖的临时目录。

## Spec And Runtime Boundary

- spec 始终拥有长期 intent、scope、requirements、外部行为、数据语义、authority、acceptance 与架构决定。
- milestone 拥有阶段 outcome、层级、硬依赖、definition、review、delivery status 和完成证据。
- runtime plan 拥有当前叶子的代码步骤、文件范围、工具、调度和验证命令，不复制进 milestone。
- thin plan 只保存跨会话 implementation working set；它继续 source-link spec，而不是 milestone。
- milestone 中形成长期决定时，先提升到 spec，再让依赖它的节点从 stale / pending 重新批准。

## Archive Completed Work

- 归档是完成后的压缩，不是新的验收状态；只有已获人类验收且没有 active descendant 的 milestone 才能归档。
- 优先归档完整关闭的 subtree。父节点仍 active 时，也可单独归档 completed leaf，但必须更新父节点的 archive locator 和汇总状态。
- 归档前把长期设计、外部行为、数据语义、authority、acceptance 变化和残余风险提升到 spec；缺失时停止归档。
- archive 只保留 outcome、spec coverage、完成摘要、验收证据索引和必要残余风险。删除实施期 scope 展开、依赖、测试意图、runtime handoff、逐层 decomposition rationale 和 Progress 流水。
- archive 不复制代码、最终 API / schema 细节或当前系统说明。需要知道“系统现在如何工作”时读代码和 spec；archive 只回答“这个交付阶段曾如何关闭”。
- 归档不改变已经成立的人类验收结论。后续需求从最新 spec 创建新 milestone；只有发现原验收结论本身无效时才显式 reopen。

## Resume And Stop Conditions

恢复时优先寻找：`review: pending` 的当前层、`definition: stale` 的受影响节点、`status: in_progress` 的 leaf，以及硬依赖已满足的 approved frontier。不要按 mtime 或数字前缀猜下一步。

出现以下情况时停止而不是继续填充：

- source spec 的成功边界或关键契约不足以安全切分。
- 当前层仍等待人类批准。
- 当前 leaf 尚未获得实施授权，或仍存在会改变结果的实质选择。
- ELI5 页面尚未生成或 Web 地址未验证；仅当人类要求先看后决定时，等待其回复。
- 实现完成但人类验收尚未通过。
- 规范性变化尚未写回 spec，或 spec 变化使当前分支 stale。
- 下一动作需要新权限、外部写入、发布、删除、生产变更或其他不可逆授权。

## Self-Review

- 是否只展开了一层，没有创建未来占位目录。
- 当前层是否完整覆盖父节点，同时没有新增未授权 scope。
- branch 与 executable leaf 的判断是否基于独立 outcome 和验收，而不是工时或文件数量。
- 是否只记录硬依赖，并把实际并行与 owner 留给 runtime。
- milestone 是否保持方向性，没有代码片段、文件清单、命令或 step-by-step 实现。
- 测试意图是否保护可观察行为和高风险 seam，而不是覆盖率或内部调用。
- 人类意图、验收 authority 和 spec authority 是否都未被 Agent 自行扩大；是否避免了重复批准请求。
- 完成与 stale 状态是否只影响必要分支，父级汇总是否准确。
- 归档是否只包含已验收且无 active descendant 的节点，长期事实已提升到 spec，压缩后没有与代码或 spec 竞争真相源。
- 每个待执行 leaf 是否已有独立、实际可访问的 ELI5 页面；已有实施授权时是否避免了多余的“继续”确认。
