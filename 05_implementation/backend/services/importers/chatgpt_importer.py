"""
ChatGPT Export Importer for Sage v4.
Parses ChatGPT conversation exports (JSON format) into knowledge graph nodes.
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from services.knowledge_extraction import KnowledgeExtractionEngine

class ChatGPTImporter:
    """Import ChatGPT conversation exports into Sage knowledge graph."""
    
    def __init__(self):
        self.extraction_engine = KnowledgeExtractionEngine()
    
    def parse_export(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a ChatGPT export JSON file.
        
        ChatGPT exports have structure:
        {
            "conversations": [
                {
                    "title": "...",
                    "create_time": timestamp,
                    "update_time": timestamp,
                    "mapping": {
                        "node_id": {
                            "message": {
                                "author": {"role": "user"|"assistant"},
                                "content": {"parts": ["..."]},
                                "create_time": timestamp
                            }
                        }
                    }
                }
            ]
        }
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        conversations = data.get("conversations", [])
        parsed_conversations = []
        
        for conv in conversations:
            parsed = self._parse_conversation(conv)
            if parsed:
                parsed_conversations.append(parsed)
        
        return parsed_conversations
    
    def _parse_conversation(self, conversation: Dict) -> Optional[Dict[str, Any]]:
        """Parse a single conversation."""
        title = conversation.get("title", "Untitled")
        mapping = conversation.get("mapping", {})
        
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
            
            timestamp = message_data.get("create_time")
            if timestamp:
                dt = datetime.fromtimestamp(timestamp)
            else:
                dt = None
            
            messages.append({
                "role": role,
                "text": text,
                "timestamp": dt.isoformat() if dt else None,
            })
        
        if not messages:
            return None
        
        # Combine all text for extraction
        full_text = "\n\n".join([m["text"] for m in messages if m["text"]])
        
        # Extract knowledge
        extraction = self.extraction_engine.extract_all(full_text)
        
        # Generate summary from assistant messages
        assistant_text = "\n".join([m["text"] for m in messages if m["role"] == "assistant"])
        summary = self.extraction_engine.generate_summary(assistant_text, max_length=300)
        
        return {
            "title": title,
            "message_count": len(messages),
            "messages": messages,
            "extraction": extraction,
            "summary": summary,
            "date_range": {
                "start": messages[0]["timestamp"] if messages else None,
                "end": messages[-1]["timestamp"] if messages else None,
            }
        }
    
    def generate_knowledge_suggestions(self, parsed_conversations: List[Dict]) -> List[Dict[str, Any]]:
        """Generate KnowledgeNode suggestions from parsed conversations."""
        suggestions = []
        
        for conv in parsed_conversations:
            extraction = conv["extraction"]
            
            # Create suggestions for each extracted type
            conv_suggestions = self.extraction_engine.create_knowledge_nodes_from_extraction(
                extraction, source_asset_id=f"chatgpt:{conv['title']}"
            )
            
            for suggestion in conv_suggestions:
                suggestion["source_conversation"] = conv["title"]
                suggestion["source_type"] = "chatgpt_export"
            
            suggestions.extend(conv_suggestions)
            
            # Also create a conversation node
            if conv["summary"]:
                suggestions.append({
                    "node_type": "conversation",
                    "title": conv["title"],
                    "content": conv["summary"],
                    "source_type": "chatgpt_export",
                    "source_id": f"chatgpt:{conv['title']}",
                    "confidence": 0.7,
                    "metadata": {
                        "message_count": conv["message_count"],
                        "date_range": conv["date_range"],
                    }
                })
        
        return suggestions
    
    def import_to_graph(self, file_path: str, workspace_id: str, db_session) -> Dict[str, Any]:
        """Import ChatGPT export directly into knowledge graph.
        
        Returns import summary.
        """
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
