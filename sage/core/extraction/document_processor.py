"""
Document-to-Knowledge Graph Processor

Processes text (documents, chat messages, web pages) and converts them into a
network of KnowledgeNodes + KnowledgeEdges with AI summaries.

Pipeline:
1. Extract entities using simple but robust heuristics
2. Create KnowledgeNodes for the document + entities
3. Link entities to the document via KnowledgeEdges
4. Generate AI summary fields for the document node
"""
import re
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# SQLAlchemy
from sqlalchemy.orm import Session

# Sage models
from models_v4 import (
    KnowledgeNode, KnowledgeEdge, NodeType, Workspace,
    KnowledgeEdge as KnowledgeEdgeModel
)


# ─── Simple but robust entity extraction ───
# We skip heavy LLM/NER here and use fast regex heuristics + context patterns.
# This is deliberate: extraction needs to be fast for real-time ingestion.

ENTITY_PATTERNS = {
    "person": {
        "regex": re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'),
        "keywords": ["founded by", "created by", "led by", "managed by", "CEO of", "CTO of", "head of", "author"],
        "examples": ["Shubhi Katiyar", "Alice Johnson"]
    },
    "organization": {
        "regex": re.compile(r'\b([A-Z][a-z]*(?:\s+[A-Z][a-z]+){0,3}(?:\s+(?:Inc|Ltd|LLC|Corp|Company|Foundation|Institute|University|College))?)'),
        "keywords": ["company", "startup", "organization", "nonprofit", "foundation", "university"],
        "examples": ["Navgunjara", "OpenAI", "Google"]
    },
    "project": {
        "regex": re.compile(r'(?:project|product|app|tool|system|platform)\s+(?:called|named)?\s*["\']?([^"\',.]{2,40})["\']?'),
        "keywords": ["project", "product", "app", "platform", "system", "tool"],
        "examples": ["Sage", "ReRoot", "Kaal"]
    },
    "technology": {
        "regex": re.compile(r'\b((?:AI|ML|NLP|React|Python|JavaScript|TypeScript|Node\.js|TensorFlow|PyTorch|Docker|Kubernetes)(?:\s+(?:model|engine|framework|library|platform))?)'),
        "keywords": ["uses", "built with", "powered by", "implemented in", "using"],
        "examples": ["Python", "React", "TensorFlow"]
    },
    "goal": {
        "regex": re.compile(r'(?:goal|objective|aim|target)\s+(?:is\s+to\s+)?["\']?([^"\',.]{5,80})["\']?'),
        "keywords": ["goal", "objective", "aim", "target", "mission"],
        "examples": ["reduce churn by 20%", "launch by December"]
    },
    "deadline": {
        "regex": re.compile(r'(?:by|before|due|deadline)\s+(?:date\s+)?["\']?([^"\',.]{3,40})["\']?'),
        "keywords": ["deadline", "due", "by", "before", "end of", "Q1", "Q2", "Q3", "Q4"],
        "examples": ["end of Q2", "March 15", "next month"]
    },
}

STOP_NAMES = {"This", "The", "A", "An", "It", "They", "We", "I", "He", "She", "That", "These", "Those"}


def _extract_entities(text: str) -> List[Dict[str, Any]]:
    """Extract candidate entities from text using patterns."""
    found = []
    seen = set()
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sent_idx, sentence in enumerate(sentences):
        sent_lower = sentence.lower()
        
        for entity_type, config in ENTITY_PATTERNS.items():
            # Try regex match
            for match in config["regex"].finditer(sentence):
                span = match.group(1) if match.groups() else match.group()
                if not span or len(span) < 2:
                    continue
                if span in STOP_NAMES or span.lower() in STOP_NAMES:
                    continue
                
                key = (span.lower(), entity_type)
                if key in seen:
                    continue
                seen.add(key)
                
                # Score based on keyword presence in sentence
                keyword_score = sum(1 for kw in config["keywords"] if kw in sent_lower)
                confidence = min(0.9, 0.5 + keyword_score * 0.1)
                
                found.append({
                    "text_span": span,
                    "canonical": span.strip(),
                    "type": entity_type,
                    "sentence_idx": sent_idx,
                    "sentence": sentence[:200],
                    "confidence": confidence,
                    "position": match.start()
                })
    
    # Sort by confidence
    found.sort(key=lambda x: x["confidence"], reverse=True)
    return found


def _extract_relations(text: str, entities: List[Dict]) -> List[Dict[str, Any]]:
    """Extract relations between entities based on sentence co-occurrence."""
    relations = []
    
    if len(entities) < 2:
        return relations
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sent_idx, sentence in enumerate(sentences):
        sent_lower = sentence.lower()
        sent_entities = [e for e in entities if e["sentence_idx"] == sent_idx]
        
        if len(sent_entities) >= 2:
            for i in range(len(sent_entities)):
                for j in range(i + 1, len(sent_entities)):
                    e1 = sent_entities[i]
                    e2 = sent_entities[j]
                    
                    # Determine relation type based on verbs/adpositions
                    rel_type = "relatedTo"
                    rel_label = "Related To"
                    
                    if any(v in sent_lower for v in ["founded", "created", "started", "built"]):
                        rel_type = "createdBy"
                        rel_label = "Created By"
                    elif any(v in sent_lower for v in ["works on", "manages", "leads", "owns"]):
                        rel_type = "worksOn"
                        rel_label = "Works On"
                    elif any(v in sent_lower for v in ["part of", "member of", "inside", "within"]):
                        rel_type = "partOf"
                        rel_label = "Part Of"
                    elif any(v in sent_lower for v in ["depends on", "requires", "needs", "relies on"]):
                        rel_type = "dependsOn"
                        rel_label = "Depends On"
                    elif any(v in sent_lower for v in ["uses", "built with", "powered by", "implemented in"]):
                        rel_type = "uses"
                        rel_label = "Uses"
                    
                    relations.append({
                        "source_text": e1["canonical"],
                        "target_text": e2["canonical"],
                        "relation_type": rel_type,
                        "relation_label": rel_label,
                        "evidence": sentence[:200],
                        "confidence": min(e1["confidence"], e2["confidence"])
                    })
    
    return relations


def _generate_ai_summary(text: str, entities: List[Dict], relations: List[Dict]) -> Dict[str, Any]:
    """Generate AI summary fields from extracted structure."""
    word_count = len(text.split())
    
    # Extract key themes (entity types)
    entity_types = {}
    for e in entities:
        entity_types[e["type"]] = entity_types.get(e["type"], 0) + 1
    themes = list(entity_types.keys())
    
    # Build a short summary from first sentence + key entities
    first_sentence = re.split(r'(?<=[.!?])\s+', text)[0][:200] if text else ""
    top_entities = [e["canonical"] for e in entities[:5]]
    
    short_summary = first_sentence
    if top_entities:
        short_summary += f"\n\nKey entities: {', '.join(top_entities)}."
    
    # Build a more detailed summary
    summary_parts = [first_sentence]
    if relations:
        summary_parts.append(f"\nIdentified {len(relations)} relationships between entities.")
    if entities:
        by_type = {}
        for e in entities:
            by_type.setdefault(e["type"], []).append(e["canonical"])
        summary_parts.append("\nExtracted entities:")
        for t, names in by_type.items():
            summary_parts.append(f"  - {t}: {', '.join(names[:5])}")
    
    full_summary = "\n".join(summary_parts)
    
    # Importance: based on entity density and relation count
    density = len(entities) / max(word_count / 100, 1)
    importance = min(1.0, 0.3 + density * 0.3 + len(relations) * 0.1)
    
    # Novelty: placeholder based on entity uniqueness (could compare to existing KG)
    novelty = 0.7  # Default to moderate novelty
    
    return {
        "ai_summary": full_summary[:2000],
        "ai_short_summary": short_summary[:500],
        "ai_keywords": themes + [e["canonical"] for e in entities[:10]],
        "ai_entities": entities,
        "ai_importance_score": round(importance, 2),
        "ai_novelty_score": round(novelty, 2),
        "ai_missing_information": "",
        "ai_suggested_questions": [],
        "ai_next_actions": [],
    }


# ───────────────────────────────────────────────────────────────
# DOCUMENT PROCESSOR
# ───────────────────────────────────────────────────────────────

class DocumentProcessor:
    """
    Processes raw text and converts it into a knowledge graph sub-network.
    """
    
    def __init__(self, db: Session, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        self._node_type_cache = {}
    
    def _get_or_create_node_type(self, slug: str, display_name: str) -> str:
        """Get or create a NodeType by name. Returns the ID."""
        if slug in self._node_type_cache:
            return self._node_type_cache[slug]
        
        nt = self.db.query(NodeType).filter(NodeType.name == slug).first()
        if nt:
            self._node_type_cache[slug] = nt.id
            return nt.id
        
        # Create new node type
        nt_id = str(uuid.uuid4())
        nt = NodeType(
            id=nt_id,
            workspace_id=self.workspace_id,
            name=slug,
            display_name=display_name,
            description=f"Auto-created node type for {display_name}"
        )
        self.db.add(nt)
        self.db.commit()
        self._node_type_cache[slug] = nt_id
        return nt_id
    
    def process(self, text: str, title: str = "Untitled Document",
                source_type: str = "extracted", source_id: str = None) -> Dict[str, Any]:
        """
        Process text and create knowledge graph nodes + edges.
        
        Returns:
            {
                "document_node_id": str,
                "entity_nodes": [node_id, ...],
                "relations_created": int,
                "ai_summary": str,
                "extracted_entities": [...],
            }
        """
        if not text or len(text.strip()) < 10:
            return {"error": "Text too short", "document_node_id": None}
        
        # Step 1: Extract entities
        entities = _extract_entities(text)
        
        # Step 2: Extract relations
        relations = _extract_relations(text, entities)
        
        # Step 3: Generate AI summary
        ai_data = _generate_ai_summary(text, entities, relations)
        
        # Step 4: Create document node
        doc_node_type_id = self._get_or_create_node_type("document", "Document")
        doc_id = str(uuid.uuid4())
        doc_slug = re.sub(r'[^\w\-]', '-', title.lower())[:50] or f"doc-{doc_id[:8]}"
        
        doc_node = KnowledgeNode(
            id=doc_id,
            workspace_id=self.workspace_id,
            node_type_id=doc_node_type_id,
            slug=doc_slug,
            title=title,
            content=text,
            layer="project",
            status="active",
            source_type=source_type,
            source_id=source_id or doc_id,
            ai_summary=ai_data["ai_summary"],
            ai_short_summary=ai_data["ai_short_summary"],
            ai_keywords=ai_data["ai_keywords"],
            ai_entities=ai_data["ai_entities"],
            ai_importance_score=ai_data["ai_importance_score"],
            ai_novelty_score=ai_data["ai_novelty_score"],
            ai_missing_information=ai_data["ai_missing_information"],
            ai_suggested_questions=ai_data["ai_suggested_questions"],
            ai_next_actions=ai_data["ai_next_actions"],
            completeness_percent=min(100, 30 + len(entities) * 5 + len(relations) * 3),
        )
        self.db.add(doc_node)
        self.db.flush()  # Get ID assigned
        
        # Step 5: Create entity nodes
        entity_nodes = {}
        entity_type_map = {
            "person": ("person", "Person"),
            "organization": ("organization", "Organization"),
            "project": ("project", "Project"),
            "technology": ("technology", "Technology"),
            "goal": ("goal", "Goal"),
            "deadline": ("deadline", "Deadline"),
        }
        
        for entity in entities:
            slug, name = entity_type_map.get(entity["type"], ("concept", "Concept"))
            nt_id = self._get_or_create_node_type(slug, name)
            
            ent_id = str(uuid.uuid4())
            ent_slug = re.sub(r'[^\w\-]', '-', entity["canonical"].lower())[:50] or f"ent-{ent_id[:8]}"
            
            ent_node = KnowledgeNode(
                id=ent_id,
                workspace_id=self.workspace_id,
                node_type_id=nt_id,
                slug=ent_slug,
                title=entity["canonical"],
                content=entity.get("sentence", ""),
                layer="project",
                status="active",
                source_type="extracted_entity",
                source_id=doc_id,
                ai_short_summary=entity.get("sentence", "")[:200],
                ai_keywords=[entity["type"]],
                ai_entities=[entity],
                ai_importance_score=entity["confidence"],
            )
            self.db.add(ent_node)
            self.db.flush()
            entity_nodes[entity["canonical"].lower()] = ent_id
        
        # Step 6: Create edges (document -> entities, entity -> entity)
        edges_created = 0
        
        # Document contains entities
        for entity in entities:
            ent_id = entity_nodes.get(entity["canonical"].lower())
            if ent_id:
                edge = KnowledgeEdgeModel(
                    id=str(uuid.uuid4()),
                    workspace_id=self.workspace_id,
                    source_id=doc_id,
                    target_id=ent_id,
                    evidence=f"Extracted from document: {title}",
                    confidence=entity["confidence"],
                    weight=1.0,
                    notes="Auto-extracted entity"
                )
                self.db.add(edge)
                edges_created += 1
        
        # Entity relationships
        for rel in relations:
            src_id = entity_nodes.get(rel["source_text"].lower())
            tgt_id = entity_nodes.get(rel["target_text"].lower())
            if src_id and tgt_id:
                edge = KnowledgeEdgeModel(
                    id=str(uuid.uuid4()),
                    workspace_id=self.workspace_id,
                    source_id=src_id,
                    target_id=tgt_id,
                    evidence=rel.get("evidence", ""),
                    confidence=rel["confidence"],
                    weight=1.0,
                    notes=f"Relation: {rel['relation_label']}"
                )
                self.db.add(edge)
                edges_created += 1
        
        self.db.commit()
        
        return {
            "document_node_id": doc_id,
            "entity_nodes": list(entity_nodes.values()),
            "relations_created": edges_created,
            "ai_summary": ai_data["ai_short_summary"],
            "extracted_entities": entities,
            "extracted_relations": relations,
            "title": title,
        }


# ─── Singleton accessor ───
def process_document(db: Session, workspace_id: str, text: str, title: str = "Untitled",
                     source_type: str = "extracted", source_id: str = None) -> Dict[str, Any]:
    """Convenience function to process a document."""
    processor = DocumentProcessor(db, workspace_id)
    return processor.process(text, title, source_type, source_id)
