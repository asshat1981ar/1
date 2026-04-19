"""
ChromaDB vector store for semantic search over toolbank records.
Falls back gracefully if chromadb is not installed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings

    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed – semantic search will be disabled.")

_client = None
_collection = None

COLLECTION_NAME = "toolbank_tools"


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    if not _CHROMA_AVAILABLE:
        return None
    _client = chromadb.PersistentClient(
        path="toolbank/chroma_data",
        settings=Settings(anonymized_telemetry=False),
    )
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def index_tool(record: dict[str, Any]) -> None:
    """Add or update a tool record in the vector index."""
    col = _get_collection()
    if col is None:
        return
    tool_id = record["id"]
    # Build a rich text representation for embedding
    text_parts = [
        record.get("name", ""),
        record.get("description", ""),
        " ".join(record.get("tags", [])),
        record.get("namespace", ""),
        record.get("transport", ""),
    ]
    doc_text = " | ".join(p for p in text_parts if p)
    metadata = {
        "namespace": record.get("namespace", ""),
        "side_effect_level": record.get("side_effect_level", "read"),
        "status": record.get("status", "draft"),
        "transport": record.get("transport", "rest"),
        "source_type": record.get("source_type", "docs"),
        "tags": json.dumps(record.get("tags", [])),
    }
    col.upsert(
        ids=[tool_id],
        documents=[doc_text],
        metadatas=[metadata],
    )
    logger.debug("Indexed tool %s in ChromaDB", tool_id)


def search_tools(
    query: str,
    n_results: int = 10,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Semantic search over indexed tools.
    Returns a list of {id, score, metadata} dicts.
    """
    col = _get_collection()
    if col is None:
        return []
    count = col.count()
    if count == 0:
        return []
    kwargs: dict[str, Any] = {
        "query_texts": [query],
        "n_results": min(n_results, count),
        "include": ["metadatas", "distances", "documents"],
    }
    where = filters or {}
    if where:
        kwargs["where"] = where
    results = col.query(**kwargs)
    hits = []
    for i, doc_id in enumerate(results["ids"][0]):
        hits.append(
            {
                "id": doc_id,
                "score": 1.0 - results["distances"][0][i],  # cosine similarity
                "metadata": results["metadatas"][0][i],
                "document": results["documents"][0][i],
            }
        )
    return hits


def remove_tool(tool_id: str) -> None:
    """Remove a tool from the vector index."""
    col = _get_collection()
    if col is None:
        return
    col.delete(ids=[tool_id])
