"""
Knowledge Node Vector Store for Semantic Chat Search

Embeds every KnowledgeNode title+content into ChromaDB and provides
cosine-similarity semantic search for the chat endpoint.
"""
from typing import List, Dict, Optional, Any
import os

# Use existing embedding infrastructure
from services.embedding_service import get_embedding, chroma_client

COLLECTION_NAME = "knowledge_nodes"

# Source types we NEVER embed (fragments, auto-extracted junk)
SKIP_SOURCE_TYPES = {"extracted_entity", "asset_extraction"}


def _node_to_text(node) -> str:
    """Convert a KnowledgeNode into an embeddable text string."""
    parts = [f"Title: {node.title or ''}"]
    if node.content:
        parts.append(f"Content: {node.content[:800]}")  # first 800 chars
    if node.ai_summary:
        parts.append(f"Summary: {node.ai_summary[:400]}")
    if node.layer:
        parts.append(f"Layer: {node.layer}")
    if node.source_type:
        parts.append(f"Type: {node.source_type}")
    return "\n".join(parts)


def sync_node(node) -> bool:
    """Upsert a single KnowledgeNode into the vector store.
    Call this after db.commit() when a node is created or updated.
    """
    if not node or not node.id:
        return False
    if node.source_type in SKIP_SOURCE_TYPES:
        return False
    if node.is_archived:
        delete_node(node.id)
        return True

    try:
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        text = _node_to_text(node)
        metadata = {
            "workspace_id": str(node.workspace_id) if node.workspace_id else "",
            "title": (node.title or "")[:200],
            "layer": node.layer or "project",
            "source_type": node.source_type or "",
        }
        embedding = get_embedding(text)
        collection.upsert(
            ids=[str(node.id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        return True
    except Exception as e:
        print(f"[KnowledgeVectorStore] sync_node error: {e}")
        return False


def delete_node(node_id: str) -> bool:
    """Remove a node from the vector store."""
    try:
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        collection.delete(ids=[str(node_id)])
        return True
    except Exception as e:
        print(f"[KnowledgeVectorStore] delete_node error: {e}")
        return False


def semantic_search(query_text: str, workspace_id: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Search knowledge nodes by semantic similarity.
    Returns a list of dicts with keys: id, text, metadata, distance, score.
    """
    try:
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

        # Check collection size first
        count = collection.count()
        if count == 0:
            return []

        query_embedding = get_embedding(query_text)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"workspace_id": str(workspace_id)}  # ChromaDB metadata filter
        )

        matches = []
        if results and results.get("ids"):
            ids = results["ids"][0]
            documents = results["documents"][0] if results.get("documents") else []
            metadatas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for i, nid in enumerate(ids):
                dist = distances[i] if i < len(distances) else 1.0
                score = max(0.0, 1.0 - dist)  # cosine distance -> similarity
                matches.append({
                    "id": nid,
                    "text": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": dist,
                    "score": round(score, 4)
                })
        return matches
    except Exception as e:
        print(f"[KnowledgeVectorStore] semantic_search error: {e}")
        return []


def get_collection_count() -> int:
    """Return the number of vectors in the knowledge_nodes collection."""
    try:
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        return collection.count()
    except Exception:
        return 0
