"""Agent API — exposes health, state, policy, one-shot run, investigation, and knowledge endpoints."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from services.agent.agent import _load_state, investigate_single_asset, run_once
from services.agent.knowledge import (
    get_document,
    list_document_summaries,
)
from services.agent.knowledge import (
    search as search_knowledge,
)
from services.agent.policy import describe_policy

app = FastAPI(
    title="Autonomous Support Agent",
    description="API for the autonomous CCTV technical-support agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health():
    return {"ok": True, "service": "agent"}


@app.get("/state", tags=["agent"])
def state():
    """Return the agent's current state (active incidents and history)."""
    return _load_state()


@app.get("/policy", tags=["agent"])
def policy():
    """Return the full action safety policy for inspection."""
    return describe_policy()


@app.post("/run-once", tags=["agent"])
async def trigger_run():
    """Execute one full investigation cycle and return state."""
    return await run_once()


@app.post("/investigate/{asset_id}", tags=["agent"])
async def trigger_investigate(asset_id: str):
    """Trigger an on-demand, end-to-end investigation for a specific asset with a detailed timeline."""
    report = await investigate_single_asset(asset_id)
    if not report.get("found", True):
        raise HTTPException(status_code=404, detail=report.get("error", "Asset not found"))
    return report


@app.get("/knowledge", tags=["knowledge"])
def get_knowledge_documents():
    """Return summaries of all available knowledge documents."""
    return list_document_summaries()


@app.get("/knowledge/doc/{doc_path:path}", tags=["knowledge"])
def get_single_document(doc_path: str):
    """Retrieve full text and metadata of a specific knowledge document."""
    doc = get_document(doc_path)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Knowledge document '{doc_path}' not found")
    return doc


@app.get("/knowledge-search", tags=["knowledge"])
def search_knowledge_endpoint(q: str = Query(..., description="Query terms to search knowledge base")):
    """Search knowledge base articles for query terms."""
    return search_knowledge(q)

