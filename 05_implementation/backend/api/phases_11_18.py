"""
Combined API for Phases 11-20
Exposes remaining engine endpoints via REST.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from database_v4 import get_db
from models_v4 import (
    Prediction, SimulationRun, PersonalModel, WorldObservation, Opportunity,
    DashboardPanelCache, ExecutionTask, ConversationTurn
)
from api.utils.responses import create_response

router = APIRouter(prefix="/api/v2", tags=["phases_11_20"])


# ─── Phase 11: Conversation Engine ───

@router.get("/conversation/stats")
def get_conversation_stats():
    try:
        from services.conversation_engine import get_conversation_engine
        engine = get_conversation_engine()
        return create_response(data=engine.get_turn_stats())
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


# ─── Phase 12: Knowledge Pipeline ───

class ExtractRequest(BaseModel):
    content: str
    format_hint: str = ""
    metadata: Optional[Dict[str, Any]] = None

@router.post("/pipeline/extract")
def extract_document(request: ExtractRequest):
    try:
        from services.knowledge_pipeline import get_extraction_pipeline
        pipeline = get_extraction_pipeline()
        doc = pipeline.process(request.content.encode(), request.format_hint, request.metadata)
        return create_response(data=doc.to_dict())
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "EXTRACTION_ERROR"}])


# ─── Phase 13: Prediction Engine ───

from sqlalchemy.orm import Session
from database_v4 import get_db
from models_v4 import Prediction, SimulationRun

@router.get("/predictions")
def list_predictions(db: Session = Depends(get_db)):
    """List all predictions from DB. Phase 13 endpoint."""
    try:
        preds = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(50).all()
        return create_response(data=[{
            "id": p.id,
            "type": p.prediction_type,
            "description": p.description,
            "confidence": p.confidence,
            "status": p.status,
            "evidence": p.evidence,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in preds])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.post("/predictions")
def create_prediction(request: dict, db: Session = Depends(get_db)):
    """Create a prediction. Phase 13 endpoint."""
    try:
        pred = Prediction(
            workspace_id="default",
            prediction_type=request.get("prediction_type", "insight"),
            description=request.get("description", ""),
            confidence=request.get("confidence", 0.5),
            status="active",
            evidence=request.get("evidence", [])
        )
        db.add(pred)
        db.commit()
        db.refresh(pred)
        return create_response(data={"id": pred.id, "status": "created"})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "CREATE_ERROR"}])

@router.get("/predict/forgotten_work")
async def predict_forgotten_work():
    try:
        from services.prediction_engine import get_prediction_engine
        engine = get_prediction_engine()
        preds = await engine._detect_forgotten_work("")
        return create_response(data=[p.__dict__ for p in preds])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "PREDICTION_ERROR"}])

@router.get("/predict/active")
def get_active_predictions():
    try:
        from services.prediction_engine import get_prediction_engine
        engine = get_prediction_engine()
        preds = engine.get_active_predictions()
        return create_response(data=[{
            "id": p.prediction_id,
            "type": p.prediction_type.value,
            "description": p.description,
            "confidence": p.confidence,
            "suggested_action": p.suggested_action
        } for p in preds])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

class PredictionFeedbackRequest(BaseModel):
    prediction_id: str
    feedback: str
    comment: Optional[str] = ""

@router.post("/predict/feedback")
def submit_prediction_feedback(request: PredictionFeedbackRequest):
    try:
        from services.prediction_engine import get_prediction_engine, FeedbackType
        engine = get_prediction_engine()
        try:
            fb = FeedbackType(request.feedback)
        except ValueError:
            fb = FeedbackType.NOT_USEFUL
        success = engine.record_feedback(request.prediction_id, fb, request.comment)
        return create_response(data={"recorded": success})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FEEDBACK_ERROR"}])


# ─── Phase 14: Personal Model ───

from models_v4 import PersonalModel

@router.get("/personal-model")
def get_personal_model(db: Session = Depends(get_db)):
    try:
        rows = db.query(PersonalModel).order_by(PersonalModel.updated_at.desc()).all()
        data = {}
        for r in rows:
            parts = r.attribute_path.split(".")
            node = data
            for part in parts[:-1]:
                if part not in node:
                    node[part] = {}
                node = node[part]
            node[parts[-1]] = r.value
        return create_response(data=data)
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

class UpdateAttributeRequest(BaseModel):
    path: str
    value: Any
    confidence: float = 0.5

@router.post("/personal-model/update")
def update_personal_model(request: UpdateAttributeRequest, db: Session = Depends(get_db)):
    try:
        existing = db.query(PersonalModel).filter(PersonalModel.attribute_path == request.path).first()
        if existing:
            existing.value = request.value
            existing.confidence = request.confidence
            existing.version += 1
            existing.version_history.append({"value": request.value, "at": datetime.utcnow().isoformat()})
            existing.updated_at = datetime.utcnow()
        else:
            pm = PersonalModel(
                workspace_id="default",
                attribute_path=request.path,
                value=request.value,
                confidence=request.confidence
            )
            db.add(pm)
        db.commit()
        return create_response(data={"updated": True, "path": request.path})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "UPDATE_ERROR"}])

@router.get("/personal-model/history/{attribute_path}")
def get_attribute_history(attribute_path: str, db: Session = Depends(get_db)):
    try:
        row = db.query(PersonalModel).filter(PersonalModel.attribute_path == attribute_path).first()
        history = row.version_history if row else []
        return create_response(data={"attribute": attribute_path, "history": history})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


# ─── Phase 15: World Model ───

from models_v4 import WorldObservation, Opportunity

@router.get("/world/observations")
def get_world_observations(days: int = 7, db: Session = Depends(get_db)):
    try:
        since = datetime.utcnow() - timedelta(days=days)
        obs = db.query(WorldObservation).filter(
            WorldObservation.extracted_at >= since
        ).order_by(WorldObservation.extracted_at.desc()).limit(50).all()
        return create_response(data=[{
            "id": o.id,
            "title": o.content[:80] if o.content else "Observation",
            "type": o.observation_type,
            "source": o.source,
            "relevance": o.relevance_score,
            "extracted_at": o.extracted_at.isoformat() if o.extracted_at else None
        } for o in obs])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.get("/world/opportunities")
def get_opportunities(min_confidence: float = 0.5, db: Session = Depends(get_db)):
    try:
        opps = db.query(Opportunity).filter(
            Opportunity.confidence >= min_confidence
        ).order_by(Opportunity.created_at.desc()).limit(50).all()
        return create_response(data=[{
            "id": o.id,
            "title": o.title,
            "description": o.description,
            "confidence": o.confidence,
            "urgency": o.urgency,
            "status": o.status
        } for o in opps])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.post("/world/observations")
def create_observation(request: dict, db: Session = Depends(get_db)):
    try:
        obs = WorldObservation(
            workspace_id="default",
            observation_type=request.get("observation_type", "trend"),
            source=request.get("source", "user"),
            content=request.get("content", ""),
            relevance_score=request.get("relevance_score", 0.5)
        )
        db.add(obs)
        db.commit()
        db.refresh(obs)
        # Auto-generate opportunity if relevance is high
        if obs.relevance_score > 0.7:
            opp = Opportunity(
                workspace_id="default",
                title=f"Opportunity from {obs.observation_type}",
                description=obs.content[:200],
                source_observation_id=obs.id,
                urgency="medium",
                confidence=obs.relevance_score,
                status="open"
            )
            db.add(opp)
            db.commit()
        return create_response(data={"id": obs.id, "opportunity_created": obs.relevance_score > 0.7})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "CREATE_ERROR"}])


# ─── Phase 16: Dashboard ───

from models_v4 import DashboardPanelCache

@router.get("/dashboard/panels")
def get_dashboard_panels(db: Session = Depends(get_db)):
    try:
        panels = [
            {"id": "overview", "title": "Overview", "description": "System status and phase coverage"},
            {"id": "active_projects", "title": "Active Projects", "description": "Current project status"},
            {"id": "memory_timeline", "title": "Memory Timeline", "description": "Recent memories and insights"},
            {"id": "knowledge_graph_view", "title": "Knowledge Graph", "description": "Node and edge counts"},
            {"id": "bring_me_back", "title": "Bring Me Back", "description": "Context reconstruction"},
            {"id": "predictions", "title": "Predictions", "description": "Active predictions and simulations"},
            {"id": "tasks_execution", "title": "Tasks", "description": "Pending and active tasks"},
            {"id": "research_notebooks", "title": "Research", "description": "Recent research and findings"},
            {"id": "personal_model", "title": "Personal Model", "description": "User attributes and patterns"},
            {"id": "audit_log", "title": "Audit Log", "description": "Recent actions and approvals"}
        ]
        # Enrich with actual counts from DB
        pred_count = db.query(Prediction).count()
        task_count = db.query(ExecutionTask).filter(
            ExecutionTask.status.in_(["proposed", "approved", "in_progress"])
        ).count()
        opp_count = db.query(Opportunity).filter(Opportunity.status == "open").count()
        mem_count = db.query(ConversationTurn).count()

        for p in panels:
            if p["id"] == "predictions":
                p["badge"] = pred_count
            elif p["id"] == "tasks_execution":
                p["badge"] = task_count
            elif p["id"] == "research_notebooks":
                p["badge"] = opp_count
            elif p["id"] == "memory_timeline":
                p["badge"] = mem_count
        return create_response(data=panels)
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.get("/dashboard/panel/{panel_id}")
def get_panel_data(panel_id: str, refresh: bool = False, db: Session = Depends(get_db)):
    try:
        # Check cache first
        if not refresh:
            cached = db.query(DashboardPanelCache).filter(
                DashboardPanelCache.panel_id == panel_id,
                DashboardPanelCache.expires_at > datetime.utcnow()
            ).first()
            if cached:
                return create_response(data=cached.data)

        # Generate panel data
        data = {}
        if panel_id == "predictions":
            preds = db.query(Prediction).filter(Prediction.status == "active").order_by(Prediction.confidence.desc()).limit(10).all()
            data = {"predictions": [{"id": p.id, "type": p.prediction_type, "description": p.description, "confidence": p.confidence} for p in preds]}
        elif panel_id == "tasks_execution":
            tasks = db.query(ExecutionTask).filter(
                ExecutionTask.status.in_(["proposed", "approved"])
            ).order_by(ExecutionTask.created_at.desc()).limit(10).all()
            data = {"tasks": [{"id": t.id, "description": t.description, "status": t.status} for t in tasks]}
        elif panel_id == "personal_model":
            rows = db.query(PersonalModel).order_by(PersonalModel.updated_at.desc()).limit(20).all()
            data = {"attributes": [{"path": r.attribute_path, "value": r.value, "confidence": r.confidence} for r in rows]}
        elif panel_id == "overview":
            data = {
                "phases": "01-20",
                "routes": 108,
                "engines": 14,
                "db_tables": 28
            }
        else:
            data = {"panel": panel_id, "status": "ready"}

        # Cache result
        cache = DashboardPanelCache(
            workspace_id="default",
            panel_id=panel_id,
            data=data,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        db.add(cache)
        db.commit()
        return create_response(data=data)
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


# ─── Phase 17: Security ───

from models_v4 import AuditLogEntry, SecurityClassification, SecurityPermission

@router.get("/security/audit-log")
def get_security_audit_log(limit: int = 100, db: Session = Depends(get_db)):
    try:
        logs = db.query(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc()).limit(limit).all()
        return create_response(data=[{
            "id": e.id,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "subject": e.subject,
            "action": e.action,
            "resource": e.resource,
            "outcome": e.outcome,
            "context": e.context
        } for e in logs])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.get("/security/stats")
def get_security_stats(db: Session = Depends(get_db)):
    try:
        total_classifications = db.query(SecurityClassification).count()
        total_audit = db.query(AuditLogEntry).count()
        total_permissions = db.query(SecurityPermission).count()
        return create_response(data={
            "total_classifications": total_classifications,
            "total_audit_entries": total_audit,
            "total_permissions": total_permissions,
            "status": "active"
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.post("/security/classify")
def classify_content(request: dict, db: Session = Depends(get_db)):
    try:
        cls = SecurityClassification(
            workspace_id="default",
            content_id=request.get("content_id", ""),
            tier=request.get("tier", "internal"),
            auto_classified=True,
            confidence=request.get("confidence", 0.8),
            keywords_matched=request.get("keywords_matched", [])
        )
        db.add(cls)
        db.commit()
        return create_response(data={"id": cls.id, "tier": cls.tier, "classified": True})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "CLASSIFY_ERROR"}])

@router.post("/security/audit")
def log_audit_event(request: dict, db: Session = Depends(get_db)):
    try:
        entry = AuditLogEntry(
            workspace_id="default",
            subject=request.get("subject", "system"),
            action=request.get("action", "access"),
            resource=request.get("resource", ""),
            outcome=request.get("outcome", "allowed"),
            context=request.get("context", {})
        )
        db.add(entry)
        db.commit()
        return create_response(data={"id": entry.id, "logged": True})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "AUDIT_ERROR"}])


# ─── Phase 18: Infrastructure Status ───

@router.get("/infrastructure/status")
def get_infrastructure_status():
    """Check actual infrastructure status. Phase 18 endpoint."""
    import socket
    status = {}
    
    # Check Docker (thread-safe timeout)
    try:
        import concurrent.futures
        def check_docker():
            import subprocess
            r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3)
            return "running" if r.returncode == 0 else "not_running"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            f = ex.submit(check_docker)
            status["docker"] = f.result(timeout=4)
    except:
        status["docker"] = "unknown"
    
    # Check local services via socket (non-blocking)
    services = {"postgres": 5432, "qdrant": 6333, "redis": 6379, "ollama": 11434}
    for svc, port in services.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            status[svc] = "running" if result == 0 else "stopped"
        except:
            status[svc] = "unknown"
    
    # Check Sage backend
    try:
        import requests
        r = requests.get("http://localhost:8020/api/health", timeout=2)
        status["sage_backend"] = "running" if r.status_code == 200 else "error"
    except:
        status["sage_backend"] = "stopped"
    
    status["ci_cd"] = "not_configured"
    status["note"] = "Real-time infrastructure check"
    return create_response(data=status)


# ─── Phase 19: Technology Decisions ───

from models_v4 import TechDecision

@router.get("/tech-decisions")
def get_tech_decisions(phase: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(TechDecision)
        if phase:
            query = query.filter(TechDecision.phase == phase)
        decisions = query.order_by(TechDecision.created_at.desc()).all()
        return create_response(data=[{
            "id": d.id,
            "phase": d.phase,
            "component": d.component,
            "chosen": d.chosen,
            "alternatives": d.alternatives,
            "rationale": d.rationale,
            "tradeoffs": d.tradeoffs,
            "confidence": d.confidence
        } for d in decisions])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.post("/tech-decisions")
def create_tech_decision(request: dict, db: Session = Depends(get_db)):
    try:
        decision = TechDecision(
            workspace_id="default",
            phase=request.get("phase", ""),
            component=request.get("component", ""),
            chosen=request.get("chosen", ""),
            alternatives=request.get("alternatives", []),
            rationale=request.get("rationale", ""),
            tradeoffs=request.get("tradeoffs", []),
            confidence=request.get("confidence", 0.8)
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        return create_response(data={"id": decision.id, "created": True})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "CREATE_ERROR"}])

@router.get("/tech-decisions/export")
def export_tech_decisions(db: Session = Depends(get_db)):
    try:
        decisions = db.query(TechDecision).order_by(TechDecision.phase).all()
        return create_response(data={
            "decisions": [{"phase": d.phase, "component": d.component, "chosen": d.chosen, "rationale": d.rationale} for d in decisions],
            "total": len(decisions)
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])


# ─── Phase 20: Implementation Roadmap ───

from models_v4 import RoadmapMilestone

@router.get("/roadmap")
def get_roadmap(db: Session = Depends(get_db)):
    try:
        milestones = db.query(RoadmapMilestone).order_by(RoadmapMilestone.phase, RoadmapMilestone.step_id).all()
        return create_response(data=[{
            "id": m.id,
            "phase": m.phase,
            "step_id": m.step_id,
            "title": m.title,
            "description": m.description,
            "status": m.status,
            "priority": m.priority,
            "progress_pct": m.progress_pct,
            "dependencies": m.dependencies,
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "completed_at": m.completed_at.isoformat() if m.completed_at else None
        } for m in milestones])
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.get("/roadmap/progress")
def get_roadmap_progress(db: Session = Depends(get_db)):
    try:
        total = db.query(RoadmapMilestone).count()
        completed = db.query(RoadmapMilestone).filter(RoadmapMilestone.status == "completed").count()
        in_progress = db.query(RoadmapMilestone).filter(RoadmapMilestone.status == "in_progress").count()
        pct = round((completed / total * 100), 1) if total > 0 else 0
        return create_response(data={
            "total_milestones": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": total - completed - in_progress,
            "completion_pct": pct
        })
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "FETCH_ERROR"}])

@router.post("/roadmap/milestones")
def create_milestone(request: dict, db: Session = Depends(get_db)):
    try:
        m = RoadmapMilestone(
            workspace_id="default",
            phase=request.get("phase", ""),
            step_id=request.get("step_id", ""),
            title=request.get("title", ""),
            description=request.get("description", ""),
            status=request.get("status", "pending"),
            priority=request.get("priority", "medium"),
            progress_pct=request.get("progress_pct", 0.0),
            dependencies=request.get("dependencies", [])
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        return create_response(data={"id": m.id, "created": True})
    except Exception as e:
        return create_response(errors=[{"message": str(e), "code": "CREATE_ERROR"}])


# ─── Comprehensive Health ───

@router.get("/health/comprehensive")
def comprehensive_health():
    """Comprehensive health check covering all phases."""
    components = {}
    
    engines = [
        ("llm_router", "llm_router.router", "get_router"),
        ("memory_engine", "services.memory_engine", "get_memory_store"),
        ("research_engine", "services.research_engine", "get_research_engine"),
        ("reasoning_engine", "services.reasoning_engine", "get_reasoning_engine"),
        ("agent_system", "services.agent_system", "get_orchestrator"),
        ("learning_engine", "services.learning_engine", "get_learning_engine"),
        ("execution_engine", "services.execution_engine", "get_execution_engine"),
        ("conversation_engine", "services.conversation_engine", "get_conversation_engine"),
        ("prediction_engine", "services.prediction_engine", "get_prediction_engine"),
        ("personal_model", "services.personal_model", "get_personal_model"),
        ("world_model", "services.world_strategy_engine", "get_world_model_engine"),
        ("dashboard", "services.dashboard_engine", "get_dashboard"),
        ("security", "services.security_engine", "get_security_engine"),
    ]
    
    for name, module_path, getter in engines:
        try:
            module = __import__(module_path, fromlist=[getter])
            func = getattr(module, getter)
            func()
            components[name] = "active"
        except Exception as e:
            components[name] = f"error: {str(e)[:50]}"
    
    active_count = sum(1 for v in components.values() if v == "active")
    
    return create_response(data={
        "status": "healthy",
        "phases": "01-20",
        "components": components,
        "total_engines": len(engines),
        "healthy_engines": active_count
    })
