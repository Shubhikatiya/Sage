from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.orm import relationship
from database import Base
import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, default="Shubhi")
    email = Column(String, nullable=True)
    timezone = Column(String, default="Asia/Kolkata")
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class LifeDomain(Base):
    __tablename__ = "life_domains"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    layer = Column(String, default="life")  # life, project, knowledge, system
    status = Column(String, default="active")  # active, archived, dormant
    parent_id = Column(String, ForeignKey("life_domains.id"), nullable=True)
    profile = Column(Text, nullable=True)  # Synthesized understanding
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    thoughts = relationship("Thought", back_populates="life_domain", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="life_domain", cascade="all, delete-orphan")
    domain_documents = relationship("DomainDocument", back_populates="life_domain", cascade="all, delete-orphan")
    research_notes = relationship("ResearchNote", back_populates="life_domain", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="life_domain", cascade="all, delete-orphan")
    daily_plans = relationship("DailyPlan", back_populates="life_domain", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    layer = Column(String, nullable=False, default="general")  # general, life, project, knowledge, system
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    context_data = Column(JSON, nullable=True)  # domain name, profile, etc. used for the response
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Thought(Base):
    __tablename__ = "thoughts"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, default="user_chat")
    conversation_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain", back_populates="thoughts")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=False)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    file_type = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain", back_populates="documents")

class ResearchNote(Base):
    __tablename__ = "research_notes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    source_title = Column(String, nullable=True)
    source_author = Column(String, nullable=True)
    page_number = Column(String, nullable=True)
    url = Column(String, nullable=True)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain", back_populates="research_notes")

class Deadline(Base):
    __tablename__ = "deadlines"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False)
    status = Column(String, default="not_started")
    priority = Column(String, default="medium")
    reminder_days = Column(JSON, default=lambda: [7, 3, 1])
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain", back_populates="deadlines")

class DailyPlan(Base):
    __tablename__ = "daily_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    focus_areas = Column(JSON, default=list)
    tasks = Column(JSON, default=list)
    completed_tasks = Column(Integer, default=0)
    total_tasks = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain", back_populates="daily_plans")

class MemoryVector(Base):
    __tablename__ = "memory_vectors"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=True)
    source_type = Column(String, default="auto_extracted")  # auto_extracted, user_defined
    source_id = Column(String, nullable=True)  # ID of the document/note it came from
    frequency = Column(Integer, default=1)  # How many times this topic appeared
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain")

class DomainDocument(Base):
    __tablename__ = "domain_documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    life_domain_id = Column(String, ForeignKey("life_domains.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="")
    document_type = Column(String, default="overview")  # overview, notes, sources, timeline
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    life_domain = relationship("LifeDomain", back_populates="domain_documents")
