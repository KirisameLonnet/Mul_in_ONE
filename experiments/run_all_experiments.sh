#!/usr/bin/env bash
set -euo pipefail

# Run all experiments sequentially
# This script assumes backend is already running

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/scripts"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_step() {
    echo -e "${YELLOW}→${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if backend is running
check_backend() {
    if ! curl -s http://localhost:8000/api/personas &>/dev/null; then
        log_error "后端未运行！请先启动后端:"
        echo "  cd ../../scripts"
        echo "  ./start_backend.sh"
        exit 1
    fi
    log_info "后端运行正常"
}

# Initialize backend data if needed
initialize_backend() {
    log_step "检查是否需要初始化后端数据..."
    
    # Check if test user exists
    if curl -s 'http://localhost:8000/api/personas?username=eval_user' 2>/dev/null | grep -q '"id"'; then
        log_info "后端数据已初始化"
    else
        log_step "初始化后端数据..."
        ./init_backend.sh || {
            log_error "后端初始化失败"
            exit 1
        }
    fi
}

# Run experiments
run_experiments() {
    local seed=${1:-42}
    
    echo ""
    echo "========================================"
    echo "  运行所有实验 (seed=$seed)"
    echo "========================================"
    echo ""
    
    # Experiment 1: RAG Evaluation
    log_step "运行实验 1: RAG 检索质量评估..."
    if uv run exp1_rag_evaluation.py --seed "$seed"; then
        log_info "实验 1 完成"
    else
        log_error "实验 1 失败"
    fi
    echo ""
    
    # Experiment 2: Scheduler Evaluation
    log_step "运行实验 2: 多智能体调度评估..."
    if timeout 180 uv run exp2_scheduler_eval.py --seed "$seed"; then
        log_info "实验 2 完成"
    else
        log_error "实验 2 失败或超时"
    fi
    echo ""
    
    # Experiment 3: Tool-First Comparison
    log_step "运行实验 3: Tool-First 对比评估..."
    if timeout 180 uv run exp3_tool_first_compare.py --seed "$seed"; then
        log_info "实验 3 完成"
    else
        log_error "实验 3 失败或超时"
    fi
    echo ""
}

# Show results
show_results() {
    echo ""
    echo "========================================"
    echo "  实验结果"
    echo "========================================"
    echo ""
    
    if [ -f "../results/exp1_results.json" ]; then
        log_info "实验 1 结果: ../results/exp1_results.json"
        echo "   查看: cat ../results/exp1_results.json | python3 -m json.tool"
    fi
    
    if [ -f "../results/exp2_results.json" ]; then
        log_info "实验 2 结果: ../results/exp2_results.json"
        echo "   查看: cat ../results/exp2_results.json | python3 -m json.tool"
    fi
    
    if [ -f "../results/exp3_results.json" ]; then
        log_info "实验 3 结果: ../results/exp3_results.json"
        echo "   查看: cat ../results/exp3_results.json | python3 -m json.tool"
    fi
    
    echo ""
}

# Main
main() {
    local seed=42
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --seed)
                seed="$2"
                shift 2
                ;;
            *)
                echo "Usage: $0 [--seed SEED]"
                exit 1
                ;;
        esac
    done
    
    check_backend
    initialize_backend
    run_experiments "$seed"
    show_results
}

main "$@"
