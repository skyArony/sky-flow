# Sky Flow Dependencies

Sky Flow 校验脚本使用 TypeScript 编写，并默认由 Node.js 直接运行。

## Runtime

默认要求：

- Node.js 24 或更新版本。

验证命令：

```bash
node --version
node .agents/skills/sky-flow/scripts/validate_flow.ts --root . "${SKY_FLOW_ROOT:-docs}/spec/tooling/sky-flow.md"
```

## 一键 setup

```bash
bash .agents/skills/sky-flow/scripts/setup.sh
```

setup 脚本只做本地环境检查，不会修改项目依赖。校验器没有第三方运行时依赖。

默认值满足项目需求时不需要配置。需要改变 Sky Flow artifact 根目录或默认输出语言时，推荐用 Codex 项目配置注入环境变量：

```toml
[shell_environment_policy.set]
SKY_FLOW_ROOT = "docs"
SKY_FLOW_LANG = "简体中文"
```

## 用户级软链接安装

Sky Flow 源码可以放在独立仓库中，再软链接到多个 runtime 的用户级 Skill 目录：

```bash
bash ~/Developer/Harness/sky-flow/scripts/install_user_symlinks.sh
```

脚本保持独立仓库为唯一源码，并创建：

- `~/.agents/skills/sky-flow -> ~/Developer/Harness/sky-flow`
- `~/.claude/skills/sky-flow -> ~/.agents/skills/sky-flow`
- `~/.codex/skills/sky-flow -> ~/.agents/skills/sky-flow`

## 外部 Skills 依赖

外部依赖的出发点：Sky Flow 自己负责 workflow 状态、artifact 纪律、路由和校验门禁；
`install_external_skills.sh` 只安装明确的知识型或工具型 Skill。计划、澄清、提交、验收、收敛、
handoff、progress tracking 等流程型能力应由 Sky Flow 子能力吸收，或由 runtime / 本地规则承担，不作为默认外部安装项。

## 项目级 adapter slot

`to-infra` 属于 Sky Flow 的基础设施 adapter slot，但 Sky Flow core 不安装、不实现具体项目环境。使用 Sky Flow 的项目如果需要查询或操作基础设施、日志、数据库、缓存、Metrics、Dashboard、告警、部署或外部系统，应在项目级提供自己的 `to-infra` Skill。

项目级 `to-infra` 应负责：

- 环境、命名空间、服务、端口、凭据来源和安全审批规则。
- 默认只读边界、允许写入的操作类型和禁止事项。
- 将具体查询分流到下表的知识型 / 工具型 Skill。
- 把证据输出为可回填 `to-debug`、`to-implement`、`to-acceptance` 或其他 artifact 的结构。

| 知识 / 工具类型     | Skill                   | 来源                           | Sky Flow 使用点                                       |
| ------------------- | ----------------------- | ------------------------------ | ----------------------------------------------------- |
| Skill 维护与发现    | `skill-creator`         | `anthropics/skills`            | 创建、更新和校验 Sky Flow 子 Skill。                  |
| Skill 维护与发现    | `find-skills`           | `vercel-labs/skills`           | 发现新的知识型或工具型 Skill 候选。                   |
| 库 / API 文档       | `context7`              | `intellectronica/agent-skills` | 查询库、框架或 API 文档；不接管 workflow。            |
| 前端设计知识        | `frontend-design`       | `anthropics/skills`            | 涉及界面、组件、页面或 UI 验收产物时提供设计知识。    |
| 可观测性 / Grafana  | `grafana-oss`           | `grafana/skills`               | Grafana 配置、数据源、面板和告警知识。                |
| 可观测性 / Grafana  | `dashboarding`          | `grafana/skills`               | 创建或维护 Grafana dashboard。                        |
| 可观测性 / Grafana  | `promql`                | `grafana/skills`               | 编写、解释或校验 PromQL 查询。                        |
| 可观测性 / Victoria | `victoriametrics-query` | `VictoriaMetrics/skills`       | 由项目级 `to-infra` 分流，用于查询 VictoriaMetrics 指标。 |
| 可观测性 / Victoria | `victorialogs-query`    | `VictoriaMetrics/skills`       | 由项目级 `to-infra` 分流，用于查询 VictoriaLogs 日志。 |
| 可观测性 / Alerting | `alertmanager-query`    | `VictoriaMetrics/skills`       | 由项目级 `to-infra` 分流，用于查询或维护 AlertManager 告警、inhibition 或 silence。 |

一键安装命令：

```bash
bash .agents/skills/sky-flow/scripts/install_external_skills.sh
```

脚本只安装上表默认外部依赖。运行该命令会写入用户级 `~/.agents/skills/`，适合换机初始化或补齐 Sky Flow
可选知识 / 工具能力。

## 可选 runtime

如果某个项目必须使用旧版 Node，可以在本地工具链中安装 `tsx`，再用：

```bash
pnpm add -D tsx typescript
pnpm exec tsx .agents/skills/sky-flow/scripts/validate_flow.ts
```
