"""
Sage v4 FastAPI Application.
Wires together the Capability Layer via REST API.
"""
import sys
import os

# Add sage paths for Phase 01 imports
SAGE_CORE = os.path.join(os.path.dirname(__file__), '..', '..', 'sage', 'core')
SAGE_SERVICES = os.path.join(os.path.dirname(__file__), '..', '..', 'sage', 'services')
if os.path.exists(SAGE_CORE) and SAGE_CORE not in sys.path:
    sys.path.insert(0, SAGE_CORE)
if os.path.exists(SAGE_SERVICES) and SAGE_SERVICES not in sys.path:
    sys.path.insert(0, SAGE_SERVICES)

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import time
import os

from database_v4 import init_db, get_db
from api import knowledge, graph, asset, reasoning, chat, memory, reasoning_v2, research, agents, learning, execute, phases_11_18, topology, graph_phase03, reasoning_v3, context, bring_me_back, phases_09_12
from api.utils.responses import create_error_response

app = FastAPI(
    title="Sage v4",
    description="Knowledge Graph Architecture for Chief of Staff AI",
    version="4.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files (catch-all for non-API routes)
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(frontend_dist):
    from fastapi.staticfiles import StaticFiles
    # Mount static assets directory
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
else:
    print(f"WARNING: Frontend dist not found at {frontend_dist}")

# Request timing middleware
@app.middleware("http")
async def add_execution_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    execution_time = int((time.time() - start_time) * 1000)
    response.headers["X-Execution-Time-Ms"] = str(execution_time)
    return response

# Error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "metadata": {
                "execution_time_ms": 0,
                "version": "v4.0.0",
                "warnings": [],
                "ai_generated": False
            },
            "errors": [{
                "message": str(exc),
                "code": "INTERNAL_ERROR",
                "status_code": 500
            }]
        }
    )

# Include routers
app.include_router(knowledge.router)
app.include_router(graph.router)
app.include_router(asset.router)
app.include_router(reasoning.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(reasoning_v2.router)
app.include_router(research.router)
app.include_router(agents.router)
app.include_router(learning.router)
app.include_router(execute.router)
app.include_router(phases_11_18.router)
app.include_router(topology.router)
app.include_router(graph_phase03.router)
app.include_router(reasoning_v3.router)
app.include_router(context.router)
app.include_router(bring_me_back.router)
app.include_router(phases_09_12.router)

@app.on_event("startup")
def startup_event():
    """Initialize database and workspace session on startup."""
    init_db()
    
    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    
    # Initialize workspace session if needed
    from database_v4 import SessionLocal
    from models_v4 import Workspace
    from services.workspace_session import WorkspaceSessionManager
    
    db = SessionLocal()
    try:
        ws = db.query(Workspace).first()
        if ws:
            session_mgr = WorkspaceSessionManager(db, ws.id)
            session = session_mgr.get_current_session()
            print(f"Workspace session initialized: {session['id']}")
    except Exception as e:
        print(f"Session init warning: {e}")
    finally:
        db.close()

@app.get("/api/health")
def health_check():
    """Health check endpoint with full Phase 01-18 status."""
    components = {}
    
    # Phase 01: Foundation
    try:
        from llm_router.router import get_router
        router = get_router()
        components["llm_router"] = router.get_stats()
    except Exception as e:
        components["llm_router"] = {"error": str(e)[:50]}
    
    try:
        from event_bus.bus import get_bus
        bus = get_bus()
        components["event_bus"] = "initialized"
    except Exception as e:
        components["event_bus"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 02: Memory Engine
    try:
        from services.memory_engine import get_memory_store
        mem = get_memory_store()
        components["memory_engine"] = "active"
    except Exception as e:
        components["memory_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 07: Research Engine
    try:
        from services.research_engine import get_research_engine
        research = get_research_engine()
        components["research_engine"] = "active"
    except Exception as e:
        components["research_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 08: Multi-Agent System
    try:
        from services.agent_system import get_orchestrator
        agents = get_orchestrator()
        components["agent_system"] = f"{len(agents.registry.list_agents())} agents"
    except Exception as e:
        components["agent_system"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 09: Learning Engine
    try:
        from services.learning_engine import get_learning_engine
        learning = get_learning_engine()
        components["learning_engine"] = "active"
    except Exception as e:
        components["learning_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 10: Execution Engine
    try:
        from services.execution_engine import get_execution_engine
        exec_engine = get_execution_engine()
        components["execution_engine"] = "active"
    except Exception as e:
        components["execution_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 11: Conversation Engine
    try:
        from services.conversation_engine import get_conversation_engine
        ce = get_conversation_engine()
        components["conversation_engine"] = "active"
    except Exception as e:
        components["conversation_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 12: Knowledge Pipeline
    try:
        from services.knowledge_pipeline import get_extraction_pipeline
        pipeline = get_extraction_pipeline()
        components["knowledge_pipeline"] = "active"
    except Exception as e:
        components["knowledge_pipeline"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 13: Prediction Engine
    try:
        from services.prediction_engine import get_prediction_engine
        pred = get_prediction_engine()
        components["prediction_engine"] = "active"
    except Exception as e:
        components["prediction_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 14: Personal Model
    try:
        from services.personal_model import get_personal_model
        pm = get_personal_model()
        components["personal_model"] = "active"
    except Exception as e:
        components["personal_model"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 15: World Model
    try:
        from services.world_strategy_engine import get_world_model_engine
        wm = get_world_model_engine()
        components["world_model"] = "active"
    except Exception as e:
        components["world_model"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 16: Dashboard
    try:
        from services.dashboard_engine import get_dashboard
        dash = get_dashboard()
        components["dashboard_engine"] = "active"
    except Exception as e:
        components["dashboard_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 17: Security
    try:
        from services.security_engine import get_security_engine
        sec = get_security_engine()
        components["security_engine"] = "active"
    except Exception as e:
        components["security_engine"] = f"not_ready: {str(e)[:50]}"
    
    # Phase 18: Infrastructure
    components["infrastructure"] = "Docker Compose configured (see sage/infra/docker)"
    
    active_count = sum(1 for v in components.values() if isinstance(v, str) and "active" in v)
    
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "v4.0.0",
            "phases_built": "01-18",
            "components": components,
            "infrastructure": {
                "database": "sqlite",
                "vector_store": "chromadb",
                "graph_store": "sqlalchemy"
            }
        },
        "metadata": {"version": "v4.0.0", "phases": "01-18", "active_engines": active_count},
        "errors": []
    }

@app.get("/api/workspace/sidebar")
def get_sidebar(db = Depends(get_db)):
    """Get sidebar tree for the workspace."""
    from models_v4 import Workspace, KnowledgeNode, NodeType
    
    ws = db.query(Workspace).first()
    if not ws:
        return JSONResponse(
            status_code=404,
            content=create_error_response("No workspace found", "NO_WORKSPACE", 404)
        )
    
    # Get nodes by type for sidebar
    node_types = db.query(NodeType).filter(
        NodeType.workspace_id == ws.id,
        NodeType.is_archived == False
    ).all()
    
    sidebar = {
        "workspace": {
            "id": ws.id,
            "name": ws.name,
            "slug": ws.slug
        },
        "sections": []
    }
    
    # Projects section
    project_type = next((t for t in node_types if t.name == "project"), None)
    if project_type:
        projects = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == ws.id,
            KnowledgeNode.node_type_id == project_type.id,
            KnowledgeNode.is_archived == False
        ).order_by(KnowledgeNode.updated_at.desc()).all()
        
        sidebar["sections"].append({
            "id": "projects",
            "title": "Projects",
            "icon": project_type.icon,
            "items": [
                {"id": p.id, "title": p.title, "slug": p.slug, "completeness": p.completeness_percent}
                for p in projects
            ]
        })
    
    # People section
    person_type = next((t for t in node_types if t.name == "person"), None)
    if person_type:
        people = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == ws.id,
            KnowledgeNode.node_type_id == person_type.id,
            KnowledgeNode.is_archived == False
        ).all()
        
        sidebar["sections"].append({
            "id": "people",
            "title": "People",
            "icon": person_type.icon,
            "items": [
                {"id": p.id, "title": p.title, "slug": p.slug}
                for p in people
            ]
        })
    
    # Concepts section
    concept_type = next((t for t in node_types if t.name == "concept"), None)
    if concept_type:
        concepts = db.query(KnowledgeNode).filter(
            KnowledgeNode.workspace_id == ws.id,
            KnowledgeNode.node_type_id == concept_type.id,
            KnowledgeNode.is_archived == False
        ).all()
        
        sidebar["sections"].append({
            "id": "concepts",
            "title": "Concepts",
            "icon": concept_type.icon,
            "items": [
                {"id": c.id, "title": c.title, "slug": c.slug}
                for c in concepts
            ]
        })
    
    return {
        "success": True,
        "data": sidebar,
        "metadata": {"version": "v4.0.0"},
        "errors": []
    }

@app.get("/api/workspace/dashboard")
def get_dashboard(db = Depends(get_db)):
    """Get workspace dashboard data."""
    from models_v4 import Workspace, KnowledgeNode, KnowledgeEdge
    
    ws = db.query(Workspace).first()
    if not ws:
        return JSONResponse(
            status_code=404,
            content=create_error_response("No workspace found", "NO_WORKSPACE", 404)
        )
    
    total_nodes = db.query(KnowledgeNode).filter(
        KnowledgeNode.workspace_id == ws.id,
        KnowledgeNode.is_archived == False
    ).count()
    
    total_edges = db.query(KnowledgeEdge).filter(
        KnowledgeEdge.workspace_id == ws.id,
        KnowledgeEdge.is_archived == False
    ).count()
    
    # Get recent nodes
    recent_nodes = db.query(KnowledgeNode).filter(
        KnowledgeNode.workspace_id == ws.id,
        KnowledgeNode.is_archived == False
    ).order_by(KnowledgeNode.updated_at.desc()).limit(5).all()
    
    return {
        "success": True,
        "data": {
            "workspace": {"id": ws.id, "name": ws.name},
            "stats": {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "total_relationships": total_edges
            },
            "recent_nodes": [
                {"id": n.id, "title": n.title, "slug": n.slug, "updated_at": n.updated_at.isoformat() if n.updated_at else None}
                for n in recent_nodes
            ]
        },
        "metadata": {"version": "v4.0.0"},
        "errors": []
    }

# SPA catch-all: serve index.html for non-API routes
@app.get("/api/system/llm_status")
async def llm_router_status():
    """Get LLM Router status and available providers."""
    try:
        from llm_router.router import get_router
        router = get_router()
        stats = router.get_stats()
        return {
            "success": True,
            "data": stats,
            "metadata": {"version": "v4.0.0"},
            "errors": []
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "metadata": {"version": "v4.0.0"},
            "errors": [{"message": str(e), "code": "ROUTER_ERROR"}]
        }

@app.get("/api/system/degradation_flags")
async def get_degradation_flags():
    """Get current system degradation status."""
    flags = {
        "llm_available": False,
        "vector_store_available": False,
        "graph_available": False,
        "event_bus_available": False
    }
    
    # Check LLM
    try:
        from llm_router.router import get_router
        router = get_router()
        available = router.get_stats().get("available_providers", [])
        flags["llm_available"] = len(available) > 0
    except:
        pass
    
    # Check vector store (ChromaDB for now)
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db_sage_v3")
        flags["vector_store_available"] = True
    except:
        pass
    
    # Check graph (SQLAlchemy for now)
    try:
        from database_v4 import get_db
        db = next(get_db())
        flags["graph_available"] = True
        db.close()
    except:
        pass
    
    return {
        "success": True,
        "data": flags,
        "metadata": {"version": "v4.0.0"},
        "errors": []
    }

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str, request: Request):
    """Serve frontend index.html for SPA routing."""
    # Don't intercept API routes
    if full_path.startswith("api/") or full_path.startswith("assets/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend not built. Run npm run build in frontend/."}
    )

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
