"""
Knowledge Extraction Engine v2 for Sage v4.
Extracts structured knowledge from text while preserving the full document.
Creates a primary document node with linked child insight nodes.
"""
import re
import json
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

# Broader patterns that catch more content
DECISION_PATTERNS = [
    r"(?i)(?:decided?|chose|opted|will use|going with)\s+(?:to\s+)?(.{10,500})",
    r"(?i)(?:we|i)\s+(?:decided?|chose)\s+(?:to\s+)?(.{10,500})",
    r"(?i)(?:decision\s*:\s*)(.{5,500})",
    r"(?i)(?:concluded?|resolved|settled on)\s+(?:that\s+)?(.{10,500})",
    r"(?i)(?:agreed?|committed to|settled on)\s+(?:to\s+)?(.{10,500})",
]

INSIGHT_PATTERNS = [
    r"(?i)(?:realized?|discovered?|found that|learned that)\s+(.{10,800})",
    r"(?i)(?:the key insight is|what i realized|important finding)\s*:?\s*(.{10,800})",
    r"(?i)(?:it became clear|i now understand|the pattern is)\s+(.{10,800})",
    r"(?i)(?:understood?|recognized?|acknowledged?)\s+(?:that\s+)?(.{10,800})",
    r"(?i)(?:notable|significant|important)\s*:?\s*(.{10,800})",
    r"^\s*[-*]\s*(.{20,500})$",  # Bullet points as potential insights
]

QUESTION_PATTERNS = [
    r"(?i)(?:should we|what if|how might|could we|would it|is it possible)\s+(.{5,500}\?)",
    r"(?i)(?:question\s*:\s*|open question\s*:\s*|research question\s*:\s*)(.{5,500})",
    r"(?i)(?:i wonder|unclear|not sure|don't know)\s+(?:if|whether|how|what|why)\s+(.{5,500})",
    r"(?i)(?:what about|how about|have you considered)\s+(.{5,500}\?)",
]

TASK_PATTERNS = [
    r"(?i)(?:need to|must|should|have to|todo|action item)\s+(.{10,500})",
    r"(?i)(?:next step|follow up|follow-up|to do)\s*:?\s*(.{10,500})",
    r"(?i)(?:task\s*:\s*|action\s*:\s*)(.{10,500})",
    r"(?i)^\s*(?:\d+\.\s+|[-*]\s+)(?:need to|must|should|have to|will|plan to)\s+(.{10,500})",  # Numbered/bullet tasks
    r"(?i)(?:implement|build|create|design|develop|deploy|test|review|write|document)\s+(.{10,500})",
]

CONCEPT_PATTERNS = [
    r"(?i)(?:concept|framework|model|theory|principle|methodology)\s*:?\s*(.{5,300})",
    r"(?i)(?:refers to|defined as|means)\s+(.{10,500})",
    r"(?i)(?:architecture|system|platform|approach|strategy|paradigm)\s*:?\s*(.{5,300})",
    r"^\s*#{1,3}\s+(.+)$",  # Markdown headers as concepts
    r"(?i)(?:called|named|known as)\s+['\"](.+?)['\"]",  # Quoted names
]

# Keywords that indicate entity types
PERSON_KEYWORDS = ["founder", "ceo", "director", "lead", "manager", "researcher", "author"]
ORGANIZATION_KEYWORDS = ["foundation", "company", "organization", "institute", "university", "inc", "ltd"]
PROJECT_KEYWORDS = ["project", "initiative", "program", "product", "system", "platform"]


class KnowledgeExtractionEngine:
    """Extracts structured knowledge from text while preserving the full document."""
    
    def __init__(self):
        self.patterns = {
            "decisions": DECISION_PATTERNS,
            "insights": INSIGHT_PATTERNS,
            "questions": QUESTION_PATTERNS,
            "tasks": TASK_PATTERNS,
            "concepts": CONCEPT_PATTERNS,
        }
    
    def _extract_with_llm(self, text: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Phase 03: LLM-based knowledge extraction.
        Returns structured extractions or None if LLM unavailable.
        """
        try:
            import asyncio
            from llm_router.router import generate_completion, ProviderType
            
            # Truncate text for LLM context
            max_chars = 8000
            truncated = text[:max_chars]
            
            prompt = f"""Analyze the following document and extract structured knowledge.
Return ONLY a valid JSON object with this exact structure:
{{
    "title": "Brief document title",
    "summary": "2-3 sentence summary",
    "key_themes": ["theme1", "theme2", "theme3"],
    "extractions": {{
        "decisions": [
            {{
                "text": "The decision made",
                "context": "Why this decision was made",
                "confidence": 0.9
            }}
        ],
        "insights": [
            {{
                "text": "The insight discovered",
                "context": "What led to this insight",
                "confidence": 0.85
            }}
        ],
        "questions": [
            {{
                "text": "The open question",
                "priority": "high|medium|low"
            }}
        ],
        "tasks": [
            {{
                "text": "Action item description",
                "priority": "high|medium|low",
                "status": "todo|in_progress|done"
            }}
        ],
        "concepts": [
            {{
                "name": "Concept name",
                "definition": "Brief definition",
                "related": ["related concept 1", "related concept 2"]
            }}
        ],
        "entities": [
            {{
                "name": "Entity name",
                "type": "person|organization|project|technology|location|other",
                "mentions": 3,
                "context": "How this entity is referenced"
            }}
        ]
    }}
}}

If a category has no items, return an empty array [].
Be precise and concise. Extract only clearly stated items.

Document:
---
{truncated}
---

JSON output:"""

            # Run async LLM call in sync context
            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    generate_completion(
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=2000,
                        temperature=0.1,
                        provider_hint=ProviderType.ANTHROPIC  # Prefer Anthropic for structured output
                    )
                )
            finally:
                loop.close()
            
            if response.error or not response.text:
                return None
            
            # Parse JSON from response
            llm_output = response.text.strip()
            
            # Extract JSON if wrapped in markdown
            if "```json" in llm_output:
                llm_output = llm_output.split("```json")[1].split("```")[0].strip()
            elif "```" in llm_output:
                llm_output = llm_output.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(llm_output)
            
            # Transform to match existing format
            result = {
                "document": {
                    "title": parsed.get("title", "Untitled Document"),
                    "content": text,
                    "word_count": len(text.split()),
                    "metadata": metadata or {}
                },
                "extractions": {
                    "decisions": [d["text"] for d in parsed["extractions"].get("decisions", [])],
                    "insights": [i["text"] for i in parsed["extractions"].get("insights", [])],
                    "questions": [q["text"] for q in parsed["extractions"].get("questions", [])],
                    "tasks": [t["text"] for t in parsed["extractions"].get("tasks", [])],
                    "concepts": [c["name"] for c in parsed["extractions"].get("concepts", [])],
                    "entities": [
                        {
                            "name": e["name"],
                            "type": e.get("type", "other"),
                            "mentions": e.get("mentions", 1),
                            "context": e.get("context", ""),
                            "confidence": e.get("confidence", 0.7)
                        }
                        for e in parsed["extractions"].get("entities", [])
                    ]
                },
                "summary": parsed.get("summary", ""),
                "key_themes": parsed.get("key_themes", []),
                "stats": {
                    "total_words": len(text.split()),
                    "decisions": len(parsed["extractions"].get("decisions", [])),
                    "insights": len(parsed["extractions"].get("insights", [])),
                    "questions": len(parsed["extractions"].get("questions", [])),
                    "tasks": len(parsed["extractions"].get("tasks", [])),
                    "concepts": len(parsed["extractions"].get("concepts", [])),
                    "entities": len(parsed["extractions"].get("entities", [])),
                    "extraction_method": "llm"
                }
            }
            
            print(f"[KnowledgeExtraction] LLM extraction: {result['stats']}")
            return result
            
        except Exception as e:
            print(f"[KnowledgeExtraction] LLM extraction failed, will fallback to regex: {e}")
            return None

    def extract_document(self, text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Full document extraction pipeline.
        Phase 03: Uses LLM first, falls back to regex patterns.
        
        Returns:
            {
                "document": {...},
                "extractions": {...},
                "summary": "...",
                "key_themes": [...],
                "stats": {...}
            }
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Phase 03: Try LLM-based extraction first
        llm_result = self._extract_with_llm(text, metadata)
        if llm_result:
            return llm_result
        
        # Fallback: regex-based extraction
        clean_text = self._clean_text(text)
        
        # Extract all knowledge types
        extractions = self.extract_all(clean_text)
        
        # Generate summary from full text
        summary = self.generate_summary(clean_text, max_length=1000)
        
        # Extract key themes (top entities + concepts)
        key_themes = self._extract_themes(extractions)
        
        # Calculate stats
        stats = {
            "total_chars": len(clean_text),
            "total_words": len(clean_text.split()),
            "extracted_items": sum(len(v) for v in extractions.values()),
            "decisions": len(extractions["decisions"]),
            "insights": len(extractions["insights"]),
            "questions": len(extractions["questions"]),
            "tasks": len(extractions["tasks"]),
            "concepts": len(extractions["concepts"]),
            "entities": len(extractions["entities"]),
        }
        
        # Generate document title from first heading or first sentence
        title = self._generate_document_title(clean_text, metadata)
        
        return {
            "document": {
                "title": title,
                "content": clean_text,  # FULL TEXT PRESERVED
                "word_count": stats["total_words"],
                "metadata": metadata or {},
            },
            "extractions": extractions,
            "summary": summary,
            "key_themes": key_themes,
            "stats": stats,
        }
    
    def extract_all(self, text: str) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all knowledge types from text."""
        if not text or not text.strip():
            return {
                "decisions": [],
                "insights": [],
                "questions": [],
                "tasks": [],
                "concepts": [],
                "entities": [],
            }
        
        return {
            "decisions": self.extract_decisions(text),
            "insights": self.extract_insights(text),
            "questions": self.extract_questions(text),
            "tasks": self.extract_tasks(text),
            "concepts": self.extract_concepts(text),
            "entities": self.extract_entities(text),
        }
    
    def extract_decisions(self, text: str) -> List[Dict[str, Any]]:
        """Extract decisions from text."""
        decisions = []
        for pattern in DECISION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                decision_text = match.group(1).strip()
                if len(decision_text) > 20:
                    decisions.append({
                        "type": "decision",
                        "text": decision_text,
                        "confidence": self._calculate_confidence(decision_text, "decision"),
                        "context": self._get_context(text, match.start(), match.end()),
                    })
        return self._deduplicate(decisions)
    
    def extract_insights(self, text: str) -> List[Dict[str, Any]]:
        """Extract insights from text."""
        insights = []
        for pattern in INSIGHT_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                insight_text = match.group(1).strip()
                if len(insight_text) > 15:
                    insights.append({
                        "type": "insight",
                        "text": insight_text,
                        "confidence": self._calculate_confidence(insight_text, "insight"),
                        "context": self._get_context(text, match.start(), match.end()),
                    })
        return self._deduplicate(insights)
    
    def extract_questions(self, text: str) -> List[Dict[str, Any]]:
        """Extract questions from text."""
        questions = []
        for pattern in QUESTION_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                question_text = match.group(1).strip()
                if len(question_text) > 10:
                    questions.append({
                        "type": "question",
                        "text": question_text,
                        "confidence": self._calculate_confidence(question_text, "question"),
                        "context": self._get_context(text, match.start(), match.end()),
                    })
        return self._deduplicate(questions)
    
    def extract_tasks(self, text: str) -> List[Dict[str, Any]]:
        """Extract tasks/action items from text."""
        tasks = []
        for pattern in TASK_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                task_text = match.group(1).strip()
                if len(task_text) > 10:
                    tasks.append({
                        "type": "task",
                        "text": task_text,
                        "confidence": self._calculate_confidence(task_text, "task"),
                        "context": self._get_context(text, match.start(), match.end()),
                    })
        return self._deduplicate(tasks)
    
    def extract_concepts(self, text: str) -> List[Dict[str, Any]]:
        """Extract concepts/frameworks from text."""
        concepts = []
        for pattern in CONCEPT_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                concept_text = match.group(1).strip()
                if len(concept_text) > 5:
                    concepts.append({
                        "type": "concept",
                        "text": concept_text,
                        "confidence": self._calculate_confidence(concept_text, "concept"),
                        "context": self._get_context(text, match.start(), match.end()),
                    })
        return self._deduplicate(concepts)
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        entities = []
        proper_noun_pattern = r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"
        matches = re.finditer(proper_noun_pattern, text)
        
        for match in matches:
            entity_text = match.group(0)
            entity_type = self._classify_entity(entity_text, text)
            entities.append({
                "type": entity_type,
                "text": entity_text,
                "confidence": 0.6,
            })
        return self._deduplicate(entities)
    
    def create_knowledge_nodes(self, extraction_result: Dict[str, Any], 
                              source_asset_id: str = None) -> Dict[str, Any]:
        """
        Create KnowledgeNode suggestions from extraction result.
        
        Creates:
        - 1 PRIMARY document node with FULL text
        - N child nodes for each extracted insight/decision/question/task/concept
        
        Returns:
            {
                "primary_node": {...},  # The document itself
                "child_nodes": [...],   # Extracted insights
                "relationships": [...]  # Links between them
            }
        """
        doc = extraction_result["document"]
        extractions = extraction_result["extractions"]
        
        # Create primary document node
        primary_node = {
            "node_type": "document",
            "title": doc["title"],
            "content": doc["content"],  # FULL TEXT
            "source_type": "asset_extraction",
            "source_id": source_asset_id,
            "confidence": 1.0,
            "metadata": {
                "word_count": doc["word_count"],
                "extracted_items": extraction_result["stats"]["extracted_items"],
                "key_themes": extraction_result["key_themes"],
            }
        }
        
        # Create child nodes for each extraction
        child_nodes = []
        type_mapping = {
            "decisions": "decision",
            "insights": "insight",
            "questions": "question",
            "tasks": "task",
            "concepts": "concept",
            "entities": "entity",
        }
        
        for extract_type, items in extractions.items():
            node_type = type_mapping.get(extract_type, "concept")
            for item in items:
                child_nodes.append({
                    "node_type": node_type,
                    "title": self._generate_title(item["text"]),
                    "content": item["text"],
                    "source_type": "asset_extraction",
                    "source_id": source_asset_id,
                    "confidence": item["confidence"],
                    "context": item.get("context", ""),
                    "parent_document_title": doc["title"],
                })
        
        # Fallback: if very few items extracted, create nodes from top paragraphs
        if len(child_nodes) < 5:
            paragraphs = [p.strip() for p in doc["content"].split("\n\n") if len(p.strip()) > 50]
            # Take first few meaningful paragraphs as context nodes
            for i, para in enumerate(paragraphs[:5]):
                if i >= 2:  # Skip first 2 paragraphs (usually header/contact info)
                    child_nodes.append({
                        "node_type": "context",
                        "title": self._generate_title(para),
                        "content": para[:500],
                        "source_type": "asset_extraction",
                        "source_id": source_asset_id,
                        "confidence": 0.5,
                        "context": para[:200],
                        "parent_document_title": doc["title"],
                    })
        
        # Create relationship suggestions between document and children
        relationships = []
        for child in child_nodes:
            relationships.append({
                "source_title": doc["title"],
                "target_title": child["title"],
                "relationship_type": "CONTAINS",
                "confidence": child["confidence"],
            })
        
        return {
            "primary_node": primary_node,
            "child_nodes": child_nodes,
            "relationships": relationships,
            "stats": extraction_result["stats"],
        }
    
    def suggest_relationships(self, extracted_entities: List[Dict], 
                             existing_nodes: List[Dict]) -> List[Dict[str, Any]]:
        """Suggest relationships between extracted entities and existing graph nodes."""
        suggestions = []
        
        for entity in extracted_entities:
            entity_text = entity["text"]
            
            for node in existing_nodes:
                node_title = node.get("title", "")
                
                # Exact match
                if entity_text.lower() == node_title.lower():
                    suggestions.append({
                        "entity": entity_text,
                        "node_id": node["id"],
                        "node_title": node_title,
                        "relationship_type": "MENTIONS",
                        "confidence": 1.0,
                        "match_type": "exact"
                    })
                    continue
                
                # Fuzzy match
                similarity = SequenceMatcher(None, entity_text.lower(), node_title.lower()).ratio()
                if similarity > 0.7:
                    suggestions.append({
                        "entity": entity_text,
                        "node_id": node["id"],
                        "node_title": node_title,
                        "relationship_type": "MENTIONS",
                        "confidence": similarity,
                        "match_type": "fuzzy"
                    })
                elif entity_text.lower() in node_title.lower() or node_title.lower() in entity_text.lower():
                    suggestions.append({
                        "entity": entity_text,
                        "node_id": node["id"],
                        "node_title": node_title,
                        "relationship_type": "MENTIONS",
                        "confidence": 0.5,
                        "match_type": "substring"
                    })
        
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions
    
    def generate_summary(self, text: str, max_length: int = 1000) -> str:
        """Generate a summary of the text."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if not sentences:
            return ""
        
        summary_sentences = [sentences[0]]
        
        for sentence in sentences[1:]:
            if len(" ".join(summary_sentences)) + len(sentence) > max_length:
                break
            if any(pattern in sentence.lower() for pattern in [
                "decision", "insight", "realized", "discovered", 
                "concluded", "important", "key", "significant", "conclusion"
            ]):
                summary_sentences.append(sentence)
        
        # Always include last sentence if it's a conclusion
        if len(sentences) > 1 and any(word in sentences[-1].lower() for word in ["conclusion", "summary", "overall", "in conclusion"]):
            if sentences[-1] not in summary_sentences:
                summary_sentences.append(sentences[-1])
        
        return " ".join(summary_sentences)
    
    def parse_chatgpt_export(self, json_data: Dict) -> List[Dict[str, Any]]:
        """Parse ChatGPT conversation export into document extractions."""
        documents = []
        conversations = json_data.get("conversations", [])
        
        for conv in conversations:
            title = conv.get("title", "Untitled Conversation")
            mapping = conv.get("mapping", {})
            
            # Extract messages
            messages = []
            for node_id, node_data in mapping.items():
                message_data = node_data.get("message")
                if not message_data:
                    continue
                
                author = message_data.get("author", {})
                role = author.get("role", "unknown")
                content = message_data.get("content", {})
                parts = content.get("parts", [])
                text = "\n".join(parts) if parts else ""
                
                if text:
                    messages.append({"role": role, "text": text})
            
            if not messages:
                continue
            
            # Build full conversation text
            full_text = "\n\n".join([
                f"**{m['role'].upper()}**: {m['text']}" for m in messages if m["text"]
            ])
            
            # Extract knowledge from this conversation
            extraction = self.extract_document(full_text, metadata={
                "source": "chatgpt_export",
                "conversation_title": title,
                "message_count": len(messages),
            })
            
            documents.append(extraction)
        
        return documents
    
    def parse_claude_export(self, json_data: Dict) -> List[Dict[str, Any]]:
        """Parse Claude conversation export into document extractions."""
        documents = []
        
        # Handle different Claude export formats
        if "conversations" in json_data:
            conversations = json_data["conversations"]
        elif "chats" in json_data:
            conversations = json_data["chats"]
        else:
            conversations = [json_data]
        
        for conv in conversations:
            title = conv.get("name", conv.get("title", "Untitled Claude Conversation"))
            
            # Extract messages
            messages = []
            raw_messages = conv.get("chat_messages", conv.get("messages", []))
            
            for msg in raw_messages:
                role = msg.get("sender", msg.get("role", "unknown"))
                text = msg.get("text", "")
                if text:
                    messages.append({"role": role, "text": text})
            
            if not messages:
                continue
            
            full_text = "\n\n".join([
                f"**{m['role'].upper()}**: {m['text']}" for m in messages
            ])
            
            extraction = self.extract_document(full_text, metadata={
                "source": "claude_export",
                "conversation_title": title,
                "message_count": len(messages),
            })
            
            documents.append(extraction)
        
        return documents
    
    # ── Private Helpers ──
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()
    
    def _generate_document_title(self, text: str, metadata: Dict = None) -> str:
        """Generate a title from document text or metadata."""
        # Try metadata first
        if metadata:
            for key in ["conversation_title", "title", "filename"]:
                if key in metadata and metadata[key]:
                    return metadata[key]
        
        # Try first markdown heading
        heading_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()
        
        # Use first sentence
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if sentences:
            first = sentences[0].strip()
            if len(first) > 10 and len(first) < 100:
                return first
        
        return "Untitled Document"
    
    def _extract_themes(self, extractions: Dict[str, List]) -> List[str]:
        """Extract key themes from extractions."""
        themes = []
        
        # Top entities
        entities = extractions.get("entities", [])
        for entity in entities[:10]:
            if entity["confidence"] > 0.5:
                themes.append(entity["text"])
        
        # Top concepts
        concepts = extractions.get("concepts", [])
        for concept in concepts[:5]:
            themes.append(concept["text"])
        
        return list(set(themes))[:15]  # Deduplicate and limit
    
    def _generate_title(self, text: str, max_length: int = 80) -> str:
        """Generate a title from extracted text."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        title = sentences[0] if sentences else text
        
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0] + "..."
        
        return title
    
    def _calculate_confidence(self, text: str, extraction_type: str) -> float:
        """Calculate confidence score for an extraction."""
        confidence = 0.5
        
        if len(text) > 50:
            confidence += 0.1
        if len(text) > 100:
            confidence += 0.1
        if text[0].isupper() and text.endswith((".", "!", "?")):
            confidence += 0.1
        if text.endswith((",", "and", "or", "but")):
            confidence -= 0.1
        
        return min(confidence, 1.0)
    
    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Get surrounding context for an extraction."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def _deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicate extractions based on text similarity."""
        unique_items = []
        
        for item in items:
            is_duplicate = False
            for existing in unique_items:
                similarity = SequenceMatcher(None, item["text"].lower(), existing["text"].lower()).ratio()
                if similarity > 0.8:
                    is_duplicate = True
                    if item["confidence"] > existing["confidence"]:
                        existing["text"] = item["text"]
                        existing["confidence"] = item["confidence"]
                    break
            
            if not is_duplicate:
                unique_items.append(item)
        
        return unique_items
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty extraction result."""
        return {
            "document": {
                "title": "Empty Document",
                "content": "",
                "word_count": 0,
                "metadata": {},
            },
            "extractions": {
                "decisions": [],
                "insights": [],
                "questions": [],
                "tasks": [],
                "concepts": [],
                "entities": [],
            },
            "summary": "",
            "key_themes": [],
            "stats": {
                "total_chars": 0,
                "total_words": 0,
                "extracted_items": 0,
            },
        }
    
    def _classify_entity(self, entity_text: str, context: str) -> str:
        """Classify entity type based on keywords in context."""
        context_lower = context.lower()
        entity_lower = entity_text.lower()
        
        for keyword in PERSON_KEYWORDS:
            if keyword in context_lower:
                return "person"
        
        for keyword in ORGANIZATION_KEYWORDS:
            if keyword in entity_lower:
                return "organization"
        
        for keyword in PROJECT_KEYWORDS:
            if keyword in context_lower:
                return "project"
        
        return "unknown"
