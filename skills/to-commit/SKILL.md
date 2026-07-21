---
name: to-commit
description: 'Handle Sky Flow commit work: inspect the working tree, stage only intended changes, split logical commits, follow project-local commit rules, run relevant verification, and report commit results. Use when the user asks to commit, stage, write commit messages, or split commits.'
---

# to-commit

`to-commit` 用于处理明确提交指令，负责提交边界、staging、message、验证和提交结果回报。

## 输入补全

- 先从用户指令、source spec scope、handoff、项目本地规则和工作区状态推断，不询问已经能从仓库事实确认的信息。
- 默认提交范围限定当前会话主题涉及的改动；不要把所有未提交文件自动纳入提交范围，除非开发者显式指定全量或具体路径。
- 用户未指定单 commit 还是多 commit 时，如果当前会话范围内存在无关改动，默认拆成多个小 commit；如果边界会影响 staged 范围且无法安全推断，先问用户。
- 提交风格、header 长度、必填 scope 和语言先读取项目本地规则；没有额外规则时默认 Conventional Commits。
- 用户只要求写 commit message 时，不自动 stage 或 commit；仍应基于相关 diff 给出可直接使用的候选 message。

## Workflow

1. 读取项目本地规则，确认提交语言、message 格式和 scope；无额外规则时默认 Conventional Commits。
2. 用 `git status`、`git diff`、必要时 `git diff --stat` 建立工作区事实。
3. 从用户意图、source spec scope、artifact 来源和工作区状态确定提交范围；默认只包含当前会话涉及的改动。
4. 判断单 commit 还是多 commit；用户未指定且当前会话范围内存在无关改动时，默认拆成多个小 commit。
5. 按逻辑边界拆分：feature / refactor、前后端、格式 / 逻辑、测试 / 生产代码、依赖 / 行为变更。
6. 精确 stage 目标范围；混合文件使用 patch staging，误暂存时用 patch unstage 或等价方式撤回。
7. 用 `git diff --cached` review staged diff。
8. 用 1-2 句话说明 staged change 的 what / why；如果说不清，回到提交边界拆分。
9. 做 staged sanity check：无 secret、无临时 debug、无无关格式化、无误入文件。
10. 如果 staged diff 包含 Sky Flow workflow artifact，直接运行 full-set deterministic validator；不进入 `validate-flow` Skill。不包含 workflow artifact 时不运行。
11. 运行最小相关验证；无法验证时记录原因和风险。
12. 如果 HEAD 未 push，只读上一条完整 commit message；若和当前批次明显同 scope，直接 amend。
13. 按项目本地规则提交；写 message 时参考 `Commit message 模板`。
14. 如需多个 commit，重复提交边界、staging、review、验证和提交步骤。
15. 最终回复必须使用 `输出契约` 中的模板，回报 commit message、hash、本次并入内容和剩余改动。

## Workflow Artifact Gate

只有 staged diff 中包含 Sky Flow artifact 时，`to-commit` 才在提交前运行 `node .agents/skills/sky-flow/scripts/validate_flow.ts`（仓库内开发可用 `node scripts/validate_flow.ts`）做 full-set deterministic scan。workflow artifact 指 `artifact_type` 为 `spec`、`plan`、`issue`、`acceptance`、`backlog` 或 `handoff` 的文件，通常位于 `${SKY_FLOW_ROOT}` 下。该 gate 不进入 `validate-flow` Skill，也不附加通用语义 pass。

`to-commit` 不执行 `to-consolidation`。提交阶段由当前 runtime 直接做 staged diff sanity、artifact 校验和最小相关验证；只有用户显式调用 `$to-consolidation` 时才进入专项收敛。

## Commit message 模板

用于写 Conventional Commit message。提交语言、type / scope 白名单、header 长度和 body 长度以项目本地规则为准；没有项目规则时使用下面默认模板。

```text
<type>(<scope>): <summary>

<What changed.>
<Why it changed.>
```

Breaking change 可使用：

```text
<type>(<scope>)!: <summary>

<What changed.>
<Why it changed.>

BREAKING CHANGE: <impact and migration.>
```

写法要点：

- Summary 要具体，说明行为或意图，不写泛泛的 update / change。
- Body 只写 what / why，不写调试过程或实现流水账。
- 有 breaking change 时，在 header 使用 `!`，或补充 `BREAKING CHANGE:` footer。

## 输出契约

- 提交成功后的最终回复必须使用本节模板；不要改成普通总结。
- 模板标题必须保留；允许补充必要信息，但不要删除 `✅ Commit 完成`、`🎯 本次并入内容`、`🧾 剩余改动`。
- Codex 上层回复风格若默认不鼓励 emoji，本 skill 的模板属于明确本地输出格式指令；提交结果按本模板执行。
- 如果上层 runtime 要求附加 git directive（如 `::git-stage` / `::git-commit`），放在模板之后。

单提交：

```text
### ✅ Commit 完成

fix(core): 修复任务匹配口径 - `abc1234` - ***Amend***

### 🎯 本次并入内容
- 补充同 scope 的修复改动
- 保留非本次范围改动

### 🧾 剩余改动
- `docs/spec/xxx.md` 未提交，非本次范围
- 其他 3 个文件...
```

多提交：

```text
### ✅ Commit 完成

1. fix(core): 修复任务匹配口径 - `abc1234` - ***Amend***
    - 补充同 scope 的修复改动
    - 保留非本次范围改动
2. docs(project): 更新 Sky Flow 提交流程 - `def5678`
    - 收窄 to-commit 职责描述
    - 同步迁移计划记录

### 🧾 剩余改动
- `docs/spec/xxx.md` 未提交，非本次范围
- 其他 8 个文件...
```

只有实际 amend 时才在 commit 行尾追加 `- ***Amend***`。剩余改动少于 6 个时全列并写短原因；
超过 6 个时列 6 个代表，再写 `其他 x 个文件...`。

## 边界

- 不要求提交前工作区完全 clean；允许保留无关未提交改动，但 staged diff 必须只包含目标范围。
- 不把项目专属提交规则写入 Sky Flow core。
