---
name: to-knowledge
description: 'Capture a concise, source-backed, project-agnostic developer knowledge note only when the user explicitly invokes $to-knowledge. Never record concrete business, customer, project, incident, domain-rule, internal-environment, account, financial, operational, or project-implementation information.'
---

# to-knowledge

`to-knowledge` 只在用户显式调用时，把开发过程中发现的通用技术事实、踩坑、注意点、工具 / 库特性和技术选型对比沉淀成长期知识笔记。日常任务可以在交付中推荐值得沉淀的主题，但不自动创建笔记。

默认写入 `${SKY_FLOW_ROOT}/knowledge/`。knowledge note 不是 Sky Flow workflow artifact；默认不要写 `artifact_type` frontmatter，除非本地知识库已经定义了独立 schema。

硬边界：knowledge note 必须是纯粹的业务无关技术知识。不得落下任何具体业务、客户、项目、线上事故、产品规则、运营策略、账号 / 订单 / 财务数据、内部环境或实施计划信息；这些信息不能作为正文、例子、证据摘录、文件名、路径、标题、标签或来源说明出现。即使技术经验来自业务场景，也必须剥离到完全不依赖业务上下文、可由公开或通用技术证据支撑的形式；剥离不了就不要写入 knowledge。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言。
2. 判断是否值得沉淀：只记录业务无关、项目无关、跨项目可复用、后续搜索成本明显高于记录成本的具体技术知识。
3. 确认证据：优先官方文档、标准、源码仓库、release notes、厂商公告或维护者文档；会随时间变化的信息必须查最新来源。
4. 读取本地 docs 入口规则：如果 `${SKY_FLOW_ROOT}/AGENTS.md` 或 `${SKY_FLOW_ROOT}/CLAUDE.md` 对 `knowledge/` 有目录或 TOC 规则，必须遵守。
5. 搜索已有笔记：先在 `${SKY_FLOW_ROOT}/knowledge/` 查同主题，优先更新已有笔记，避免重复文件。
6. 选择路径：`${SKY_FLOW_ROOT}/knowledge/<category>/<slug>.md`，slug 使用短横线英文；目录不存在时创建。
7. 写入干练笔记：记录结论、适用场景、注意点、来源链接和检查日期；不要大段复述原文。
8. 自检边界：确认没有任何项目 / 业务 / 客户 / 事故 / 产品规则 / 账号数据 / 内部环境 / 密钥 / 内部 URL，没有未经验证的事实，没有把当前任务计划写成知识。

## Capture Gate

应该沉淀：

- 基础设施、网络、Kubernetes、操作系统、云服务或运维工具的通用行为、风险和配置要点。
- 基础组件、库、框架、CLI、协议或标准的能力边界、关键限制、版本差异和常见坑。
- 技术选型候选、全栈类型安全方案、通信协议、存储 / 缓存 / 队列方案等通用对比。
- 长篇官方文档、RFC、设计文章或 release notes 中对日常开发有复用价值的精简摘要。
- 排障或调研中发现的非项目专属经验，例如“某类自动更新会影响集群稳定性，需要关闭或 pin 版本”。

不要沉淀：

- 任何业务相关信息：业务事实、领域规则、客户需求、线上事故细节、产品 / 运营策略、账号 / 订单 / 玩家 / 用户 / 财务数据、内部部署拓扑、密钥、内网地址、公司专有流程或项目专属命名。
- 看似“泛化”但仍依赖具体业务背景才能成立的结论；除非能剥离成业务无关技术事实并用通用来源证明，否则不要写。
- 当前 feature 的设计、范围、Progress、验收或 handoff；这些属于 `to-spec` / `to-acceptance` / `to-handoff`。
- 一眼能从官方首页得到、无需总结的普通入口链接。
- 未查证的传闻、论坛结论或模型记忆；只能作为待验证线索，不写成事实。
- 为了“完整”搬运原始文档、教程全文、API 列表或大段代码。

## Invocation Policy

- 只有用户显式调用 `$to-knowledge` 时才创建或更新笔记；主任务中偶然发现知识点不自动旁路沉淀。
- 一次默认只处理一个高价值主题；用户明确要求批量整理时才扩展。
- 默认由当前 Agent 完成。只有用户显式要求 delegation / subagent 时才派发，并保持 Topic、Evidence、Boundary、Output 四项输入紧凑。
- 需要额外长时间调研、登录或生产系统证据时，先说明缺口与授权边界，不扩大当前任务。

## Categories

优先使用这些目录；本地已有更细分类时沿用本地结构。

- `infrastructure/`：Kubernetes、网络、OS、云服务、Tailscale、部署基础设施。
- `libraries/`：npm / Go / Python / Rust 等库、框架、SDK、协议实现。
- `tooling/`：构建、测试、代码生成、CLI、编辑器、Agent 工具链。
- `architecture/`：通用架构模式、类型安全、服务通信、状态同步、可观测性设计。
- `data/`：数据库、缓存、队列、对象存储、搜索、数据建模。
- `security/`：认证授权、密钥管理、供应链、安全边界和权限模型。

## Note Template

正文保持短小。没有价值的 section 直接省略。

```markdown
# <Topic>

最后更新：<YYYY-MM-DD>
检查日期：<YYYY-MM-DD>
分类：<category>

## 结论

- <1-5 条可复用结论。>

## 适用场景

- <什么时候应该想起这条知识。>

## 注意点

- <限制、版本差异、迁移风险、易踩坑。>

## 选型对比

| 方案 | 适合 | 不适合 | 关键依据 |
| --- | --- | --- | --- |
| <option> | <case> | <case> | <source / reason> |

## Sources

- [<source title>](<url>)：<为什么引用它，或它证明了哪条结论。>
```

## Writing Rules

- 先写结论，再写来源；读者应在 30 秒内知道这条笔记是否有用。
- 链接优先指向权威来源；第三方文章只能作为补充，不替代官方依据。
- 对长文档做摘要时，只保留决策和使用会受影响的信息，不复制章节结构。
- 对比较类笔记，只比较会改变选型的维度，例如类型安全、运行时成本、生态成熟度、维护状态、迁移成本和失败模式。
- 对时间敏感事实写清 `检查日期`，必要时写“截至 <date>”；不要把当前状态伪装成永久事实。
- 明确区分事实、推论和个人 / Agent 判断；推论必须标注依据。
- 保持单条笔记聚焦一个主题。主题扩大时拆分文件，并在文末互链。

## Recommendation Boundaries

- 发现项目设计真相源缺口：推荐 `to-spec`，不要写进 knowledge。
- 发现尚不进入实施的问题或机会：推荐 `to-issue`。
- 当前阶段被阻塞且需要恢复条件：推荐 `to-backlog`。
- 需要跨会话可执行恢复状态：推荐 `to-handoff`。
- 创建或修改了真正的 Sky Flow workflow artifact：运行 `validate-flow`。只写普通 knowledge note 时不需要运行 `validate-flow`。

## Self-Review

- Scope：是否完全业务无关、项目无关、跨项目可复用；是否不依赖具体业务背景才成立。
- Evidence：是否有权威链接；时间敏感事实是否查了最新来源并写明检查日期。
- Brevity：是否只保留结论、适用场景、坑点和来源，没有搬运原文。
- Safety：是否没有任何业务事实、客户信息、账号 / 订单 / 财务数据、产品规则、运营策略、密钥、内部地址、项目专属部署细节或事故细节。
- Placement：是否先搜索并更新已有笔记，路径和分类是否稳定。
