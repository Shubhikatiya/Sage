"""
Semantic Multi-Agent Extraction System for Sage

Implements the 3-methodology approach:
1. Mapping Agent: Extracts entities and maps them to vocabulary terms
2. Relation Agent: Identifies relationships between extracted entities
3. Validator Agent: Validates mappings and relations with confidence scores

Each agent outputs structured JSON with a confidence level (HIGH, MEDIUM, LOW).
"""
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from sage.core.vocabulary.vocab_vector_store import get_vocab_store, TermMatch
from sage.core.vocabulary.personal_vocab import get_term_by_uri, VocabTermType


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ExtractedEntity:
    """An entity extracted from text with its vocabulary mapping."""
    text_span: str              # The exact text from the document
    entity_type_uri: str        # e.g., spv:Person
    entity_type_label: str      # e.g., "Person"
    canonical_name: str         # Normalized name (e.g., "Shubhi Katiyar")
    confidence: ConfidenceLevel
    vocabulary_match_score: float
    properties: Dict[str, Any] = field(default_factory=dict)  # Extracted properties
    position: Optional[int] = None  # Character position in source text


@dataclass
class ExtractedRelation:
    """A relationship between two extracted entities."""
    source_entity_text: str
    target_entity_text: str
    relation_uri: str
    relation_label: str
    evidence_text: str          # The sentence/phrase supporting this relation
    confidence: ConfidenceLevel
    vocabulary_match_score: float


@dataclass
class ValidationResult:
    """Result from the Validator Agent."""
    is_valid: bool
    issues: List[str]
    suggested_fixes: List[str]
    adjusted_confidence: ConfidenceLevel
    original_confidence: ConfidenceLevel


@dataclass
class ExtractionPipelineResult:
    """Complete output from the multi-agent extraction pipeline."""
    source_text: str
    entities: List[ExtractedEntity]
    relations: List[ExtractedRelation]
    validation_summary: Dict[str, Any]
    overall_confidence: ConfidenceLevel
    agent_logs: List[Dict[str, Any]]


# ───────────────────────────────────────────────────────────────
# AGENT 1: MAPPING AGENT
# ───────────────────────────────────────────────────────────────

class MappingAgent:
    """
    Extracts entities from text and maps them to vocabulary terms.
    Uses a hybrid approach: regex heuristics + vocabulary vector retrieval.
    """
    
    def __init__(self):
        self.vocab_store = get_vocab_store()
    
    def extract(self, text: str, context: Optional[Dict] = None) -> List[ExtractedEntity]:
        """
        Extract entities from text and map them to vocabulary terms.
        
        Process:
        1. Split text into sentences/phrases
        2. For each phrase, query the vocabulary vector store for entity matches
        3. Extract candidate spans using NER-like heuristics
        4. Score and filter by confidence threshold
        """
        entities = []
        agent_log = {"agent": "MappingAgent", "steps": []}
        
        # Step 1: Split into sentences
        sentences = self._split_sentences(text)
        agent_log["steps"].append({"action": "split_sentences", "count": len(sentences)})
        
        # Step 2: Process each sentence
        for sent in sentences:
            sent_entities = self._extract_from_sentence(sent)
            entities.extend(sent_entities)
        
        # Step 3: Deduplicate by canonical name
        entities = self._deduplicate_entities(entities)
        
        agent_log["steps"].append({"action": "final_entities", "count": len(entities)})
        self._last_log = agent_log
        
        return entities
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _extract_from_sentence(self, sentence: str) -> List[ExtractedEntity]:
        """Extract entities from a single sentence."""
        entities = []
        
        # Strategy 1: Query vocab store for entity types matching this sentence
        term_matches = self.vocab_store.query_for_entities(sentence, n_results=3)
        
        for match in term_matches:
            if match.similarity_score < 0.3:
                continue  # Too weak
            
            # Strategy 2: Find candidate text spans in the sentence
            candidates = self._find_candidate_spans(sentence, match)
            
            for candidate in candidates:
                confidence = self._score_confidence(match, candidate)
                entity = ExtractedEntity(
                    text_span=candidate["text"],
                    entity_type_uri=match.term_uri,
                    entity_type_label=match.term_label,
                    canonical_name=candidate["canonical"],
                    confidence=confidence,
                    vocabulary_match_score=match.similarity_score,
                    properties=self._extract_properties(sentence, candidate["text"], match),
                    position=candidate["position"]
                )
                entities.append(entity)
        
        return entities
    
    def _find_candidate_spans(self, sentence: str, term_match: TermMatch) -> List[Dict]:
        """
        Find text spans in the sentence that could be instances of this entity type.
        Uses simple heuristics: proper nouns, quoted phrases, role descriptors.
        """
        candidates = []
        
        # Pattern 1: Capitalized phrases (proper nouns)
        proper_noun_pattern = r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+'
        for m in re.finditer(proper_noun_pattern, sentence):
            candidates.append({
                "text": m.group(),
                "canonical": m.group(),
                "position": m.start()
            })
        
        # Pattern 2: Quoted strings
        quote_pattern = r'["\']([^"\']+)["\']'
        for m in re.finditer(quote_pattern, sentence):
            candidates.append({
                "text": m.group(1),
                "canonical": m.group(1),
                "position": m.start()
            })
        
        # Pattern 3: "my X" or "the X" patterns for roles/projects
        role_patterns = {
            "spv:Person": r'(?:my|our|the)\s+([a-z]+(?:\s+[a-z]+){0,2})',
            "spv:Project": r'(?:project|initiative|campaign)\s+(?:called|named)?\s*["\']?([^"\',.]+)',
            "spv:Organization": r'(?:company|startup|team|organization)\s+(?:called|named)?\s*["\']?([^"\',.]+)',
        }
        
        if term_match.term_uri in role_patterns:
            for m in re.finditer(role_patterns[term_match.term_uri], sentence, re.IGNORECASE):
                candidates.append({
                    "text": m.group(1).strip(),
                    "canonical": m.group(1).strip().title(),
                    "position": m.start()
                })
        
        # Pattern 4: If no candidates found, use the whole sentence as weak candidate
        if not candidates:
            candidates.append({
                "text": sentence[:50],
                "canonical": sentence[:50],
                "position": 0
            })
        
        return candidates
    
    def _score_confidence(self, match: TermMatch, candidate: Dict) -> ConfidenceLevel:
        """Score the confidence of an extraction."""
        score = match.similarity_score * match.confidence_weight
        
        # Boost for proper nouns (capitalized)
        if candidate["canonical"][0].isupper():
            score += 0.1
        
        # Boost for longer, more specific names
        if len(candidate["canonical"].split()) >= 2:
            score += 0.05
        
        if score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _extract_properties(self, sentence: str, entity_text: str, match: TermMatch) -> Dict[str, Any]:
        """Extract properties of the entity from surrounding context."""
        properties = {}
        
        # Look for role patterns: "Alice, the CEO, ..." or "Alice (CEO)"
        role_patterns = [
            rf'{re.escape(entity_text)}[\s,]*(?:the|a|an)?\s+([A-Za-z\s]+?)(?:[,;]|\s+(?:who|that|and|or|is|was))',
            rf'([A-Za-z\s]+?)\s+(?:who|that)\s+(?:is|was)\s+{re.escape(entity_text)}',
        ]
        
        for pattern in role_patterns:
            m = re.search(pattern, sentence, re.IGNORECASE)
            if m:
                role = m.group(1).strip()
                if len(role) > 2 and len(role) < 30:
                    properties["role"] = role
                    break
        
        # Look for status patterns
        status_keywords = ["active", "completed", "on hold", "planning", "blocked", "in progress"]
        for status in status_keywords:
            if status in sentence.lower():
                properties["status"] = status
                break
        
        return properties
    
    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Remove duplicate extractions of the same entity."""
        seen = {}
        unique = []
        
        for e in entities:
            key = (e.canonical_name.lower(), e.entity_type_uri)
            if key in seen:
                # Keep the higher confidence one
                if e.vocabulary_match_score > seen[key].vocabulary_match_score:
                    seen[key] = e
            else:
                seen[key] = e
        
        return list(seen.values())


# ───────────────────────────────────────────────────────────────
# AGENT 2: RELATION AGENT
# ───────────────────────────────────────────────────────────────

class RelationAgent:
    """
    Identifies relationships between extracted entities.
    Uses vocabulary relationship terms and sentence structure analysis.
    """
    
    def __init__(self):
        self.vocab_store = get_vocab_store()
    
    def extract_relations(self, text: str, entities: List[ExtractedEntity]) -> List[ExtractedRelation]:
        """
        Extract relationships between entities from the text.
        
        Process:
        1. For each pair of entities, find sentences containing both
        2. Query vocabulary for relationship terms matching the sentence
        3. Extract relationship with evidence
        """
        if len(entities) < 2:
            return []
        
        relations = []
        agent_log = {"agent": "RelationAgent", "steps": []}
        
        sentences = self._split_sentences(text)
        
        for sent in sentences:
            # Find which entities appear in this sentence
            sent_entities = [e for e in entities if e.text_span in sent or e.canonical_name in sent]
            
            if len(sent_entities) >= 2:
                # Try all pairs
                for i in range(len(sent_entities)):
                    for j in range(i + 1, len(sent_entities)):
                        e1 = sent_entities[i]
                        e2 = sent_entities[j]
                        
                        relation = self._extract_relation_between(e1, e2, sent)
                        if relation:
                            relations.append(relation)
        
        # Deduplicate
        relations = self._deduplicate_relations(relations)
        
        agent_log["steps"].append({"action": "final_relations", "count": len(relations)})
        self._last_log = agent_log
        
        return relations
    
    def _split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _extract_relation_between(self, e1: ExtractedEntity, e2: ExtractedEntity, sentence: str) -> Optional[ExtractedRelation]:
        """Extract the relationship between two entities in a sentence."""
        
        # Build a relation query from the sentence and entity types
        relation_query = f"{e1.entity_type_label} {e2.entity_type_label} {sentence}"
        
        # Query vocabulary for relationship terms
        rel_matches = self.vocab_store.query_for_relationships(relation_query, n_results=3)
        
        if not rel_matches or rel_matches[0].similarity_score < 0.3:
            # Fall back to generic "relatedTo"
            return ExtractedRelation(
                source_entity_text=e1.canonical_name,
                target_entity_text=e2.canonical_name,
                relation_uri="spv:relatedTo",
                relation_label="Related To",
                evidence_text=sentence[:200],
                confidence=ConfidenceLevel.LOW,
                vocabulary_match_score=0.3
            )
        
        best_match = rel_matches[0]
        confidence = self._score_relation_confidence(best_match, sentence)
        
        return ExtractedRelation(
            source_entity_text=e1.canonical_name,
            target_entity_text=e2.canonical_name,
            relation_uri=best_match.term_uri,
            relation_label=best_match.term_label,
            evidence_text=sentence[:200],
            confidence=confidence,
            vocabulary_match_score=best_match.similarity_score
        )
    
    def _score_relation_confidence(self, match: TermMatch, sentence: str) -> ConfidenceLevel:
        """Score the confidence of a relation extraction."""
        score = match.similarity_score
        
        # Boost for explicit relation verbs in sentence
        relation_verbs = ["is", "works on", "manages", "leads", "created", "founded", "depends on", "part of"]
        for verb in relation_verbs:
            if verb.lower() in sentence.lower():
                score += 0.1
                break
        
        if score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def _deduplicate_relations(self, relations: List[ExtractedRelation]) -> List[ExtractedRelation]:
        """Remove duplicate relations."""
        seen = {}
        unique = []
        
        for r in relations:
            key = (r.source_entity_text.lower(), r.target_entity_text.lower(), r.relation_uri)
            if key in seen:
                if r.vocabulary_match_score > seen[key].vocabulary_match_score:
                    seen[key] = r
            else:
                seen[key] = r
        
        return list(seen.values())


# ───────────────────────────────────────────────────────────────
# AGENT 3: VALIDATOR AGENT
# ───────────────────────────────────────────────────────────────

class ValidatorAgent:
    """
    Validates and corrects entity mappings and relationships.
    Checks for consistency, completeness, and confidence thresholds.
    """
    
    def validate_entities(self, entities: List[ExtractedEntity]) -> List[ValidationResult]:
        """Validate each extracted entity."""
        results = []
        
        for entity in entities:
            issues = []
            fixes = []
            
            # Check 1: Confidence threshold
            if entity.vocabulary_match_score < 0.4:
                issues.append(f"Low vocabulary match score: {entity.vocabulary_match_score:.2f}")
                fixes.append("Consider re-mapping to a broader term or flagging for manual review")
            
            # Check 2: Name quality
            if len(entity.canonical_name) < 2:
                issues.append("Entity name is too short")
                fixes.append("Expand using surrounding context")
            
            # Check 3: Properties completeness
            term = get_term_by_uri(entity.entity_type_uri)
            if term and term.properties:
                missing = [p for p in term.properties if p.split(":")[-1] not in entity.properties]
                if len(missing) > len(term.properties) / 2:
                    issues.append(f"Missing expected properties: {', '.join(missing[:3])}")
                    fixes.append("Scan text for additional property indicators")
            
            # Adjust confidence
            adjusted = entity.confidence
            if issues:
                if entity.confidence == ConfidenceLevel.HIGH:
                    adjusted = ConfidenceLevel.MEDIUM
                elif entity.confidence == ConfidenceLevel.MEDIUM:
                    adjusted = ConfidenceLevel.LOW
            
            results.append(ValidationResult(
                is_valid=len(issues) == 0,
                issues=issues,
                suggested_fixes=fixes,
                adjusted_confidence=adjusted,
                original_confidence=entity.confidence
            ))
        
        return results
    
    def validate_relations(self, relations: List[ExtractedRelation], entities: List[ExtractedEntity]) -> List[ValidationResult]:
        """Validate each extracted relation."""
        results = []
        entity_names = {e.canonical_name.lower() for e in entities}
        
        for relation in relations:
            issues = []
            fixes = []
            
            # Check 1: Entities exist
            if relation.source_entity_text.lower() not in entity_names:
                issues.append(f"Source entity not found in extracted entities: {relation.source_entity_text}")
                fixes.append("Re-extract entities or remove orphaned relation")
            
            if relation.target_entity_text.lower() not in entity_names:
                issues.append(f"Target entity not found in extracted entities: {relation.target_entity_text}")
                fixes.append("Re-extract entities or remove orphaned relation")
            
            # Check 2: Relation type validity
            term = get_term_by_uri(relation.relation_uri)
            if not term:
                issues.append(f"Unknown relation URI: {relation.relation_uri}")
                fixes.append("Map to a known vocabulary term")
            
            # Check 3: Confidence
            if relation.vocabulary_match_score < 0.3:
                issues.append(f"Very low relation match score: {relation.vocabulary_match_score:.2f}")
                fixes.append("Flag for manual review or use generic 'relatedTo'")
            
            adjusted = relation.confidence
            if issues:
                if relation.confidence == ConfidenceLevel.HIGH:
                    adjusted = ConfidenceLevel.MEDIUM
                elif relation.confidence == ConfidenceLevel.MEDIUM:
                    adjusted = ConfidenceLevel.LOW
            
            results.append(ValidationResult(
                is_valid=len(issues) == 0,
                issues=issues,
                suggested_fixes=fixes,
                adjusted_confidence=adjusted,
                original_confidence=relation.confidence
            ))
        
        return results
    
    def compute_overall_confidence(self, entity_validations: List[ValidationResult],
                                    relation_validations: List[ValidationResult]) -> ConfidenceLevel:
        """Compute the overall confidence score for the extraction."""
        all_scores = []
        
        for v in entity_validations:
            score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[v.adjusted_confidence.value]
            all_scores.append(score)
        
        for v in relation_validations:
            score = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[v.adjusted_confidence.value]
            all_scores.append(score)
        
        if not all_scores:
            return ConfidenceLevel.LOW
        
        avg = sum(all_scores) / len(all_scores)
        
        if avg >= 2.5:
            return ConfidenceLevel.HIGH
        elif avg >= 1.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


# ───────────────────────────────────────────────────────────────
# ORCHESTRATOR: Multi-Agent Pipeline
# ───────────────────────────────────────────────────────────────

class SemanticExtractionPipeline:
    """
    Orchestrates the Mapping, Relation, and Validator agents
    to produce a complete structured extraction from raw text.
    """
    
    def __init__(self):
        self.mapping_agent = MappingAgent()
        self.relation_agent = RelationAgent()
        self.validator_agent = ValidatorAgent()
    
    def process(self, text: str, context: Optional[Dict] = None) -> ExtractionPipelineResult:
        """
        Run the full multi-agent extraction pipeline.
        
        Args:
            text: The raw text to extract from (document, chat, etc.)
            context: Optional metadata (source type, author, date, etc.)
        
        Returns:
            ExtractionPipelineResult with entities, relations, and validation
        """
        agent_logs = []
        
        # Step 1: Mapping Agent — extract entities
        entities = self.mapping_agent.extract(text, context)
        agent_logs.append(getattr(self.mapping_agent, '_last_log', {"agent": "MappingAgent"}))
        
        # Step 2: Relation Agent — extract relationships
        relations = self.relation_agent.extract_relations(text, entities)
        agent_logs.append(getattr(self.relation_agent, '_last_log', {"agent": "RelationAgent"}))
        
        # Step 3: Validator Agent — validate everything
        entity_validations = self.validator_agent.validate_entities(entities)
        relation_validations = self.validator_agent.validate_relations(relations, entities)
        
        # Apply validation adjustments
        for entity, validation in zip(entities, entity_validations):
            entity.confidence = validation.adjusted_confidence
        
        for relation, validation in zip(relations, relation_validations):
            relation.confidence = validation.adjusted_confidence
        
        # Filter out invalid items with LOW confidence and issues
        valid_entities = [e for e, v in zip(entities, entity_validations) 
                         if v.is_valid or e.confidence != ConfidenceLevel.LOW]
        valid_relations = [r for r, v in zip(relations, relation_validations)
                          if v.is_valid or r.confidence != ConfidenceLevel.LOW]
        
        overall_confidence = self.validator_agent.compute_overall_confidence(
            entity_validations, relation_validations
        )
        
        validation_summary = {
            "total_entities_extracted": len(entities),
            "valid_entities": sum(1 for v in entity_validations if v.is_valid),
            "total_relations_extracted": len(relations),
            "valid_relations": sum(1 for v in relation_validations if v.is_valid),
            "entity_issues": sum(len(v.issues) for v in entity_validations),
            "relation_issues": sum(len(v.issues) for v in relation_validations),
        }
        
        return ExtractionPipelineResult(
            source_text=text[:500],
            entities=valid_entities,
            relations=valid_relations,
            validation_summary=validation_summary,
            overall_confidence=overall_confidence,
            agent_logs=agent_logs
        )
    
    def to_knowledge_nodes(self, result: ExtractionPipelineResult) -> List[Dict[str, Any]]:
        """
        Convert extraction result into KnowledgeNode-compatible dictionaries.
        These can be directly inserted into the Sage knowledge graph.
        """
        nodes = []
        
        for entity in result.entities:
            node = {
                "title": entity.canonical_name,
                "content": f"Extracted from text: {entity.text_span}\n\nType: {entity.entity_type_label}",
                "node_type_id": entity.entity_type_uri.replace("spv:", ""),  # Map to NodeType
                "source_type": "extracted",
                "confidence": 1.0 if entity.confidence == ConfidenceLevel.HIGH else 
                             0.7 if entity.confidence == ConfidenceLevel.MEDIUM else 0.4,
                "metadata": {
                    "extracted_properties": entity.properties,
                    "vocabulary_match_score": entity.vocabulary_match_score,
                }
            }
            nodes.append(node)
        
        for relation in result.relations:
            # Relations become edge records
            edge = {
                "type": "relationship",
                "source_title": relation.source_entity_text,
                "target_title": relation.target_entity_text,
                "relation_type": relation.relation_label,
                "evidence": relation.evidence_text,
                "confidence": 1.0 if relation.confidence == ConfidenceLevel.HIGH else
                             0.7 if relation.confidence == ConfidenceLevel.MEDIUM else 0.4,
            }
            nodes.append(edge)
        
        return nodes


# ─── Singleton ───
_pipeline: Optional[SemanticExtractionPipeline] = None


def get_extraction_pipeline() -> SemanticExtractionPipeline:
    """Get or create the extraction pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = SemanticExtractionPipeline()
    return _pipeline
