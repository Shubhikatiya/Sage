"""
Graph Traversal Engine + Subgraph Summarizer

When a node is matched in the knowledge graph, traverse 1-2 hops outward
to collect all connected content, then summarize it into coherent text.
"""
from typing import List, Dict, Optional, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models_v4 import KnowledgeNode, KnowledgeEdge


def _get_connected_nodes(db: Session, workspace_id: str, node_id: str, max_hops: int = 2,
                         min_edge_confidence: float = 0.0) -> List[Dict[str, Any]]:
    """
    Traverse the knowledge graph from a starting node, collecting connected nodes.

    Args:
        db: SQLAlchemy session
        workspace_id: workspace scope
        node_id: starting node ID
        max_hops: how many hops to traverse (1 = direct neighbors, 2 = neighbors of neighbors)
        min_edge_confidence: filter out low-confidence edges

    Returns:
        List of node dicts with distance from origin
    """
    visited = {node_id: 0}
    queue = [(node_id, 0)]
    collected = []
    
    while queue:
        current_id, distance = queue.pop(0)
        if distance >= max_hops:
            continue
        
        # Find edges from current node
        edges = db.query(KnowledgeEdge).filter(
            KnowledgeEdge.workspace_id == workspace_id,
            KnowledgeEdge.is_archived == False,
            KnowledgeEdge.confidence >= min_edge_confidence,
            or_(
                KnowledgeEdge.source_id == current_id,
                KnowledgeEdge.target_id == current_id
            )
        ).all()
        
        for edge in edges:
            # Get the other end of the edge
            other_id = edge.target_id if edge.source_id == current_id else edge.source_id
            
            if other_id not in visited:
                visited[other_id] = distance + 1
                queue.append((other_id, distance + 1))
                
                # Fetch the actual node
                node = db.query(KnowledgeNode).filter(
                    KnowledgeNode.id == other_id,
                    KnowledgeNode.workspace_id == workspace_id,
                    KnowledgeNode.is_archived == False
                ).first()
                
                if node:
                    collected.append({
                        "id": node.id,
                        "title": node.title,
                        "content": node.content or "",
                        "ai_summary": node.ai_short_summary or node.ai_summary or "",
                        "node_type": getattr(node.node_type, 'name', 'unknown') if node.node_type else 'unknown',
                        "layer": node.layer or "project",
                        "distance": distance + 1,
                        "edge_evidence": edge.evidence or "",
                        "edge_confidence": edge.confidence or 1.0,
                        "relation_notes": edge.notes or "",
                    })
    
    # Also include the origin node
    origin = db.query(KnowledgeNode).filter(
        KnowledgeNode.id == node_id,
        KnowledgeNode.workspace_id == workspace_id
    ).first()
    
    if origin:
        collected.insert(0, {
            "id": origin.id,
            "title": origin.title,
            "content": origin.content or "",
            "ai_summary": origin.ai_short_summary or origin.ai_summary or "",
            "node_type": getattr(origin.node_type, 'name', 'unknown') if origin.node_type else 'unknown',
            "layer": origin.layer or "project",
            "distance": 0,
            "edge_evidence": "",
            "edge_confidence": 1.0,
            "relation_notes": "Origin node",
        })
    
    # Sort by distance (closest first) then by edge confidence
    collected.sort(key=lambda x: (x["distance"], -x["edge_confidence"]))
    return collected


def _deduplicate_nodes(nodes: List[Dict]) -> List[Dict]:
    """Remove duplicate nodes by ID, keeping the closest instance."""
    seen = {}
    for n in nodes:
        nid = n["id"]
        if nid not in seen or n["distance"] < seen[nid]["distance"]:
            seen[nid] = n
    return list(seen.values())


def _build_context_text(nodes: List[Dict], origin_title: str) -> str:
    """
    Build a rich context text from collected nodes for summarization.
    """
    parts = []
    parts.append(f"# Knowledge Subgraph for: {origin_title}\n")
    
    for node in nodes:
        distance_label = "Origin" if node["distance"] == 0 else f"Connected (hop {node['distance']})"
        parts.append(f"\n## {node['title']} [{distance_label}]")
        
        if node["ai_summary"]:
            parts.append(f"Summary: {node['ai_summary'][:400]}")
        elif node["content"]:
            parts.append(f"Content: {node['content'][:400]}")
        
        if node["edge_evidence"]:
            parts.append(f"Relation evidence: {node['edge_evidence'][:200]}")
        
        if node["relation_notes"]:
            parts.append(f"Notes: {node['relation_notes']}")
    
    return "\n".join(parts)


def summarize_subgraph(db: Session, workspace_id: str, node_id: str,
                       max_hops: int = 2, min_edge_confidence: float = 0.0) -> Dict[str, Any]:
    """
    Traverse the knowledge graph from a node and produce a summary.

    Returns:
        {
            "origin_node_id": str,
            "origin_title": str,
            "total_nodes_collected": int,
            "nodes": [ {...}, ... ],
            "context_text": str,      # Raw assembled context for LLM
            "summary": str,           # Formatted summary (if no LLM, uses heuristic)
            "key_entities": [str],
            "key_relationships": [str],
        }
    """
    # Step 1: Get origin node info
    origin = db.query(KnowledgeNode).filter(
        KnowledgeNode.id == node_id,
        KnowledgeNode.workspace_id == workspace_id
    ).first()
    
    if not origin:
        return {"error": "Origin node not found", "origin_node_id": node_id}
    
    # Step 2: Traverse graph
    raw_nodes = _get_connected_nodes(db, workspace_id, node_id, max_hops, min_edge_confidence)
    nodes = _deduplicate_nodes(raw_nodes)
    
    # Step 3: Build context text
    context_text = _build_context_text(nodes, origin.title)
    
    # Step 4: Generate summary (heuristic if no LLM available)
    summary_parts = [f"Based on your knowledge graph, here's everything connected to **{origin.title}**:"]
    
    # Group by distance
    by_distance = {}
    for n in nodes:
        by_distance.setdefault(n["distance"], []).append(n)
    
    if 0 in by_distance:
        origin_node = by_distance[0][0]
        if origin_node.get("content"):
            summary_parts.append(f"\n**Direct content:** {origin_node['content'][:500]}")
    
    if 1 in by_distance:
        summary_parts.append(f"\n**Directly connected ({len(by_distance[1])} nodes):**")
        for n in by_distance[1][:5]:
            line = f"- {n['title']}"
            if n.get("ai_summary"):
                line += f": {n['ai_summary'][:100]}..."
            elif n.get("content"):
                line += f": {n['content'][:100]}..."
            summary_parts.append(line)
    
    if 2 in by_distance:
        summary_parts.append(f"\n**Second-degree connections ({len(by_distance[2])} nodes):**")
        for n in by_distance[2][:3]:
            line = f"- {n['title']}"
            if n.get("ai_summary"):
                line += f": {n['ai_summary'][:80]}..."
            summary_parts.append(line)
    
    summary = "\n".join(summary_parts)
    
    key_entities = [n["title"] for n in nodes if n["distance"] > 0]
    key_relationships = list(set(
        n.get("relation_notes", "") for n in nodes if n.get("relation_notes")
    ))
    
    return {
        "origin_node_id": node_id,
        "origin_title": origin.title,
        "total_nodes_collected": len(nodes),
        "nodes": nodes,
        "context_text": context_text,
        "summary": summary,
        "key_entities": key_entities,
        "key_relationships": key_relationships,
    }


def get_enriched_answer(db: Session, workspace_id: str, query_text: str,
                        matched_node: KnowledgeNode, max_hops: int = 2) -> str:
    """
    Generate an enriched answer for chat by traversing from a matched node.
    This is what Sage calls when a node is matched — it doesn't just return
    the node's content, it fetches the whole subgraph and summarizes it.
    """
    result = summarize_subgraph(db, workspace_id, matched_node.id, max_hops=max_hops)
    
    if "error" in result:
        return f"From your knowledge graph, here's what I know about **{matched_node.title}**:\n\n{matched_node.content or '(No content stored)'}")
    
    # Build a rich, conversational response
    lines = [
        f"From your knowledge graph, here's what I know about **{matched_node.title}**:",
    ]
    
    # Add origin content
    if matched_node.content and len(matched_node.content) > 10:
        lines.append(f"\n{matched_node.content[:800]}")
    
    # Add connected context
    if result["key_entities"]:
        lines.append(f"\n**Connected to ({len(result['key_entities'])} nodes):**")
        for entity in result["key_entities"][:8]:
            lines.append(f"  - {entity}")
    
    # Add relation evidence if available
    relation_notes = [r for r in result["key_relationships"] if r and r != "Origin node"]
    if relation_notes:
        lines.append(f"\n**Key relationships:**")
        for note in relation_notes[:5]:
            lines.append(f"  - {note}")
    
    # Suggest questions
    if matched_node.ai_suggested_questions:
        questions = matched_node.ai_suggested_questions
        if isinstance(questions, list) and len(questions) > 0:
            lines.append(f"\n**You might also ask:**")
            for q in questions[:3]:
                lines.append(f"  - {q}")
    
    return "\n".join(lines)
