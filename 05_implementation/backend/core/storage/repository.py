"""
Generic repository pattern for Sage v4.
Provides base CRUD operations with workspace filtering and soft delete support.
"""
from sqlalchemy.orm import Session
from typing import Type, List, Optional, Dict, Any

class Repository:
    """Base repository with workspace-aware CRUD."""
    
    def __init__(self, db: Session, model_class: Type, workspace_id: str):
        self.db = db
        self.model_class = model_class
        self.workspace_id = workspace_id
    
    def get_all(self, include_archived: bool = False) -> List[Any]:
        """Get all records for this workspace."""
        query = self.db.query(self.model_class).filter(
            self.model_class.workspace_id == self.workspace_id
        )
        if not include_archived:
            query = query.filter(self.model_class.is_archived == False)
        return query.all()
    
    def get_by_id(self, record_id: str, include_archived: bool = False) -> Optional[Any]:
        """Get a record by ID."""
        query = self.db.query(self.model_class).filter(
            self.model_class.id == record_id,
            self.model_class.workspace_id == self.workspace_id
        )
        if not include_archived:
            query = query.filter(self.model_class.is_archived == False)
        return query.first()
    
    def get_by_slug(self, slug: str, include_archived: bool = False) -> Optional[Any]:
        """Get a record by slug."""
        query = self.db.query(self.model_class).filter(
            self.model_class.slug == slug,
            self.model_class.workspace_id == self.workspace_id
        )
        if not include_archived:
            query = query.filter(self.model_class.is_archived == False)
        return query.first()
    
    def create(self, data: Dict[str, Any]) -> Any:
        """Create a new record."""
        data['workspace_id'] = self.workspace_id
        record = self.model_class(**data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Any]:
        """Update a record."""
        record = self.get_by_id(record_id)
        if not record:
            return None
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record
    
    def soft_delete(self, record_id: str, deleted_by: str = "system") -> bool:
        """Soft delete a record (sets deleted_at and is_archived)."""
        import datetime
        record = self.get_by_id(record_id)
        if not record:
            return False
        record.is_archived = True
        record.deleted_at = datetime.datetime.utcnow()
        record.deleted_by = deleted_by
        self.db.commit()
        return True
    
    def hard_delete(self, record_id: str) -> bool:
        """Permanently delete a record."""
        record = self.get_by_id(record_id, include_archived=True)
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True
    
    def restore(self, record_id: str) -> Optional[Any]:
        """Restore a soft-deleted record."""
        record = self.get_by_id(record_id, include_archived=True)
        if not record:
            return None
        record.is_archived = False
        record.deleted_at = None
        record.deleted_by = None
        self.db.commit()
        self.db.refresh(record)
        return record
