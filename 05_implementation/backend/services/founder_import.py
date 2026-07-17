"""
Founder Knowledge Import Pipeline for Sage v4.
Imports knowledge from ChatGPT exports, Claude exports, and Obsidian vaults.
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.knowledge_extraction import KnowledgeExtractionEngine

class ChatGPTImporter:
    """Import knowledge from ChatGPT conversation exports (JSON format)."""
    
    def __init__(self):
        self.extraction_engine = KnowledgeExtractionEngine()
    
    def parse_export(self, file_path: str) -> Dict[str, Any]:
        """Parse a ChatGPT export JSON file.
        
        Returns dict with conversations, messages, and extracted knowledge.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return {"success": False, "error": f"Failed to parse JSON: {str(e)}", "conversations": []}
        
        # ChatGPT exports can have different structures
        # Handle both array of conversations and single conversation
        conversations = []
        
        if isinstance(data, list):
            for conv in data:
                parsed = self._parse_conversation(conv)
                if parsed:
                    conversations.append(parsed)
        elif isinstance(data, dict):
            # Single conversation or wrapper
            if "conversations" in data:
                for conv in data["conversations"]:
                    parsed = self._parse_conversation(conv)
                    if parsed:
                        conversations.append(parsed)
            else:
                parsed = self._parse_conversation(data)
                if parsed:
                    conversations.append(parsed)
        
        # Extract knowledge from all conversations
        all_knowledge = []
        for conv in conversations:
            knowledge = self._extract_from_conversation(conv)
            all_knowledge.extend(knowledge)
        
        return {
            "success": True,
            "conversations": conversations,
            "total_conversations": len(conversations),
            "total_messages": sum(len(c.get("messages", [])) for c in conversations),
            "extracted_knowledge": all_knowledge,
        }
    
    def _parse_conversation(self, data: Dict) -> Optional[Dict]:
        """Parse a single conversation from ChatGPT export."""
        try:
            # Handle different export formats
            title = data.get("title", "Untitled Conversation")
            create_time = data.get("create_time")
            update_time = data.get("update_time")
            
            messages = []
            mapping = data.get("mapping", {})
            
            if mapping:
                # Newer format with mapping
                for msg_id, msg_data in mapping.items():
                    if msg_data and msg_data.get("message"):
                        message = msg_data["message"]
                        role = message.get("author", {}).get("role", "unknown")
                        content = message.get("content", {})
                        
                        # Handle different content types
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            text = "\n".join(str(p) for p in parts if p)
                        else:
                            text = str(content)
                        
                        messages.append({
                            "role": role,
                            "text": text,
                            "timestamp": message.get("create_time")
                        })
            else:
                # Older format with messages array
                for msg in data.get("messages", []):
                    messages.append({
                        "role": msg.get("role", "unknown"),
                        "text": msg.get("content", ""),
                        "timestamp": msg.get("timestamp")
                    })
            
            return {
                "title": title,
                "create_time": create_time,
                "update_time": update_time,
                "messages": messages
            }
            
        except Exception as e:
            print(f"Error parsing conversation: {e}")
            return None
    
    def _extract_from_conversation(self, conversation: Dict) -> List[Dict]:
        """Extract knowledge from a single conversation."""
        knowledge = []
        
        # Combine all assistant messages for context
        assistant_text = "\n\n".join([
            m["text"] for m in conversation.get("messages", [])
            if m["role"] == "assistant" and m["text"]
        ])
        
        # Extract from assistant messages (summaries, research, analysis)
        if assistant_text:
            extraction = self.extraction_engine.extract_all(assistant_text)
            suggestions = self.extraction_engine.create_knowledge_nodes_from_extraction(extraction)
            
            for suggestion in suggestions:
                suggestion["source_conversation"] = conversation.get("title")
                knowledge.append(suggestion)
        
        # Extract from user messages (insights, decisions, questions)
        user_text = "\n\n".join([
            m["text"] for m in conversation.get("messages", [])
            if m["role"] == "user" and m["text"]
        ])
        
        if user_text:
            extraction = self.extraction_engine.extract_all(user_text)
            suggestions = self.extraction_engine.create_knowledge_nodes_from_extraction(extraction)
            
            for suggestion in suggestions:
                suggestion["source_conversation"] = conversation.get("title")
                knowledge.append(suggestion)
        
        return knowledge


class ClaudeImporter:
    """Import knowledge from Claude conversation exports."""
    
    def __init__(self):
        self.extraction_engine = KnowledgeExtractionEngine()
    
    def parse_export(self, file_path: str) -> Dict[str, Any]:
        """Parse a Claude export file.
        
        Claude exports can be JSON or Markdown format.
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == ".json":
            return self._parse_json_export(file_path)
        elif file_ext in [".md", ".markdown", ".txt"]:
            return self._parse_markdown_export(file_path)
        else:
            return {"success": False, "error": f"Unsupported file format: {file_ext}", "conversations": []}
    
    def _parse_json_export(self, file_path: str) -> Dict[str, Any]:
        """Parse Claude JSON export."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return {"success": False, "error": f"Failed to parse JSON: {str(e)}", "conversations": []}
        
        conversations = []
        
        # Handle different Claude export structures
        if isinstance(data, list):
            for item in data:
                parsed = self._parse_claude_conversation(item)
                if parsed:
                    conversations.append(parsed)
        elif isinstance(data, dict):
            if "conversations" in data:
                for conv in data["conversations"]:
                    parsed = self._parse_claude_conversation(conv)
                    if parsed:
                        conversations.append(parsed)
            else:
                parsed = self._parse_claude_conversation(data)
                if parsed:
                    conversations.append(parsed)
        
        all_knowledge = []
        for conv in conversations:
            knowledge = self._extract_from_conversation(conv)
            all_knowledge.extend(knowledge)
        
        return {
            "success": True,
            "conversations": conversations,
            "total_conversations": len(conversations),
            "total_messages": sum(len(c.get("messages", [])) for c in conversations),
            "extracted_knowledge": all_knowledge,
        }
    
    def _parse_markdown_export(self, file_path: str) -> Dict[str, Any]:
        """Parse Claude markdown export (conversations separated by headers)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}", "conversations": []}
        
        # Split by conversation headers (## or #)
        conversations = []
        sections = re.split(r'\n##\s+', content)
        
        for section in sections:
            if not section.strip():
                continue
            
            # Extract title (first line)
            lines = section.strip().split('\n')
            title = lines[0].strip().lstrip('#').strip() if lines else "Untitled"
            
            # Parse messages (Human: / Assistant: pattern)
            messages = []
            current_role = None
            current_text = []
            
            for line in lines[1:]:
                if line.startswith("Human:") or line.startswith("User:"):
                    if current_role and current_text:
                        messages.append({
                            "role": current_role,
                            "text": "\n".join(current_text).strip()
                        })
                    current_role = "user"
                    current_text = [line.replace("Human:", "").replace("User:", "").strip()]
                elif line.startswith("Assistant:"):
                    if current_role and current_text:
                        messages.append({
                            "role": current_role,
                            "text": "\n".join(current_text).strip()
                        })
                    current_role = "assistant"
                    current_text = [line.replace("Assistant:", "").strip()]
                elif current_role:
                    current_text.append(line)
            
            # Don't forget the last message
            if current_role and current_text:
                messages.append({
                    "role": current_role,
                    "text": "\n".join(current_text).strip()
                })
            
            conversations.append({
                "title": title,
                "messages": messages
            })
        
        all_knowledge = []
        for conv in conversations:
            knowledge = self._extract_from_conversation(conv)
            all_knowledge.extend(knowledge)
        
        return {
            "success": True,
            "conversations": conversations,
            "total_conversations": len(conversations),
            "total_messages": sum(len(c.get("messages", [])) for c in conversations),
            "extracted_knowledge": all_knowledge,
        }
    
    def _parse_claude_conversation(self, data: Dict) -> Optional[Dict]:
        """Parse a single Claude conversation."""
        try:
            title = data.get("name", data.get("title", "Untitled Conversation"))
            messages = []
            
            for msg in data.get("chat_messages", data.get("messages", [])):
                role = msg.get("sender", msg.get("role", "unknown"))
                if role == "human":
                    role = "user"
                
                text = msg.get("text", "")
                if not text and "content" in msg:
                    text = msg["content"]
                
                messages.append({
                    "role": role,
                    "text": text,
                    "timestamp": msg.get("created_at")
                })
            
            return {
                "title": title,
                "messages": messages
            }
        except Exception as e:
            print(f"Error parsing Claude conversation: {e}")
            return None
    
    def _extract_from_conversation(self, conversation: Dict) -> List[Dict]:
        """Extract knowledge from a Claude conversation."""
        # Same logic as ChatGPT importer
        knowledge = []
        
        all_text = "\n\n".join([
            m["text"] for m in conversation.get("messages", [])
            if m["text"]
        ])
        
        if all_text:
            extraction = self.extraction_engine.extract_all(all_text)
            suggestions = self.extraction_engine.create_knowledge_nodes_from_extraction(extraction)
            
            for suggestion in suggestions:
                suggestion["source_conversation"] = conversation.get("title")
                knowledge.append(suggestion)
        
        return knowledge


class ObsidianImporter:
    """Import knowledge from Obsidian vault (Markdown files)."""
    
    def __init__(self):
        self.extraction_engine = KnowledgeExtractionEngine()
    
    def parse_vault(self, vault_path: str) -> Dict[str, Any]:
        """Parse all markdown files in an Obsidian vault.
        
        Returns extracted knowledge and file structure.
        """
        vault = Path(vault_path)
        
        if not vault.exists():
            return {"success": False, "error": f"Vault not found: {vault_path}", "files": []}
        
        markdown_files = list(vault.rglob("*.md"))
        
        parsed_files = []
        all_knowledge = []
        
        for md_file in markdown_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                parsed = self._parse_markdown(content, md_file.relative_to(vault))
                parsed_files.append(parsed)
                
                # Extract knowledge
                if parsed["content"]:
                    extraction = self.extraction_engine.extract_all(parsed["content"])
                    suggestions = self.extraction_engine.create_knowledge_nodes_from_extraction(extraction)
                    
                    for suggestion in suggestions:
                        suggestion["source_file"] = str(parsed["path"])
                        all_knowledge.append(suggestion)
                
            except Exception as e:
                print(f"Error parsing {md_file}: {e}")
                parsed_files.append({
                    "path": str(md_file.relative_to(vault)),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "vault_path": vault_path,
            "total_files": len(markdown_files),
            "files": parsed_files,
            "extracted_knowledge": all_knowledge,
            "tags": self._collect_all_tags(parsed_files),
            "links": self._collect_all_links(parsed_files),
        }
    
    def _parse_markdown(self, content: str, path: Path) -> Dict[str, Any]:
        """Parse a single markdown file."""
        # Extract YAML frontmatter
        frontmatter = {}
        body = content
        
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            try:
                import yaml
                frontmatter = yaml.safe_load(frontmatter_match.group(1))
                body = content[frontmatter_match.end():]
            except ImportError:
                pass
        
        # Extract Obsidian wiki links [[...]]
        wiki_links = re.findall(r'\[\[(.*?)\]\]', body)
        
        # Extract standard markdown links [...](...)
        md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', body)
        
        # Extract tags #tag or tags in frontmatter
        tags = re.findall(r'#(\w+)', body)
        if frontmatter and "tags" in frontmatter:
            tags.extend(frontmatter["tags"] if isinstance(frontmatter["tags"], list) else [frontmatter["tags"]])
        
        # Extract headers
        headers = re.findall(r'^(#{1,6})\s+(.+)$', body, re.MULTILINE)
        
        return {
            "path": str(path),
            "title": frontmatter.get("title", path.stem),
            "frontmatter": frontmatter,
            "content": body.strip(),
            "tags": list(set(tags)),
            "wiki_links": wiki_links,
            "markdown_links": [link[0] for link in md_links],
            "headers": [h[1] for h in headers],
        }
    
    def _collect_all_tags(self, parsed_files: List[Dict]) -> Dict[str, int]:
        """Collect all tags across files with frequency."""
        tag_counts = {}
        for f in parsed_files:
            for tag in f.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return tag_counts
    
    def _collect_all_links(self, parsed_files: List[Dict]) -> Dict[str, List[str]]:
        """Collect all internal links."""
        links = {}
        for f in parsed_files:
            for link in f.get("wiki_links", []):
                if link not in links:
                    links[link] = []
                links[link].append(f["path"])
        return links


class FounderKnowledgeImportPipeline:
    """Orchestrates importing founder knowledge from various sources."""
    
    def __init__(self):
        self.chatgpt_importer = ChatGPTImporter()
        self.claude_importer = ClaudeImporter()
        self.obsidian_importer = ObsidianImporter()
    
    def import_chatgpt(self, file_path: str) -> Dict[str, Any]:
        """Import ChatGPT export."""
        return self.chatgpt_importer.parse_export(file_path)
    
    def import_claude(self, file_path: str) -> Dict[str, Any]:
        """Import Claude export."""
        return self.claude_importer.parse_export(file_path)
    
    def import_obsidian(self, vault_path: str) -> Dict[str, Any]:
        """Import Obsidian vault."""
        return self.obsidian_importer.parse_vault(vault_path)
    
    def import_file(self, file_path: str, source_type: str = None) -> Dict[str, Any]:
        """Auto-detect and import from a file.
        
        Args:
            file_path: Path to file
            source_type: Optional explicit type ('chatgpt', 'claude', 'obsidian', 'markdown')
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Auto-detect if not specified
        if not source_type:
            if path.suffix == ".json":
                # Try to detect by content
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Check for ChatGPT-specific fields
                    if isinstance(data, dict) and "mapping" in data:
                        source_type = "chatgpt"
                    elif isinstance(data, list) and len(data) > 0 and "mapping" in data[0]:
                        source_type = "chatgpt"
                    else:
                        source_type = "claude"
                except:
                    source_type = "claude"
            elif path.suffix in [".md", ".markdown"]:
                source_type = "markdown"
            else:
                return {"success": False, "error": f"Cannot auto-detect type for {path.suffix}"}
        
        # Route to appropriate importer
        if source_type == "chatgpt":
            return self.import_chatgpt(file_path)
        elif source_type == "claude":
            return self.import_claude(file_path)
        elif source_type in ["obsidian", "vault"]:
            return self.import_obsidian(file_path)
        elif source_type == "markdown":
            return self.obsidian_importer.parse_vault(str(path.parent))
        else:
            return {"success": False, "error": f"Unknown source type: {source_type}"}
    
    def import_directory(self, dir_path: str, recursive: bool = True) -> Dict[str, Any]:
        """Import all supported files from a directory."""
        directory = Path(dir_path)
        
        if not directory.exists():
            return {"success": False, "error": f"Directory not found: {dir_path}"}
        
        results = {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "imports": []
        }
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix in [".json", ".md", ".markdown", ".txt"]:
                results["total_files"] += 1
                
                import_result = self.import_file(str(file_path))
                
                if import_result.get("success"):
                    results["successful"] += 1
                else:
                    results["failed"] += 1
                
                results["imports"].append({
                    "file": str(file_path),
                    "success": import_result.get("success", False),
                    "knowledge_count": len(import_result.get("extracted_knowledge", []))
                })
        
        return results


class FounderKnowledgeImporter:
    """Unified interface for importing founder knowledge from all sources."""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self.importers = {
            "chatgpt": ChatGPTImporter(),
            "claude": ClaudeImporter(),
            "obsidian": ObsidianImporter(),
        }
    
    def detect_source(self, file_path: str) -> str:
        """Auto-detect the source type from file content."""
        path = Path(file_path)
        
        # Check file extension
        if path.suffix.lower() == ".json":
            # Could be ChatGPT or Claude
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Try to parse and detect
            try:
                data = json.loads(content)
                if "conversations" in data:
                    return "chatgpt"
                elif "chats" in data or "messages" in data:
                    return "claude"
            except:
                pass
            
            return "unknown"
        
        elif path.suffix.lower() == ".md":
            # Single markdown file
            return "markdown"
        
        elif path.is_dir():
            # Check if it's an Obsidian vault
            if any(path.glob("*.md")):
                return "obsidian"
        
        return "unknown"
    
    def import_file(self, file_path: str, source_type: str = None) -> Dict[str, Any]:
        """Import knowledge from a file or directory.
        
        Args:
            file_path: Path to file or directory
            source_type: Optional source type override (chatgpt, claude, obsidian, markdown)
        
        Returns:
            Import results with extracted knowledge
        """
        if not source_type:
            source_type = self.detect_source(file_path)
        
        if source_type == "chatgpt":
            importer = self.importers["chatgpt"]
            return importer.parse_export(file_path)
        elif source_type == "claude":
            importer = self.importers["claude"]
            return importer.parse_export(file_path)
        elif source_type == "obsidian":
            importer = self.importers["obsidian"]
            return {"success": True, "notes": importer.parse_vault(file_path)}
        elif source_type == "markdown":
            # Parse single markdown file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            extraction_engine = KnowledgeExtractionEngine()
            extraction = extraction_engine.extract_all(content)
            
            return {
                "success": True,
                "source": "markdown",
                "extraction": extraction,
                "suggestions": extraction_engine.create_knowledge_nodes_from_extraction(extraction, file_path)
            }
        else:
            return {
                "success": False,
                "error": f"Unknown source type: {source_type}"
            }
    
    def import_multiple(self, paths: List[str]) -> List[Dict[str, Any]]:
        """Import multiple files/directories."""
        results = []
        for path in paths:
            results.append(self.import_file(path))
        return results

