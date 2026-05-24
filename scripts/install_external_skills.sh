#!/usr/bin/env bash
set -euo pipefail

# 安装 Sky Flow 推荐的外部知识 / 工具型 Skills；这些不是 artifact schema 的运行时依赖。
# 流程型 Skills 默认不安装，避免与 Sky Flow 自身的路由、状态和 artifact 纪律冲突。
if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required. Install Node.js/npm before installing external Skills."
  exit 1
fi

# ToDo: 推荐 Skill 清单变化时，只维护这里的集中安装入口。
install_skill() {
  local repo="$1"
  local skill="$2"

  echo "Installing ${skill} from ${repo}"
  npx --yes skills add "$repo" --skill "$skill" -g -y
}

# Skill 维护与发现
install_skill "https://github.com/anthropics/skills" "skill-creator"
install_skill "https://github.com/vercel-labs/skills" "find-skills"

# 库 / API 文档
install_skill "https://github.com/intellectronica/agent-skills" "context7"

# 前端设计知识
install_skill "https://github.com/anthropics/skills" "frontend-design"

# 可观测性 / Grafana
install_skill "https://github.com/grafana/skills" "grafana-oss"
install_skill "https://github.com/grafana/skills" "dashboarding"
install_skill "https://github.com/grafana/skills" "promql"

# 可观测性 / VictoriaMetrics 和 AlertManager
install_skill "https://github.com/VictoriaMetrics/skills" "victoriametrics-query"
install_skill "https://github.com/VictoriaMetrics/skills" "victorialogs-query"
install_skill "https://github.com/VictoriaMetrics/skills" "alertmanager-query"

echo "Sky Flow external knowledge/tool Skills are installed."
