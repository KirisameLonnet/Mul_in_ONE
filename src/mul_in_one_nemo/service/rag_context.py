"""Context management for multi-tenant RAG operations.

Provides thread-safe context storage for tenant_id and persona_id
that tools can access during execution without exposing these
system metadata to the LLM.
"""

import contextvars
from typing import Optional

# Context variables for tenant and persona
_tenant_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'tenant_context', default=None
)
_persona_context: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    'persona_context', default=None
)


def set_rag_context(tenant_id: str, persona_id: int) -> None:
    """Set the current RAG context for this async task.
    
    Args:
        tenant_id: Tenant identifier for multi-tenant isolation
        persona_id: Persona identifier within the tenant
    """
    _tenant_context.set(tenant_id)
    _persona_context.set(persona_id)


def get_rag_context() -> tuple[Optional[str], Optional[int]]:
    """Get the current RAG context.
    
    Returns:
        Tuple of (tenant_id, persona_id)
    """
    return _tenant_context.get(), _persona_context.get()


def clear_rag_context() -> None:
    """Clear the RAG context for this async task."""
    _tenant_context.set(None)
    _persona_context.set(None)
