#!/bin/bash
# 停止后端服务

set +e

echo "════════════════════════════════════════════════════════════"
echo "停止后端服务"
echo "════════════════════════════════════════════════════════════"

echo ""
echo "停止后端服务..."
pkill -f "uvicorn.*mul_in_one" || true
pkill -f "uv run" || true
sleep 1
echo "✓ 后端服务已停止"

echo ""
echo "注意: PostgreSQL 和 Milvus 服务由 ./scripts/ 下的脚本管理"
echo "停止数据库: cd .. && ./scripts/db_control.sh stop"
echo "停止向量库: cd .. && ./scripts/milvus_control.sh stop"
echo "════════════════════════════════════════════════════════════"
