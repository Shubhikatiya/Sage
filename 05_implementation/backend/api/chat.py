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

    # ─── Conversational state tracking ───
    # context_data_out: what we'll save WITH the assistant's response
    context_data_out = {}

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

    # ─── CHECK CONVERSATIONAL STATE FIRST ───
    # Only trigger if the assistant's LAST message (just before this user message)
    # was explicitly asking for knowledge. This prevents stale states from old
    # conversations or test runs from interfering.
    last_two_messages = db.query(ChatMessageModel).filter(
        ChatMessageModel.workspace_id == workspace.id
    ).order_by(ChatMessageModel.created_at.desc()).limit(2).all()
    
    last_context_data = {}
    if len(last_two_messages) >= 2:
        prev_msg = last_two_messages[1]  # message before the current user message
        if prev_msg.role == "assistant" and prev_msg.context_data:
            import json
            last_context_data = prev_msg.context_data if isinstance(prev_msg.context_data, dict) else json.loads(prev_msg.context_data) if prev_msg.context_data else {}
    
    if last_context_data.get("sage_state") == "awaiting_knowledge":
        # Extract topic from USER'S message, not the stale pending_topic
        # User might teach us about something completely different
        user_topic = ""
        
        # Try to extract a heading: "# Topic" or "## Topic"
        heading_match = __import__('re').search(r'^#+\s*(.+)$', message.strip(), __import__('re').MULTILINE)
        if heading_match:
            user_topic = heading_match.group(1).strip()[:50]
        
        # If no heading, try first proper noun phrase (capitalized words)
        if not user_topic:
            proper_noun = __import__('re').search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})', message)
            if proper_noun:
                user_topic = proper_noun.group(1).strip()[:50]
        
        # Fallback to pending_topic or generic
        if not user_topic:
            user_topic = last_context_data.get("pending_topic", "")
        if not user_topic:
            # Last resort: first 3 meaningful words (skip stop words)
            words = [w for w in message.split() if len(w) > 2 and w.lower() not in STOP_WORDS]
            if words:
                user_topic = " ".join(words[:3])[:50]
        if not user_topic:
            user_topic = "that"
        
        # Clean topic: remove control chars, box-drawing chars, excessive punctuation
        import re
        user_topic = re.sub(r'[\x00-\x1f\x7f-\x9f┌┐└┘├┤┬┴┼─│═║╒╓╔╕╖╗╘╙╚╛╜╝╞╟╠╡╢╣╤╥╦╧╨╩╪╫╬]', '', user_topic)
        user_topic = re.sub(r'[^\w\s\-]', '', user_topic).strip()
        if len(user_topic) < 2:
            user_topic = "Information"
        
        # Detect multiple topics: comma-separated, "and", or bullet list
        # If message has multiple distinct capitalized terms, create nodes for each
        topics = [user_topic]
        multi_match = re.findall(r'\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})?)\b', message)
        if len(multi_match) >= 2 and len(message) > 50:
            # User might be teaching about multiple things
            topics = list(dict.fromkeys([t for t in multi_match if len(t) > 3 and t.lower() not in STOP_WORDS][:5]))
            if not topics:
                topics = [user_topic]
        
        saved_nodes = []
        for topic in topics:
            topic = topic.strip()[:50]
            if len(topic) < 2:
                continue
            
            slug = re.sub(r'[^\w\-]', '-', topic.lower())[:50]
            try:
                # Check if node already exists
                existing = db.query(KnowledgeNode).filter(
                    KnowledgeNode.workspace_id == workspace.id,
                    KnowledgeNode.title.ilike(topic)
                ).first()
                if existing:
                    # Update existing node content instead of creating duplicate
                    existing.content = (existing.content or "") + f"\n\n[Updated {datetime.utcnow().strftime('%Y-%m-%d')}]: {message.strip()[:500]}"
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                    saved_nodes.append(topic)
                    continue
                
                new_node = KnowledgeNode(
                    workspace_id=workspace.id,
                    node_type_id="e3bf8bdd-050b-4dba-968c-32b0b0e0ef08",
                    slug=slug,
                    title=topic,
                    content=message.strip(),
                    layer="project",
                    source_type="user_taught",
                    source_id=last_context_data.get("query_id", "")
                )
                db.add(new_node)
                db.commit()
                db.refresh(new_node)
                
                # Sync to vector store for semantic search
                try:
                    from services.knowledge_vector_store import sync_node
                    sync_node(new_node)
                except Exception as ve:
                    print(f"[Chat] Vector sync error (non-critical): {ve}")
                
                saved_nodes.append(topic)
            except Exception as e:
                db.rollback()
                print(f"[KG Builder] Error saving node for '{topic}': {e}")
        
        if saved_nodes:
            if len(saved_nodes) == 1:
                response_text = (
                    f"Got it. I've saved **{saved_nodes[0]}** to your knowledge graph. "
                    f"You can now ask me about it anytime, and I'll recall this information."
                )
            else:
                response_text = (
                    f"Got it. I've saved **{', '.join(saved_nodes)}** to your knowledge graph. "
                    f"You can now ask me about any of them anytime."
                )
        else:
            response_text = "I tried to save that but couldn't create the knowledge node. Could you rephrase?"
        
        # Save response (no awaiting state — conversation is complete)
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

    # ─── SEMANTIC SEARCH: Find knowledge nodes by meaning, not just keywords ───
    context_nodes = []
    title_matches = []
    content_matches = []
    fallback_nodes = []
    has_direct_knowledge = False

    try:
        from services.knowledge_vector_store import semantic_search, get_collection_count

        vec_count = get_collection_count()
        if vec_count > 0:
            semantic_results = semantic_search(
                query_text=message,
                workspace_id=workspace.id,
                n_results=5
            )
            if semantic_results:
                # Load full nodes from DB so graph traversal works
                for r in semantic_results:
                    node = db.query(KnowledgeNode).filter(
                        KnowledgeNode.id == r["id"],
                        KnowledgeNode.workspace_id == workspace.id,
                        KnowledgeNode.is_archived == False
                    ).first()
                    if node:
                        title_matches.append(node)
                        context_nodes.append(node)
                has_direct_knowledge = len(title_matches) > 0
                print(f"[Chat] Semantic search found {len(title_matches)} matches")
        else:
            print("[Chat] Vector store empty, falling back to keyword search")
    except Exception as e:
        print(f"[Chat] Semantic search error: {e}, falling back to keyword search")

    # ─── KEYWORD FALLBACK ───
    # If semantic search failed or returned nothing, use the old keyword search
    if not has_direct_knowledge:
        msg_lower = message.lower()
        STOP_WORDS = {"what", "know", "about", "this", "that", "your", "from", "with", "have", "there", "when", "where", "which", "their", "would", "could", "should", "does", "did", "will", "they", "them", "than", "then", "more", "some", "very", "just", "like", "also", "only", "even", "into", "over", "such", "make", "made", "most", "many", "other", "well", "been", "being", "time", "here", "how", "who", "whom", "whose", "why", "those", "these", "each", "every", "both", "either", "neither", "much", "little", "few", "between", "among", "through", "during", "before", "after", "above", "below", "under", "again", "further", "once", "once", "down", "off", "out", "up", "way", "own", "same", "so", "than", "too", "very", "can", "had", "has", "her", "his", "him", "its", "may", "might", "must", "shall", "were", "was", "are", "is", "am", "be", "do", "get", "got", "say", "said", "see", "seen", "come", "came", "go", "went", "take", "took", "give", "gave", "find", "found", "think", "thought", "tell", "told", "ask", "asked", "work", "worked", "try", "tried", "feel", "felt", "become", "became", "leave", "left", "put", "mean", "meant", "keep", "kept", "let", "begin", "began", "seem", "seemed", "help", "helped", "show", "showed", "hear", "heard", "play", "played", "run", "ran", "move", "moved", "live", "lived", "believe", "believed", "bring", "brought", "happen", "happened", "write", "wrote", "provide", "provided", "sit", "sat", "stand", "stood", "lose", "lost", "pay", "paid", "meet", "met", "include", "included", "continue", "continued", "set", "learn", "learned", "change", "changed", "lead", "led", "understand", "understood", "watch", "watched", "follow", "followed", "stop", "stopped", "create", "created", "speak", "spoke", "read", "allow", "allowed", "add", "added", "spend", "spent", "grow", "grew", "open", "opened", "walk", "walked", "win", "won", "offer", "offered", "remember", "remembered", "love", "loved", "consider", "considered", "appear", "appeared", "buy", "bought", "wait", "waited", "serve", "served", "die", "died", "send", "sent", "expect", "expected", "build", "built", "stay", "stayed", "fall", "fell", "cut", "reach", "reached", "kill", "killed", "remain", "remained", "suggest", "suggested", "raise", "raised", "pass", "passed", "sell", "sold", "require", "required", "report", "reported", "decide", "decided", "pull", "pulled"}
        
        raw_keywords = [w.strip("?.,!;:") for w in msg_lower.split() if len(w.strip("?.,!;:")) > 3]
        keywords = [w for w in raw_keywords if w not in STOP_WORDS]
        keywords = sorted(keywords, key=len, reverse=True)
        
        if keywords:
            from sqlalchemy import or_
            title_clauses = [KnowledgeNode.title.ilike(f"%{kw}%") for kw in keywords[:3]]
            title_matches = db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == workspace.id,
                or_(*title_clauses),
                KnowledgeNode.is_archived == False
            ).all()
            context_nodes.extend(title_matches)
        
        has_direct_knowledge = len(title_matches) > 0
        
        if keywords and not has_direct_knowledge:
            from sqlalchemy import or_, func
            content_clauses = [KnowledgeNode.content.ilike(f"%{kw}%") for kw in keywords[:3]]
            content_matches = db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == workspace.id,
                or_(*content_clauses),
                KnowledgeNode.is_archived == False,
                KnowledgeNode.source_type.notin_(["extracted_entity", "asset_extraction"]),
                func.length(KnowledgeNode.title) >= 4,
                KnowledgeNode.title != "",
                KnowledgeNode.title.isnot(None),
            ).limit(3).all()
    
    # Fallback: recent nodes
    if not context_nodes:
        if layer == "project":
            fallback_nodes = db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == workspace.id,
                KnowledgeNode.is_archived == False
            ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
        elif layer == "life":
            fallback_nodes = db.query(KnowledgeNode).filter(
                KnowledgeNode.workspace_id == workspace.id,
                KnowledgeNode.is_archived == False
            ).limit(5).all()
        context_nodes = fallback_nodes

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
            # If we found a node whose TITLE matches the query, traverse the graph
            # to collect connected nodes and produce an enriched summary.
            if has_direct_knowledge:
                # Direct title match — fetch the whole subgraph, not just the node
                from sage.core.extraction.graph_traversal import get_enriched_answer
                node = title_matches[0]  # best title match
                
                try:
                    response_text = get_enriched_answer(
                        db=db,
                        workspace_id=workspace.id,
                        query_text=message,
                        matched_node=node,
                        max_hops=2
                    )
                except Exception as e:
                    print(f"[Chat] Graph traversal error: {e}")
                    # Fallback to simple answer
                    response_text = (
                        f"From your knowledge graph, here's what I know about **{node.title}**:\n\n"
                        f"{node.content or '(No detailed content stored for this node.)'}"
                    )
                
                # If there are other title matches, mention them
                if len(title_matches) > 1:
                    related = [n.title for n in title_matches[1:3]]
                    response_text += f"\n\nOther matches: {', '.join(related)}"
            
            elif content_matches:
                # The topic is MENTIONED in other nodes but has no dedicated node.
                # Show a contextual hint and trigger the builder.
                mentioned_in = content_matches[0]
                hint = (
                    f"I found mentions of that in **{mentioned_in.title}**, "
                    f"but I don't have a dedicated entry yet.\n\n"
                    f"Would you like to tell me about it? Just reply with what you know — "
                    f"I'll create a knowledge node so I can answer properly next time."
                )
                
                # Set up conversational state
                import uuid
                query_id = str(uuid.uuid4())[:8]
                context_data_out["sage_state"] = "awaiting_knowledge"
                context_data_out["pending_topic"] = keywords[0].capitalize() if keywords else "that"
                context_data_out["query_id"] = query_id
                
                response_text = hint
            
            else:
                # ─── NO KG MATCH — USE GROQ/OPENAI FOR GENERAL KNOWLEDGE ───
                import os
                provider = os.environ.get("LLM_PROVIDER", "ollama")
                
                response_text = ""
                
                if provider == "groq" and os.environ.get("GROQ_API_KEY"):
                    try:
                        import requests
                        groq_url = "https://api.groq.com/openai/v1/chat/completions"
                        groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")
                        system_msg = "You are Sage, the user's AI Chief of Staff. Be helpful, concise, and conversational."
                        
                        resp = requests.post(
                            groq_url,
                            headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": "application/json"},
                            json={
                                "model": groq_model,
                                "messages": [
                                    {"role": "system", "content": system_msg},
                                    {"role": "user", "content": message}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 800
                            },
                            timeout=30
                        )
                        if resp.status_code == 200:
                            response_text = resp.json()["choices"][0]["message"]["content"].strip()
                        else:
                            print(f"[Groq] Error {resp.status_code}: {resp.text[:200]}")
                    except Exception as e:
                        print(f"[Groq] Exception: {e}")
                
                elif provider == "openai" and os.environ.get("OPENAI_API_KEY"):
                    try:
                        import requests
                        openai_url = "https://api.openai.com/v1/chat/completions"
                        openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
                        system_msg = "You are Sage, the user's AI Chief of Staff. Be helpful, concise, and conversational."
                        
                        resp = requests.post(
                            openai_url,
                            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"},
                            json={
                                "model": openai_model,
                                "messages": [
                                    {"role": "system", "content": system_msg},
                                    {"role": "user", "content": message}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 800
                            },
                            timeout=30
                        )
                        if resp.status_code == 200:
                            response_text = resp.json()["choices"][0]["message"]["content"].strip()
                        else:
                            print(f"[OpenAI] Error {resp.status_code}: {resp.text[:200]}")
                    except Exception as e:
                        print(f"[OpenAI] Exception: {e}")
                
                # If no LLM response or no API key configured, use knowledge builder
                if not response_text:
                    import uuid
                    query_id = str(uuid.uuid4())[:8]
                    
                    topic_guess = ""
                    if keywords:
                        topic_guess = keywords[0].capitalize()
                    
                    if topic_guess:
                        response_text = (
                            f"I don't have anything about **{topic_guess}** in your knowledge graph yet.\n\n"
                            f"Would you like to tell me about it? "
                            f"Just reply with what you know — I'll remember it for next time."
                        )
                    else:
                        response_text = (
                            "I don't have anything about that in your knowledge graph yet.\n\n"
                            "Would you like to tell me about it? "
                            "Just reply with what you know — I'll remember it for next time."
                        )
                    
                    context_data_out["sage_state"] = "awaiting_knowledge"
                    context_data_out["pending_topic"] = topic_guess
                    context_data_out["query_id"] = query_id

    except Exception as e:
        import traceback
        print(f"[Chat] ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        try:
            db.rollback()
        except:
            pass
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

    # Save assistant response WITH conversational state
    assistant_msg = ChatMessageModel(
        workspace_id=workspace.id,
        layer=layer,
        role="assistant",
        content=response_text,
        context_data=context_data_out if context_data_out else None
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
