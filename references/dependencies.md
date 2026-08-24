# Sky Flow Dependencies

Sky Flow 通过 `./install.sh` 提供安装、更新和 readiness 管理。核心 workflow 不依赖中央 artifact validator，也没有额外 Node.js runtime 要求。

## Install And Update

```bash
./install.sh
./install.sh --dry-run
./install.sh list
./install.sh doctor
./install.sh update
./install.sh to-claude-review
```

安装模型：

- Claude 从 `~/.claude/skills` 读取 Skill。
- Codex 从 `~/.agents/skills` 读取 Skill。
- Claude 不发现 nested Skill，因此安装 suite entry 与 callable children 的直接链接。
- Codex 默认安装 suite entry 并从 suite root 发现 children；需要显式顶层调用的 `to-milestone` 额外安装直接链接。
- copy-mode 会比较完整 managed subtree，包括 references 和 scripts。
- Skill-level `install_targets` 继续生效；例如 `to-claude-review` 只安装到 Codex。
- `archive/skills/` 下的历史能力不参与发现、安装、更新或 readiness。

`eli5` 位于 `skills/eli5/`，是 Sky Flow suite 内嵌的 leaf 讲解能力，不依赖用户级或项目级 Skill。`to-milestone` 通过 suite-relative 路径读取它；缺失时 leaf 必须停在实现前，不能跳过 HTML Web 讲解。

升级后运行 `./install.sh update` 与 `./install.sh doctor`。安装器只自动移除明确指向当前 checkout retired path 的 symlink；copied 或 foreign install 需要用户显式处理。

## Runtime Config

Sky Flow 只读取 runtime 提供的环境变量：

- `SKY_FLOW_ROOT`：durable document 根目录，默认 `docs`。
- `SKY_FLOW_LANG`：文档与 Skill 输出语言，默认跟随用户。

示例：

```toml
[shell_environment_policy.set]
SKY_FLOW_ROOT = "docs"
SKY_FLOW_LANG = "简体中文"
```

## Project Adapter Slot

`to-infra` 是 project-provided adapter slot。Sky Flow core 不包含项目凭据、环境范围或基础设施命令；项目按自身审批边界提供对应 Skill 与工具。
