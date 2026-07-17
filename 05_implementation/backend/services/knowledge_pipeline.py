"""
Sage Knowledge Extraction Pipeline — Phase 12
Pluggable adapters, structure-aware chunking, NormalizedDocument envelope.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import hashlib


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    PDF_TEXT = "pdf_text"
    PDF_OCR = "pdf_ocr"
    HTML = "html"
    DOCX = "docx"
    IMAGE = "image"
    SLIDE_DECK = "slide_deck"
    SPREADSHEET = "spreadsheet"


class ContentBlockType(str, Enum):
    """Types of content blocks within a document."""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    QUOTE = "quote"
    IMAGE = "image"
    METADATA = "metadata"


@dataclass
class ContentBlock:
    """A single block of content within a document."""
    block_type: ContentBlockType
    content: str
    level: int = 0  # For headings: 1-6
    metadata: Dict[str, Any] = field(default_factory=dict)
    index: int = 0  # Position in document


@dataclass
class NormalizedDocument:
    """
    Phase 12: Standard document envelope.
    All documents, regardless of source format, resolve to this structure.
    """
    doc_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_format: DocumentFormat = DocumentFormat.PLAIN_TEXT
    original_filename: Optional[str] = None
    source_url: Optional[str] = None
    title: str = ""
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    language: str = "en"
    
    # Structure-aware content
    blocks: List[ContentBlock] = field(default_factory=list)
    
    # Chunking output
    chunks: List[str] = field(default_factory=list)
    chunk_embeddings: Optional[List[List[float]]] = None
    
    # Metadata
    word_count: int = 0
    page_count: Optional[int] = None
    extracted_images: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source_format": self.source_format.value,
            "word_count": self.word_count,
            "blocks_count": len(self.blocks),
            "chunks_count": len(self.chunks),
            "language": self.language,
            "extracted_at": self.extracted_at.isoformat()
        }


class DocumentAdapter:
    """Base class for document adapters."""
    
    def supports(self, raw_content: bytes, hint: str = "") -> bool:
        """Check if this adapter can handle the content."""
        raise NotImplementedError
    
    def parse(self, raw_content: bytes, metadata: Optional[Dict] = None) -> NormalizedDocument:
        """Parse raw content into NormalizedDocument."""
        raise NotImplementedError


class TextAdapter(DocumentAdapter):
    """Adapter for plain text and markdown."""
    
    def supports(self, raw_content: bytes, hint: str = "") -> bool:
        return hint in ("txt", "md", "text", "")
    
    def parse(self, raw_content: bytes, metadata: Optional[Dict] = None) -> NormalizedDocument:
        text = raw_content.decode('utf-8', errors='ignore')
        doc = NormalizedDocument(
            source_format=DocumentFormat.MARKDOWN if metadata and metadata.get('ext') == '.md' else DocumentFormat.PLAIN_TEXT,
            original_filename=metadata.get('filename') if metadata else None,
            title=metadata.get('title', '') if metadata else text.split('\n')[0][:100]
        )
        
        # Parse into blocks
        lines = text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            if stripped.startswith('#'):
                level = len(stripped) - len(stripped.lstrip('#'))
                doc.blocks.append(ContentBlock(
                    block_type=ContentBlockType.HEADING,
                    content=stripped.lstrip('#').strip(),
                    level=min(level, 6),
                    index=i
                ))
            elif stripped.startswith('- ') or stripped.startswith('* '):
                doc.blocks.append(ContentBlock(
                    block_type=ContentBlockType.LIST_ITEM,
                    content=stripped[2:],
                    index=i
                ))
            else:
                doc.blocks.append(ContentBlock(
                    block_type=ContentBlockType.PARAGRAPH,
                    content=stripped,
                    index=i
                ))
        
        doc.word_count = len(text.split())
        doc.content_hash = hashlib.sha256(raw_content).hexdigest()[:16]
        return doc


class PDFAdapter(DocumentAdapter):
    """Adapter for PDF documents."""
    
    def supports(self, raw_content: bytes, hint: str = "") -> bool:
        return hint == "pdf" or raw_content[:4] == b'%PDF'
    
    def parse(self, raw_content: bytes, metadata: Optional[Dict] = None) -> NormalizedDocument:
        # Phase 12 MVP: Treat as text extraction
        # Future: Use PyPDF2 or pdfplumber for proper parsing
        text = raw_content.decode('utf-8', errors='ignore')[:5000]
        
        doc = NormalizedDocument(
            source_format=DocumentFormat.PDF_TEXT,
            original_filename=metadata.get('filename') if metadata else None,
            title=metadata.get('title', 'PDF Document')
        )
        
        # Simple block extraction
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            doc.blocks.append(ContentBlock(
                block_type=ContentBlockType.PARAGRAPH,
                content=para[:500],
                index=i
            ))
        
        doc.word_count = len(text.split())
        doc.content_hash = hashlib.sha256(raw_content).hexdigest()[:16]
        return doc


class StructureAwareChunker:
    """
    Phase 12: Structure-aware chunking.
    Respects document boundaries (paragraphs, headings, lists).
    """
    
    def __init__(self, target_chunk_size: int = 500, overlap: int = 50):
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap
    
    def chunk(self, doc: NormalizedDocument) -> List[str]:
        """Chunk a normalized document while preserving structure."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for block in doc.blocks:
            block_text = block.content
            
            # Start new chunk on major boundaries
            if block.block_type == ContentBlockType.HEADING and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [block_text]
                current_size = len(block_text)
                continue
            
            # Check if adding this block would exceed target
            if current_size + len(block_text) > self.target_chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                # Carry over overlap
                overlap_text = current_chunk[-1] if len(current_chunk[-1]) <= self.overlap else current_chunk[-1][-self.overlap:]
                current_chunk = [overlap_text, block_text]
                current_size = len(overlap_text) + len(block_text)
            else:
                current_chunk.append(block_text)
                current_size += len(block_text)
        
        # Add remaining
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks


class KnowledgeExtractionPipeline:
    """
    Phase 12: Unified extraction pipeline.
    """
    
    def __init__(self):
        self.adapters: List[DocumentAdapter] = [
            TextAdapter(),
            PDFAdapter(),
            # Future: HTMLAdapter, DOCXAdapter, ImageOCRAdapter
        ]
        self.chunker = StructureAwareChunker()
    
    def process(self, raw_content: bytes, format_hint: str = "", metadata: Optional[Dict] = None) -> NormalizedDocument:
        """
        Main entry point: Process any document into NormalizedDocument.
        """
        # Step 1: Find appropriate adapter
        adapter = None
        for a in self.adapters:
            if a.supports(raw_content, format_hint):
                adapter = a
                break
        
        if not adapter:
            # Fallback to text adapter
            adapter = self.adapters[0]
        
        # Step 2: Parse into normalized document
        doc = adapter.parse(raw_content, metadata)
        
        # Step 3: Structure-aware chunking
        doc.chunks = self.chunker.chunk(doc)
        
        return doc
    
    def add_adapter(self, adapter: DocumentAdapter):
        """Register a new document adapter."""
        self.adapters.insert(0, adapter)  # Higher priority


# Singleton
_pipeline: Optional[KnowledgeExtractionPipeline] = None


def get_extraction_pipeline() -> KnowledgeExtractionPipeline:
    """Get or create the global Knowledge Extraction Pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = KnowledgeExtractionPipeline()
    return _pipeline
