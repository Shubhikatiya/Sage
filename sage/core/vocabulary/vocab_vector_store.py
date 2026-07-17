"""
Sage Graph-Vector Store for Semantic Term Retrieval

Stores vocabulary term subgraphs as vector embeddings.
During extraction, agents query this store to find the most
semantically similar Schema.org-like terms for the content being mapped.

Adapted from the methodology's "Graph-Vector store construction" section.
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Use the existing embedding service
from services.embedding_service import get_embedding, chroma_client

# Import vocabulary
from sage.core.vocabulary.personal_vocab import CORE_VOCABULARY, VocabTerm, VocabTermType


COLLECTION_NAME = "sage_personal_vocabulary"


@dataclass
class TermMatch:
    """A matched vocabulary term with similarity score and subgraph context."""
    term_uri: str
    term_label: str
    term_type: str
    description: str
    similarity_score: float
    subgraph_text: str
    synonyms: List[str]
    examples: List[str]
    confidence_weight: float


class VocabVectorStore:
    """
    Graph-Vector store for personal vocabulary terms.
    Each term is stored as a vector embedding of its enriched subgraph.
    """
    
    def __init__(self, collection_name: str = COLLECTION_NAME):
        self.collection_name = collection_name
        self.collection = chroma_client.get_or_create_collection(name=collection_name)
        self._term_index: Dict[str, VocabTerm] = {}
        self._build_term_index()
    
    def _build_term_index(self):
        """Build an in-memory index of all vocabulary terms."""
        for term in CORE_VOCABULARY:
            self._term_index[term.uri] = term
    
    def populate(self, force_rebuild: bool = False):
        """
        Populate the vector store with all vocabulary term subgraphs.
        Call this once at system initialization.
        """
        existing = self.collection.count()
        if existing > 0 and not force_rebuild:
            print(f"[VocabVectorStore] Already populated with {existing} terms.")
            return
        
        if force_rebuild and existing > 0:
            print(f"[VocabVectorStore] Rebuilding...")
            chroma_client.delete_collection(name=self.collection_name)
            self.collection = chroma_client.get_or_create_collection(name=self.collection_name)
        
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for term in CORE_VOCABULARY:
            subgraph_text = term.to_subgraph_text()
            embedding = get_embedding(subgraph_text)
            
            ids.append(term.uri)
            documents.append(subgraph_text)
            embeddings.append(embedding)
            metadatas.append({
                "uri": term.uri,
                "label": term.label,
                "term_type": term.term_type.value,
                "description": term.description,
                "synonyms": json.dumps(term.synonyms),
                "examples": json.dumps(term.examples),
                "confidence_weight": term.confidence_weight,
            })
        
        # Batch add to ChromaDB
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:end],
                documents=documents[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end]
            )
        
        print(f"[VocabVectorStore] Populated with {len(ids)} terms.")
    
    def query(self, query_text: str, n_results: int = 5, term_type_filter: Optional[VocabTermType] = None) -> List[TermMatch]:
        """
        Find the most semantically similar vocabulary terms for a given text.
        
        Args:
            query_text: The text to match (e.g., a column name, document snippet, or chat message)
            n_results: Number of top matches to return
            term_type_filter: Optional filter to only return terms of a specific type
        
        Returns:
            List of TermMatch objects ordered by similarity
        """
        query_embedding = get_embedding(query_text)
        
        # Query the vector store
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2,  # Fetch extra to allow filtering
            include=["documents", "metadatas", "distances"]
        )
        
        matches = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, uri in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Convert distance to similarity (cosine distance -> similarity)
                similarity = 1.0 - distance
                
                # Apply type filter if specified
                if term_type_filter and metadata.get("term_type") != term_type_filter.value:
                    continue
                
                matches.append(TermMatch(
                    term_uri=uri,
                    term_label=metadata.get("label", ""),
                    term_type=metadata.get("term_type", ""),
                    description=metadata.get("description", ""),
                    similarity_score=similarity,
                    subgraph_text=results["documents"][0][i] if results["documents"] else "",
                    synonyms=json.loads(metadata.get("synonyms", "[]")),
                    examples=json.loads(metadata.get("examples", "[]")),
                    confidence_weight=metadata.get("confidence_weight", 1.0),
                ))
        
        # Sort by similarity descending and limit
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:n_results]
    
    def query_for_entities(self, query_text: str, n_results: int = 5) -> List[TermMatch]:
        """Convenience method: query only for ENTITY type terms."""
        return self.query(query_text, n_results, VocabTermType.ENTITY)
    
    def query_for_properties(self, query_text: str, n_results: int = 5) -> List[TermMatch]:
        """Convenience method: query only for PROPERTY type terms."""
        return self.query(query_text, n_results, VocabTermType.PROPERTY)
    
    def query_for_relationships(self, query_text: str, n_results: int = 5) -> List[TermMatch]:
        """Convenience method: query only for RELATIONSHIP type terms."""
        return self.query(query_text, n_results, VocabTermType.RELATIONSHIP)
    
    def get_term_details(self, uri: str) -> Optional[VocabTerm]:
        """Get full term details from the in-memory index."""
        return self._term_index.get(uri)
    
    def get_stats(self) -> Dict[str, any]:
        """Get store statistics."""
        return {
            "collection_name": self.collection_name,
            "total_terms": self.collection.count(),
            "entity_terms": len([t for t in CORE_VOCABULARY if t.term_type == VocabTermType.ENTITY]),
            "property_terms": len([t for t in CORE_VOCABULARY if t.term_type == VocabTermType.PROPERTY]),
            "action_terms": len([t for t in CORE_VOCABULARY if t.term_type == VocabTermType.ACTION]),
            "relationship_terms": len([t for t in CORE_VOCABULARY if t.term_type == VocabTermType.RELATIONSHIP]),
            "layer_terms": len([t for t in CORE_VOCABULARY if t.term_type == VocabTermType.LAYER]),
            "state_terms": len([t for t in CORE_VOCABULARY if t.term_type == VocabTermType.STATE]),
        }


# Singleton instance
_vocab_store: Optional[VocabVectorStore] = None


def get_vocab_store() -> VocabVectorStore:
    """Get or create the vocabulary vector store singleton."""
    global _vocab_store
    if _vocab_store is None:
        _vocab_store = VocabVectorStore()
    return _vocab_store


# ─── BOOTSTRAP FUNCTION ───
def initialize_vocab_store(force_rebuild: bool = False):
    """
    Initialize the vocabulary vector store at system startup.
    Call this from main_v4.py during application startup.
    """
    store = get_vocab_store()
    store.populate(force_rebuild=force_rebuild)
    stats = store.get_stats()
    print(f"[VocabVectorStore] Initialized: {stats['total_terms']} terms embedded")
    return store


if __name__ == "__main__":
    # Quick test
    store = initialize_vocab_store(force_rebuild=True)
    
    print("\n--- Query: 'my colleague Alice who manages the backend' ---")
    matches = store.query("my colleague Alice who manages the backend", n_results=3)
    for m in matches:
        print(f"  {m.term_label} ({m.term_type}) — similarity: {m.similarity_score:.3f}")
    
    print("\n--- Query for entities: 'project deadline next week' ---")
    entity_matches = store.query_for_entities("project deadline next week", n_results=3)
    for m in entity_matches:
        print(f"  {m.term_label} — similarity: {m.similarity_score:.3f}")
    
    print("\n--- Query for relationships: 'caused by' ---")
    rel_matches = store.query_for_relationships("caused by", n_results=3)
    for m in rel_matches:
        print(f"  {m.term_label} — similarity: {m.similarity_score:.3f}")
