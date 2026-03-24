"""Query endpoints — persistent insight queries with background execution."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from logos.data.insight_queries import (
    _MAX_CONCURRENT,
    active_count,
    delete,
    get,
    load_all,
    start,
)
from logos.query_dispatch import get_agent_list

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


class QueryRunRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be empty")
        return v.strip()


class QueryRefineRequest(BaseModel):
    query: str
    parent_id: str
    prior_result: str
    agent_type: str

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be empty")
        return v.strip()


@router.get("/agents")
async def list_query_agents():
    """List available query agent types."""
    agents = get_agent_list()
    return [
        {
            "agent_type": a.agent_type,
            "name": a.name,
            "description": a.description,
        }
        for a in agents
    ]


@router.post("/run")
async def run_query_endpoint(req: QueryRunRequest):
    """Start a background insight query. Returns immediately with the query ID."""
    if active_count() >= _MAX_CONCURRENT:
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent queries (max {_MAX_CONCURRENT})",
        )
    record = start(req.query)
    return {"id": record["id"], "status": record["status"]}


@router.post("/refine")
async def refine_query_endpoint(req: QueryRefineRequest):
    """Start a refinement query with prior context."""
    agent_types = {a.agent_type for a in get_agent_list()}
    if req.agent_type not in agent_types:
        raise HTTPException(status_code=400, detail=f"Unknown agent type: {req.agent_type}")

    if active_count() >= _MAX_CONCURRENT:
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent queries (max {_MAX_CONCURRENT})",
        )

    record = start(
        req.query,
        parent_id=req.parent_id,
        prior_context=req.prior_result,
        agent_type_override=req.agent_type,
    )
    return {"id": record["id"], "status": record["status"]}


@router.get("/list")
async def list_queries():
    """List all persisted insight queries, newest first."""
    records = load_all()
    records.reverse()
    return {"queries": records}


@router.get("/{query_id}")
async def get_query(query_id: str):
    """Get a single insight query by ID."""
    record = get(query_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Query not found")
    return record


@router.delete("/{query_id}")
async def delete_query(query_id: str):
    """Delete an insight query. Cancels it if still running."""
    if not delete(query_id):
        raise HTTPException(status_code=404, detail="Query not found")
    return {"deleted": query_id}
