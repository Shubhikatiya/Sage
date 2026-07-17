"""
Standardized API response envelope for Sage v4.
Every API response follows this structure.
"""
import time
from typing import Any, Dict, List, Optional

def create_response(
    data: Any = None,
    success: bool = True,
    errors: List[Dict] = None,
    warnings: List[str] = None,
    metadata: Dict = None
) -> Dict[str, Any]:
    """Create a standardized API response envelope.
    
    Args:
        data: The response payload
        success: Whether the operation succeeded
        errors: List of error objects
        warnings: List of warning messages
        metadata: Additional metadata about the request
    
    Returns:
        Standardized response dictionary
    """
    return {
        "success": success,
        "data": data,
        "metadata": {
            "execution_time_ms": metadata.get("execution_time_ms", 0) if metadata else 0,
            "workspace": metadata.get("workspace") if metadata else None,
            "version": metadata.get("version", "v4.0.0") if metadata else "v4.0.0",
            "warnings": warnings or [],
            "ai_generated": metadata.get("ai_generated", False) if metadata else False,
            **({k: v for k, v in metadata.items() if k not in ["execution_time_ms", "workspace", "version", "ai_generated"]} if metadata else {})
        },
        "errors": errors or []
    }

def create_error_response(
    message: str,
    code: str = "INTERNAL_ERROR",
    status_code: int = 500,
    details: Dict = None
) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        message: Human-readable error message
        code: Error code for programmatic handling
        status_code: HTTP status code
        details: Additional error details
    
    Returns:
        Standardized error response
    """
    return create_response(
        data=None,
        success=False,
        errors=[{
            "message": message,
            "code": code,
            "status_code": status_code,
            "details": details or {}
        }]
    )

def create_paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    per_page: int = 20,
    **kwargs
) -> Dict[str, Any]:
    """Create a paginated response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number (1-based)
        per_page: Items per page
        **kwargs: Additional response data
    
    Returns:
        Standardized paginated response
    """
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return create_response(
        data={
            "items": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            **kwargs
        }
    )

class APIResponse:
    """Context manager for tracking execution time and building responses."""
    
    def __init__(self, workspace_id: str = None):
        self.workspace_id = workspace_id
        self.start_time = None
        self.warnings = []
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def build(self, data: Any = None, success: bool = True, errors: List[Dict] = None) -> Dict[str, Any]:
        execution_time = int((time.time() - self.start_time) * 1000) if self.start_time else 0
        
        return create_response(
            data=data,
            success=success,
            errors=errors,
            warnings=self.warnings,
            metadata={
                "execution_time_ms": execution_time,
                "workspace": self.workspace_id,
                "version": "v4.0.0",
                "ai_generated": False
            }
        )
