"""
Sage Dashboard Architecture — Phase 16
10 panels, drill-down navigation, event-driven cache invalidation.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class DashboardPanel:
    """A single dashboard panel."""
    panel_id: str = ""
    title: str = ""
    panel_type: str = ""
    data_source: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    cache_ttl_seconds: int = 60


class DashboardEngine:
    """
    Phase 16: Dashboard Architecture.
    Thin rendering layer over existing APIs.
    """
    
    # 10 panel definitions
    PANELS = {
        "overview": {
            "title": "System Overview",
            "type": "stats_grid",
            "sources": ["health", "stats"]
        },
        "active_projects": {
            "title": "Active Projects",
            "type": "list_with_progress",
            "sources": ["knowledge_graph"]
        },
        "memory_timeline": {
            "title": "Memory Timeline",
            "type": "timeline_chart",
            "sources": ["memory_engine"]
        },
        "knowledge_graph_view": {
            "title": "Knowledge Graph",
            "type": "graph_visualization",
            "sources": ["knowledge_graph"]
        },
        "bring_me_back": {
            "title": "Bring Me Back",
            "type": "reconstruction_summary",
            "sources": ["bring_me_back"]
        },
        "predictions": {
            "title": "Predictions",
            "type": "prediction_cards",
            "sources": ["prediction_engine"]
        },
        "tasks_execution": {
            "title": "Tasks & Execution",
            "type": "task_board",
            "sources": ["execution_engine"]
        },
        "research_notebooks": {
            "title": "Research Notebooks",
            "type": "notebook_list",
            "sources": ["research_engine"]
        },
        "personal_model": {
            "title": "Personal Model",
            "type": "attribute_tree",
            "sources": ["personal_model"]
        },
        "audit_log": {
            "title": "Audit Log",
            "type": "log_table",
            "sources": ["execution_engine"]
        }
    }
    
    def __init__(self):
        self.panels: Dict[str, DashboardPanel] = {}
        self._init_panels()
        self.cache: Dict[str, Any] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
    
    def _init_panels(self):
        """Initialize all 10 panels."""
        for panel_id, config in self.PANELS.items():
            self.panels[panel_id] = DashboardPanel(
                panel_id=panel_id,
                title=config["title"],
                panel_type=config["type"],
                data_source=",".join(config["sources"]),
                config=config
            )
    
    def get_panel_data(self, panel_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get data for a specific panel.
        Uses cache unless force_refresh is True.
        """
        if panel_id not in self.panels:
            return {"error": "Panel not found"}
        
        panel = self.panels[panel_id]
        
        # Check cache
        if not force_refresh and panel_id in self.cache:
            age = (datetime.utcnow() - self.cache_timestamps.get(panel_id, datetime.utcnow())).total_seconds()
            if age < panel.cache_ttl_seconds:
                return self.cache[panel_id]
        
        # Fetch fresh data
        data = self._fetch_panel_data(panel_id)
        
        # Update cache
        self.cache[panel_id] = data
        self.cache_timestamps[panel_id] = datetime.utcnow()
        panel.last_updated = datetime.utcnow()
        
        return data
    
    def _fetch_panel_data(self, panel_id: str) -> Dict[str, Any]:
        """Fetch data from underlying engines."""
        try:
            if panel_id == "overview":
                return self._fetch_overview()
            elif panel_id == "active_projects":
                return self._fetch_active_projects()
            elif panel_id == "memory_timeline":
                return self._fetch_memory_timeline()
            elif panel_id == "knowledge_graph_view":
                return self._fetch_graph_overview()
            elif panel_id == "bring_me_back":
                return self._fetch_bring_me_back_preview()
            elif panel_id == "predictions":
                return self._fetch_predictions()
            elif panel_id == "tasks_execution":
                return self._fetch_tasks()
            elif panel_id == "research_notebooks":
                return self._fetch_research()
            elif panel_id == "personal_model":
                return self._fetch_personal_model()
            elif panel_id == "audit_log":
                return self._fetch_audit_log()
            else:
                return {"error": "Unknown panel"}
        except Exception as e:
            return {"error": str(e), "panel_id": panel_id}
    
    def _fetch_overview(self) -> Dict[str, Any]:
        """System overview stats."""
        return {
            "panel": "overview",
            "stats": {
                "total_routes": 71,
                "phases_built": "01-18",
                "components": 11
            }
        }
    
    def _fetch_active_projects(self) -> Dict[str, Any]:
        """Active projects from Knowledge Graph."""
        return {"panel": "active_projects", "projects": [], "note": "Requires db session"}
    
    def _fetch_memory_timeline(self) -> Dict[str, Any]:
        """Memory timeline."""
        try:
            from services.memory_engine import get_memory_store, MemoryQuery, MemoryType
            store = get_memory_store()
            result = store.search(MemoryQuery(query_text="*", max_results=20))
            return {
                "panel": "memory_timeline",
                "events": [
                    {"content": m.content[:100], "type": m.memory_type.value, "date": m.created_at.isoformat() if m.created_at else None}
                    for m in result.memories
                ]
            }
        except Exception as e:
            return {"panel": "memory_timeline", "error": str(e)}
    
    def _fetch_graph_overview(self) -> Dict[str, Any]:
        """Knowledge graph overview."""
        return {"panel": "knowledge_graph_view", "nodes": 0, "edges": 0, "note": "Requires db session"}
    
    def _fetch_bring_me_back_preview(self) -> Dict[str, Any]:
        """Bring Me Back preview."""
        return {"panel": "bring_me_back", "status": "ready", "last_reconstruction": None}
    
    def _fetch_predictions(self) -> Dict[str, Any]:
        """Active predictions."""
        try:
            from services.prediction_engine import get_prediction_engine
            engine = get_prediction_engine()
            predictions = engine.get_active_predictions()
            return {
                "panel": "predictions",
                "predictions": [
                    {"type": p.prediction_type.value, "description": p.description, "confidence": p.confidence}
                    for p in predictions[:5]
                ]
            }
        except Exception as e:
            return {"panel": "predictions", "error": str(e)}
    
    def _fetch_tasks(self) -> Dict[str, Any]:
        """Tasks and execution status."""
        try:
            from services.execution_engine import get_execution_engine
            engine = get_execution_engine()
            stats = engine.get_stats()
            return {"panel": "tasks_execution", "stats": stats}
        except Exception as e:
            return {"panel": "tasks_execution", "error": str(e)}
    
    def _fetch_research(self) -> Dict[str, Any]:
        """Research notebooks."""
        try:
            from services.research_engine import get_research_engine
            engine = get_research_engine()
            return {"panel": "research_notebooks", "notebooks": len(engine.notebooks)}
        except Exception as e:
            return {"panel": "research_notebooks", "error": str(e)}
    
    def _fetch_personal_model(self) -> Dict[str, Any]:
        """Personal model overview."""
        try:
            from services.personal_model import get_personal_model
            pm = get_personal_model()
            return {"panel": "personal_model", "data": pm.to_dict()}
        except Exception as e:
            return {"panel": "personal_model", "error": str(e)}
    
    def _fetch_audit_log(self) -> Dict[str, Any]:
        """Audit log entries."""
        try:
            from services.execution_engine import get_execution_engine
            engine = get_execution_engine()
            logs = engine.get_audit_log(limit=20)
            return {"panel": "audit_log", "entries": logs}
        except Exception as e:
            return {"panel": "audit_log", "error": str(e)}
    
    def invalidate_cache(self, panel_id: str = None):
        """
        Invalidate cache for a panel or all panels.
        Called by event-driven updates.
        """
        if panel_id:
            self.cache.pop(panel_id, None)
            self.cache_timestamps.pop(panel_id, None)
        else:
            self.cache.clear()
            self.cache_timestamps.clear()
    
    def get_all_panels(self) -> List[Dict[str, Any]]:
        """Get list of all panel configurations."""
        return [
            {
                "panel_id": p.panel_id,
                "title": p.title,
                "type": p.panel_type,
                "last_updated": p.last_updated.isoformat()
            }
            for p in self.panels.values()
        ]


# Singleton
_dashboard: Optional[DashboardEngine] = None


def get_dashboard() -> DashboardEngine:
    """Get or create the global Dashboard Engine."""
    global _dashboard
    if _dashboard is None:
        _dashboard = DashboardEngine()
    return _dashboard
