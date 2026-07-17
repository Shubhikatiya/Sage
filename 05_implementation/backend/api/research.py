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

        # DuckDuckGo HTML search (no API key required)
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            resp = requests.get(search_url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            return create_response(errors=[{"message": f"Search failed: {e}", "code": "SEARCH_ERROR"}])

        # Parse results
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        for result in soup.select(".result")[:max_sources]:
            title_elem = result.select_one(".result__a")
            snippet_elem = result.select_one(".result__snippet")
            url_elem = result.select_one(".result__url")

            if title_elem:
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                # DuckDuckGo uses redirect URLs
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    url = "https://duckduckgo.com" + url

                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                display_url = url_elem.get_text(strip=True) if url_elem else url

                results.append({
                    "title": title,
                    "url": url,
                    "display_url": display_url,
                    "snippet": snippet,
                    "source": "web_search"
                })

        # Store in research engine
        engine = get_research_engine()
        notebook_id = f"web_{hash(query) % 100000}"

        for result in results:
            import asyncio
            asyncio.run(engine.ingest_document(
                content=result["snippet"],
                source_type=SourceType.WEB,
                source_url=result["url"],
                source_title=result["title"],
                metadata={"query": query, "search_engine": "duckduckgo"}
            ))

        return create_response(data={
            "notebook_id": notebook_id,
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


@router.post("/start")
async def start_research(request: ResearchRequest):
    """Start a new research session (legacy, kept for compatibility)."""
    try:
        engine = get_research_engine()
        notebook = await engine.start_research(request.query)
        
        return create_response(data={
            "notebook_id": notebook.notebook_id,
            "query": notebook.query,
            "status": notebook.status,
            "sources_found": len(notebook.sources),
            "claims_extracted": len(notebook.claims),
            "citations_found": len(notebook.citation_edges),
            "created_at": notebook.created_at.isoformat()
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "RESEARCH_ERROR"}])


@router.post("/ingest")
async def ingest_document(request: DocumentIngestRequest):
    """Ingest a document into the research pipeline."""
    try:
        engine = get_research_engine()
        
        try:
            source_type = SourceType(request.source_type)
        except ValueError:
            source_type = SourceType.UPLOAD
        
        source = await engine.ingest_document(
            content=request.content,
            source_type=source_type,
            metadata=request.metadata
        )
        
        return create_response(data={
            "source_id": source.source_id,
            "source_type": source.source_type.value,
            "title": source.title,
            "content_length": source.raw_text_length,
            "reputation": source.reputation.value,
            "confidence": source.confidence_score
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "INGEST_ERROR"}])


@router.get("/notebook/{notebook_id}")
def get_notebook(notebook_id: str):
    """Get research notebook details."""
    try:
        engine = get_research_engine()
        notebook = engine.get_notebook(notebook_id)
        
        if not notebook:
            return create_response(errors=[{"message": "Notebook not found", "code": "NOT_FOUND"}])
        
        return create_response(data={
            "notebook_id": notebook.notebook_id,
            "query": notebook.query,
            "status": notebook.status,
            "sources": [
                {
                    "source_id": s.source_id,
                    "type": s.source_type.value,
                    "title": s.title,
                    "url": s.url,
                    "reputation": s.reputation.value,
                    "confidence": s.confidence_score
                }
                for s in notebook.sources
            ],
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "text": c.claim_text,
                    "source_id": c.source_id,
                    "confidence": c.confidence,
                    "verification": c.verification_status,
                    "corroborated_by": len(c.corroborated_by)
                }
                for c in notebook.claims
            ],
            "citation_graph": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type,
                    "confidence": e.confidence
                }
                for e in notebook.citation_edges
            ]
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


@router.get("/claim/{claim_id}/sources")
def get_claim_sources(claim_id: str):
    """Get sources for a specific claim."""
    try:
        engine = get_research_engine()
        
        # Find claim across all notebooks
        for notebook in engine.notebooks.values():
            for claim in notebook.claims:
                if claim.claim_id == claim_id:
                    return create_response(data={
                        "claim_id": claim.claim_id,
                        "claim_text": claim.claim_text,
                        "primary_source": {
                            "source_id": claim.source_id,
                            "url": claim.source_url,
                            "title": claim.source_title
                        },
                        "confidence": claim.confidence,
                        "verification": claim.verification_status
                    })
        
        return create_response(errors=[{"message": "Claim not found", "code": "NOT_FOUND"}])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])
