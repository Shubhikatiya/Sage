"""
Chat API for Sage v4.
Real chat with LLM integration and persistent message history.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import uuid

from database_v4 import get_db
from models_v4 import ChatMessage as ChatMessageModel, Workspace, KnowledgeNode, NodeType
from schemas import ChatMessage as ChatMessageSchema, ChatMessageHistory, ChatResponse

router = APIRouter(prefix="/api", tags=["Chat"])


# Dependency placeholder - in production this would validate auth token
def get_current_workspace(db: Session = Depends(get_db)) -> Workspace:
    """Get the current active workspace."""
    workspace = db.query(Workspace).filter(Workspace.is_active == True).first()
    if not workspace:
        # Create default workspace if none exists
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name="Default Workspace",
            slug="default",
            is_active=True
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    return workspace


@router.post("/chat/message")
def send_message(
    layer: str,
    message: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Send a message in the chat and get a response."""
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Save user message
    user_msg = ChatMessageModel(
        workspace_id=workspace.id,
        layer=layer,
        role="user",
        content=message
    )
    db.add(user_msg)
    db.commit()

    # Get recent messages for context
    recent_messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.workspace_id == workspace.id
    ).order_by(ChatMessageModel.created_at.desc()).limit(10).all()
    recent_messages.reverse()  # Oldest first

    # Phase 02: Retrieve memories for context
    retrieved_memories = []
    try:
        from services.memory_engine import get_memory_store
        mem_store = get_memory_store()
        retrieved_memories = mem_store.search(
            query_text=message,
            workspace_id=workspace.id,
            limit=3
        )
    except Exception as e:
        print(f"[MemoryEngine] Failed to retrieve memories: {e}")

    # Build context from knowledge graph — search ALL nodes for keywords in the message
    context_nodes = []
    msg_lower = message.lower()
    
    # Extract keywords: filter out short words and common stop words
    STOP_WORDS = {"what", "know", "about", "this", "that", "your", "from", "with", "have", "there", "when", "where", "which", "their", "would", "could", "should", "does", "did", "will", "they", "them", "than", "then", "more", "some", "very", "just", "like", "also", "only", "even", "into", "over", "such", "make", "made", "most", "many", "other", "well", "been", "being", "time", "here", "how", "who", "whom", "whose", "why", "those", "these", "each", "every", "both", "either", "neither", "much", "little", "few", "between", "among", "through", "during", "before", "after", "above", "below", "under", "again", "further", "once", "once", "down", "off", "out", "up", "way", "own", "same", "so", "than", "too", "very", "can", "had", "has", "her", "his", "him", "its", "may", "might", "must", "shall", "were", "was", "are", "is", "am", "be", "do", "get", "got", "say", "said", "see", "seen", "come", "came", "go", "went", "take", "took", "give", "gave", "find", "found", "think", "thought", "tell", "told", "ask", "asked", "work", "worked", "try", "tried", "feel", "felt", "become", "became", "leave", "left", "put", "mean", "meant", "keep", "kept", "let", "begin", "began", "seem", "seemed", "help", "helped", "show", "showed", "hear", "heard", "play", "played", "run", "ran", "move", "moved", "live", "lived", "believe", "believed", "bring", "brought", "happen", "happened", "write", "wrote", "provide", "provided", "sit", "sat", "stand", "stood", "lose", "lost", "pay", "paid", "meet", "met", "include", "included", "continue", "continued", "set", "learn", "learned", "change", "changed", "lead", "led", "understand", "understood", "watch", "watched", "follow", "followed", "stop", "stopped", "create", "created", "speak", "spoke", "read", "allow", "allowed", "add", "added", "spend", "spent", "grow", "grew", "open", "opened", "walk", "walked", "win", "won", "offer", "offered", "remember", "remembered", "love", "loved", "consider", "considered", "appear", "appeared", "buy", "bought", "wait", "waited", "serve", "served", "die", "died", "send", "sent", "expect", "expected", "build", "built", "stay", "stayed", "fall", "fell", "cut", "reach", "reached", "kill", "killed", "remain", "remained", "suggest", "suggested", "raise", "raised", "pass", "passed", "sell", "sold", "require", "required", "report", "reported", "decide", "decided", "pull", "pulled"}
    
    # Extract meaningful keywords: longer than 3 chars, not a stop word
    raw_keywords = [w.strip("?.,!;:") for w in msg_lower.split() if len(w.strip("?.,!;:")) > 3]
    keywords = [w for w in raw_keywords if w not in STOP_WORDS]
    
    # Sort by length descending so most specific words are used first
    keywords = sorted(keywords, key=len, reverse=True)
    
    # PRIORITY 1: Title contains any keyword (use up to 3 longest)
    if keywords:
        from sqlalchemy import or_
        title_clauses = [KnowledgeNode.title.ilike(f"%{kw}%") for kw in keywords[:3]]
        title_matches = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            or_(*title_clauses),
            KnowledgeNode.is_archived == False
        ).all()
        context_nodes.extend(title_matches)
    
    # PRIORITY 2: Content contains keyword (only if no title matches)
    if keywords and not context_nodes:
        from sqlalchemy import or_
        content_clauses = [KnowledgeNode.content.ilike(f"%{kw}%") for kw in keywords[:3]]
        content_matches = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            or_(*content_clauses),
            KnowledgeNode.is_archived == False
        ).limit(3).all()
        context_nodes.extend(content_matches)
    
    # Also fetch layer-specific nodes as fallback
    if layer == "project":
        project_nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            KnowledgeNode.is_archived == False
        ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
        context_nodes = list(dict.fromkeys(context_nodes + project_nodes))  # dedupe
    elif layer == "life":
        person_nodes = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == workspace.id,
            KnowledgeNode.is_archived == False
        ).limit(5).all()
        context_nodes = list(dict.fromkeys(context_nodes + person_nodes))

    # Try to use LLM service if available
    response_text = ""
    tool_calls = []
    try:
        from services.llm_service import generate_response
        from services.bring_me_back import BringMeBackEngine

        # Phase 05: Context Engine - detect intent and build structured context
        context_result = None
        try:
            from services.context_engine import build_context_for_chat
            hist_for_context = []
            for msg in recent_messages:
                hist_for_context.append({
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat() if msg.created_at else None
                })

            context_result = build_context_for_chat(
                user_message=message,
                conversation_history=hist_for_context,
                system_prompt="",
                workspace_id=workspace.id
            )

            detected_intent = context_result["intent"]
            print(f"[ContextEngine] Intent: {detected_intent['type']} (confidence: {detected_intent['confidence']:.2f})")

            if detected_intent.get("referenced_project"):
                print(f"[ContextEngine] Referenced project: {detected_intent['referenced_project']}")
        except Exception as e:
            print(f"[ContextEngine] Error (non-critical): {e}")

        # Phase 11: Track tool calls for frontend visibility
        tool_calls = []

        # Check for special commands
        if message.lower().strip() in ["bring me back", "briefing", "what did i miss", "catch me up"]:
            tool_calls.append({"tool": "bring_me_back", "status": "success"})
            # Phase 06: Use new Bring Me Back v2 engine
            try:
                from services.bring_me_back_v2 import BringMeBackEngineV2
                engine = BringMeBackEngineV2(db, workspace.id)
                reconstruction = engine.reconstruct()
                response_text = engine.format_reconstruction_markdown(reconstruction)
            except Exception as e:
                print(f"[BringMeBackV2] Error, falling back to v1: {e}")
                engine = BringMeBackEngine(db, workspace.id)
                briefing = engine.generate_briefing()
                response_text = engine.format_briefing_markdown(briefing)
        else:
            # Build context for LLM
            context_parts = []
            if context_nodes:
                context_parts.append("Relevant knowledge:\n" + "\n".join([
                    f"- {n.title}: {n.content[:200]}..." if n.content else f"- {n.title}"
                    for n in context_nodes[:3]
                ]))

            # Add retrieved memories to context
            if retrieved_memories:
                mem_parts = ["Relevant memories:"]
                for mem in retrieved_memories[:3]:
                    preview = mem["content"][:200]
                    mem_parts.append(f"  [{mem['type']}] {preview}... (relevance: {mem['score']:.2f})")
                context_parts.append("\n".join(mem_parts))

            context = "\n\n".join(context_parts)

            # ─── KNOWLEDGE-FIRST PATH ───
            # If we found knowledge graph nodes, answer directly from them.
            # The 1.5B model can't reliably follow "use only context" instructions,
            # so we format the answer ourselves and skip the LLM call.
            if context_nodes:
                # Build a clean, direct answer from the knowledge graph
                node = context_nodes[0]  # best match
                answer_lines = [f"From your knowledge graph, here's what I know about **{node.title}**:"]
                if node.content and len(node.content) > 10:
                    answer_lines.append(node.content)
                else:
                    answer_lines.append("(No detailed content stored for this node.)")
                
                # If there are related nodes, mention them
                if len(context_nodes) > 1:
                    related = [n.title for n in context_nodes[1:3]]
                    answer_lines.append(f"\nRelated: {', '.join(related)}")
                
                response_text = "\n\n".join(answer_lines)
            else:
                # No KG match — fall back to LLM for general knowledge
                # Build prompt with conversation history
                history_parts = []
                for msg in recent_messages[-5:]:
                    prefix = "User" if msg.role == "user" else "Sage"
                    history_parts.append(f"{prefix}: {msg.content}")

                history_text = "\n".join(history_parts)
                full_prompt = message
                if history_text:
                    full_prompt = f"Previous conversation:\n{history_text}\n\nCurrent message: {message}"

                # Direct Ollama HTTP call with strict timeout — uses local Ollama
                import os, requests
                ollama_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/') + '/api/chat'
                ollama_model = os.environ.get('OLLAMA_MODEL', 'llama3.2:1b')
                system_msg = "You are Sage, the user's AI Chief of Staff."
                
                try:
                    resp = requests.post(
                        ollama_url,
                        json={
                            "model": ollama_model,
                            "messages": [
                                {"role": "system", "content": system_msg},
                                {"role": "user", "content": full_prompt}
                            ],
                            "options": {"temperature": 0.7, "num_predict": 500, "top_p": 0.9},
                            "stream": False
                        },
                        timeout=20
                    )
                    if resp.status_code == 200:
                        response_text = resp.json().get("message", {}).get("content", "").strip()
                    else:
                        print(f"[Chat] Ollama returned {resp.status_code}")
                        response_text = ""
                except Exception as e:
                    print(f"[Chat] Ollama call error: {e}")
                    response_text = ""

    except Exception as e:
        print(f"[Chat] LLM service error: {e}")
        response_text = ""

    if not response_text:
        # Fallback response
        layer_responses = {
            "general": f"I received your message: '{message}'. I'm currently running in fallback mode because the LLM service is not configured. Try asking me to 'bring me back' for a briefing.",
            "life": f"You asked about life: '{message}'. In the full implementation, I would search your life domains and provide contextual advice.",
            "project": f"You asked about projects: '{message}'. In the full implementation, I would search your project knowledge and provide updates.",
            "knowledge": f"You shared knowledge: '{message}'. In the full implementation, I would connect this to relevant concepts in your graph.",
            "system": f"You asked about the system: '{message}'. Sage v4 is running with a knowledge graph backend. Try 'bring me back' for a status briefing."
        }
        response_text = layer_responses.get(layer, layer_responses["general"])

    # Save assistant response
    assistant_msg = ChatMessageModel(
        workspace_id=workspace.id,
        layer=layer,
        role="assistant",
        content=response_text
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "success": True,
        "data": {
            "message": response_text,
            "layer": layer,
            "timestamp": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None
        }
    }


@router.get("/chat/history")
def get_chat_history(
    layer: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Get chat history for a workspace."""
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    query = db.query(ChatMessageModel).filter(ChatMessageModel.workspace_id == workspace.id)
    if layer:
        query = query.filter(ChatMessageModel.layer == layer)

    messages = query.order_by(ChatMessageModel.created_at.desc()).limit(limit).all()
    messages.reverse()

    return {
        "success": True,
        "data": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "layer": msg.layer,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    }


@router.get("/chat/layer")
def layer_context(
    message: str = "hello",
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """Detect which layer (general, life, project, knowledge, system) a message belongs to."""
    if not workspace:
        return {"layer": "general", "confidence": 0.0}

    msg_lower = message.lower()

    # Simple keyword-based classification
    if any(k in msg_lower for k in ["project", "task", "deadline", "milestone", "sprint"]):
        layer = "project"
    elif any(k in msg_lower for k in ["life", "goal", "habit", "health", "career", "family", "relationship"]):
        layer = "life"
    elif any(k in msg_lower for k in ["what is", "explain", "how does", "define", "concept", "theory"]):
        layer = "knowledge"
    elif any(k in msg_lower for k in ["system", "config", "setting", "api", "backend", "bug", "feature request", "version"]):
        layer = "system"
    else:
        layer = "general"

    return {
        "success": True,
        "data": {
            "layer": layer,
            "message": message,
            "confidence": 1.0 if layer != "general" else 0.5
        }
    }


# Dependency placeholder - in production this would validate auth token
def get_current_workspace(db: Session = Depends(get_db)) -> Workspace:
    """Get the current active workspace."""
    workspace = db.query(Workspace).filter(Workspace.is_active == True).first()
    if not workspace:
        # Create default workspace if none exists
        workspace = Workspace(
            id=str(uuid.uuid4()),
            name="Default Workspace",
            slug="default",
            is_active=True
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
    return workspace
