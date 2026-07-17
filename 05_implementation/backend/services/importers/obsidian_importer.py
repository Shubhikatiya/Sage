"""
Obsidian Vault Importer for Sage v4.
Parses Obsidian markdown files into knowledge graph nodes.
"""
import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from services.knowledge_extraction import KnowledgeExtractionEngine

class ObsidianImporter:
    """Import Obsidian vault markdown files into Sage knowledge graph."""
    
    def __init__(self):
        self.extraction_engine = KnowledgeExtractionEngine()
    
    def parse_vault(self, vault_path: str) -> List[Dict[str, Any]]:
        """Parse all markdown files in an Obsidian vault.
        
        Returns list of parsed notes.
        """
        notes = []
        vault = Path(vault_path)
        
        for md_file in vault.rglob("*.md"):
            try:
                note = self._parse_note(md_file, vault)
                if note:
                    notes.append(note)
            except Exception as e:
                print(f"Error parsing {md_file}: {e}")
        
        return notes
    
    def _parse_note(self, file_path: Path, vault_root: Path) -> Optional[Dict[str, Any]]:
        """Parse a single Obsidian markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract frontmatter
        frontmatter = {}
        body = content
        
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            try:
                frontmatter = yaml.safe_load(frontmatter_match.group(1)) or {}
                body = content[frontmatter_match.end():]
            except yaml.YAMLError:
                pass
        
        # Extract Obsidian links [[...]]
        obsidian_links = re.findall(r'\[\[(.*?)\]\]', content)
        
        # Extract tags #tag
        tags = re.findall(r'#(\w+)', content)
        
        # Extract headings
        headings = re.findall(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        
        # Determine note type from frontmatter or folder
        note_type = frontmatter.get("type", "note")
        if note_type == "note":
            # Infer from folder structure
            relative_path = file_path.relative_to(vault_root)
            folder = relative_path.parts[0] if len(relative_path.parts) > 1 else ""
            
            folder_type_map = {
                "projects": "project",
                "people": "person",
                "concepts": "concept",
                "research": "research",
                "decisions": "decision",
                "insights": "insight",
                "tasks": "task",
                "daily": "journal",
            }
            
            note_type = folder_type_map.get(folder.lower(), "note")
        
        # Extract knowledge
        extraction = self.extraction_engine.extract_all(body)
        
        return {
            "title": frontmatter.get("title", file_path.stem),
            "file_path": str(file_path),
            "relative_path": str(file_path.relative_to(vault_root)),
            "note_type": note_type,
            "frontmatter": frontmatter,
            "body": body,
            "links": obsidian_links,
            "tags": list(set(tags)),
            "headings": [h[1] for h in headings],
            "extraction": extraction,
            "word_count": len(body.split()),
            "created": frontmatter.get("created"),
            "updated": frontmatter.get("updated"),
        }
    
    def generate_knowledge_suggestions(self, notes: List[Dict]) -> List[Dict[str, Any]]:
        """Generate KnowledgeNode suggestions from parsed Obsidian notes."""
        suggestions = []
        
        for note in notes:
            # Create primary node for the note itself
            suggestions.append({
                "node_type": note["note_type"],
                "title": note["title"],
                "content": note["body"][:2000],  # Truncate for storage
                "source_type": "obsidian_import",
                "source_id": note["file_path"],
                "confidence": 0.8,
                "metadata": {
                    "original_path": note["relative_path"],
                    "word_count": note["word_count"],
                    "tags": note["tags"],
                    "links": note["links"],
                }
            })
            
            # Extract embedded knowledge
            extraction = note["extraction"]
            embedded = self.extraction_engine.create_knowledge_nodes_from_extraction(
                extraction, source_asset_id=note["file_path"]
            )
            
            for item in embedded:
                item["source_note"] = note["title"]
                item["source_type"] = "obsidian_extraction"
            
            suggestions.extend(embedded)
        
        return suggestions
    
    def import_to_graph(self, vault_path: str, workspace_id: str, db_session) -> Dict[str, Any]:
        """Import Obsidian vault directly into knowledge graph.
        
        Returns import summary.
        """
        notes = self.parse_vault(vault_path)
        suggestions = self.generate_knowledge_suggestions(notes)
        
        return {
            "notes_found": len(notes),
            "suggestions_generated": len(suggestions),
            "breakdown": {
                "decisions": len([s for s in suggestions if s["node_type"] == "decision"]),
                "insights": len([s for s in suggestions if s["node_type"] == "insight"]),
                "questions": len([s for s in suggestions if s["node_type"] == "question"]),
                "tasks": len([s for s in suggestions if s["node_type"] == "task"]),
                "concepts": len([s for s in suggestions if s["node_type"] == "concept"]),
                "notes": len([s for s in suggestions if s["node_type"] == "note"]),
            },
            "suggestions": suggestions,
            "requires_approval": True
        }
    
    def generate_relationship_suggestions(self, notes: List[Dict]) -> List[Dict[str, Any]]:
        """Generate relationship suggestions based on Obsidian links."""
        relationships = []
        
        for note in notes:
            for link in note["links"]:
                relationships.append({
                    "source_title": note["title"],
                    "target_title": link,
                    "relationship_type": "LINKS_TO",
                    "source": "obsidian_link",
                    "confidence": 0.9
                })
        
        return relationships
