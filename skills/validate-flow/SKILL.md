---
name: validate-flow
description: 'Run an explicit full-set or migration audit for Sky Flow artifacts. Routine artifact writers call the deterministic validator directly on changed paths instead of entering this skill.'
---

# validate-flow

`validate-flow` 是显式 artifact audit，不是 durable 写回后的自动语义 pass。日常创建或修改 artifact 时，由当前 owning Skill 直接运行 `validate_flow.ts`；只有用户要求全量检查、迁移审计或独立 artifact audit 时才进入本 Skill。

当前 file-backed artifact 只有：`spec`、`plan`、`issue`、`acceptance`、`backlog`、`handoff`。plan 是可选 thin working set；task / step、owner、依赖、并行与 fan-in 批次仍属于退休拓扑或 runtime。

## Quick Path

1. 确定 `SKY_FLOW_ROOT` 和 `SKY_FLOW_LANG`；未设置时默认 `docs` 和 `简体中文`。
2. 全量 audit 不传 artifact 路径：

```bash
node .agents/skills/sky-flow/scripts/validate_flow.ts
```

仓库内开发时也可以运行：

```bash
node scripts/validate_flow.ts
```

3. 用户只要求定点 audit 时传入明确文件或目录。显式文件范围只做局部 lint，不解析未传入 source，也不因此产生 missing-source warning。
4. 先处理 `errors`，再判断本地 `warnings`；不要从成功报告派生新的模型审查轮次。

报告 schema 为 `sky-flow-validate-report/v3`，只包含配置、summary、checked artifacts、errors 和 warnings；不输出 source graph 或通用 LLM review hints。

## Deterministic Checks

脚本只检查机器可以可靠判断且维护成本低的内容：

- frontmatter、最小字段、枚举、id / 文件名和 root。
- spec / plan 的旧数字前缀、退休 `plan/done`、issue fixed 目录和 acceptance type。
- plan 不允许 `draft`，必须保留稳定 `source_type: spec` / `source_id` locator；全量 audit / commit / CI 检查孤儿 plan，局部 lint 不解析 source。
- ready / active / completed spec 与 active plan 是否缺少 `Progress` heading。
- retired task / step artifact、legacy plan 字段、topology / append-log body section 或其他退休字段。

validator 不维护文档关系图，不同步 plan / spec lifecycle，不检查多 active plan，不反向查找 abandoned → backlog，也不验证 acceptance / backlog / handoff 的可选 provenance。

## Semantic Ownership

- spec 的设计一致性、readiness、Progress 和 constraints 由 `to-spec` 在写入时负责。
- plan 的物化价值、source spec 是否仍 ready / unfinished、多 active plan 选择、promotion 和 closure 由 `to-implement` 在真实创建 / 恢复 / 收口边界负责。
- acceptance、backlog、handoff 和 issue 的内容充分性由各自 owning Skill 负责。
- 用户明确要求 semantic artifact review 时，只审查其指定范围；不要因为 validator 成功而自动扩大到全库。

## Invocation Policy

- routine artifact create / update：owning Skill 直接对 changed paths 运行 deterministic script，不进入本 Skill。
- plan resume：`to-implement` 解析 source spec 并做一次轻量 readiness / ambiguity 检查；不先做全库 audit。
- staged workflow artifact commit、CI 或 migration：运行 full-set deterministic validator。
- 用户显式要求 `$validate-flow`：按其指定范围执行 audit。

## Boundaries

- 只读检查，不自动修复。
- 不做代码 review、diff consolidation、普通测试选择或 runtime 调度。
- 不用 source graph 或另一套严格 schema 取代已经删除的执行拓扑。
- `html_interactive` 仍是保留枚举，默认 warning。

## Dependencies

依赖和安装方式见 `../../references/dependencies.md`。validator 默认使用 Node.js 直接运行 TypeScript。
