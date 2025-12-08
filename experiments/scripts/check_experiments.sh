#!/usr/bin/env bash
# Quick check for experiment completion status

RESULTS_DIR="$(cd "$(dirname "$0")/../results" && pwd)"

echo "实验完成状态检查"
echo "===================="
echo ""

for exp in exp1 exp2 exp3; do
    result_file="$RESULTS_DIR/${exp}_results.json"
    if [ -f "$result_file" ]; then
        echo "✓ ${exp}: 已完成"
        echo "  文件: $result_file"
        size=$(wc -c < "$result_file")
        echo "  大小: ${size} bytes"
    else
        echo "✗ ${exp}: 未完成"
    fi
    echo ""
done

echo "运行汇总: uv run summarize_results.py"
