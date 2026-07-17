"""Sage v4 API modules."""

# Import all routers for easy access
from .knowledge import router as knowledge_router
from .graph import router as graph_router
from .asset import router as asset_router
from .reasoning import router as reasoning_router
from .chat import router as chat_router
from .memory import router as memory_router
from .reasoning_v2 import router as reasoning_v2_router
from .research import router as research_router
from .agents import router as agents_router
from .learning import router as learning_router
from .execute import router as execute_router
from .phases_11_18 import router as phases_11_18_router
from .topology import router as topology_router
from .graph_phase03 import router as graph_phase03_router
from .reasoning_v3 import router as reasoning_v3_router
from .context import router as context_router
from .bring_me_back import router as bring_me_back_router
from .phases_09_12 import router as phases_09_12_router

__all__ = [
    "knowledge_router",
    "graph_router",
    "asset_router",
    "reasoning_router",
    "chat_router",
    "memory_router",
    "reasoning_v2_router",
    "research_router",
    "agents_router",
    "learning_router",
    "execute_router",
    "phases_11_18_router",
    "topology_router",
    "graph_phase03_router",
    "reasoning_v3_router",
    "context_router",
    "bring_me_back_router",
    "phases_09_12_router",
]
