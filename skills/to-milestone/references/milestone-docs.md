# Milestone Document Contract

本参考只在 `$to-milestone` 创建、细化、恢复或收口 milestone 文档时读取。milestone 是 Skill-owned durable document，不依赖中央 artifact schema 或全库关系图。

## Directory Shape

source spec 是树根，不额外创建 root milestone 文档：

```text
${SKY_FLOW_ROOT:-docs}/milestone/<spec-id>/
├── technology-selection/
│   ├── technology-selection.md
│   ├── database-selection/
│   │   └── database-selection.md
│   └── cache-selection/
│       └── cache-selection.md
└── walking-skeleton/
    └── walking-skeleton.md
```

完成后的压缩归档使用独立根目录，并保留原层级以便追溯：

```text
${SKY_FLOW_ROOT:-docs}/milestone-archive/<spec-id>/
└── technology-selection/
    └── technology-selection.md
```

规则：

- 每个节点一个目录，目录内只有一个与目录同名的主文档；支撑资料只有确有长期价值时才增加。
- 子 milestone 目录位于父目录中。一级 milestone 直接位于 `<spec-id>/` 下。
- 一次只创建当前评审层；不创建空子目录、未来 placeholder 或一次性展开整棵树。
- slug 使用稳定、简短、面向 outcome 的 kebab-case；排序与下一 frontier 不依赖数字前缀或 mtime。
- 移动节点会改变层级语义，必须重新检查 parent coverage、硬依赖和受影响节点 review。
- active tree 只保留仍需规划、实施、验收或汇总的节点。归档节点移到 `milestone-archive`；active parent 通过稳定 id 和 archive locator 引用它，不复制归档正文。

## Frontmatter

推荐最小形状：

```yaml
---
id: <stable-milestone-id>
artifact_type: milestone
source_id: <spec-id>
parent_id: <parent-milestone-id | spec-id>
definition: outline | branch | executable | stale
review: pending | approved
status: not_started | in_progress | completed | archived | abandoned
hard_dependencies: []
---
```

这些字段由 `to-milestone` 自己解释，不是 Sky Flow 全局 schema：

- `id` 在当前 source spec 的树内稳定唯一。路径可以表达层级，id 不需要复制完整路径。
- `artifact_type` 只用于人和工具识别文档种类，不进入中央白名单。
- `source_id` 指向规范性 spec。
- 一级节点的 `parent_id` 使用 source spec id；其他节点使用直接父 milestone id。
- `definition: outline` 表示本层已识别但尚未决定 branch / executable。
- `definition: branch` 表示直接子层已建立。
- `definition: executable` 表示已停止细化，等待或正在 runtime 实施。
- `definition: stale` 表示 source spec 或上游决定已使当前定义失效；重新评审前不得实施。
- `review: pending` 表示当前 definition 或其材料尚未获得明确人类批准。
- `review: approved` 可以来自覆盖当前范围的自然语言授权，不要求人类逐字段或逐 gate 重复确认；记录结论，不记录聊天流水。
- `status` 只描述交付状态；等待评审不伪装成实施进度。
- `status: archived` 只用于已经完成压缩并移出 active tree 的节点，不替代 `completed` 所要求的人类验收。
- `hard_dependencies` 只列真实 gate。空列表表示没有已知硬依赖，不表示必须并行。

不要为了统一格式给所有节点增加空字段。确需表达 required / optional 时可以增加 `required: true | false`；原始 spec outcome 只有经人类明确接受才可变为 optional 或 abandoned。

## Shared Sections

每个节点保持以下方向性内容：

```markdown
# <Milestone Title>

## Outcome

<完成后稳定成立的能力、决定或系统状态。>

## Scope

- In: <明确包含>
- Out: <明确不包含>

## Spec Coverage

- <source spec 中被本节点承接的 requirement、scenario、constraint 或 section>

## Dependencies

- <硬依赖、共享 contract 或 none>

## Progress

- Checkpoint: <当前稳定状态>
- Next: <下一次评审、细化、执行或验收入口>
- Blockers: <解除条件或 none>
- Evidence: <已有结论与残余风险；没有则省略>
```

不复制 source spec 的整段 intent、requirements 或 constraints。引用稳定标题或 requirement id 即可；没有编号时使用清楚的语义引用，不为 milestone 强行重写 spec 编号体系。

## Outline

outline 只需要说明 outcome、边界、coverage 和已知硬依赖。不要提前填写虚假的验收、测试或子节点。

人类批准当前层后，outline 可以保持 `definition: outline`、`review: approved`，直到被选中继续细化。选中时基于最新事实判断 branch 或 executable。

## Branch

branch 额外增加：

```markdown
## Direct Children

- [<child outcome>](<relative child document path>) — <它承担的父级范围>

## Decomposition Rationale

<为什么这些直接子节点形成清楚的独立验收边界；说明交叉 coverage 或父级整体 closure。>
```

只列直接子节点，不维护全树索引、task DAG、owner 或并行 lane。父级 Progress 用覆盖快照汇总，不追加每轮时间线。

## Executable Leaf

executable leaf 额外增加：

```markdown
## Acceptance

- <可观察且可由证据判断的完成条件>

## Verification Intent

- Core behavior: <最高价值行为场景与预期结果>
- Unit: <需要保护的稳定逻辑 seam，或不适用理由>
- Integration / E2E: <必要入口，或不适用理由>
- Human: <人类最终验收方式与必须观察的结果>

## Runtime Handoff

- Ready for runtime plan: yes | no
- Constraints: <runtime 不得越过的范围、authority 与 stop condition>
```

行为场景描述输入、前置状态和可观察结果；不写 mock、私有 helper、测试代码或调用顺序。项目已有测试治理时遵守项目规则。

Runtime Handoff 不写文件清单、代码步骤、命令、commit、Agent 分工或详细顺序。`Ready for runtime plan: yes` 在 definition、验收合同和实施授权能从人类意图确定后成立；不要求逐项重复批准。

## Review And State Transitions

推荐转换：

```text
outline/pending/not_started
  └─ human approves level → outline/approved/not_started
       ├─ split proposed → branch/pending/not_started
       │    └─ human approves children → branch/approved/not_started
       └─ leaf proposed → executable/pending/not_started
            └─ human intent authorizes contract / execution → executable/approved/not_started
                 └─ runtime starts → executable/approved/in_progress
                      └─ evidence + human acceptance → executable/approved/completed
```

任何 approved definition 被规范性变化推翻时改为 `definition: stale`、`review: pending`。保留已经成立的 delivery evidence，但暂停继续实施。completed 节点是否需要 reopen 属于人类决策；不得仅因相邻增强自动改写历史完成结论。

Branch 状态按 required children 汇总：

- 没有 child 开始：`not_started`。
- 任一 child 已开始或部分完成、但 required children 未全部完成：`in_progress`。
- 所有 required children 完成，且父级独有整体 gate 已关闭：`completed`。
- `abandoned` 必须有明确人类决定或 source spec 已正式移除该 outcome。

## Closure

Leaf 收口顺序：

1. runtime 完成与风险匹配的测试、静态检查、build、真实路径和 diff sanity。
2. 长期架构、contract 或外部语义决定先提升到 source spec。
3. 在 leaf Progress 中压缩记录 outcome、关键 evidence、残余风险和人类验收入口。
4. 请求人类验收；未明确通过时保持 `in_progress`。
5. 明确通过后标记 `completed`，逐级汇总 parent，并推荐下一 approved frontier。

Milestone 文档不保存完整命令输出、逐文件 diff、tool / Agent 消息或聊天流水。

## Archive And Compaction

归档资格：

- 节点已经 `completed`，对应人类验收明确成立。
- 节点没有未完成、stale、等待评审或正在实施的 descendant。
- 长期设计决定、外部行为、数据语义、authority、最终 acceptance 和必要 residual risk 已写入最新 spec。
- 代码、测试和 spec 足以说明当前系统；删除 milestone 实施细节不会破坏当前工作的恢复入口。

归档动作：

1. 优先选择完整关闭的最高层 subtree，避免把大量 leaf 分散留在 active tree。
2. 将 subtree 移到 `${SKY_FLOW_ROOT:-docs}/milestone-archive/<spec-id>/` 下的原相对层级。
3. 每个归档文档改为 `status: archived`，压缩为下面的 archive summary；已无追溯价值的 descendant 文档可以折叠进最近的归档祖先摘要后删除。
4. 更新仍 active 的 parent：保留 child id、完成结论和 archive locator，不保留旧的 active 链接或详细 Progress。
5. 检查 active frontier、父级汇总和 spec 引用仍可恢复；归档目录不得被当作下一执行入口扫描。

归档文档只保留：

```markdown
# <Milestone Title>

## Outcome

<经人类验收、已经交付的阶段结果。>

## Spec Coverage

- <最终由 source spec 承接的 requirement / decision / acceptance 引用>

## Completion Summary

- Accepted: <人类验收结论或 durable acceptance locator>
- Evidence: <稳定的测试、commit、release 或其他短索引>
- Residual risk: <仍需从 spec 读取的风险引用，或 none>
```

归档时删除：实施期 Scope 展开、Dependencies、Direct Children 清单、Decomposition Rationale、Verification Intent、Runtime Handoff、过程性 Progress、命令输出和逐文件说明。归档摘要不重新描述当前代码结构、API、schema 或配置；当前实现以代码为准，规范性语义以 spec 为准。
