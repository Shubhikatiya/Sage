import os
import shutil
import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from database import SessionLocal, engine
from models import Base
from schemas import (
    LifeDomainCreate, LifeDomain,
    ThoughtCreate, Thought,
    DocumentCreate, Document,
    ResearchNoteCreate, ResearchNote,
    DeadlineCreate, Deadline,
    DailyPlanCreate, DailyPlan,
    ChatMessage, ChatMessageHistory, ChatResponse, RetrieveRequest, RetrievedMemory,
    DomainDocument
)
from crud import (
    create_life_domain, get_life_domains, get_life_domain, get_life_domain_by_name,
    update_life_domain, delete_life_domain,
    create_thought, get_thoughts,
    create_document, get_documents,
    create_research_note, get_research_notes,
    create_deadline, get_deadlines,
    create_daily_plan, get_daily_plans,
    create_memory_vector,
    create_or_update_topic, get_topics,
    create_chat_message, get_chat_messages_by_layer,
    get_or_create_user, update_user_name,
    get_or_create_domain_document, get_domain_documents, update_domain_document
)
from services.document_processor import process_document, summarize_document
from services.embedding_service import store_embedding, get_embedding
from services.retrieval_service import retrieve_memories
from services.classifier_service import classify_document
from services.topic_service import extract_document_topics
from services.llm_service import generate_response, has_llm

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title='Sage API', version='0.2.0')

# Debug endpoint to verify code version
@app.get('/api/debug')
def debug_info():
    from services.llm_service import _fallback_response
    import inspect
    source = inspect.getsource(_fallback_response)
    return {'source_file': _fallback_response.__code__.co_filename, 'source_preview': source[:300]}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://localhost:5174', 'http://localhost:5175'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Ensure upload directory exists
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- SEED DEFAULT LIFE DOMAINS ---
DEFAULT_DOMAINS = [
    {"name": "Self", "description": "Physical, mental, emotional, spiritual well-being"},
    {"name": "Career", "description": "Professional identity, skills, reputation"},
    {"name": "Sage", "description": "AI Chief of Staff product and mission", "children": [
        {"name": "Sage / Product", "description": "Product vision, features, roadmap"},
        {"name": "Sage / Engineering", "description": "Technical architecture, implementation"},
        {"name": "Sage / Research", "description": "AI research, memory systems, retrieval"},
        {"name": "Sage / Business", "description": "Strategy, monetization, go-to-market"},
        {"name": "Sage / Users", "description": "User research, feedback, community"},
    ]},
    {"name": "Kaal", "description": "Time philosophy and temporal intelligence project"},
    {"name": "Navgunjara Foundation", "description": "Ancient wisdom meets modern science initiative"},
    {"name": "ReRoot", "description": "Human flourishing and transformation platform"},
    {"name": "AI Research", "description": "General AI/ML exploration and experiments"},
    {"name": "Human Development Research", "description": "Psychology, neuroscience, growth"},
    {"name": "Technology Mastery", "description": "Tools, systems, technical skills"},
    {"name": "Entrepreneurship", "description": "Business building, ventures, investments"},
    {"name": "Writing", "description": "Articles, essays, books, content"},
    {"name": "Speaking", "description": "Talks, podcasts, workshops, teaching"},
    {"name": "Community", "description": "Networks, relationships, collaborations"},
    {"name": "Finance", "description": "Wealth, budgeting, financial planning"},
    {"name": "Research Library", "description": "Books, papers, notes, knowledge base"},
    {"name": "Experiments", "description": "Personal and professional experiments"},
    {"name": "Life Administration", "description": "Logistics, health, legal, daily ops"},
    {"name": "Long-term Dreams", "description": "Vision, legacy, 10+ year aspirations"},
]

@app.post('/api/seed')
def seed_domains(db: Session = Depends(get_db)):
    """Create default life domains if they don't exist."""
    created = []
    for domain_data in DEFAULT_DOMAINS:
        children = domain_data.pop('children', [])
        existing = get_life_domain_by_name(db, domain_data['name'])
        if not existing:
            parent = create_life_domain(db, LifeDomainCreate(**domain_data))
            created.append(parent.name)
            for child_data in children:
                child_data['parent_id'] = parent.id
                child = create_life_domain(db, LifeDomainCreate(**child_data))
                created.append(child.name)
    return {'seeded': len(created), 'domains': created}

# --- LIFE DOMAINS ---
@app.post('/api/life-domains', response_model=LifeDomain)
def create_new_domain(domain: LifeDomainCreate, db: Session = Depends(get_db)):
    return create_life_domain(db=db, domain=domain)

@app.get('/api/life-domains', response_model=List[LifeDomain])
def read_domains(layer: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_life_domains(db=db, layer=layer, skip=skip, limit=limit)

@app.get('/api/life-domains/{domain_id}', response_model=LifeDomain)
def read_domain(domain_id: str, db: Session = Depends(get_db)):
    db_domain = get_life_domain(db=db, domain_id=domain_id)
    if db_domain is None:
        raise HTTPException(status_code=404, detail='Life domain not found')
    return db_domain

@app.put('/api/life-domains/{domain_id}')
def update_domain(domain_id: str, updates: dict, db: Session = Depends(get_db)):
    db_domain = update_life_domain(db=db, domain_id=domain_id, updates=updates)
    if not db_domain:
        raise HTTPException(status_code=404, detail='Life domain not found')
    return db_domain

@app.delete('/api/life-domains/{domain_id}')
def remove_domain(domain_id: str, db: Session = Depends(get_db)):
    success = delete_life_domain(db=db, domain_id=domain_id)
    if not success:
        raise HTTPException(status_code=404, detail='Life domain not found')
    return {'message': 'Life domain deleted'}

@app.post('/api/life-domains/{domain_id}/subsections')
def create_subsection(domain_id: str, name: str = Form(...), description: str = Form(''), db: Session = Depends(get_db)):
    parent = get_life_domain(db=db, domain_id=domain_id)
    if not parent:
        raise HTTPException(status_code=404, detail='Parent domain not found')
    subsection = create_life_domain(db=db, domain=LifeDomainCreate(
        name=f"{parent.name} / {name}",
        description=description,
        parent_id=domain_id
    ))
    return subsection

# --- THOUGHTS ---
@app.post('/api/thoughts', response_model=Thought)
def create_new_thought(thought: ThoughtCreate, db: Session = Depends(get_db)):
    db_thought = create_thought(db=db, thought=thought)
    store_embedding(
        'memories',
        str(db_thought.id),
        thought.content,
        {
            'type': 'thought',
            'life_domain_id': str(thought.life_domain_id),
            'source': thought.source
        }
    )
    return db_thought

@app.get('/api/life-domains/{domain_id}/thoughts', response_model=List[Thought])
def read_thoughts(domain_id: str, db: Session = Depends(get_db)):
    return get_thoughts(db=db, life_domain_id=domain_id)

# --- DOCUMENTS ---
@app.post('/api/documents/upload')
def upload_document(
    life_domain_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_ext = os.path.splitext(file.filename)[1]
    file_name = f'{uuid.uuid4()}{file_ext}'
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(file_path, 'wb') as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    text = process_document(file_path)
    summary = summarize_document(text) if text else "No text extracted."
    
    # --- AUTO-CLASSIFY if no domain specified ---
    assigned_domain = None
    classification = None
    
    if not life_domain_id:
        all_domains = get_life_domains(db=db)
        # Pass domain objects directly — classifier handles dict or object
        classification = classify_document(text or summary, all_domains)
        if classification:
            life_domain_id = classification['domain_id']
            assigned_domain = next((d for d in all_domains if d.id == life_domain_id), None)
    else:
        assigned_domain = get_life_domain(db=db, domain_id=life_domain_id)
    
    if not life_domain_id:
        life_domain_id = ''
    
    doc_data = DocumentCreate(
        life_domain_id=life_domain_id,
        filename=file.filename,
        content=text or '',
        file_path=file_path,
        file_type=file_ext.lstrip('.')
    )
    db_doc = create_document(db=db, document=doc_data)
    
    # Create a research note with the summary
    note_data = ResearchNoteCreate(
        life_domain_id=life_domain_id,
        title=f'Document: {file.filename}',
        content=summary,
        tags=['auto-synthesis', 'document-upload']
    )
    db_note = create_research_note(db=db, note=note_data)
    
    if text:
        store_embedding(
            'memories',
            str(db_doc.id),
            text,
            {
                'type': 'document',
                'life_domain_id': str(life_domain_id),
                'filename': file.filename
            }
        )
        store_embedding(
            'memories',
            str(db_note.id),
            summary,
            {
                'type': 'research_note',
                'life_domain_id': str(life_domain_id),
                'title': f'Document: {file.filename}'
            }
        )
    
    # --- EXTRACT TOPICS from the document ---
    extracted_topics = []
    if text:
        from services.topic_service import extract_document_topics
        from crud import create_or_update_topic
        topics = extract_document_topics(text, life_domain_id=life_domain_id, source_id=str(db_doc.id))
        for topic_data in topics:
            db_topic = create_or_update_topic(db=db, topic_data=topic_data)
            extracted_topics.append({
                'name': db_topic.name,
                'frequency': db_topic.frequency
            })
    
    # --- SYNTHESIZE DOMAIN PROFILE after upload ---
    if life_domain_id:
        from services.profile_service import update_domain_profile
        try:
            updated_profile = update_domain_profile(db=db, domain_id=life_domain_id)
        except Exception as e:
            print(f"Profile update error: {e}")
    
    result = {
        'document_id': str(db_doc.id),
        'note_id': str(db_note.id),
        'filename': file.filename,
        'summary': summary,
        'assigned_domain': assigned_domain.name if assigned_domain else None,
        'extracted_topics': extracted_topics,
        'content_preview': text[:500] + '...' if text and len(text) > 500 else (text or 'No text extracted')
    }
    
    if classification:
        result['classification'] = classification
    
    return result

@app.get('/api/life-domains/{domain_id}/uploaded-files', response_model=List[Document])
def read_documents(domain_id: str, db: Session = Depends(get_db)):
    """Get all uploaded file documents for a domain."""
    return get_documents(db=db, life_domain_id=domain_id)

# --- TOPICS ---
@app.get('/api/topics')
def read_topics(life_domain_id: Optional[str] = None, db: Session = Depends(get_db)):
    from crud import get_topics
    topics = get_topics(db=db, life_domain_id=life_domain_id)
    return {
        'topics': [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'life_domain_id': t.life_domain_id,
                'frequency': t.frequency,
                'created_at': t.created_at.isoformat() if t.created_at else None
            }
            for t in topics
        ],
        'count': len(topics)
    }

@app.get('/api/life-domains/{domain_id}/topics')
def read_domain_topics(domain_id: str, db: Session = Depends(get_db)):
    from crud import get_topics
    topics = get_topics(db=db, life_domain_id=domain_id)
    return {
        'topics': [
            {
                'id': t.id,
                'name': t.name,
                'frequency': t.frequency,
                'created_at': t.created_at.isoformat() if t.created_at else None
            }
            for t in topics
        ],
        'count': len(topics)
    }

# --- RESEARCH NOTES ---
@app.post('/api/research/notes', response_model=ResearchNote)
def create_new_research_note(note: ResearchNoteCreate, db: Session = Depends(get_db)):
    db_note = create_research_note(db=db, note=note)
    store_embedding(
        'memories',
        str(db_note.id),
        note.content,
        {
            'type': 'research_note',
            'life_domain_id': str(note.life_domain_id) if note.life_domain_id else None,
            'topic': note.title
        }
    )
    return db_note

@app.get('/api/research/notes', response_model=List[ResearchNote])
def read_research_notes(life_domain_id: Optional[str] = None, db: Session = Depends(get_db)):
    return get_research_notes(db=db, life_domain_id=life_domain_id)

# --- DEADLINES ---
@app.post('/api/deadlines', response_model=Deadline)
def create_new_deadline(deadline: DeadlineCreate, db: Session = Depends(get_db)):
    return create_deadline(db=db, deadline=deadline)

@app.get('/api/deadlines', response_model=List[Deadline])
def read_deadlines(
    life_domain_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return get_deadlines(db=db, life_domain_id=life_domain_id, status=status)

# --- DAILY PLANS ---
@app.post('/api/plans', response_model=DailyPlan)
def create_new_daily_plan(plan: DailyPlanCreate, db: Session = Depends(get_db)):
    return create_daily_plan(db=db, plan=plan)

@app.get('/api/plans', response_model=List[DailyPlan])
def read_daily_plans(life_domain_id: Optional[str] = None, db: Session = Depends(get_db)):
    return get_daily_plans(db=db, life_domain_id=life_domain_id)

# --- CHAT ---
@app.post('/api/chat')
def chat(message: ChatMessage, db: Session = Depends(get_db)):
    user_message = message.message.lower().strip()
    current_domain = None
    if message.life_domain_id:
        current_domain = get_life_domain(db=db, domain_id=message.life_domain_id)
    
    # --- SUBSECTION CREATION ---
    if user_message.startswith('create subsection') or user_message.startswith('add subsection'):
        msg = message.message
        # Extract parent name and subsection name
        parent_name = None
        sub_name = None
        
        if ' called ' in msg.lower():
            parts = msg.split(' called ', 1)
            before = parts[0].lower().replace('create subsection', '').replace('add subsection', '').strip()
            sub_name = parts[1].strip()
        elif ' named ' in msg.lower():
            parts = msg.split(' named ', 1)
            before = parts[0].lower().replace('create subsection', '').replace('add subsection', '').strip()
            sub_name = parts[1].strip()
        else:
            return ChatResponse(response='To create a subsection, say: "Create subsection in [Domain] called [Name]"')
        
        # Remove leading "in" or "to" or "under"
        for prefix in ['in ', 'to ', 'under ', 'for ']:
            if before.startswith(prefix):
                before = before[len(prefix):].strip()
                break
        parent_name = before
        
        if not parent_name or not sub_name:
            return ChatResponse(response='To create a subsection, say: "Create subsection in [Domain] called [Name]"')
        
        parent = None
        for d in get_life_domains(db=db):
            if d.name.lower() == parent_name.lower():
                parent = d
                break
        
        if not parent:
            return ChatResponse(response=f'I could not find a domain called "{parent_name}".')
        
        subsection = create_life_domain(db=db, domain=LifeDomainCreate(
            name=f"{parent.name} / {sub_name}",
            description=f'Subsection of {parent.name}',
            parent_id=parent.id
        ))
        return ChatResponse(response=f'Created subsection "{sub_name}" in {parent.name}.')
    
    # --- DOMAIN DELETION ---
    if user_message.startswith('delete domain') or user_message.startswith('remove domain'):
        domain_name = message.message.split('domain', 1)[1].strip()
        target = None
        for d in get_life_domains(db=db):
            if d.name.lower() == domain_name.lower():
                target = d
                break
        if not target:
            return ChatResponse(response=f'I could not find a domain called "{domain_name}".')
        delete_life_domain(db=db, domain_id=target.id)
        return ChatResponse(response=f'Deleted domain "{target.name}".')
    
    # --- DOMAIN RENAME ---
    if user_message.startswith('rename'):
        full_msg = message.message
        lower_msg = full_msg.lower()
        idx = lower_msg.find(' to ')
        if idx == -1:
            return ChatResponse(response='To rename, say: "Rename [Old Name] to [New Name]"')
        old_name = full_msg[6:idx].strip()  # Remove "rename " prefix
        new_name = full_msg[idx + 4:].strip()  # Preserve original case
        target = None
        for d in get_life_domains(db=db):
            if d.name.lower() == old_name.lower():
                target = d
                break
        if not target:
            return ChatResponse(response=f'I could not find a domain called "{old_name}".')
        update_life_domain(db=db, domain_id=target.id, updates={'name': new_name})
        return ChatResponse(response=f'Renamed "{target.name}" to "{new_name}".')
    
    # --- 'BRING ME BACK' ---
    if 'bring me back' in user_message or 'where was i' in user_message:
        found_domain = None
        for domain in get_life_domains(db=db):
            if domain.name.lower() in user_message:
                found_domain = domain
                break
        
        if found_domain:
            memories = retrieve_memories(
                f'latest context for {found_domain.name}',
                life_domain_id=found_domain.id,
                n_results=5
            )
        else:
            memories = retrieve_memories(user_message, n_results=5)
        
        context = '\n\n'.join([m['content'] for m in memories[:3]])
        
        return ChatResponse(
            response=f'Here is what I remember about this:\n\n{context}\n\n[AI synthesis coming in Phase 4 - for now, this is raw retrieval]',
            retrieved_memories=[RetrievedMemory(**m) for m in memories]
        )
    
    # --- RETRIEVAL QUERIES ---
    # Normalize common abbreviations and variations
    query_text = user_message.replace('abt', 'about').replace('wat', 'what').replace('do u', 'do you')
    
    is_retrieval = (
        'what do i know' in query_text or 
        'what do we know' in query_text or
        'tell me about' in query_text or
        'tell me abt' in query_text or
        query_text.startswith('what is') or
        query_text.startswith('who is') or
        query_text.startswith('explain') or
        query_text.startswith('describe') or
        'find' in query_text or
        'info on' in query_text or
        'information about' in query_text
    )
    
    if is_retrieval:
        # Extract topic by removing query prefixes
        topic = query_text
        for prefix in [
            'what do i know about', 'what do we know about', 
            'tell me about', 'tell me abt',
            'what is', 'who is', 'explain', 'describe',
            'find', 'info on', 'information about'
        ]:
            topic = topic.replace(prefix, '')
        topic = topic.strip('?. ')
        
        # --- SMART DOMAIN DETECTION ---
        # Check if the query is asking about a specific life domain by name
        matched_domain = None
        all_domains = get_life_domains(db=db)
        for d in all_domains:
            if d.name.lower() == topic.lower() or d.name.lower() in topic.lower():
                matched_domain = d
                break
        
        if matched_domain and matched_domain.profile:
            # Gather context for LLM
            recent_docs = get_documents(db=db, life_domain_id=matched_domain.id)[:3]
            domain_topics = get_topics(db=db, life_domain_id=matched_domain.id)[:8]
            
            context_data = {
                'domain_name': matched_domain.name,
                'domain_profile': matched_domain.profile,
                'layer': matched_domain.layer,
                'topics': [t.name for t in domain_topics],
                'documents': [d.filename for d in recent_docs]
            }
            
            # Generate human-like response
            llm_response = generate_response(
                user_message,
                context_data=context_data
            )
            
            return ChatResponse(
                response=llm_response,
                retrieved_memories=[]
            )
        
        # Fallback to vector search for general queries
        if current_domain:
            memories = retrieve_memories(topic, life_domain_id=current_domain.id, n_results=10)
        else:
            memories = retrieve_memories(topic, n_results=10)
        
        if memories:
            # Try LLM synthesis of retrieved memories
            context_data = {
                'domain_name': current_domain.name if current_domain else None,
                'retrieved_memories': memories[:5]
            }
            llm_response = generate_response(
                user_message,
                context_data=context_data
            )
            
            return ChatResponse(
                response=llm_response,
                retrieved_memories=[RetrievedMemory(**m) for m in memories]
            )
        else:
            return ChatResponse(
                response=f'I do not have any information about "{topic}" in my memory yet.',
                retrieved_memories=[]
            )
    
    # --- STORE THOUGHT IN CURRENT DOMAIN (skip if it's a command/query) ---
    is_command = (
        user_message.startswith('create') or 
        user_message.startswith('add') or 
        user_message.startswith('delete') or 
        user_message.startswith('remove') or
        user_message.startswith('rename') or
        'bring me back' in user_message or
        is_retrieval
    )
    
    if current_domain and not is_command:
        db_thought = create_thought(db=db, thought=ThoughtCreate(
            life_domain_id=current_domain.id,
            content=message.message,
            source='user_chat'
        ))
        store_embedding(
            'memories',
            str(db_thought.id),
            message.message,
            {
                'type': 'thought',
                'life_domain_id': current_domain.id,
                'source': 'user_chat'
            }
        )
    elif not is_command:
        # Store in general memory even without a domain
        store_embedding(
            'memories',
            str(uuid.uuid4()),
            message.message,
            {
                'type': 'thought',
                'source': 'user_chat'
            }
        )
    
    # --- DEFAULT: GENERATE LLM RESPONSE ---
    context_data = {}
    if current_domain:
        context_data['domain_name'] = current_domain.name
        context_data['domain_profile'] = current_domain.profile
        context_data['layer'] = current_domain.layer
    
    llm_response = generate_response(
        message.message,
        context_data=context_data
    )
    
    return ChatResponse(
        response=llm_response,
        retrieved_memories=[]
    )

# --- RETRIEVAL ENDPOINT ---
@app.post('/api/retrieve')
def retrieve(request: RetrieveRequest):
    memories = retrieve_memories(
        request.query,
        life_domain_id=request.life_domain_id,
        n_results=request.n_results or 5
    )
    return {
        'memories': memories,
        'count': len(memories)
    }

# --- LAYER-BASED CHAT ---
from crud import create_chat_message, get_chat_messages_by_layer

@app.post('/api/chat/layer', response_model=ChatResponse)
def chat_layer(message: ChatMessage, db: Session = Depends(get_db)):
    """
    Layer-based chat: general, life, project, knowledge, system.
    Messages are stored with layer context and auto-saved as thoughts.
    """
    layer = message.layer or 'general'
    user_message = message.message
    
    # Store the user message in chat history
    create_chat_message(db=db, layer=layer, role='user', content=user_message)
    
    # Get recent conversation history for context
    recent_messages = get_chat_messages_by_layer(db=db, layer=layer, limit=10)
    conversation_context = '\n'.join([
        f"{m.role}: {m.content}" for m in recent_messages[-5:]
    ])
    conversation_length = len(recent_messages)  # 1 = just the user's current message was stored
    
    # --- STORE/CLASSIFY COMMAND ---
    store_keywords = ['store this', 'classify this', 'save this', 'store it', 'classify it', 'save it']
    is_store_command = any(kw in user_message.lower() for kw in store_keywords)
    
    if is_store_command:
        # Get the most recent non-command user messages to store
        recent_user_msgs = [m for m in recent_messages if m.role == 'user' and not any(kw in m.content.lower() for kw in store_keywords)]
        if recent_user_msgs:
            content_to_store = recent_user_msgs[-1].content
        else:
            content_to_store = user_message
        
        # Get all domains
        all_domains = get_life_domains(db=db, limit=1000)
        
        # Try semantic classification
        matched_domain = None
        try:
            from services.classifier_service import classify_document
            classification = classify_document(content_to_store, all_domains)
            if classification and classification.get('matched_domain_id'):
                for d in all_domains:
                    if d.id == classification['matched_domain_id']:
                        matched_domain = d
                        break
        except Exception as e:
            print(f"Store classification error: {e}")
        
        # Fallback: keyword matching
        if not matched_domain:
            for d in all_domains:
                if d.name.lower() in content_to_store.lower():
                    matched_domain = d
                    break
        
        if matched_domain:
            create_thought(db=db, thought=ThoughtCreate(
                life_domain_id=matched_domain.id,
                content=content_to_store,
                source=f'{layer}_chat_stored'
            ))
            response = f"Done! I've stored that under **{matched_domain.name}** ({matched_domain.layer})."
        else:
            general_domain = next((d for d in all_domains if d.layer == 'knowledge'), None)
            if general_domain:
                create_thought(db=db, thought=ThoughtCreate(
                    life_domain_id=general_domain.id,
                    content=content_to_store,
                    source=f'{layer}_chat_unclassified'
                ))
                response = f"Stored under **{general_domain.name}** — I wasn't sure which domain, so I put it here."
            else:
                response = "I couldn't find a domain to store this in. Tell me which domain it belongs to?"
        
        create_chat_message(db=db, layer=layer, role='assistant', content=response)
        return ChatResponse(response=response, retrieved_memories=[])
    
    # --- LAYER-SPECIFIC RESPONSE LOGIC ---
    
    if layer == 'general':
        # General chat: can talk about anything, retrieve from all domains
        response = generate_response(
            user_message,
            context_data={'conversation': conversation_context, 'conversation_length': conversation_length}
        )
        
    elif layer == 'life':
        # Life layer: focus on personal domains (Self, Career, Finance, etc.)
        life_domains = get_life_domains(db=db, layer='life')
        context = {
            'layer': 'life',
            'domains': [d.name for d in life_domains],
            'conversation': conversation_context,
            'conversation_length': conversation_length
        }
        response = generate_response(
            f"[Life Context] {user_message}",
            context_data=context
        )
        
    elif layer == 'project':
        # Project layer: focus on active projects
        project_domains = get_life_domains(db=db, layer='project')
        
        # Try to match a specific project name
        matched_project = None
        for d in project_domains:
            if d.name.lower() in user_message.lower():
                matched_project = d
                break
        
        if matched_project:
            # Fetch the domain's overview document
            docs = get_domain_documents(db=db, life_domain_id=matched_project.id)
            overview = next((d for d in docs if d.document_type == 'overview'), None)
            document_content = overview.content if overview else ""
            
            context = {
                'domain_name': matched_project.name,
                'domain_profile': matched_project.profile or "",
                'domain_document': document_content,
                'layer': 'project',
                'conversation': conversation_context,
                'conversation_length': conversation_length
            }
        else:
            context = {
                'layer': 'project',
                'domains': [d.name for d in project_domains],
                'conversation': conversation_context,
                'conversation_length': conversation_length
            }
        
        response = generate_response(
            user_message,
            context_data=context
        )
        
    elif layer == 'knowledge':
        # Knowledge layer: focus on research and learning
        knowledge_domains = get_life_domains(db=db, layer='knowledge')
        context = {
            'layer': 'knowledge',
            'domains': [d.name for d in knowledge_domains],
            'conversation': conversation_context,
            'conversation_length': conversation_length
        }
        response = generate_response(
            user_message,
            context_data=context
        )
        
    elif layer == 'system':
        # System layer: talk about how Sage works
        system_domains = get_life_domains(db=db, layer='system')
        context = {
            'layer': 'system',
            'domains': [d.name for d in system_domains],
            'conversation': conversation_context
        }
        response = generate_response(
            user_message,
            context_data=context
        )
    else:
        response = generate_response(user_message, context_data={'conversation': conversation_context})
    
    # Store assistant response in chat history
    create_chat_message(db=db, layer=layer, role='assistant', content=response)
    
    # --- AUTO-STORE as thought AND append to domain document ---
    all_domains = get_life_domains(db=db, limit=1000)
    
    # Try semantic classification first
    matched_domain = None
    try:
        from services.classifier_service import classify_document
        classification = classify_document(user_message, all_domains)
        if classification and classification.get('matched_domain_id'):
            for d in all_domains:
                if d.id == classification['matched_domain_id']:
                    matched_domain = d
                    break
    except Exception:
        pass
    
    # Fallback: keyword matching
    if not matched_domain:
        for d in all_domains:
            if d.name.lower() in user_message.lower():
                matched_domain = d
                break
    
    # If still no match, store in the current layer's catch-all
    if not matched_domain:
        if layer == 'life':
            matched_domain = next((d for d in all_domains if d.layer == 'life'), None)
        elif layer == 'project':
            matched_domain = next((d for d in all_domains if d.layer == 'project'), None)
        elif layer == 'knowledge':
            matched_domain = next((d for d in all_domains if d.layer == 'knowledge'), None)
        else:
            matched_domain = next((d for d in all_domains if d.layer == 'system'), None)
    
    if matched_domain:
        # 1. Store as thought (fast lookup)
        create_thought(db=db, thought=ThoughtCreate(
            life_domain_id=matched_domain.id,
            content=user_message,
            source=f'{layer}_chat_auto'
        ))
        
        # 2. Create or update domain document with proper title
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Detect content type for document naming
            content_lower = user_message.lower()
            doc_type = "notes"
            doc_title = f"{matched_domain.name} Notes"
            
            if any(k in content_lower for k in ['purpose', 'vision', 'mission', 'philosophy', 'core']):
                doc_type = "overview"
                doc_title = f"{matched_domain.name} Overview"
            elif any(k in content_lower for k in ['architecture', 'design', 'system', 'template', 'structure', 'framework']):
                doc_type = "architecture"
                doc_title = f"{matched_domain.name} Architecture"
            elif any(k in content_lower for k in ['decision', 'choose', 'chose', 'will use', 'going with']):
                doc_type = "decisions"
                doc_title = f"{matched_domain.name} Decisions"
            elif any(k in content_lower for k in ['insight', 'realization', 'discovered', 'learned that']):
                doc_type = "insights"
                doc_title = f"{matched_domain.name} Insights"
            elif any(k in content_lower for k in ['task', 'todo', 'action item', 'next step', 'should']):
                doc_type = "tasks"
                doc_title = f"{matched_domain.name} Tasks"
            
            # Get or create document with proper title
            doc = get_or_create_domain_document(
                db=db,
                life_domain_id=matched_domain.id,
                title=doc_title,
                document_type=doc_type
            )
            
            # Format entry with emoji
            icon_map = {
                'overview': '🎯', 'architecture': '🏗️', 'decisions': '⚖️',
                'insights': '💡', 'tasks': '✅', 'notes': '📝'
            }
            icon = icon_map.get(doc_type, '📝')
            new_entry = f"\n\n{icon} **{doc_type.upper()}** [{timestamp}]\n{user_message}\n\n---\n"
            
            # Build content
            current = doc.content or ""
            if not current.strip():
                current = f"# {matched_domain.name}\n\n> Knowledge document auto-updated from conversations.\n\n---\n\n"
            
            new_content = current + new_entry
            
            # Truncate if too long
            if len(new_content) > 15000:
                header_end = current.find('---\n\n') + 6
                header = current[:header_end]
                body = current[header_end:]
                truncated = body[-10000:]
                entry_start = truncated.find('\n' + icon)
                if entry_start > 0:
                    truncated = truncated[entry_start:]
                new_content = header + truncated + new_entry
            
            doc.content = new_content
            db.commit()
            db.refresh(doc)
        except Exception as e:
            print(f"Document update error: {e}")
    
    return ChatResponse(response=response, retrieved_memories=[])

def _format_document_entry(content, timestamp):
    """Format a chat entry into a structured document section."""
    
    # Detect content type and format accordingly
    content_lower = content.lower()
    
    # Check if it's a vision/mission statement
    if any(k in content_lower for k in ['purpose', 'vision', 'mission', 'philosophy', 'core']):
        return f"\n## 🎯 Vision Update [{timestamp}]\n\n{content}\n\n---\n"
    
    # Check if it's architecture/technical
    if any(k in content_lower for k in ['architecture', 'design', 'system', 'template', 'structure', 'framework']):
        return f"\n## 🏗️ Architecture [{timestamp}]\n\n{content}\n\n---\n"
    
    # Check if it's a decision
    if any(k in content_lower for k in ['decision', 'choose', 'chose', 'will use', 'going with']):
        return f"\n## ⚖️ Decision [{timestamp}]\n\n{content}\n\n---\n"
    
    # Check if it's an insight
    if any(k in content_lower for k in ['insight', 'realization', 'discovered', 'learned that']):
        return f"\n## 💡 Insight [{timestamp}]\n\n{content}\n\n---\n"
    
    # Check if it's a question
    if '?' in content and len(content) < 200:
        return f"\n## ❓ Question [{timestamp}]\n\n{content}\n\n---\n"
    
    # Check if it's tasks/action items
    if any(k in content_lower for k in ['task', 'todo', 'action item', 'next step', 'should']):
        return f"\n## ✅ Action Item [{timestamp}]\n\n{content}\n\n---\n"
    
    # Default: general note
    return f"\n## 📝 Note [{timestamp}]\n\n{content}\n\n---\n"

@app.get('/api/chat/layer/{layer}', response_model=List[ChatMessageHistory])
def get_layer_chat_history(layer: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get conversation history for a specific layer chat."""
    messages = get_chat_messages_by_layer(db=db, layer=layer, limit=limit)
    return [ChatMessageHistory.from_orm(m) for m in messages]

# --- USER ENDPOINTS ---

@app.get('/api/user')
def get_user(db: Session = Depends(get_db)):
    """Get or create the user profile."""
    user = get_or_create_user(db=db)
    return {'name': user.name, 'created_at': user.created_at}

@app.put('/api/user')
def update_user(name: str = Form(...), db: Session = Depends(get_db)):
    """Update the user's name."""
    user = update_user_name(db=db, name=name)
    return {'name': user.name, 'message': f'Updated name to {name}'}

@app.get('/api/greet')
def greet(db: Session = Depends(get_db)):
    """Generate a personalized greeting for the user."""
    user = get_or_create_user(db=db)
    hour = datetime.datetime.now().hour
    
    if 5 <= hour < 12:
        time_greeting = 'morning'
    elif 12 <= hour < 17:
        time_greeting = 'afternoon'
    elif 17 <= hour < 21:
        time_greeting = 'evening'
    else:
        time_greeting = 'night'
    
    # Use LLM if available, otherwise fallback
    if has_llm():
        prompt = f"""Say a brief, warm greeting to {user.name}. It's {time_greeting}.
        RULES:
        - Maximum 12 words
        - Casual and friendly, like texting a friend
        - Ask what they're working on
        - NO long intros, NO explaining who you are
        
        Examples of good length:
        "Hey Shubhi! What are we building today?"
        "Morning! What's on your mind?"
        "Evening, Shubhi. How was today?"
        """
        greeting = generate_response(prompt, context_data={})
    else:
        greetings = [
            f"Hey {user.name}! Good {time_greeting}. What are we building today?",
            f"Hi {user.name}! Ready for a productive {time_greeting}?",
            f"{user.name}! Good to see you. What's on your mind this {time_greeting}?",
            f"Hey there {user.name}! What shall we tackle today?"
        ]
        import random
        greeting = random.choice(greetings)
    
    return {'greeting': greeting, 'name': user.name, 'time_of_day': time_greeting}

# --- DOMAIN DOCUMENT ENDPOINTS ---

@app.get('/api/life-domains/{domain_id}/documents')
def list_domain_documents(domain_id: str, db: Session = Depends(get_db)):
    """Get all editable documents for a domain."""
    docs = get_domain_documents(db=db, life_domain_id=domain_id)
    # Return as plain dicts so FastAPI serializes them
    result = []
    for doc in docs:
        result.append({
            'id': doc.id,
            'life_domain_id': doc.life_domain_id,
            'title': doc.title,
            'content': doc.content,
            'document_type': doc.document_type,
            'version': doc.version,
            'created_at': doc.created_at.isoformat() if doc.created_at else None,
            'updated_at': doc.updated_at.isoformat() if doc.updated_at else None,
        })
    return result

@app.post('/api/life-domains/{domain_id}/documents')
def create_or_update_document(domain_id: str, title: str = Form(...), content: str = Form(""), doc_type: str = Form("overview"), db: Session = Depends(get_db)):
    """Create or update an editable document for a domain."""
    doc = get_or_create_domain_document(db=db, life_domain_id=domain_id, title=title, document_type=doc_type)
    if content:
        update_domain_document(db=db, document_id=doc.id, content=content)
    return {
        'id': doc.id,
        'life_domain_id': doc.life_domain_id,
        'title': doc.title,
        'content': doc.content,
        'document_type': doc.document_type,
        'version': doc.version,
        'created_at': doc.created_at.isoformat() if doc.created_at else None,
        'updated_at': doc.updated_at.isoformat() if doc.updated_at else None,
    }

@app.get('/api/domain-documents/{doc_id}')
def get_document_detail(doc_id: str, db: Session = Depends(get_db)):
    """Get a single document by ID."""
    from models import DomainDocument
    doc = db.query(DomainDocument).filter(DomainDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        'id': doc.id,
        'life_domain_id': doc.life_domain_id,
        'title': doc.title,
        'content': doc.content,
        'document_type': doc.document_type,
        'version': doc.version,
        'created_at': doc.created_at.isoformat() if doc.created_at else None,
        'updated_at': doc.updated_at.isoformat() if doc.updated_at else None,
    }

@app.put('/api/domain-documents/{doc_id}')
def patch_document(doc_id: str, content: str = Form(...), db: Session = Depends(get_db)):
    """Update document content."""
    doc = update_domain_document(db=db, document_id=doc_id, content=content)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {'id': doc.id, 'title': doc.title, 'version': doc.version, 'content_length': len(doc.content)}

# --- STATIC FILES (SERVE FRONTEND) ---
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')

if os.path.exists(FRONTEND_BUILD_DIR):
    app.mount('/assets', StaticFiles(directory=os.path.join(FRONTEND_BUILD_DIR, 'assets')), name='assets')

    @app.get('/')
    def serve_root():
        return FileResponse(os.path.join(FRONTEND_BUILD_DIR, 'index.html'))

    @app.get('/{path:path}')
    def serve_spa(path: str):
        if path.startswith('api/'):
            return {'detail': 'Not Found'}
        return FileResponse(os.path.join(FRONTEND_BUILD_DIR, 'index.html'))
