"""Persona and API profile routes."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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


class EmbeddingConfigResponse(BaseModel):
    username: str
    api_profile_id: int | None
    api_profile_name: str | None = None
    api_model: str | None = None
    api_base_url: AnyHttpUrl | None = None


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
    )


@router.put("/embedding-config", response_model=EmbeddingConfigResponse)
async def update_embedding_config(
    payload: EmbeddingConfigUpdate,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> EmbeddingConfigResponse:
    """设置用户的全局 Embedding 模型配置"""
    logger.info("Updating embedding config for user=%s to profile_id=%s", username, payload.api_profile_id)
    try:
        config = await repository.update_user_embedding_config(username, payload.api_profile_id)
        return EmbeddingConfigResponse(
            username=username,
            api_profile_id=config.get("api_profile_id"),
            api_profile_name=config.get("api_profile_name"),
            api_model=config.get("api_model"),
            api_base_url=config.get("api_base_url"),
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


@router.get("/api-profiles/{profile_id}/health", response_model=APIHealthResponse)
async def healthcheck_api_profile(
    profile_id: int,
    username: str = Query(..., description="User identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIHealthResponse:
    """Perform a minimal health check against the configured third-party API.

    Tries common OpenAI-compatible endpoints. Does NOT expose the API key.
    """
    record = await repository.get_api_profile_with_key(username, profile_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API profile not found")

    base_url = str(record["base_url"]).rstrip("/")
    api_key = record.get("api_key") or None
    model = record.get("model") or ""

    # Smart path detection: if base_url already ends with /v1, don't add it again
    base_has_v1 = base_url.endswith("/v1")
    
    candidates: list[dict] = []
    # GET /models (or /v1/models if base doesn't have /v1)
    models_path = "/models" if base_has_v1 else "/v1/models"
    candidates.append({
        "method": "GET",
        "url": f"{base_url}{models_path}",
        "headers": {"Authorization": f"Bearer {api_key}"} if api_key else {},
        "json": None,
    })
    # If model provided, try embeddings
    if model:
        embed_path = "/embeddings" if base_has_v1 else "/v1/embeddings"
        candidates.append({
            "method": "POST",
            "url": f"{base_url}{embed_path}",
            "headers": {
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
            },
            "json": {"model": model, "input": "ping"},
        })
    # fallback: GET base
    candidates.append({
        "method": "GET",
        "url": base_url,
        "headers": {"Authorization": f"Bearer {api_key}"} if api_key else {},
        "json": None,
    })

    timeout_s = 8.0

    # Prefer httpx; fallback to urllib
    try:
        import httpx  # type: ignore
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            for req in candidates:
                try:
                    resp = await client.request(
                        req["method"],
                        req["url"],
                        headers=req["headers"],
                        json=req["json"],
                    )  # type: ignore[arg-type]
                    if 200 <= resp.status_code < 300:
                        return APIHealthResponse(status="OK", provider_status=resp.status_code)
                    last_detail = f"HTTP {resp.status_code}: {resp.text[:500]}"
                except Exception as exc:  # pragma: no cover
                    last_detail = str(exc)
        return APIHealthResponse(status="FAILED", provider_status=None, detail=last_detail)
    except Exception:  # ImportError or runtime issues
        import urllib.request
        import json as pyjson
        for req in candidates:
            try:
                data = None
                if req["json"] is not None:
                    data = pyjson.dumps(req["json"]).encode("utf-8")
                request = urllib.request.Request(req["url"], data=data, method=req["method"])  # type: ignore[arg-type]
                for k, v in (req["headers"] or {}).items():
                    request.add_header(k, v)
                with urllib.request.urlopen(request, timeout=timeout_s) as resp:
                    code = getattr(resp, "status", 200)
                    if 200 <= code < 300:
                        return APIHealthResponse(status="OK", provider_status=code)
                    last_detail = f"HTTP {code}"
            except Exception as exc:  # pragma: no cover
                last_detail = str(exc)
        return APIHealthResponse(status="FAILED", provider_status=None, detail=last_detail)


