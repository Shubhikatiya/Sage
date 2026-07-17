from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class LifeDomainCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    layer: str = "life"  # life, project, knowledge, system
    parent_id: Optional[str] = None

class LifeDomain(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    layer: str
    status: str
    parent_id: Optional[str] = None
    profile: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ThoughtCreate(BaseModel):
    life_domain_id: str
    content: str
    source: str = "user_chat"
    conversation_id: Optional[str] = None

class Thought(BaseModel):
    id: str
    life_domain_id: str
    content: str
    source: str
    conversation_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentCreate(BaseModel):
    life_domain_id: str
    filename: str
    content: str
    file_path: Optional[str] = None
    file_type: str = "txt"

class Document(BaseModel):
    id: str
    life_domain_id: str
    filename: str
    content: str
    file_path: Optional[str] = None
    file_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResearchNoteCreate(BaseModel):
    life_domain_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    source: Optional[str] = None
    source_title: Optional[str] = None
    source_author: Optional[str] = None
    page_number: Optional[str] = None
    url: Optional[str] = None
    tags: List[str] = []

class ResearchNote(BaseModel):
    id: str
    life_domain_id: Optional[str] = None
    title: str
    content: str
    source: Optional[str] = None
    source_title: Optional[str] = None
    source_author: Optional[str] = None
    page_number: Optional[str] = None
    url: Optional[str] = None
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DeadlineCreate(BaseModel):
    life_domain_id: str
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    due_date: datetime
    priority: str = "medium"
    reminder_days: List[int] = [7, 3, 1]

class Deadline(BaseModel):
    id: str
    life_domain_id: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    status: str
    priority: str
    reminder_days: List[int]
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class DailyPlanCreate(BaseModel):
    life_domain_id: str
    date: datetime
    focus_areas: List[str] = []
    tasks: List[dict] = []
    notes: Optional[str] = None

class DailyPlan(BaseModel):
    id: str
    life_domain_id: str
    date: datetime
    focus_areas: List[str]
    tasks: List[dict]
    completed_tasks: int
    total_tasks: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    life_domain_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    layer: Optional[str] = "general"  # general, life, project, knowledge, system

class ChatMessageHistory(BaseModel):
    id: str
    layer: str
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class RetrievedMemory(BaseModel):
    id: Optional[str] = None
    content: str
    metadata: Optional[dict] = None
    distance: Optional[float] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None
    retrieved_memories: List[RetrievedMemory] = []

class RetrieveRequest(BaseModel):
    life_domain_id: Optional[str] = None
    query: str = Field(..., min_length=1)
    n_results: int = 5

class UserProfile(BaseModel):
    name: str = "Shubhi Katiyar"
    created_at: Optional[datetime] = None

class GreetingResponse(BaseModel):
    greeting: str

class DomainDocumentCreate(BaseModel):
    life_domain_id: str
    title: str
    content: str = ""
    document_type: str = "overview"

class DomainDocumentUpdate(BaseModel):
    content: str

class DomainDocument(BaseModel):
    id: str
    life_domain_id: str
    title: str
    content: str
    document_type: str
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
