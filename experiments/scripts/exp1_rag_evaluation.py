import argparse
import json
import logging
import random
import statistics
from pathlib import Path
from typing import Dict, List

from utils.api_client import assert_backend_ready, load_api_config, BackendAPIClient
from utils.data_loader import load_qa_dataset
from utils.metrics import recall_at_k, mrr, ndcg_at_k
from utils.visualizer import save_json, print_table

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def evaluate(
    config: Dict,
    api_client: BackendAPIClient,
    username: str = "test_user",
    persona_id: int = 1
) -> Dict:
    """
    真实 RAG 评估：调用后端 RAG 检索接口，评估检索质量。
    
    流程：
    1. 为指定 Persona 摄取评估数据集
    2. 遍历 QA 对，调用后端检索 API
    3. 计算 Recall@K, MRR, NDCG 等指标
    """
    logger.info("Starting real RAG evaluation against backend...")
    
    # Load QA dataset
    qa_file = Path(config["dataset"]["qa_file"])
    if not qa_file.is_absolute():
        qa_file = Path(__file__).parent.parent / qa_file
    
    qa_data = load_qa_dataset(qa_file)
    logger.info(f"Loaded {len(qa_data)} QA pairs from {qa_file}")
    
    top_k_values = config["dataset"].get("top_k_values", [1, 3, 5])
    
    # Ingest dataset documents as RAG background
    logger.info(f"Ingesting {len(qa_data)} documents into persona {persona_id}...")
    ingested_count = 0
    for qa_pair in qa_data:
        doc_text = f"Question: {qa_pair.get('question', '')}\nAnswer: {qa_pair.get('answer', '')}"
        doc_id = qa_pair.get("id", f"doc_{ingested_count}")
        try:
            api_client.ingest_text(
                persona_id=persona_id,
                username=username,
                text=doc_text,
                source=f"qa_dataset_{doc_id}"
            )
            ingested_count += 1
        except Exception as e:
            logger.warning(f"Failed to ingest document {doc_id}: {e}")
    
    logger.info(f"Ingested {ingested_count}/{len(qa_data)} documents")
    
    # Perform retrieval evaluation
    results = {
        "experiment": config["experiment"],
        "total_queries": len(qa_data),
        "metrics_by_k": {}
    }
    
    for k in top_k_values:
        logger.info(f"Evaluating retrieval with top_k={k}...")
        
        recalls = []
        mrrs = []
        ndcgs = []
        
        for idx, qa_pair in enumerate(qa_data):
            if idx % 10 == 0:
                logger.info(f"  Processing query {idx}/{len(qa_data)}...")
            
            query = qa_pair.get("question", "")
            correct_doc_ids = set(qa_pair.get("relevant_docs", []))
            
            if not correct_doc_ids or not query:
                continue
            
            try:
                # Call backend RAG retrieve API
                resp = api_client.retrieve_documents(
                    persona_id=persona_id,
                    username=username,
                    query=query,
                    top_k=k
                )
                
                # Extract retrieved document IDs from response
                retrieved_docs = resp.get("documents", [])
                retrieved_ids = set(
                    doc.get("metadata", {}).get("source", f"doc_{i}").split("_")[-1]
                    for i, doc in enumerate(retrieved_docs)
                )
                
                # Calculate metrics
                r = recall_at_k(correct_doc_ids, retrieved_ids, k)
                m = mrr(correct_doc_ids, retrieved_ids)
                n = ndcg_at_k(correct_doc_ids, retrieved_ids, k)
                
                recalls.append(r)
                mrrs.append(m)
                ndcgs.append(n)
                
            except Exception as e:
                logger.warning(f"Failed to retrieve for query {idx}: {e}")
                continue
        
        if recalls:
            results["metrics_by_k"][f"k={k}"] = {
                "recall_mean": round(statistics.mean(recalls), 4),
                "recall_std": round(statistics.stdev(recalls) if len(recalls) > 1 else 0, 4),
                "mrr_mean": round(statistics.mean(mrrs), 4),
                "ndcg_mean": round(statistics.mean(ndcgs), 4),
                "queries_evaluated": len(recalls)
            }
    
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="config/rag_eval_config.json")
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
    parser.add_argument(
        "--persona-id",
        type=int,
        default=1,
        help="用于评估的 Persona ID"
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
        username=username,
        persona_id=persona_id
    )
    
    save_json(results, out_file)
    print_table("RAG Evaluation Results", results["metrics_by_k"])
    print(f"\n✓ 结果已保存到 {out_file}")


if __name__ == "__main__":
    main()
