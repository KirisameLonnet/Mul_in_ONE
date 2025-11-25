"""Persona and API profile routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import AnyHttpUrl, BaseModel, Field

from mul_in_one_nemo.service.dependencies import get_persona_repository, get_rag_service
from mul_in_one_nemo.service.models import APIProfileRecord, PersonaRecord
from mul_in_one_nemo.service.rag_service import RAGService
from mul_in_one_nemo.service.repositories import PersonaDataRepository

router = APIRouter(tags=["personas"])


class APIProfileCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=64)
    base_url: AnyHttpUrl
    model: str = Field(..., min_length=1, max_length=255)
    api_key: str = Field(..., min_length=8)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class APIProfileResponse(BaseModel):
    id: int
    tenant_id: str
    name: str
    base_url: AnyHttpUrl
    model: str
    temperature: float | None
    created_at: datetime
    api_key_preview: str | None

    @classmethod
    def from_record(cls, record: APIProfileRecord) -> "APIProfileResponse":
        return cls(
            id=record.id,
            tenant_id=record.tenant_id,
            name=record.name,
            base_url=record.base_url,
            model=record.model,
            temperature=record.temperature,
            created_at=record.created_at,
            api_key_preview=record.api_key_preview,
        )


class APIProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: AnyHttpUrl | None = None
    model: str | None = Field(default=None, min_length=1, max_length=255)
    api_key: str | None = Field(default=None, min_length=8)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class PersonaCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    prompt: str = Field(..., min_length=1)
    handle: str | None = Field(default=None, max_length=128)
    tone: str = Field(default="neutral", max_length=64)
    proactivity: float = Field(default=0.5, ge=0.0, le=1.0)
    memory_window: int = Field(default=8, ge=1, le=200)
    max_agents_per_turn: int = Field(default=2, ge=1, le=8)
    api_profile_id: int | None = Field(default=None, ge=1)
    is_default: bool = False


class PersonaResponse(BaseModel):
    id: int
    tenant_id: str
    name: str
    handle: str
    prompt: str
    tone: str
    proactivity: float
    memory_window: int
    max_agents_per_turn: int
    is_default: bool
    api_profile_id: int | None = None
    api_profile_name: str | None = None
    api_model: str | None = None
    api_base_url: AnyHttpUrl | None = None
    temperature: float | None = None

    @classmethod
    def from_record(cls, record: PersonaRecord) -> "PersonaResponse":
        return cls(
            id=record.id,
            tenant_id=record.tenant_id,
            name=record.name,
            handle=record.handle,
            prompt=record.prompt,
            tone=record.tone,
            proactivity=record.proactivity,
            memory_window=record.memory_window,
            max_agents_per_turn=record.max_agents_per_turn,
            is_default=record.is_default,
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
    memory_window: int | None = Field(default=None, ge=1, le=200)
    max_agents_per_turn: int | None = Field(default=None, ge=1, le=8)
    api_profile_id: int | None = Field(default=None, ge=1)
    is_default: bool | None = None


class PersonaIngestRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="URL to ingest content from for RAG")

class PersonaIngestResponse(BaseModel):
    status: str = Field(..., description="Status of the ingestion process")
    documents_added: int | None = Field(default=None, description="Number of document chunks added")
    collection_name: str | None = Field(default=None, description="Milvus collection name used")


@router.get("/api-profiles", response_model=list[APIProfileResponse])
async def list_api_profiles(
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> list[APIProfileResponse]:
    records = await repository.list_api_profiles(tenant_id)
    return [APIProfileResponse.from_record(record) for record in records]


@router.get("/api-profiles/{profile_id}", response_model=APIProfileResponse)
async def get_api_profile(
    profile_id: int,
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIProfileResponse:
    record = await repository.get_api_profile(tenant_id, profile_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API profile not found")
    return APIProfileResponse.from_record(record)


@router.post("/api-profiles", response_model=APIProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_api_profile(
    payload: APIProfileCreate,
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIProfileResponse:
    record = await repository.create_api_profile(
        tenant_id=payload.tenant_id,
        name=payload.name,
        base_url=str(payload.base_url),
        model=payload.model,
        api_key=payload.api_key,
        temperature=payload.temperature,
    )
    return APIProfileResponse.from_record(record)


@router.patch("/api-profiles/{profile_id}", response_model=APIProfileResponse)
async def update_api_profile(
    profile_id: int,
    payload: APIProfileUpdate,
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> APIProfileResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided")
    try:
        record = await repository.update_api_profile(tenant_id, profile_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return APIProfileResponse.from_record(record)


@router.delete("/api-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_profile(
    profile_id: int,
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> Response:
    try:
        await repository.delete_api_profile(tenant_id, profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/personas", response_model=list[PersonaResponse])
async def list_personas(
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> list[PersonaResponse]:
    records = await repository.list_personas(tenant_id)
    return [PersonaResponse.from_record(record) for record in records]


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: int,
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> PersonaResponse:
    record = await repository.get_persona(tenant_id, persona_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")
    return PersonaResponse.from_record(record)


@router.post("/personas", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    payload: PersonaCreate,
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> PersonaResponse:
    try:
        record = await repository.create_persona(
            tenant_id=payload.tenant_id,
            name=payload.name,
            prompt=payload.prompt,
            handle=payload.handle,
            tone=payload.tone,
            proactivity=payload.proactivity,
            memory_window=payload.memory_window,
            max_agents_per_turn=payload.max_agents_per_turn,
            api_profile_id=payload.api_profile_id,
            is_default=payload.is_default,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PersonaResponse.from_record(record)


@router.patch("/personas/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: int,
    payload: PersonaUpdate,
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> PersonaResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided")
    try:
        record = await repository.update_persona(tenant_id, persona_id, **updates)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return PersonaResponse.from_record(record)


@router.delete("/personas/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: int,
    tenant_id: str = Query(..., description="Tenant identifier"),
    repository: PersonaDataRepository = Depends(get_persona_repository),
) -> Response:
    try:
        await repository.delete_persona(tenant_id, persona_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/personas/{persona_id}/ingest", response_model=PersonaIngestResponse, status_code=status.HTTP_200_OK)
async def ingest_persona_data(
    persona_id: int,
    payload: PersonaIngestRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> PersonaIngestResponse:
    try:
        result = await rag_service.ingest_url(payload.url, persona_id)
        return PersonaIngestResponse(
            status=result["status"],
            documents_added=result["documents_added"],
            collection_name=result["collection_name"],
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

