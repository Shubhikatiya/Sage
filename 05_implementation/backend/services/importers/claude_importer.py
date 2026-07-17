"""
Claude Export Importer for Sage v4.
Parses Claude conversation exports (JSON format) into knowledge graph nodes.
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from services.knowledge_extraction import KnowledgeExtractionEngine

class ClaudeImporter:
    """Import Claude conversation exports into Sage knowledge graph."""
    
    def __init__(self):
        self.extraction_engine = KnowledgeExtractionEngine()
    
    def parse_export(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a Claude export JSON file.
        
        Claude exports typically have structure:
        {
            "conversations": [
                {
                    "name": "...",
                    "created_at": "ISO timestamp",
                    "messages": [
                        {
                            "role": "human" | "assistant",
                            "content": "...",
                            "timestamp": "ISO timestamp"
                        }
                    ]
                }
            ]
        }
        Or:
        [
            {
                "uuid": "...",
                "name": "...",
                "chat_messages": [...]
            }
        ]
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        conversations = []
        
        # Handle different export formats
        if isinstance(data, dict) and "conversations" in data:
            conversations = data["conversations"]
        elif isinstance(data, list):
            conversations = data
        else:
            # Single conversation
            conversations = [data]
        
        parsed = []
        for conv in conversations:
            parsed_conv = self._parse_conversation(conv)
            if parsed_conv:
                parsed.append(parsed_conv)
        
        return parsed
    
    def _parse_conversation(self, conversation: Dict) -> Optional[Dict[str, Any]]:
        """Parse a single Claude conversation."""
        # Handle different field names
        title = conversation.get("name") or conversation.get("title") or "Untitled"
        
        # Get messages - try different field names
        messages = []
        if "chat_messages" in conversation:
            raw_messages = conversation["chat_messages"]
        elif "messages" in conversation:
            raw_messages = conversation["messages"]
        else:
            raw_messages = []
        
        parsed_messages = []
        for msg in raw_messages:
            role = msg.get("role", "unknown")
            # Map Claude roles to standard roles
            if role in ["human", "user"]:
                role = "user"
            elif role in ["assistant", "ai"]:
                role = "assistant"
            
            content = msg.get("content") or msg.get("text", "")
            timestamp = msg.get("timestamp") or msg.get("created_at")
            
            parsed_messages.append({
                "role": role,
                "text": content,
                "timestamp": timestamp,
            })
        
        if not parsed_messages:
            return None
        
        # Combine text for extraction
        full_text = "\n\n".join([m["text"] for m in parsed_messages if m["text"]])
        extraction = self.extraction_engine.extract_all(full_text)
        
        # Summary from assistant messages
        assistant_text = "\n".join([m["text"] for m in parsed_messages if m["role"] == "assistant"])
        summary = self.extraction_engine.generate_summary(assistant_text, max_length=300)
        
        return {
            "title": title,
            "message_count": len(parsed_messages),
            "messages": parsed_messages,
            "extraction": extraction,
            "summary": summary,
        }
    
    def generate_knowledge_suggestions(self, parsed_conversations: List[Dict]) -> List[Dict[str, Any]]:
        """Generate KnowledgeNode suggestions from Claude conversations."""
        suggestions = []
        
        for conv in parsed_conversations:
            extraction = conv["extraction"]
            
            conv_suggestions = self.extraction_engine.create_knowledge_nodes_from_extraction(
                extraction, source_asset_id=f"claude:{conv['title']}"
            )
            
            for suggestion in conv_suggestions:
                suggestion["source_conversation"] = conv["title"]
                suggestion["source_type"] = "claude_export"
            
            suggestions.extend(conv_suggestions)
            
            # Create conversation node
            if conv["summary"]:
                suggestions.append({
                    "node_type": "conversation",
                    "title": conv["title"],
                    "content": conv["summary"],
                    "source_type": "claude_export",
                    "source_id": f"claude:{conv['title']}",
                    "confidence": 0.7,
                    "metadata": {
                        "message_count": conv["message_count"],
                    }
                })
        
        return suggestions
    
    def import_to_graph(self, file_path: str, workspace_id: str, db_session) -> Dict[str, Any]:
        """Import Claude export directly into knowledge graph."""
        conversations = self.parse_export(file_path)
        suggestions = self.generate_knowledge_suggestions(conversations)
        
        return {
            "conversations_found": len(conversations),
            "suggestions_generated": len(suggestions),
            "breakdown": {
                "decisions": len([s for s in suggestions if s["node_type"] == "decision"]),
                "insights": len([s for s in suggestions if s["node_type"] == "insight"]),
                "questions": len([s for s in suggestions if s["node_type"] == "question"]),
                "tasks": len([s for s in suggestions if s["node_type"] == "task"]),
                "concepts": len([s for s in suggestions if s["node_type"] == "concept"]),
            },
            "suggestions": suggestions,
            "requires_approval": True
        }
