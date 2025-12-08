#!/usr/bin/env python3
"""Summarize experiment results."""

import json
from pathlib import Path

def main():
    results_dir = Path(__file__).parent.parent / "results"
    
    print("=" * 70)
    print("实验结果汇总".center(70))
    print("=" * 70)
    print()
    
    # Exp1: RAG Evaluation
    print("📊 实验 1: RAG 检索质量评估")
    print("-" * 70)
    exp1_path = results_dir / "exp1_results.json"
    if exp1_path.exists():
        exp1 = json.loads(exp1_path.read_text())
        print(f"  评估指标:")
        for top_k_key in ["top_k=1", "top_k=3", "top_k=5"]:
            if top_k_key in exp1:
                print(f"    {top_k_key.upper()}:")
                metrics = exp1[top_k_key]
                for metric, value in metrics.items():
                    print(f"      {metric.upper()}: {value:.4f}")
    else:
        print("  ⚠ 结果文件未找到")
    print()
    
    # Exp2: Scheduler Evaluation
    print("⚙️  实验 2: 多 Agent 调度器评估")
    print("-" * 70)
    exp2_path = results_dir / "exp2_results.json"
    if exp2_path.exists():
        exp2 = json.loads(exp2_path.read_text())
        print(f"  Gini 系数 (公平性): {exp2.get('gini', 'N/A'):.4f}")
        print(f"  垄断率: {exp2.get('monopoly_rate', 'N/A'):.2%}")
        print(f"  冷启动率: {exp2.get('cold_rate', 'N/A'):.2%}")
        print(f"  最大并发 Agent 数: {exp2.get('max_agents', 'N/A')}")
        print(f"  静默阈值: {exp2.get('silence_threshold_seconds', 'N/A')}s")
    else:
        print("  ⚠ 结果文件未找到")
    print()
    
    # Exp3: Tool-First Comparison
    print("🔧 实验 3: Tool-First vs Baseline 对比")
    print("-" * 70)
    exp3_path = results_dir / "exp3_results.json"
    if exp3_path.exists():
        exp3 = json.loads(exp3_path.read_text())
        print(f"  测试用例数: {exp3['cases']}")
        print(f"  Token 节省率: {exp3['token_saving_rate']:.1%}")
        print(f"  Baseline 平均 Token: {exp3['baseline_token_avg']:.0f}")
        print(f"  Tool-First 平均 Token: {exp3['tool_first_token_avg']:.0f}")
        print(f"  Baseline 延迟: {exp3['baseline_latency_s']:.3f}s")
        print(f"  Tool-First 延迟: {exp3['tool_first_latency_s']:.3f}s")
        print(f"  评估指标: {', '.join(exp3['metrics'])}")
    else:
        print("  ⚠ 结果文件未找到")
    print()
    
    print("=" * 70)
    print("✓ 所有实验完成！".center(70))
    print("=" * 70)
    print()
    print("结果文件位置:")
    print(f"  - {exp1_path}")
    print(f"  - {exp2_path}")
    print(f"  - {exp3_path}")
    print()

if __name__ == "__main__":
    main()
