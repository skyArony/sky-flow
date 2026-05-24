---
name: to-consolidation
description: 'Consolidate completed stage code or concrete output changes by checking the target scope for patchy implementation, temporary code, duplicate logic, dead leftovers, and fan-in residue. Use after a verifiable stage, multi-agent fan-in, when a plan/task inserts a consolidation task, or when the user asks to consolidate pending work.'
---

# to-consolidation

## 核心原则

收敛必须保持行为不变。这是 `to-consolidation` 的 P0 原则；任何可能改变外部行为、错误处理、兼容逻辑、数据口径、日志 / 指标语义或用户可见结果的“简化”，都不允许作为自动收敛处理，必须先询问人类。

`to-consolidation` 用于阶段产物完成后的代码收敛检查，让目标范围呈现为干净、统一、可交付的一体化结果。

它不是普通 code review，也不是架构重构入口；它只回答一个问题：当前目标 diff 是否像一次成型的清晰实现。收敛优先提升可读性、显式性和一致性，不以“更少行数”为目标。Sky Flow artifact 结构、状态、依赖、验收证据和 backlog / handoff 归宿由 `validate-flow` 负责，不在这里检查或修正。

默认范围是当前工作区 pending diff，明确包括 unstaged diff、staged diff 和 untracked files。用户指定路径、模块、文件、提交或提交区间时，只检查指定范围对应的代码 / 产物 diff；用户指定 plan / task artifact 时，只把它作为定位代码范围的上下文，不检查 artifact 状态。

`to-consolidation` 不作为 `to-commit` 的固定前置步骤。它应像 review 一样，由 `to-task` 根据阶段风险、fan-in 复杂度、产物形态和 diff 熵值灵活插入为阶段性 task，或由用户显式触发。

## Workflow

1. 建立范围事实：用只读 Git / 文件命令确认 unstaged、staged、untracked 三类 pending diff，以及目标路径、模块或提交区间。
2. 只读扫描目标 diff 和必要相邻代码，记录补丁式痕迹、重复实现和 fan-in 残留。
3. 判断是否需要只读并行审查；共享核心文件只能并行分析、串行修改。
4. Fan-in 发现，分类为可直接收敛、需要人类确认、保留但说明原因。
5. 只修无歧义低风险整理，例如当前目标 diff 引入的临时代码、重复实现、非公共错误抽象、浅层 wrapper、过深嵌套、旧注释、debug 残留、无用配置，以及目标范围内明确的 format / lint 问题。
6. guard / fallback、错误处理、职责分布只在本次 diff 引入重复、叠加、遮蔽或风格漂移且证据明确时收敛；涉及行为口径、兼容逻辑或公共契约时先询问人类。
7. 检查目标 diff 和必要相邻代码后停止；不要为了理论上的历史问题做全仓搜索式清理。
8. 复查 diff，确认没有引入目标文件外的无关格式化、额外重构、临时代码或扩大范围。
9. 如果实际修改了可执行代码，运行与改动相关的最小验证；无法验证时说明原因。

## 收敛判定

收敛只处理目标 diff 暴露出的实现熵值：临时代码、重复业务知识、错误抽象、过度跳转、命名口径漂移、debug 残留和 fan-in 半成品。Code smell 只是调查信号，不是自动修改理由；如果无法证明修改会降低目标 diff 的阅读成本或维护成本，就保留现状。

优先顺序是：删除无用残留 > 内联过度抽象 > 统一无歧义命名 / 注释 > 扁平化局部控制流 > 合并稳定重复知识。新增抽象放在最后，只有同一业务知识已经稳定、调用方语义一致、且不会引入 mode / flag / caller 特例时才做。

任何 helper、wrapper、类型或分支在删除、内联、拆分前，先确认它不是公共 API、测试 seam、领域命名、可观测性边界或多调用方契约；确认不了就列为需确认，不要猜。

外部 code-simplifier / refactoring 资料只提供“保持行为不变、提升清晰度、避免错误抽象”的原则，不导入外部项目风格规则；具体代码风格以本仓库规则和目标模块规则为准。

## 关注点

- 当前范围新增但已无引用的 helper、分支、类型、fixture、mock 或导出。
- 临时命名、试验变量、过渡文件名和口径不一致的命名。
- 同一业务知识或行为被重复实现，或多个执行 lane 各写了一套近似逻辑；不要因为第一次文本相似就急着抽象。
- 几行简单逻辑只被一处引用，却被抽成函数、helper 或 wrapper，导致阅读跳转成本大于复用收益。
- 本次目标 diff 引入或明显变形的非公共 helper，是否为了 DRY 过早抽象并开始携带 mode、flag、type 分支或调用方特例。
- 只做透传、不隐藏复杂度、也不承载领域命名价值的浅层 wrapper / layer。
- 过深嵌套、嵌套三元、密集 one-liner 或 clever 写法是否让代码难读难调试。
- 本次 diff 引入的 guard / fallback 是否重复、叠加、互相遮蔽，且有证据表明已过期或可合并。
- 关键函数、状态流转、数据转换或错误处理里是否存在比较绕的逻辑，却缺少必要注释说明意图。
- 当前需求不再需要的配置、参数、flag、类型字段、测试数据和一次性验证脚本。
- 旧注释、旧文档、旧测试描述是否还在描述已被推翻的方案。
- 注释掉的旧代码、永远关闭的 feature flag、保留但不执行的分支是否仍留在目标 diff。
- 测试专用绕路是否进入生产代码，或生产代码是否为 mock 调用顺序变形。
- 遗留 `debug`、`probe`、临时日志、打印、断点和手动验证残留。
- 本次 diff 是否把同类职责散入 controller、service、job、gateway、helper 等多个入口。
- 同一链路内本次 diff 引入的错误处理风格是否和既有模块风格不一致。
- 未提交文件之间是否存在互相依赖但未统一收口的半成品。
- 本次已经触达的目标文件中，是否仍有一眼明确、局部可修的 format / lint 警告。

判断标准是“这个 diff 是否像一次成型的清晰实现”，不是追求代码洁癖。

## 自动修复边界

可以直接修复：

- 删除当前目标范围新增但已无引用的临时代码、fixture、测试数据和导出。
- 合并同一业务知识的重复实现；如果只是第一次文本相似，优先保留清晰重复，不急着抽象。
- 内联当前目标范围内过度抽离的简单单引用函数、helper 或 wrapper。
- 拆掉当前目标范围内本次 diff 引入或明显变形的非公共错误抽象：内联、拆分调用方特例，或退回更直接的局部实现。
- 内联只做透传且没有领域命名价值的浅层 wrapper。
- 扁平化无歧义的过深嵌套，替换嵌套三元和难调试的密集 one-liner。
- 移除临时日志、断点、probe 和一次性验证代码。
- 统一无歧义的临时命名、测试描述、旧注释和字段口径。
- 为关键函数或比较绕的逻辑补充最小必要注释，说明业务意图、状态前提或取舍原因；不要写显而易见的逐行解释。
- 删除当前需求不再使用的参数、配置、flag、注释掉的旧代码和永远不可达分支。
- 修复本次目标范围内已经触达文件的 format / lint 警告；可以顺手格式化这些文件，但如果会产生大面积 format churn，就只做局部修复，不扩展到未触达文件或全仓清扫。

必须先问人：

- 涉及业务语义、产品口径、数据口径或用户可见行为取舍。
- 删除大块逻辑，且无法从 diff 和相邻代码确认其已废弃。
- 影响公共接口、数据库 schema、迁移、部署配置或生产行为。
- 内联或拆分的 helper 已有多个调用方、承担公共 API、测试 seam、领域命名或可观测性边界。
- 多个合理收敛方向都成立，且会影响后续维护方式。
- 整理会扩大 diff、改变原需求边界，或可能覆盖其他执行 lane 的工作。

## 并行策略

小 diff 由主会话直接检查。fan-in 或跨模块 diff 可拆成 `2-3` 个只读 lane，按文件组或风险视角并行审查；子代理只输出发现、证据和建议，主会话负责 fan-in、判断 ROI 和最终修改。

如果 runtime 没有子代理，就按同样视角串行执行，不因此扩大 scope。

## No Goals

- 不检查或修正 Sky Flow artifact/status 一致性；需要时交给 `validate-flow`。
- 不清理历史无关死代码。
- 不顺手重构相邻模块。
- 不把 code smell 当作必须修改项；没有明确收益或证据不足时不改。
- 不为了第一次重复强行抽象；DRY 只针对同一业务知识，不针对表面相似文本。
- 不为了风格偏好扩大到未触达文件；但允许在本次目标文件内顺手修复明确 format / lint 警告。
- 不为了运行 formatter 产生大面积无关 format churn。
- 不把代码压缩成更短但更难读的 clever 写法。
- 不替代正式 review、安全审计、业务验收或测试设计。
- 不把主任务正常实现、优化、测试或文档更新包装成收敛成果。

## 参考资料

以下资料只用于校准“行为不变、减少补丁感、提升清晰度”的判断，不作为强制风格规则，也不覆盖本仓库模块规则：

- Claude Code Simplifier / code-simplifier 类资料：关注 agent 产物里的补丁式实现、绕路 helper、临时残留和过度抽象。
- Martin Fowler, *Refactoring: Improving the Design of Existing Code*：参考 code smells、行为保持式重构和小步整理原则。
- Kent Beck, *Tidy First?*：参考先做低风险局部整理、把结构性整理和行为修改分开的原则。
- John Ousterhout, *A Philosophy of Software Design*：参考降低复杂度、避免浅模块和信息泄漏的判断。
- Steve McConnell, *Code Complete*：参考命名、控制流、复杂度和构造质量的基础实践。
- Google Engineering Practices, Code Review Developer Guide：参考可维护性、复杂度、范围控制和 review 反馈分级。
- Refactoring.Guru Code Smells catalog：作为 smell 名称和排查方向索引；不得因为命中 smell 就自动修改。

## 输出

只输出收敛阶段专门做的熵减结果。没有实际收敛或需要确认的问题时，不输出固定区块。

```text
### 收敛 - 已完成
1. ...

### 收敛 - 需确认
1. ...
```

不要固定罗列命令过程。验证、扫描范围或跳过原因只有在影响判断时才说明。
