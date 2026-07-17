"""
Sage Research Engine — Phase 07
Web research, document ingestion, source verification, and citation graph.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class SourceType(str, Enum):
    """Types of research sources."""
    WEB = "web"
    PDF = "pdf"
    IMAGE = "image"
    OCR = "ocr"
    UPLOAD = "upload"
    API = "api"


class SourceReputation(str, Enum):
    """Reputation tier of a source."""
    PRIMARY = "primary"       # Original source, first-party
    ESTABLISHED = "established" # Well-known publication
    UNVERIFIED = "unverified"   # Unknown source
    UNRELIABLE = "unreliable"   # Known unreliable


@dataclass
class ResearchSource:
    """A single research source with provenance."""
    source_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: SourceType = SourceType.WEB
    url: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    content_hash: str = ""  # For detecting changes
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    reputation: SourceReputation = SourceReputation.UNVERIFIED
    confidence_score: float = 0.5
    verification_notes: str = ""
    raw_text_length: int = 0


@dataclass
class SourcedClaim:
    """A claim extracted from research with full provenance."""
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    claim_text: str = ""
    source_id: str = ""
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.5
    corroborated_by: List[str] = field(default_factory=list)  # Other source_ids
    verification_status: str = "unverified"  # unverified, verified, disputed
    context: str = ""  # Surrounding text for context


@dataclass
class CitationEdge:
    """Edge in the citation graph."""
    source_id: str = ""  # Who is citing
    target_id: str = ""  # What is being cited
    edge_type: str = "cites"  # cites, corroborates, disputes
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ResearchNotebook:
    """Multi-step research session state."""
    notebook_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    status: str = "active"  # active, paused, complete
    sources: List[ResearchSource] = field(default_factory=list)
    claims: List[SourcedClaim] = field(default_factory=list)
    citation_edges: List[CitationEdge] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ResearchEngine:
    """
    Phase 07: Research Engine.
    Handles web fetching, document ingestion, source verification, and citation graph.
    """
    
    def __init__(self):
        self.notebooks: Dict[str, ResearchNotebook] = {}
        self.citation_graph: Dict[str, List[CitationEdge]] = {}
    
    async def start_research(self, query: str) -> ResearchNotebook:
        """Start a new research session."""
        notebook = ResearchNotebook(query=query)
        self.notebooks[notebook.notebook_id] = notebook
        
        # Step 1: Formulate search queries
        search_queries = await self._formulate_queries(query)
        
        # Step 2: Execute searches
        for sq in search_queries[:3]:
            sources = await self._execute_search(sq)
            notebook.sources.extend(sources)
        
        # Step 3: Extract claims from sources
        for source in notebook.sources[:10]:
            claims = await self._extract_claims(source)
            notebook.claims.extend(claims)
        
        # Step 4: Build citation graph
        notebook.citation_edges = self._build_citation_graph(notebook.claims)
        
        # Step 5: Score source confidence
        notebook = self._score_sources(notebook)
        
        notebook.updated_at = datetime.utcnow()
        return notebook
    
    async def _formulate_queries(self, query: str) -> List[str]:
        """Break research query into specific search queries."""
        # Phase 07 MVP: Simple decomposition
        # Future: Use LLM to generate targeted queries
        return [
            query,
            f"{query} latest news",
            f"{query} overview summary"
        ]
    
    async def _execute_search(self, search_query: str) -> List[ResearchSource]:
        """Execute web search and fetch results."""
        sources = []
        
        # MVP: Simulate search results
        # Future: Integrate with actual search API (Google, Bing, DuckDuckGo)
        mock_sources = [
            {
                "url": f"https://example.com/search?q={search_query.replace(' ', '+')}",
                "title": f"Results for: {search_query}",
                "content": f"This is a simulated search result for '{search_query}'. In production, this would be actual web content fetched from a search API.",
                "reputation": SourceReputation.UNVERIFIED
            }
        ]
        
        for data in mock_sources:
            source = ResearchSource(
                source_type=SourceType.WEB,
                url=data["url"],
                title=data["title"],
                content=data["content"],
                reputation=data["reputation"],
                raw_text_length=len(data["content"])
            )
            sources.append(source)
        
        return sources
    
    async def ingest_document(
        self,
        content: str,
        source_type: SourceType,
        metadata: Optional[Dict] = None
    ) -> ResearchSource:
        """
        Ingest a document (PDF, image OCR, uploaded text) into the research pipeline.
        """
        source = ResearchSource(
            source_type=source_type,
            title=metadata.get("filename", "Untitled Document") if metadata else "Untitled",
            content=content,
            raw_text_length=len(content)
        )
        
        # Assess reputation if URL provided
        if source.url:
            source.reputation = self._assess_reputation(source.url)
        
        # Hash content for change detection
        import hashlib
        source.content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        return source
    
    async def _extract_claims(self, source: ResearchSource) -> List[SourcedClaim]:
        """Extract factual claims from a source."""
        claims = []
        
        # MVP: Extract sentences as claims
        # Future: Use LLM to identify factual claims specifically
        sentences = [s.strip() for s in source.content.split('.') if len(s.strip()) > 20]
        
        for sentence in sentences[:5]:  # Limit to top 5 claims per source
            claim = SourcedClaim(
                claim_text=sentence[:500],
                source_id=source.source_id,
                source_url=source.url,
                source_title=source.title,
                confidence=0.5 if source.reputation == SourceReputation.UNVERIFIED else 0.7,
                context=sentence
            )
            claims.append(claim)
        
        return claims
    
    def _build_citation_graph(self, claims: List[SourcedClaim]) -> List[CitationEdge]:
        """Build citation edges between sources and claims."""
        edges = []
        
        # Group claims by source
        claims_by_source: Dict[str, List[SourcedClaim]] = {}
        for claim in claims:
            claims_by_source.setdefault(claim.source_id, []).append(claim)
        
        # Find corroborating claims (same text, different sources)
        claim_texts: Dict[str, List[str]] = {}  # text -> source_ids
        for claim in claims:
            key = claim.claim_text.lower().strip()
            claim_texts.setdefault(key, []).append(claim.source_id)
        
        # Create corroboration edges
        for text, source_ids in claim_texts.items():
            if len(source_ids) > 1:
                for i, sid in enumerate(source_ids):
                    for other_id in source_ids[i+1:]:
                        edges.append(CitationEdge(
                            source_id=sid,
                            target_id=other_id,
                            edge_type="corroborates",
                            confidence=min(0.5 + (len(source_ids) * 0.1), 0.9)
                        ))
        
        return edges
    
    def _score_sources(self, notebook: ResearchNotebook) -> ResearchNotebook:
        """Score source confidence based on reputation and corroboration."""
        # Count corroborations per source
        corroboration_counts: Dict[str, int] = {}
        for edge in notebook.citation_edges:
            if edge.edge_type == "corroborates":
                corroboration_counts[edge.source_id] = corroboration_counts.get(edge.source_id, 0) + 1
                corroboration_counts[edge.target_id] = corroboration_counts.get(edge.target_id, 0) + 1
        
        # Update source confidence scores
        for source in notebook.sources:
            base_score = {
                SourceReputation.PRIMARY: 0.9,
                SourceReputation.ESTABLISHED: 0.7,
                SourceReputation.UNVERIFIED: 0.5,
                SourceReputation.UNRELIABLE: 0.2
            }.get(source.reputation, 0.5)
            
            # Boost for corroboration
            corroboration_bonus = min(corroboration_counts.get(source.source_id, 0) * 0.05, 0.2)
            source.confidence_score = min(base_score + corroboration_bonus, 1.0)
            
            # Update claim confidences
            for claim in notebook.claims:
                if claim.source_id == source.source_id:
                    claim.confidence = source.confidence_score
                    if corroboration_bonus > 0:
                        claim.verification_status = "verified"
        
        return notebook
    
    def _assess_reputation(self, url: str) -> SourceReputation:
        """Assess source reputation from URL."""
        # MVP: Simple domain-based assessment
        # Future: Maintain a reputation database
        established_domains = [
            "wikipedia.org", "github.com", "arxiv.org",
            "nytimes.com", "bbc.com", "reuters.com",
            "medium.com", "substack.com"
        ]
        
        for domain in established_domains:
            if domain in url.lower():
                return SourceReputation.ESTABLISHED
        
        return SourceReputation.UNVERIFIED
    
    def get_notebook(self, notebook_id: str) -> Optional[ResearchNotebook]:
        """Retrieve a research notebook by ID."""
        return self.notebooks.get(notebook_id)
    
    def get_corroborated_claims(self, notebook_id: str) -> List[SourcedClaim]:
        """Get claims that have multiple source corroboration."""
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return []
        
        return [c for c in notebook.claims if len(c.corroborated_by) >= 1]
    
    def get_claim_sources(self, notebook_id: str) -> Dict[str, List[str]]:
        """Map claims to their supporting sources."""
        notebook = self.notebooks.get(notebook_id)
        if not notebook:
            return {}
        
        claim_sources = {}
        for claim in notebook.claims:
            claim_sources.setdefault(claim.claim_text, []).append(claim.source_id)
        
        return claim_sources


# Singleton
_research_engine: Optional[ResearchEngine] = None


def get_research_engine() -> ResearchEngine:
    """Get or create the global Research Engine."""
    global _research_engine
    if _research_engine is None:
        _research_engine = ResearchEngine()
    return _research_engine
