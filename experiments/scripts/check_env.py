#!/usr/bin/env python3
"""
环境诊断和快速启动脚本
检查所有依赖和连接
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_python_env():
    """检查 Python 版本和依赖"""
    logger.info("检查 Python 环境...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        logger.error(f"Python 版本过低: {version.major}.{version.minor}, 需要 3.11+")
        return False
    
    logger.info(f"✓ Python 版本: {version.major}.{version.minor}")
    
    # Check critical imports
    imports_to_check = [
        ('pyyaml', 'yaml'),
        ('httpx', 'httpx'),
        ('sqlalchemy', 'sqlalchemy'),
        ('pymilvus', 'pymilvus'),
    ]
    
    missing = []
    for pkg_name, import_name in imports_to_check:
        try:
            __import__(import_name)
            logger.info(f"✓ {pkg_name}")
        except ImportError:
            logger.warning(f"✗ {pkg_name} 未安装")
            missing.append(pkg_name)
    
    if missing:
        logger.error(f"缺少依赖: {', '.join(missing)}")
        logger.info(f"安装: pip install {' '.join(missing)}")
        return False
    
    return True


def check_config_files():
    """检查配置文件"""
    logger.info("\n检查配置文件...")
    
    # 配置文件在 experiments/config 目录下，不是 scripts/config
    exp_dir = Path(__file__).parent.parent
    required_files = [
        'config/api_config.json',
        'config/rag_eval_config.json',
        'config/scheduler_config.json',
        'config/tool_first_config.json',
    ]
    
    missing = []
    for file_path in required_files:
        full_path = exp_dir / file_path
        if full_path.exists():
            logger.info(f"✓ {file_path}")
        else:
            logger.warning(f"✗ {file_path} 不存在")
            missing.append(file_path)
    
    if missing:
        logger.warning(f"缺少配置文件: {missing}")
        return False
    
    return True


def check_backend_api(config_path: Path = None):
    """检查后端 API 可用性"""
    logger.info("\n检查后端 API...")
    
    if config_path is None:
        # 配置文件在 experiments/config 目录下
        config_path = Path(__file__).parent.parent / 'config/api_config.json'
    
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"无法读取配置文件: {e}")
        return False
    
    base_url = cfg.get('base_url', 'http://localhost:8000')
    health_path = cfg.get('health_path', '/health')
    
    import urllib.request
    health_url = base_url.rstrip('/') + health_path
    
    try:
        req = urllib.request.Request(health_url, method='GET')
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                logger.info(f"✓ 后端 API: {base_url}")
                return True
            else:
                logger.error(f"✗ 后端返回状态码 {resp.status}")
                return False
    except Exception as e:
        logger.error(f"✗ 无法连接后端: {e}")
        logger.info(f"  启动后端: ./scripts/start_backend.sh")
        return False


def check_database(config_path: Path = None):
    """检查 PostgreSQL 连接"""
    logger.info("\n检查 PostgreSQL...")
    
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config/api_config.json'
    
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"无法读取配置文件: {e}")
        return False
    
    dsn = cfg.get('postgres', {}).get('dsn', '')
    if not dsn:
        logger.warning("PostgreSQL DSN 未配置")
        return False
    
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine
        
        async def test_db():
            engine = create_async_engine(dsn, echo=False)
            async with engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                return result.scalar() == 1
        
        result = asyncio.run(test_db())
        if result:
            logger.info(f"✓ PostgreSQL 连接正常")
            return True
        else:
            logger.error("✗ PostgreSQL 查询失败")
            return False
    except Exception as e:
        logger.error(f"✗ PostgreSQL 连接失败: {e}")
        logger.info(f"  启动数据库: ./scripts/db_control.sh start")
        return False


def check_milvus(config_path: Path = None):
    """检查 Milvus 连接"""
    logger.info("\n检查 Milvus...")
    
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config/api_config.json'
    
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"无法读取配置文件: {e}")
        return False
    
    host = cfg.get('milvus', {}).get('host', 'localhost')
    port = cfg.get('milvus', {}).get('port', 19530)
    
    try:
        from pymilvus import connections
        connections.connect(alias='default', host=host, port=port, pool_size=1)
        logger.info(f"✓ Milvus 连接正常 ({host}:{port})")
        connections.disconnect(alias='default')
        return True
    except Exception as e:
        logger.error(f"✗ Milvus 连接失败: {e}")
        logger.info(f"  启动 Milvus: ./scripts/milvus_control.sh start")
        return False


def check_llm_api(config_path: Path = None):
    """检查 LLM API 配置"""
    logger.info("\n检查 LLM API...")
    
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config/api_config.json'
    
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"无法读取配置文件: {e}")
        return False
    
    llm_cfg = cfg.get('llm', {})
    
    if not llm_cfg.get('api_key'):
        logger.error("✗ LLM API Key 未配置")
        return False
    
    if llm_cfg.get('api_key').startswith('sk-'):
        logger.info(f"✓ LLM API 已配置: {llm_cfg.get('model', 'unknown')}")
        return True
    else:
        logger.error("✗ LLM API Key 格式不正确")
        return False


def check_embedding_api(config_path: Path = None):
    """检查 Embedding API 配置"""
    logger.info("\n检查 Embedding API...")
    
    if config_path is None:
        config_path = Path(__file__).parent.parent / 'config/api_config.json'
    
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception as e:
        logger.error(f"无法读取配置文件: {e}")
        return False
    
    emb_cfg = cfg.get('embedding', {})
    
    if not emb_cfg.get('api_key'):
        logger.error("✗ Embedding API Key 未配置")
        return False
    
    if emb_cfg.get('api_key').startswith(('AIza', 'sk-')):
        logger.info(f"✓ Embedding API 已配置: {emb_cfg.get('model', 'unknown')}")
        return True
    else:
        logger.error("✗ Embedding API Key 格式不正确")
        return False


def main():
    """运行所有检查"""
    logger.info("="*60)
    logger.info("Mul-in-One 实验环境检查")
    logger.info("="*60)
    
    checks = [
        ("Python 环境", check_python_env),
        ("配置文件", check_config_files),
        ("LLM API", check_llm_api),
        ("Embedding API", check_embedding_api),
    ]
    
    optional_checks = [
        ("后端 API", check_backend_api),
        ("PostgreSQL", check_database),
        ("Milvus", check_milvus),
    ]
    
    results = {}
    
    logger.info("\n必需检查:")
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            logger.error(f"检查失败 {name}: {e}")
            results[name] = False
    
    logger.info("\n可选检查（运行脚本前需要）:")
    for name, check_fn in optional_checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            logger.error(f"检查失败 {name}: {e}")
            results[name] = False
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("检查结果:")
    logger.info("="*60)
    
    for name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ 所有检查通过，可以运行实验脚本！")
        logger.info("\n快速开始:")
        logger.info("  python exp1_rag_evaluation.py")
        logger.info("  python exp2_scheduler_eval.py")
        logger.info("  python exp3_tool_first_compare.py")
        return 0
    else:
        logger.error("\n✗ 某些检查失败，请按上述提示修复后重试")
        return 1


if __name__ == '__main__':
    sys.exit(main())
