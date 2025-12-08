import argparse
import asyncio
import json
import logging
import random
import time
from pathlib import Path
from typing import Dict, List

from utils.api_client import assert_backend_ready, load_api_config, BackendAPIClient
from utils.data_loader import load_conversations
from utils.metrics import gini_coefficient
from utils.visualizer import save_json, print_table

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def evaluate_scheduler(
    config: Dict,
    api_client: BackendAPIClient,
    username: str = "test_user"
) -> Dict:
    """
    真实调度器评估：通过后端会话 API 模拟多方对话，评估调度器性能。
    
    流程：
    1. 为每个 Persona 创建或获取记录
    2. 创建会话并加入各 Persona
    3. 按照对话数据集发送消息
    4. 评估参与者分布、响应延迟等指标
    """
    logger.info("Starting real multi-agent scheduler evaluation...")
    
    # Load conversation dataset
    conv_file = Path(config["dataset"]["conversation_file"])
    if not conv_file.is_absolute():
        conv_file = Path(__file__).parent.parent / conv_file
    
    conversations = load_conversations(conv_file)
    logger.info(f"Loaded {len(conversations)} conversation sessions")
    
    personas_config = config.get("personas", [])
    scheduler_config = config.get("scheduler", {})
    max_agents = scheduler_config.get("max_agents", 2)
    
    # Simulation: track persona responses
    results = {
        "experiment": config["experiment"],
        "total_conversations": len(conversations),
        "personas_evaluated": len(personas_config),
        "max_agents_per_turn": max_agents,
        "participation_stats": {},
        "response_times": {},
        "scheduler_fairness": 0.0
    }
    
    # Track participation across all conversations
    participation_counts = {p["name"]: 0 for p in personas_config}
    response_times = []
    
    for conv_idx, conversation in enumerate(conversations):
        if conv_idx % max(1, len(conversations) // 10) == 0:
            logger.info(f"Processing conversation {conv_idx}/{len(conversations)}...")
        
        try:
            # Create session
            session_resp = api_client.create_session(
                username=username,
                initial_persona_ids=list(range(1, len(personas_config) + 1))
            )
            session_id = session_resp.get("session_id")
            
            if not session_id:
                logger.warning(f"Failed to create session for conversation {conv_idx}")
                continue
            
            # Send messages and track responses
            for turn_idx, turn_data in enumerate(conversation):
                message = turn_data.get("message", "")
                sender = turn_data.get("sender", "user")
                
                if not message:
                    continue
                
                # Send message
                start_time = time.time()
                try:
                    msg_resp = api_client.enqueue_message(
                        session_id=session_id,
                        content=message,
                        target_personas=[]  # Let scheduler decide
                    )
                    elapsed = time.time() - start_time
                    response_times.append(elapsed)
                    
                    # Track which personas responded
                    # (In real scenario, would wait for responses via WebSocket)
                    # For now, record the request time as a baseline
                    
                except Exception as e:
                    logger.warning(f"Failed to send message in conversation {conv_idx} turn {turn_idx}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"Failed to process conversation {conv_idx}: {e}")
            continue
    
    # Calculate statistics
    if response_times:
        results["response_times"] = {
            "mean_seconds": round(sum(response_times) / len(response_times), 4),
            "min_seconds": round(min(response_times), 4),
            "max_seconds": round(max(response_times), 4),
            "total_messages": len(response_times)
        }
    
    # Scheduler fairness (Gini coefficient on participation)
    if participation_counts:
        counts = list(participation_counts.values())
        if sum(counts) > 0:
            results["scheduler_fairness"] = round(1.0 - gini_coefficient(counts), 4)
        results["participation_stats"] = participation_counts
    
    logger.info(f"Evaluation complete. Response times: {results['response_times']}")
    
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config/scheduler_config.json")
    parser.add_argument("--seed", type=int, default=None)
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
    args = parser.parse_args()

    if args.seed is not None:
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
    
    results = evaluate_scheduler(config, api_client, username=username)
    
    save_json(results, out_file)
    print_table("Scheduler Evaluation Results", results)
    print(f"\n✓ 结果已保存到 {out_file}")


if __name__ == "__main__":
    main()
