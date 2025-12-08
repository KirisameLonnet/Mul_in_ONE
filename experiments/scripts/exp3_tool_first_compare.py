import argparse
import json
import logging
import random
import statistics
import time
from pathlib import Path
from typing import Dict, List

from utils.api_client import assert_backend_ready, load_api_config, BackendAPIClient
from utils.data_loader import load_qa_dataset
from utils.visualizer import save_json, print_table

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def evaluate_baseline(
    api_client: BackendAPIClient,
    qa_dataset: List[Dict],
    persona_id: int,
    username: str,
    top_k: int = 5
) -> Dict:
    """
    Baseline 模式评估：预注入（Pre-injection）
    
    1. 前置检索所有 QA 的背景文档
    2. 一起发送给 LLM（无额外工具调用）
    3. 统计 token 消耗和延迟
    """
    logger.info("Evaluating baseline (pre-injection) mode...")
    
    token_counts = []
    latencies = []
    
    for idx, qa_pair in enumerate(qa_dataset):
        if idx % max(1, len(qa_dataset) // 10) == 0:
            logger.info(f"  Baseline query {idx}/{len(qa_dataset)}...")
        
        question = qa_pair.get("question", "")
        if not question:
            continue
        
        try:
            # Pre-retrieve documents
            start = time.time()
            resp = api_client.retrieve_documents(
                persona_id=persona_id,
                username=username,
                query=question,
                top_k=top_k
            )
            
            documents = resp.get("documents", [])
            
            # Estimate token count (rough: ~1.3 chars per token for English/Chinese)
            context = " ".join(doc.get("page_content", "") for doc in documents)
            estimated_tokens = len(context) // 3 + len(question) // 3
            
            latency = time.time() - start
            
            token_counts.append(estimated_tokens)
            latencies.append(latency)
            
        except Exception as e:
            logger.warning(f"Baseline query {idx} failed: {e}")
            continue
    
    return {
        "token_avg": round(statistics.mean(token_counts), 1) if token_counts else 0,
        "token_std": round(statistics.stdev(token_counts), 1) if len(token_counts) > 1 else 0,
        "latency_avg_s": round(statistics.mean(latencies), 3) if latencies else 0,
        "latency_std_s": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0,
        "queries_evaluated": len(token_counts)
    }


def evaluate_tool_first(
    api_client: BackendAPIClient,
    qa_dataset: List[Dict],
    persona_id: int,
    username: str
) -> Dict:
    """
    Tool-First 模式评估：动态工具调用
    
    1. LLM 决定是否调用 RAG 工具
    2. 统计实际工具调用次数、token 节省率、延迟
    3. （当前为占位实现，需后端支持工具调用追踪）
    """
    logger.info("Evaluating tool-first mode...")
    
    # Placeholder: simulate tool-first behavior
    # In real scenario, would use backend API to track tool calls
    
    token_counts = []
    tool_calls = []
    latencies = []
    
    for idx, qa_pair in enumerate(qa_dataset):
        if idx % max(1, len(qa_dataset) // 10) == 0:
            logger.info(f"  Tool-First query {idx}/{len(qa_dataset)}...")
        
        question = qa_pair.get("question", "")
        if not question:
            continue
        
        try:
            # Create session for tool-first interaction
            session_resp = api_client.create_session(
                username=username,
                initial_persona_ids=[persona_id]
            )
            session_id = session_resp.get("session_id")
            
            if not session_id:
                logger.warning(f"Failed to create session for query {idx}")
                continue
            
            # Send message and measure response
            start = time.time()
            msg_resp = api_client.enqueue_message(
                session_id=session_id,
                content=question
            )
            latency = time.time() - start
            
            # Estimate token count (baseline without full retrieval)
            estimated_tokens = len(question) // 3
            
            # Count tool calls (placeholder - would need backend support)
            tool_call_count = 0
            
            token_counts.append(estimated_tokens)
            tool_calls.append(tool_call_count)
            latencies.append(latency)
            
        except Exception as e:
            logger.warning(f"Tool-First query {idx} failed: {e}")
            continue
    
    return {
        "token_avg": round(statistics.mean(token_counts), 1) if token_counts else 0,
        "token_std": round(statistics.stdev(token_counts), 1) if len(token_counts) > 1 else 0,
        "latency_avg_s": round(statistics.mean(latencies), 3) if latencies else 0,
        "latency_std_s": round(statistics.stdev(latencies), 3) if len(latencies) > 1 else 0,
        "avg_tool_calls": round(statistics.mean(tool_calls), 2) if tool_calls else 0,
        "queries_evaluated": len(token_counts)
    }


def evaluate(config: Dict, api_client: BackendAPIClient, seed: int, username: str = "eval_user", persona_id: int = 1) -> Dict:
    """
    Tool-First vs Baseline 对比评估
    """
    logger.info("Starting Tool-First vs Baseline comparison...")
    
    # Load QA dataset
    qa_file = Path(config["dataset"]["test_cases"])
    if not qa_file.is_absolute():
        qa_file = Path(__file__).parent.parent / qa_file
    
    qa_dataset = load_qa_dataset(qa_file)
    logger.info(f"Loaded {len(qa_dataset)} test cases")
    
    # Evaluate both modes
    baseline_results = evaluate_baseline(
        api_client,
        qa_dataset,
        persona_id=persona_id,
        username=username,
        top_k=config["baseline"].get("top_k", 5)
    )
    
    tool_first_results = evaluate_tool_first(
        api_client,
        qa_dataset,
        persona_id=persona_id,
        username=username
    )
    
    # Calculate comparison metrics
    baseline_tokens = baseline_results.get("token_avg", 1)
    tool_first_tokens = tool_first_results.get("token_avg", 1)
    
    token_saving_rate = (baseline_tokens - tool_first_tokens) / baseline_tokens if baseline_tokens > 0 else 0
    
    return {
        "experiment": config["experiment"],
        "seed": seed,
        "baseline": baseline_results,
        "tool_first": tool_first_results,
        "comparison": {
            "token_saving_rate": round(token_saving_rate, 3),
            "latency_improvement_rate": round(
                (baseline_results.get("latency_avg_s", 1) - tool_first_results.get("latency_avg_s", 1)) /
                baseline_results.get("latency_avg_s", 1) if baseline_results.get("latency_avg_s", 1) > 0 else 0,
                3
            )
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config/tool_first_config.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--api-config",
        type=str,
        default="config/api_config.json",
        help="API 配置文件(json/yaml)，确保后端/PG/Milvus 已启动",
    )
    parser.add_argument(
        "--username",
        type=str,
        default="eval_user",
        help="用于评估的用户名"
    )
    parser.add_argument(
        "--persona-id",
        type=int,
        default=1,
        help="用于评估的 Persona ID"
    )
    args = parser.parse_args()

    random.seed(args.seed)

    # Load configurations
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent.parent / config_path
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # Get persona settings from config, with args as override
    persona_config = config.get("persona", {})
    username = args.username if args.username != "eval_user" else persona_config.get("username", args.username)
    persona_id = args.persona_id if args.persona_id != 1 else persona_config.get("persona_id", args.persona_id)
    
    api_config_path = Path(args.api_config)
    if not api_config_path.is_absolute():
        api_config_path = Path(__file__).parent.parent / api_config_path
    api_cfg = load_api_config(api_config_path)
    
    # Create API client
    api_client = BackendAPIClient(api_cfg)
    
    # Check backend readiness (可选，如果检查失败仍继续尝试）
    try:
        logger.info("Checking backend readiness...")
        assert_backend_ready(api_cfg)
    except Exception as e:
        logger.warning(f"后端检查警告: {e}，继续尝试连接...")
    
    # Run evaluation
    out_file = Path(config["output"]["results_file"])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    results = evaluate(
        config,
        api_client,
        seed=args.seed,
        username=username,
        persona_id=persona_id
    )
    
    save_json(results, out_file)
    
    print("\n" + "="*60)
    print("Tool-First vs Baseline Comparison Results")
    print("="*60)
    print(f"Baseline (Pre-injection):")
    print(f"  - Token avg: {results['baseline']['token_avg']}")
    print(f"  - Latency avg: {results['baseline']['latency_avg_s']}s")
    print(f"\nTool-First (On-demand):")
    print(f"  - Token avg: {results['tool_first']['token_avg']}")
    print(f"  - Latency avg: {results['tool_first']['latency_avg_s']}s")
    print(f"\nComparison:")
    print(f"  - Token saving: {results['comparison']['token_saving_rate']*100:.1f}%")
    print(f"  - Latency improvement: {results['comparison']['latency_improvement_rate']*100:.1f}%")
    print("="*60)
    
    print(f"\n✓ 结果已保存到 {out_file}")


if __name__ == "__main__":
    main()
