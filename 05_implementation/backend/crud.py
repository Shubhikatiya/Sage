from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import models, schemas

# --- LIFE DOMAINS ---

def create_life_domain(db: Session, domain: schemas.LifeDomainCreate):
    db_domain = models.LifeDomain(**domain.model_dump())
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    return db_domain

def get_life_domains(db: Session, layer: Optional[str] = None, skip: int = 0, limit: int = 1000):
    query = db.query(models.LifeDomain)
    if layer:
        query = query.filter(models.LifeDomain.layer == layer)
    return query.order_by(desc(models.LifeDomain.updated_at)).offset(skip).limit(limit).all()

def get_life_domain(db: Session, domain_id: str):
    return db.query(models.LifeDomain).filter(models.LifeDomain.id == domain_id).first()

def get_life_domain_by_name(db: Session, name: str):
    return db.query(models.LifeDomain).filter(models.LifeDomain.name == name).first()

def update_life_domain(db: Session, domain_id: str, updates: dict):
    db_domain = get_life_domain(db, domain_id)
    if not db_domain:
        return None
    for key, value in updates.items():
        if hasattr(db_domain, key):
            setattr(db_domain, key, value)
    db.commit()
    db.refresh(db_domain)
    return db_domain

def delete_life_domain(db: Session, domain_id: str):
    db_domain = get_life_domain(db, domain_id)
    if not db_domain:
        return False
    db.delete(db_domain)
    db.commit()
    return True

# --- THOUGHTS ---

def create_thought(db: Session, thought: schemas.ThoughtCreate):
    db_thought = models.Thought(**thought.model_dump())
    db.add(db_thought)
    db.commit()
    db.refresh(db_thought)
    return db_thought

def get_thoughts(db: Session, life_domain_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.Thought).filter(models.Thought.life_domain_id == life_domain_id).order_by(desc(models.Thought.created_at)).offset(skip).limit(limit).all()

# --- DOCUMENTS ---

def create_document(db: Session, document: schemas.DocumentCreate):
    db_document = models.Document(**document.model_dump())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def get_documents(db: Session, life_domain_id: str):
    return db.query(models.Document).filter(models.Document.life_domain_id == life_domain_id).all()

# --- RESEARCH NOTES ---

def create_research_note(db: Session, note: schemas.ResearchNoteCreate):
    db_note = models.ResearchNote(**note.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def get_research_notes(db: Session, life_domain_id: Optional[str] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.ResearchNote)
    if life_domain_id:
        query = query.filter(models.ResearchNote.life_domain_id == life_domain_id)
    return query.order_by(desc(models.ResearchNote.created_at)).offset(skip).limit(limit).all()

# --- DEADLINES ---

def create_deadline(db: Session, deadline: schemas.DeadlineCreate):
    db_deadline = models.Deadline(**deadline.model_dump())
    db.add(db_deadline)
    db.commit()
    db.refresh(db_deadline)
    return db_deadline

def get_deadlines(db: Session, life_domain_id: Optional[str] = None, status: Optional[str] = None):
    query = db.query(models.Deadline)
    if life_domain_id:
        query = query.filter(models.Deadline.life_domain_id == life_domain_id)
    if status:
        query = query.filter(models.Deadline.status == status)
    return query.order_by(models.Deadline.due_date).all()

# --- DAILY PLANS ---

def create_daily_plan(db: Session, plan: schemas.DailyPlanCreate):
    db_plan = models.DailyPlan(**plan.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

def get_daily_plans(db: Session, life_domain_id: Optional[str] = None):
    query = db.query(models.DailyPlan)
    if life_domain_id:
        query = query.filter(models.DailyPlan.life_domain_id == life_domain_id)
    return query.order_by(desc(models.DailyPlan.date)).all()

# --- MEMORY VECTORS ---

def create_memory_vector(db: Session, life_domain_id: str, content: str, embedding: list, source_type: str, source_id: str):
    db_vector = models.MemoryVector(
        life_domain_id=life_domain_id,
        content=content,
        embedding=embedding,
        source_type=source_type,
        source_id=source_id
    )
    db.add(db_vector)
    db.commit()
    db.refresh(db_vector)
    return db_vector

def get_memory_vectors(db: Session, life_domain_id: str, skip: int = 0, limit: int = 100):
    return db.query(models.MemoryVector).filter(models.MemoryVector.life_domain_id == life_domain_id).offset(skip).limit(limit).all()

# --- TOPICS ---

def create_or_update_topic(db: Session, topic_data: dict):
    """Create a new topic or update frequency if it already exists in the same domain."""
    existing = db.query(models.Topic).filter(
        models.Topic.name == topic_data['name'],
        models.Topic.life_domain_id == topic_data.get('life_domain_id')
    ).first()
    
    if existing:
        existing.frequency += topic_data.get('frequency', 1)
        existing.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        db_topic = models.Topic(
            name=topic_data['name'],
            description=topic_data.get('description'),
            life_domain_id=topic_data.get('life_domain_id'),
            source_type=topic_data.get('source_type', 'auto_extracted'),
            source_id=topic_data.get('source_id'),
            frequency=topic_data.get('frequency', 1),
            extra_data=topic_data.get('extra_data', {})
        )
        db.add(db_topic)
        db.commit()
        db.refresh(db_topic)
        return db_topic

def get_topics(db: Session, life_domain_id: str = None, skip: int = 0, limit: int = 100):
    query = db.query(models.Topic)
    if life_domain_id:
        query = query.filter(models.Topic.life_domain_id == life_domain_id)
    return query.order_by(models.Topic.frequency.desc()).offset(skip).limit(limit).all()

def get_topic_by_name(db: Session, name: str, life_domain_id: str = None):
    query = db.query(models.Topic).filter(models.Topic.name == name)
    if life_domain_id:
        query = query.filter(models.Topic.life_domain_id == life_domain_id)
    return query.first()

# --- CHAT MESSAGES ---

def create_chat_message(db: Session, layer: str, role: str, content: str, context_data: dict = None):
    db_msg = models.ChatMessage(
        layer=layer,
        role=role,
        content=content,
        context_data=context_data or {}
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_chat_messages_by_layer(db: Session, layer: str, limit: int = 50):
    return db.query(models.ChatMessage)\
        .filter(models.ChatMessage.layer == layer)\
        .order_by(models.ChatMessage.created_at)\
        .limit(limit)\
        .all()

# --- CHAT MESSAGES (Layer-based chat history) ---

def create_chat_message(db: Session, layer: str, role: str, content: str, context_data: dict = None):
    db_msg = models.ChatMessage(
        layer=layer,
        role=role,
        content=content,
        context_data=context_data or {}
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def get_chat_history(db: Session, layer: str, limit: int = 50):
    """Get recent chat history for a specific layer."""
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.layer == layer
    ).order_by(models.ChatMessage.created_at).limit(limit).all()

# --- USER ---

def get_or_create_user(db: Session, name: str = "Shubhi Katiyar"):
    user = db.query(models.User).first()
    if not user:
        user = models.User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def update_user_name(db: Session, name: str):
    user = db.query(models.User).first()
    if user:
        user.name = name
        db.commit()
        db.refresh(user)
    return user

# --- DOMAIN DOCUMENTS ---

def get_or_create_domain_document(db: Session, life_domain_id: str, title: str, document_type: str = "overview"):
    """Get existing or create new editable document for a domain."""
    doc = db.query(models.DomainDocument).filter(
        models.DomainDocument.life_domain_id == life_domain_id,
        models.DomainDocument.title == title
    ).first()
    if not doc:
        doc = models.DomainDocument(
            life_domain_id=life_domain_id,
            title=title,
            content="",
            document_type=document_type
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    return doc

def get_domain_documents(db: Session, life_domain_id: str):
    return db.query(models.DomainDocument).filter(
        models.DomainDocument.life_domain_id == life_domain_id
    ).order_by(desc(models.DomainDocument.updated_at)).all()

def update_domain_document(db: Session, document_id: str, content: str):
    doc = db.query(models.DomainDocument).filter(models.DomainDocument.id == document_id).first()
    if doc:
        doc.content = content
        doc.version += 1
        db.commit()
        db.refresh(doc)
    return doc
