# Frontend API Specification

All endpoints are served from the FastAPI application (default base URL `http://localhost:8000`). Every route described below resides under the `/api` prefix unless otherwise noted.

## 1. API Profiles

### `GET /api/api-profiles`
- **Query parameters**: `tenant_id` (string, required)
- **Description**: Returns all API profiles belonging to the tenant. API keys are never returned; only a masked preview is shown.
- **Response** (`200 OK`):
```json
[
  {
    "id": 1,
    "tenant_id": "default",
    "name": "nim-default",
    "base_url": "https://integrate.api.nvidia.com/v1",
    "model": "meta/llama-3.1-70b-instruct",
    "temperature": 0.4,
    "created_at": "2025-11-20T09:30:00Z",
    "api_key_preview": "****abcd"
  }
]
```

### `POST /api/api-profiles`
- **Body fields**:
  - `tenant_id` (string, required)
  - `name` (string, required)
  - `base_url` (URL string, required)
  - `model` (string, required)
  - `api_key` (string, required; stored encrypted)
  - `temperature` (number, optional; defaults to 0.4)
- **Response** (`201 Created`): Returns the created profile without the raw API key.

## 2. Personas

### `GET /api/personas`
- **Query parameters**: `tenant_id` (string, required)
- **Description**: Lists all personas along with their bound API profile metadata.
- **Response** (`200 OK`):
```json
[
  {
    "id": 1,
    "tenant_id": "default",
    "name": "技术专家",
    "handle": "tech_expert",
    "prompt": "你是一个博学的技术专家",
    "tone": "confident",
    "proactivity": 0.7,
    "memory_window": 12,
    "max_agents_per_turn": 3,
    "is_default": true,
    "api_profile_id": 1,
    "api_profile_name": "nim-default",
    "api_model": "meta/llama-3.1-70b-instruct",
    "api_base_url": "https://integrate.api.nvidia.com/v1",
    "temperature": 0.4
  }
]
```

### `POST /api/personas`
- **Body fields**:
  - `tenant_id` (string, required)
  - `name` (string, required)
  - `prompt` (string, required)
  - `handle` (string, optional; defaults to slugified name)
  - `tone` (string, optional; default `neutral`)
  - `proactivity` (float 0-1, default 0.5)
  - `memory_window` (int ≥1, default 8)
  - `max_agents_per_turn` (int ≥1, default 2)
  - `api_profile_id` (int, optional)
  - `is_default` (bool, optional)
- **Response** (`201 Created`): Returns the persona summary.

## 3. Sessions & Messages

### `POST /api/sessions`
- **Query/body parameters**: `tenant_id` (string), `user_id` (string)
- **Description**: Allocates a new chat session and boots the runtime if needed.
- **Response** (`201 Created`): `{ "session_id": "sess_default_ab12cd34" }`

### `POST /api/sessions/{session_id}/messages`
- **Body fields**: `content` (string), optional `target_personas` field is handled by `SessionService` if included in future revisions.
- **Response** (`202 Accepted`): Message queued for runtime processing.

### `GET /api/sessions/{session_id}/messages`
- **Query parameters**: `limit` (int, default 50)
- **Response** (`200 OK`): Returns chronological message history with sender, content, and timestamp.

### `GET /api/sessions/{session_id}/messages (WebSocket)`
- **Endpoint**: `/ws/sessions/{session_id}`
- **Description**: Real-time stream of agent chunks for a running session. Messages are sent as JSON events of the form `{ "event": "agent.chunk", "data": "text" }`.

## 4. Error Handling

- All REST endpoints return standard HTTP status codes with `{"detail": "..."}` payloads on error.
- Persona creation validates API profile ownership and returns `400 Bad Request` if the IDs mismatch.
- Session and message routes return `404 Not Found` if the session does not exist.

## 5. Authentication

Authentication/authorization is not yet enforced; tenants are identified via the explicit `tenant_id` parameter. When integrating with the real frontend, pass the tenant context obtained during login.

Use these endpoints to drive the admin UI (API key management, persona editor) and the chat UI (session + WebSocket streaming).
