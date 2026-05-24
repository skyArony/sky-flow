#!/usr/bin/env bash
set -euo pipefail

# 检查 Sky Flow 本地脚本运行环境；不安装依赖，也不修改项目配置。
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT_DIR/scripts/validate_flow.ts"
SKY_FLOW_ROOT_VALUE="${SKY_FLOW_ROOT:-docs}"
SKY_FLOW_LANG_VALUE="${SKY_FLOW_LANG:-简体中文}"

# 校验器依赖 Node.js 直接执行 TypeScript，低版本 Node 需要项目自行接入 tsx。
if ! command -v node >/dev/null 2>&1; then
  echo "node is required. Install Node.js 24+ or provide a project runtime that can execute TypeScript."
  exit 1
fi

NODE_MAJOR="$(node -p "Number(process.versions.node.split('.')[0])")"
if [ "$NODE_MAJOR" -lt 24 ]; then
  echo "Node.js 24+ is recommended for direct TypeScript execution. Current: $(node --version)"
  echo "Optional fallback: pnpm add -D tsx typescript && pnpm exec tsx $VALIDATOR"
  exit 1
fi

# 跑一次空范围校验，确认当前目录下的 Sky Flow artifact 可以被扫描。
node "$VALIDATOR" --root "$(pwd)" >/dev/null
echo "Sky Flow TypeScript runtime is ready."
echo "Sky Flow runtime config: SKY_FLOW_ROOT[$SKY_FLOW_ROOT_VALUE], SKY_FLOW_LANG[$SKY_FLOW_LANG_VALUE]"
echo "No config is needed when defaults fit. To customize, set SKY_FLOW_ROOT / SKY_FLOW_LANG in .codex/config.toml under [shell_environment_policy.set]."
