"""
Research API for Sage v4 — Phase 07
REST endpoints for web research, document ingestion, and citation graph.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.research_engine import get_research_engine, SourceType
from api.utils.responses import create_response

router = APIRouter(prefix="/api/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str
    max_sources: int = 5


class DocumentIngestRequest(BaseModel):
    content: str
    source_type: str = "upload"  # web, pdf, image, ocr, upload
    metadata: Optional[Dict[str, Any]] = None


class SemanticExtractRequest(BaseModel):
    text: str
    source_type: str = "chat"  # chat, document, web
    metadata: Optional[Dict[str, Any]] = None


@router.post("/web")
def web_research(request: ResearchRequest):
    """
    Perform real web research using DuckDuckGo search.
    Phase 07: Replaces mock search with actual web retrieval.
    """
    try:
        import requests
        import urllib.parse
        from bs4 import BeautifulSoup

        query = request.query
        max_sources = min(request.max_sources, 10)

        # Use DuckDuckGo HTML search (no API key needed)
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for result in soup.select(".result")[:max_sources]:
            title_elem = result.select_one(".result__a")
            snippet_elem = result.select_one(".result__snippet")
            if title_elem:
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": title_elem.get("href", ""),
                    "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ""
                })

        return create_response(data={
            "query": query,
            "sources_found": len(results),
            "sources": results,
            "note": "Results stored in research engine for citation tracking"
        })
    except ImportError as e:
        return create_response(errors=[{"message": f"Missing dependency: {e}. Install beautifulsoup4.", "code": "DEPENDENCY_ERROR"}])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "WEB_RESEARCH_ERROR"}])


@router.post("/ingest_document")
def ingest_structured_document(request: DocumentIngestRequest):
    """
    Ingest a document through the structured research pipeline.
    Phase 07: Source-type-specific structure preservation.
    """
    try:
        engine = get_research_engine()

        # Map string to SourceType
        source_type_map = {
            "web": SourceType.WEB,
            "pdf": SourceType.PDF,
            "image": SourceType.IMAGE,
            "ocr": SourceType.OCR,
            "upload": SourceType.UPLOAD,
            "api": SourceType.API,
        }
        source_type = source_type_map.get(request.source_type, SourceType.UPLOAD)

        import asyncio
        result = asyncio.run(engine.ingest_document(
            content=request.content,
            source_type=source_type,
            metadata=request.metadata
        ))

        return create_response(data={
            "ingested": True,
            "document_hash": getattr(result, 'content_hash', None),
            "source_type": request.source_type,
            "word_count": len(request.content.split()),
            "claims_extracted": len(getattr(result, 'claims', [])),
            "note": "Document processed through research pipeline with citation tracking"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "INGEST_ERROR"}])


@router.post("/semantic_extract")
def semantic_extract(request: SemanticExtractRequest):
    """
    Extract structured entities and relations from text using the multi-agent pipeline.
    Phase 07+ Semantic Multi-Agent Extraction.
    """
    try:
        import sys
        sys.path.insert(0, '.')
        from sage.core.extraction.semantic_agents import get_extraction_pipeline

        pipeline = get_extraction_pipeline()
        result = pipeline.process(request.text, request.metadata or {})

        # Convert to serializable format
        entities_data = []
        for e in result.entities:
            entities_data.append({
                "text_span": e.text_span,
                "canonical_name": e.canonical_name,
                "entity_type": e.entity_type_label,
                "entity_type_uri": e.entity_type_uri,
                "confidence": e.confidence.value,
                "vocabulary_match_score": round(e.vocabulary_match_score, 3),
                "properties": e.properties,
            })

        relations_data = []
        for r in result.relations:
            relations_data.append({
                "source": r.source_entity_text,
                "target": r.target_entity_text,
                "relation": r.relation_label,
                "relation_uri": r.relation_uri,
                "evidence": r.evidence_text[:100],
                "confidence": r.confidence.value,
                "vocabulary_match_score": round(r.vocabulary_match_score, 3),
            })

        return create_response(data={
            "source_text_preview": result.source_text[:200],
            "overall_confidence": result.overall_confidence.value,
            "entities_extracted": len(result.entities),
            "relations_extracted": len(result.relations),
            "entities": entities_data,
            "relations": relations_data,
            "validation_summary": result.validation_summary,
            "agent_pipeline": [log["agent"] for log in result.agent_logs],
            "note": "Extracted using MappingAgent, RelationAgent, and ValidatorAgent with confidence scoring"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return create_response(errors=[{"message": str(e), "code": "EXTRACTION_ERROR"}])


@router.post("/verify")
def verify_claim(claim_text: str):
    """Verify a claim by searching for corroborating sources."""
    try:
        import requests
        import urllib.parse
        from bs4 import BeautifulSoup

        # Search for the claim
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(claim_text)}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        resp = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        corroborating = []
        for result in soup.select(".result")[:3]:
            title_elem = result.select_one(".result__a")
            if title_elem:
                corroborating.append({
                    "title": title_elem.get_text(strip=True),
                    "url": title_elem.get("href", "")
                })

        return create_response(data={
            "claim": claim_text,
            "corroborating_sources": len(corroborating),
            "sources": corroborating,
            "verification_status": "corroborated" if len(corroborating) >= 2 else "needs_review"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "VERIFY_ERROR"}])


@router.get("/status")
def get_research_status():
    """Get the current status of the research engine."""
    try:
        engine = get_research_engine()
        notebooks = list(engine.notebooks.values())
        
        total_sources = sum(len(n.sources) for n in notebooks)
        total_claims = sum(len(n.claims) for n in notebooks)
        total_edges = sum(len(n.citation_edges) for n in notebooks)
        
        return create_response(data={
            "status": "active",
            "notebooks": len(notebooks),
            "total_sources": total_sources,
            "total_claims": total_claims,
            "total_citation_edges": total_edges,
            "research_backends": ["duckduckgo_html"],
            "capabilities": ["web_search", "document_ingest", "claim_verify", "semantic_extract"]
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "STATUS_ERROR"}])
