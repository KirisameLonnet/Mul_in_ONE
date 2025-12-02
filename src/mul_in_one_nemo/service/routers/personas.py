"""Persona and API profile routes."""

from __future__ import annotations

import logging
from datetime import datetime
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import AnyHttpUrl, BaseModel, Field
import json
import asyncio

from mul_in_one_nemo.service.dependencies import get_persona_repository, get_rag_service
from mul_in_one_nemo.service.models import APIProfileRecord, PersonaRecord
from mul_in_one_nemo.service.rag_service import RAGService
from mul_in_one_nemo.service.repositories import PersonaDataRepository

router = APIRouter(tags=["personas"])
logger = logging.getLogger(__name__)

AVATAR_UPLOAD_DIR = Path(os.getenv("PERSONA_AVATAR_DIR", Path.cwd() / "configs" / "persona_avatars"))
AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2MB


class APIProfileCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=64)
    base_url: AnyHttpUrl
    model: str = Field(..., min_length=1, max_length=255)
    api_key: str = Field(..., min_length=8)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    is_embedding_model: bool = Field(default=False, description="Whether this profile is for an embedding model")
    embedding_dim: int | None = Field(
        default=None,
        ge=1,
        description="Maximum embedding dimension supported by the model (e.g., 4096 for Qwen3-Embedding-8B). Users can specify smaller dimensions at runtime."
    )


class APIProfileResponse(BaseModel):
    id: int
    username: str
    name: str
    base_url: AnyHttpUrl
    model: str
    temperature: float | None
    created_at: datetime
    api_key_preview: str | None
    is_embedding_model: bool = False
    embedding_dim: int | None = None

    @classmethod
    def from_record(cls, record: APIProfileRecord) -> "APIProfileResponse":
        return cls(
            id=record.id,
            username=record.username,
            name=record.name,
            base_url=record.base_url,
            model=record.model,
            temperature=record.temperature,
            created_at=record.created_at,
            api_key_preview=record.api_key_preview,
            is_embedding_model=getattr(record, 'is_embedding_model', False),
            embedding_dim=getattr(record, 'embedding_dim', None),
        )


class APIProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: AnyHttpUrl | None = None
    model: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, min_length=8)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    is_embedding_model: bool | None = Field(default=None, description="Whether this profile is for an embedding model")
    embedding_dim: int | None = Field(
        default=None,
        ge=1,
        description="Maximum embedding dimension supported by the model (e.g., 4096 for Qwen3-Embedding-8B). Users can specify smaller dimensions at runtime."
    )


class PersonaCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    prompt: str = Field(..., min_length=1)
    handle: str | None = Field(default=None, max_length=128)
    tone: str = Field(default="neutral", max_length=64)
    proactivity: float = Field(default=0.5, ge=0.0, le=1.0)
    memory_window: int = Field(default=8, ge=-1, le=200, description="会话记忆窗口；-1 表示不限制（全量历史）")
    max_agents_per_turn: int = Field(default=2, ge=-1, le=8, description="每轮最多发言的 Persona 数；-1 表示不限制（等于参与 Persona 数)")
    api_profile_id: int | None = Field(default=None, ge=1)
    is_default: bool = False
    background: str | None = Field(default=None, description="Background story or biography for RAG")
    avatar_path: str | None = Field(default=None, max_length=512, description="头像文件访问路径或 URL")


class PersonaResponse(BaseModel):
    id: int
    username: str
    name: str
    handle: str
    prompt: str
    tone: str
    proactivity: float
    memory_window: int
    max_agents_per_turn: int
    is_default: bool
    background: str | None = None
    api_profile_id: int | None = None
    api_profile_name: str | None = None
    api_model: str | None = None
    api_base_url: AnyHttpUrl | None = None
    temperature: float | None = None
    avatar_path: str | None = None

    @classmethod
    def from_record(cls, record: PersonaRecord) -> "PersonaResponse":
        return cls(
            id=record.id,
            username=record.username,
            name=record.name,
            handle=record.handle,
            prompt=record.prompt,
            tone=record.tone,
            proactivity=record.proactivity,
            memory_window=record.memory_window,
            max_agents_per_turn=record.max_agents_per_turn,
            is_default=record.is_default,
            background=record.background,
            api_profile_id=record.api_profile_id,
            api_profile_name=record.api_profile_name,
            api_model=record.api_model,
            api_base_url=record.api_base_url,
            temperature=record.temperature,
            avatar_path=record.avatar_path,
        )


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    prompt: str | None = Field(default=None, min_length=1)
    handle: str | None = Field(default=None, max_length=128)
    tone: str | None = Field(default=None, max_length=64)
    proactivity: float | None = Field(default=None, ge=0.0, le=1.0)
    memory_window: int | None = Field(default=None, ge=-1, le=200, description="-1 表示不限制")
    max_agents_per_turn: int | None = Field(default=None, ge=-1, le=8, description="-1 表示不限制")
    api_profile_id: int | None = Field(default=None, ge=1)
    is_default: bool | None = None
    background: str | None = Field(default=None, description="Background story or biography for RAG")
    avatar_path: str | None = Field(default=None, max_length=512, description="头像文件访问路径或 URL")


class PersonaIngestRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="URL to ingest content from for RAG")

class PersonaTextIngestRequest(BaseModel):
    text: str = Field(..., description="Raw text to ingest for RAG")

class PersonaIngestResponse(BaseModel):
    status: str = Field(..., description="Status of the ingestion process")
    documents_added: int | None = Field(default=None, description="Number of document chunks added")
    collection_name: str | None = Field(default=None, description="Milvus collection name used")


class EmbeddingConfigUpdate(BaseModel):
    api_profile_id: int | None = Field(default=None, ge=1, description="API Profile ID for embedding model")
    actual_embedding_dim: int | None = Field(default=None, ge=32, le=8192, description="Actual embedding dimension to use (32-8192)")


class EmbeddingConfigResponse(BaseModel):
    username: str
    api_profile_id: int | None
    api_profile_name: str | None = None
    api_model: str | None = None
    api_base_url: AnyHttpUrl | None = None
    actual_embedding_dim: int | None = None


@router.get("/api-profiles", response_model=list[APIProfileResponse])
async def list_api_profiles(
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> list[APIProfileResponse]:
    logger.info("Listing API profiles for user '%s'", username)
    records = await repository.list_api_profiles(username)
    return [APIProfileResponse.from_record(record) for record in records]


@router.get("/api-profiles/{profile_id}", response_model=APIProfileResponse)
async def get_api_profile(
    profile_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIProfileResponse:
    logger.info("Fetching API profile id=%s for user '%s'", profile_id, username)
    record = await repository.get_api_profile(username, profile_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API profile not found")
    return APIProfileResponse.from_record(record)


@router.post("/api-profiles", response_model=APIProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_api_profile(
    payload: APIProfileCreate,
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIProfileResponse:
    logger.info("Creating API profile '%s' for user '%s'", payload.name, payload.username)
    record = await repository.create_api_profile(
        username=payload.username,
        name=payload.name,
        base_url=str(payload.base_url),
        model=payload.model,
        api_key=payload.api_key,
        temperature=payload.temperature,
        is_embedding_model=payload.is_embedding_model,
        embedding_dim=payload.embedding_dim,
    )
    return APIProfileResponse.from_record(record)


@router.patch("/api-profiles/{profile_id}", response_model=APIProfileResponse)
async def update_api_profile(
    profile_id: int,
    payload: APIProfileUpdate,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIProfileResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided")
    # Convert AnyHttpUrl to string for database storage
    if "base_url" in updates and updates["base_url"] is not None:
        updates["base_url"] = str(updates["base_url"])
    try:
        logger.info(
            "Updating API profile id=%s for user '%s' with fields=%s",
            profile_id,
            username,
            list(updates.keys()),
        )
        record = await repository.update_api_profile(username, profile_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return APIProfileResponse.from_record(record)


@router.delete("/api-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_profile(
    profile_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> Response:
    try:
        logger.info("Deleting API profile id=%s for user '%s'", profile_id, username)
        await repository.delete_api_profile(username, profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/personas", response_model=list[PersonaResponse])
async def list_personas(
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> list[PersonaResponse]:
    logger.info("Listing personas for user '%s'", username)
    records = await repository.list_personas(username)
    return [PersonaResponse.from_record(record) for record in records]


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> PersonaResponse:
    logger.info("Fetching persona id=%s for user '%s'", persona_id, username)
    record = await repository.get_persona(username, persona_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return PersonaResponse.from_record(record)


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    payload: PersonaCreate,
    repository: PersonaDataRepository = Depends(get_persona_repository),
    rag_service: RAGService = Depends(get_rag_service),
) -> PersonaResponse:
    try:
        logger.info("Creating persona '%s' for user '%s'", payload.name, payload.username)
        record = await repository.create_persona(
            username=payload.username,
            name=payload.name,
            prompt=payload.prompt,
            handle=payload.handle,
            tone=payload.tone,
            proactivity=payload.proactivity,
            memory_window=payload.memory_window,
            max_agents_per_turn=payload.max_agents_per_turn,
            api_profile_id=payload.api_profile_id,
            is_default=payload.is_default,
            background=payload.background,
            avatar_path=payload.avatar_path,
        )
        
        # 自动摄取 background 到 RAG
        if payload.background and payload.background.strip():
            try:
                logger.info(
                    "Auto-ingesting background for persona_id=%s (user=%s)",
                    record.id,
                    payload.username,
                )
                await rag_service.ingest_text(
                    text=payload.background,
                    persona_id=record.id,
                    username=payload.username,
                    source="background"
                )
                logger.info("Background ingestion completed for persona_id=%s", record.id)
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.warning(
                    "Failed to auto-ingest background for persona_id=%s: %s",
                    record.id,
                    exc,
                )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PersonaResponse.from_record(record)


@router.patch("/personas/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: int,
    payload: PersonaUpdate,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
    rag_service: RAGService = Depends(get_rag_service),
) -> PersonaResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided")
    try:
        logger.info(
            "Updating persona id=%s for user '%s' with fields=%s",
            persona_id,
            username,
            list(updates.keys()),
        )
        record = await repository.update_persona(username, persona_id, **updates)
        
        # 如果更新了 background，重新摄取到 RAG
        if "background" in updates and updates["background"]:
            background_text = updates["background"]
            if background_text.strip():
                try:
                    logger.info("Refreshing background documents for persona_id=%s", persona_id)
                    await rag_service.delete_documents_by_source(persona_id, username, source="background")
                    await rag_service.ingest_text(
                        text=background_text,
                        persona_id=persona_id,
                        username=username,
                        source="background"
                    )
                    logger.info("Background re-ingestion completed for persona_id=%s", persona_id)
                except Exception as exc:  # pragma: no cover - best effort logging
                    logger.warning(
                        "Failed to re-ingest background for persona_id=%s: %s",
                        persona_id,
                        exc,
                    )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PersonaResponse.from_record(record)


@router.post("/personas/{persona_id}/avatar", response_model=PersonaResponse)
async def upload_persona_avatar(
    persona_id: int,
    file: UploadFile = File(..., description="头像图片文件"),
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> PersonaResponse:
    """Upload and attach an avatar image to a Persona."""
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 PNG、JPG、WEBP 格式的头像",
        )

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="头像文件过大，最大 2MB",
        )

    suffix = Path(file.filename or "").suffix.lower() or ".png"
    safe_name = f"{username}_persona_{persona_id}{suffix}"
    file_path = AVATAR_UPLOAD_DIR / safe_name
    try:
        file_path.write_bytes(content)
    except OSError as exc:  # pragma: no cover - IO failures bubble up
        logger.exception("Failed to save avatar to %s", file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法保存头像文件: {exc}",
        ) from exc

    try:
        record = await repository.update_persona(
            username,
            persona_id,
            avatar_path=f"/persona-avatars/{safe_name}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return PersonaResponse.from_record(record)


@router.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
    rag_service: RAGService = Depends(get_rag_service),
) -> Response:
    try:
        logger.info("Deleting persona id=%s for user '%s'", persona_id, username)
        await repository.delete_persona(username, persona_id)
        
        # Also delete the associated Milvus collection
        try:
            await rag_service.delete_collection(persona_id, username)
        except Exception as e:
            logger.warning(f"Failed to delete Milvus collection for persona {persona_id}: {e}")
            
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/personas/{persona_id}/ingest", response_model=PersonaIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_url(
    persona_id: int,
    payload: PersonaIngestRequest,
    username: str = Query(..., description="User identifier"),
    rag_service: RAGService = Depends(get_rag_service),
) -> PersonaIngestResponse:
    try:
        logger.info("Manual URL ingest for persona_id=%s user=%s url=%s", persona_id, username, payload.url)
        result = await rag_service.ingest_url(payload.url, persona_id, username)
        return PersonaIngestResponse(
            status=result["status"],
            documents_added=result["documents_added"],
            collection_name=result["collection_name"],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

@router.post("/personas/{persona_id}/ingest_text", response_model=PersonaIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_text(
    persona_id: int,
    payload: PersonaTextIngestRequest,
    username: str = Query(..., description="User identifier"),
    rag_service: RAGService = Depends(get_rag_service),
) -> PersonaIngestResponse:
    try:
        logger.info("Manual text ingest for persona_id=%s user=%s (chars=%s)", persona_id, username, len(payload.text))
        result = await rag_service.ingest_text(payload.text, persona_id, username)
        return PersonaIngestResponse(
            status=result["status"],
            documents_added=result["documents_added"],
            collection_name=result["collection_name"],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc



@router.post("/personas/{persona_id}/refresh_rag", response_model=PersonaIngestResponse, status_code=status.HTTP_200_OK)
async def refresh_persona_rag(
    persona_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
    rag_service: RAGService = Depends(get_rag_service),
) -> PersonaIngestResponse:
    """刷新 Persona 的 RAG 资料库（从数据库中的 background 字段重新摄取）"""
    try:
        logger.info("Refreshing RAG background for persona_id=%s user=%s", persona_id, username)
        persona = await repository.get_persona(username, persona_id)
        if persona is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")

        if not persona.background or not persona.background.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Persona has no background content to ingest"
            )

        await rag_service.delete_documents_by_source(persona_id, username, source="background")
        result = await rag_service.ingest_text(
            text=persona.background,
            persona_id=persona_id,
            username=username,
            source="background"
        )

        logger.info(
            "Persona background refresh completed: persona_id=%s documents=%s",
            persona_id,
            result["documents_added"],
        )

        return PersonaIngestResponse(
            status=result["status"],
            documents_added=result["documents_added"],
            collection_name=result["collection_name"],
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - surface failure to client
        logger.exception("Failed to refresh persona background for id=%s", persona_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/embedding-config", response_model=EmbeddingConfigResponse)
async def get_embedding_config(
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> EmbeddingConfigResponse:
    """获取用户的全局 Embedding 模型配置"""
    logger.info("Fetching embedding config for user=%s", username)
    config = await repository.get_user_embedding_config(username)
    return EmbeddingConfigResponse(
        username=username,
        api_profile_id=config.get("api_profile_id"),
        api_profile_name=config.get("api_profile_name"),
        api_model=config.get("api_model"),
        api_base_url=config.get("api_base_url"),
        actual_embedding_dim=config.get("actual_embedding_dim"),
    )


@router.put("/embedding-config", response_model=EmbeddingConfigResponse)
async def update_embedding_config(
    payload: EmbeddingConfigUpdate,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> EmbeddingConfigResponse:
    """设置用户的全局 Embedding 模型配置"""
    logger.info("Updating embedding config for user=%s to profile_id=%s, actual_dim=%s", 
                username, payload.api_profile_id, payload.actual_embedding_dim)
    try:
        config = await repository.update_user_embedding_config(
            username, 
            payload.api_profile_id, 
            payload.actual_embedding_dim
        )
        return EmbeddingConfigResponse(
            username=username,
            api_profile_id=config.get("api_profile_id"),
            api_profile_name=config.get("api_profile_name"),
            api_model=config.get("api_model"),
            api_base_url=config.get("api_base_url"),
            actual_embedding_dim=config.get("actual_embedding_dim"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


class BuildVectorDBResponse(BaseModel):
    status: str
    message: str
    personas_processed: int
    total_documents: int
    errors: list[str] = Field(default_factory=list)


@router.post("/build-vector-db")
async def build_vector_database(
    username: str = Query(..., description="User identifier"),
    expected_dim: int | None = Query(None, description="Expected embedding dimension (e.g., 384)"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
    rag_service: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    """为所有 Persona 批量构建/更新向量数据库 (流式响应进度)"""
    logger.info("Building vector database for user=%s", username)
    
    async def progress_generator():
        personas_processed = 0
        total_documents = 0
        errors = []
        
        try:
            # 获取所有 persona
            personas = await repository.list_personas(username)
            total_personas = len(personas)
            
            # 过滤出有 background 的 persona 数量用于计算进度（可选，这里简单起见用总数）
            # 实际上我们会在循环中跳过，所以进度条可能会跳跃，但总数是确定的
            
            if total_personas == 0:
                yield json.dumps({
                    "progress": 100,
                    "message": "No personas found",
                    "status": "completed",
                    "details": {"processed": 0, "docs": 0, "errors": []}
                }) + "\n"
                return

            for i, persona in enumerate(personas):
                current_progress = int((i / total_personas) * 100)
                yield json.dumps({
                    "progress": current_progress,
                    "message": f"Processing {persona.name}...",
                    "status": "processing"
                }) + "\n"

                try:
                    # 跳过没有 background 的 persona
                    if not persona.background or not persona.background.strip():
                        logger.info(f"Skipping persona {persona.id} ({persona.name}): no background content")
                        continue
                    
                    logger.info(f"Processing persona {persona.id} ({persona.name})")
                    
                    # 删除旧数据
                    await rag_service.delete_documents_by_source(persona.id, username, source="background")
                    
                    # 重新摄取
                    result = await rag_service.ingest_text(
                        text=persona.background,
                        persona_id=persona.id,
                        username=username,
                        source="background",
                        expected_dim=expected_dim,
                    )
                    
                    personas_processed += 1
                    total_documents += result.get("documents_added", 0)
                    
                    logger.info(
                        f"Persona {persona.id} processed: {result.get('documents_added', 0)} documents"
                    )
                    
                except Exception as e:
                    error_msg = f"Persona {persona.id} ({persona.name}): {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            # 完成
            status_msg = "completed" if not errors else "completed_with_errors"
            final_message = f"Processed {personas_processed} personas, added {total_documents} documents"
            
            yield json.dumps({
                "progress": 100,
                "message": final_message,
                "status": status_msg,
                "details": {
                    "processed": personas_processed,
                    "docs": total_documents,
                    "errors": errors
                }
            }) + "\n"
            
        except Exception as exc:
            logger.exception("Failed to build vector database")
            yield json.dumps({
                "progress": 100,
                "message": f"Failed: {str(exc)}",
                "status": "failed",
                "error": str(exc)
            }) + "\n"

    return StreamingResponse(progress_generator(), media_type="application/x-ndjson")


class APIHealthResponse(BaseModel):
    status: str
    provider_status: int | None = None
    detail: str | None = None


def _truncate_detail(text: str | None, limit: int = 500) -> str:
    if not text:
        return ""
    return text[:limit]


def _extract_error_detail(payload: dict | None, fallback_text: str | None = None) -> str:
    """Derive a readable error string from provider response."""
    if isinstance(payload, dict):
        if "error" in payload:
            err = payload.get("error")
            if isinstance(err, dict):
                return _truncate_detail(err.get("message") or err.get("code") or str(err))
            return _truncate_detail(str(err))
        if "message" in payload:
            return _truncate_detail(str(payload.get("message")))
    return _truncate_detail(fallback_text or "Provider error")


def _evaluate_provider_response(
    status_code: int | None,
    text_body: str | None,
    json_body: dict | None,
    expect: str,
) -> APIHealthResponse:
    """Evaluate provider response and return strict health status."""
    provider_status = status_code
    if status_code is None:
        return APIHealthResponse(status="FAILED", provider_status=None, detail="No status code from provider")

    if not (200 <= status_code < 300):
        detail = _extract_error_detail(json_body, text_body)
        return APIHealthResponse(status="FAILED", provider_status=provider_status, detail=detail)

    if not isinstance(json_body, dict):
        return APIHealthResponse(
            status="FAILED",
            provider_status=provider_status,
            detail="Non-JSON response from provider",
        )

    # Some providers return 200 + error payload; catch it explicitly
    if "error" in json_body:
        detail = _extract_error_detail(json_body, text_body)
        return APIHealthResponse(status="FAILED", provider_status=provider_status, detail=detail)

    if expect == "chat":
        choices = json_body.get("choices")
        if not choices or not isinstance(choices, list):
            return APIHealthResponse(
                status="FAILED",
                provider_status=provider_status,
                detail="Response missing choices array",
            )
        return APIHealthResponse(status="OK", provider_status=provider_status)

    if expect == "embedding":
        data = json_body.get("data")
        if not data or not isinstance(data, list):
            return APIHealthResponse(
                status="FAILED",
                provider_status=provider_status,
                detail="Response missing embedding data array",
            )
        first = data[0] if data else None
        if not isinstance(first, dict) or "embedding" not in first:
            return APIHealthResponse(
                status="FAILED",
                provider_status=provider_status,
                detail="Embedding response missing embedding vector",
            )
        return APIHealthResponse(status="OK", provider_status=provider_status)

    return APIHealthResponse(
        status="FAILED",
        provider_status=provider_status,
        detail=f"Unsupported health check mode '{expect}'",
    )


@router.get("/api-profiles/{profile_id}/health", response_model=APIHealthResponse)
async def healthcheck_api_profile(
    profile_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIHealthResponse:
    """Perform a minimal health check against the configured third-party API.

    Calls the real model endpoint with a lightweight request and validates the response payload.
    """
    record = await repository.get_api_profile_with_key(username, profile_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API profile not found")

    base_url = str(record["base_url"]).rstrip("/")
    api_key = record.get("api_key") or None
    model = record.get("model") or ""
    is_embedding = bool(record.get("is_embedding_model"))
    mode = "embedding" if is_embedding else "chat"

    if not base_url:
        return APIHealthResponse(status="FAILED", provider_status=None, detail="Base URL not configured")
    if not model:
        return APIHealthResponse(status="FAILED", provider_status=None, detail="Model not configured")

    base_has_v1 = base_url.endswith("/v1")
    path = "/embeddings" if is_embedding else "/chat/completions"
    path = path if base_has_v1 else f"/v1{path}"
    target_url = f"{base_url}{path}"

    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
    }
    payload = (
        {"model": model, "input": "healthcheck"}
        if is_embedding
        else {
            "model": model,
            "messages": [{"role": "user", "content": "healthcheck"}],
            "max_tokens": 1,
            "stream": False,
        }
    )

    timeout_s = 8.0
    last_detail: str | None = None

    # Prefer httpx; fallback to urllib
    try:
        import httpx  # type: ignore
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            resp = await client.post(target_url, headers=headers, json=payload)
        json_body = None
        try:
            parsed = resp.json()
            if isinstance(parsed, dict):
                json_body = parsed
        except Exception:
            json_body = None
        return _evaluate_provider_response(resp.status_code, resp.text, json_body, mode)
    except Exception as exc:  # pragma: no cover
        last_detail = str(exc)

    try:
        import urllib.request
        import json as pyjson

        data_bytes = pyjson.dumps(payload).encode("utf-8")
        request = urllib.request.Request(target_url, data=data_bytes, method="POST")  # type: ignore[arg-type]
        for k, v in headers.items():
            request.add_header(k, v)
        with urllib.request.urlopen(request, timeout=timeout_s) as resp:
            code = getattr(resp, "status", None) or getattr(resp, "getcode", lambda: None)()
            body_bytes = resp.read()
            text_body = body_bytes.decode("utf-8", errors="ignore")
            json_body = None
            try:
                parsed = pyjson.loads(body_bytes)
                if isinstance(parsed, dict):
                    json_body = parsed
            except Exception:
                json_body = None
            return _evaluate_provider_response(code, text_body, json_body, mode)
    except Exception as exc:  # pragma: no cover
        last_detail = str(exc) if last_detail is None else last_detail

    fallback_detail = last_detail or "Health check failed"
    return APIHealthResponse(status="FAILED", provider_status=None, detail=_truncate_detail(fallback_detail))
