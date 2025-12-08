#!/bin/bash
# 运行实验脚本（需要后端已启动）
# 使用 uv 运行 Python 脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_SCRIPTS_DIR="$PROJECT_ROOT/scripts"

echo "════════════════════════════════════════════════════════════"
echo "Mul-in-One 实验脚本运行器 (uv)"
echo "════════════════════════════════════════════════════════════"

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "✗ uv 未安装，请先安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ uv 版本: $(uv --version)"

# 检查环境
echo ""
echo "[1/3] 检查环境..."
cd "$EXP_SCRIPTS_DIR"
uv run check_env.py
if [ $? -ne 0 ]; then
    echo "✗ 环境检查失败，请确保后端服务已启动"
    exit 1
fi

# 运行三个实验
echo ""
echo "[2/3] 运行 RAG 评估实验..."
uv run exp1_rag_evaluation.py \
  --config config/rag_eval_config.json \
  --api-config config/api_config.json \
  --seed 42

echo ""
echo "[3/3] 运行调度器评估实验..."
uv run exp2_scheduler_eval.py \
  --config config/scheduler_config.json \
  --api-config config/api_config.json \
  --seed 42

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ 实验运行完成！"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "结果文件:"
echo "  - results/exp1_results.json (RAG 评估)"
echo "  - results/exp2_results.json (调度器评估)"
echo ""
echo "可选：运行 Tool-First 对比:"
echo "  uv run exp3_tool_first_compare.py --seed 42"
echo "════════════════════════════════════════════════════════════"
