"""
Sage Service Topology Registry
Phase 01: Foundation — Formalized system architecture map in code.
Tracks all subsystems, their health, dependencies, and failure modes.
"""
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class FailureImpact(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    CRITICAL = "critical"


@dataclass
class ServiceDefinition:
    name: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    exposed_apis: List[str] = field(default_factory=list)
    failure_impact: FailureImpact = FailureImpact.PARTIAL
    fallback_strategy: str = ""
    health_check: Optional[Callable] = None


@dataclass
class ServiceInstance:
    definition: ServiceDefinition
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_heartbeat: float = 0.0
    latency_ms: float = 0.0
    error_rate: float = 0.0
    message: str = ""


class ServiceTopologyRegistry:
    _services: Dict[str, ServiceInstance] = {}
    _definitions: Dict[str, ServiceDefinition] = {}

    def __init__(self):
        self._register_all_services()

    def _register_all_services(self):
        services = [
            ServiceDefinition(
                name="api_gateway", description="Auth, rate limiting, request routing",
                exposed_apis=["/api/*"], failure_impact=FailureImpact.CRITICAL,
                fallback_strategy="No fallback — API gateway is the entry point"
            ),
            ServiceDefinition(
                name="conversation_engine", description="Dialogue state, persona, streaming responses",
                depends_on=["context_engine", "memory_engine", "llm_router"],
                exposed_apis=["/api/chat/*"], failure_impact=FailureImpact.CRITICAL,
                fallback_strategy="Return cached responses with degraded flag"
            ),
            ServiceDefinition(
                name="context_engine", description="Resolves what's relevant right now",
                depends_on=["memory_engine", "knowledge_graph"],
                exposed_apis=["/api/context/resolve"], failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Return memory-only context with graph_unavailable flag"
            ),
            ServiceDefinition(
                name="memory_engine", description="Stores/retrieves all memory types",
                depends_on=["vector_store"], exposed_apis=["/api/memory/*"],
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Fallback to keyword/graph retrieval"
            ),
            ServiceDefinition(
                name="knowledge_graph", description="Entity/relationship store",
                depends_on=["graph_store"], exposed_apis=["/api/graph/*"],
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Return memory-only context with graph_unavailable flag"
            ),
            ServiceDefinition(
                name="reasoning_engine", description="Multi-step reasoning, planning",
                depends_on=["llm_router", "memory_engine", "knowledge_graph"],
                exposed_apis=["/api/reason/*"], failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Return evidence_incomplete flag with partial answer"
            ),
            ServiceDefinition(
                name="research_engine", description="Web/document research",
                depends_on=["blob_storage"], exposed_apis=["/api/research/*"],
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Circuit breaker: treat as cancellable"
            ),
            ServiceDefinition(
                name="orchestrator", description="Decomposes requests into agent tasks",
                depends_on=["conversation_engine", "reasoning_engine", "research_engine",
                           "execution_engine", "learning_engine", "prediction_engine"],
                failure_impact=FailureImpact.CRITICAL,
                fallback_strategy="Direct pass-through to individual engines"
            ),
            ServiceDefinition(
                name="execution_engine", description="Tasks, scheduling, workflows",
                depends_on=["orchestrator"], exposed_apis=["/api/execute/*"],
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Queue tasks for later execution"
            ),
            ServiceDefinition(
                name="learning_engine", description="Consumes feedback, updates models",
                depends_on=["event_bus"], failure_impact=FailureImpact.NONE,
                fallback_strategy="Acceptable staleness: updates lag until recovery"
            ),
            ServiceDefinition(
                name="prediction_engine", description="Forecasts deadlines, risks",
                depends_on=["knowledge_graph", "memory_engine"],
                exposed_apis=["/api/predict/*"], failure_impact=FailureImpact.NONE,
                fallback_strategy="Return stale predictions with stale flag"
            ),
            ServiceDefinition(
                name="personal_model", description="Structured model of the user",
                depends_on=["learning_engine"], exposed_apis=["/api/model/user"],
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Return cached model snapshot"
            ),
            ServiceDefinition(
                name="security_layer", description="Encryption, secrets, audit",
                failure_impact=FailureImpact.CRITICAL,
                fallback_strategy="Fail-closed: deny all until recovery"
            ),
            ServiceDefinition(
                name="llm_router", description="Provider-agnostic routing",
                depends_on=["external_llm_apis"], exposed_apis=["/api/llm/*"],
                failure_impact=FailureImpact.CRITICAL,
                fallback_strategy="Multi-provider fallback + local Ollama"
            ),
            ServiceDefinition(
                name="event_bus", description="Async event delivery",
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="In-memory event log buffer until bus recovers"
            ),
            ServiceDefinition(
                name="relational_store", description="Postgres — source of truth",
                failure_impact=FailureImpact.CRITICAL,
                fallback_strategy="No fallback — data loss unacceptable"
            ),
            ServiceDefinition(
                name="vector_store", description="Qdrant — semantic search",
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Keyword-only fallback"
            ),
            ServiceDefinition(
                name="graph_store", description="Kuzu/Neo4j — entities, relationships",
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Return memory-only context"
            ),
            ServiceDefinition(
                name="blob_storage", description="MinIO/S3 — raw docs, images",
                failure_impact=FailureImpact.PARTIAL,
                fallback_strategy="Serve cached previews"
            ),
        ]
        for svc in services:
            self._definitions[svc.name] = svc
            self._services[svc.name] = ServiceInstance(definition=svc)

    def get_service(self, name: str) -> Optional[ServiceInstance]:
        return self._services.get(name)

    def get_all_services(self) -> List[ServiceInstance]:
        return list(self._services.values())

    def get_dependencies(self, name: str) -> List[str]:
        svc = self._definitions.get(name)
        return svc.depends_on if svc else []

    def get_dependents(self, name: str) -> List[str]:
        return [svc.name for svc in self._definitions.values() if name in svc.depends_on]

    def update_health(self, name: str, status: ServiceStatus, message: str = ""):
        if name in self._services:
            self._services[name].status = status
            self._services[name].last_heartbeat = time.time()
            self._services[name].message = message

    def get_topology_map(self) -> Dict:
        return {
            "layers": {
                "client": ["cli", "web_ui", "mobile"],
                "api_gateway": ["api_gateway"],
                "engines": ["conversation_engine", "orchestrator", "execution_engine"],
                "core_engines": [
                    "context_engine", "memory_engine", "knowledge_graph",
                    "reasoning_engine", "research_engine"
                ],
                "cross_cutting": [
                    "learning_engine", "prediction_engine", "personal_model",
                    "security_layer", "llm_router", "observability"
                ],
                "data": [
                    "event_bus", "relational_store", "vector_store",
                    "graph_store", "blob_storage"
                ]
            },
            "services": {
                name: {
                    "description": svc.definition.description,
                    "status": svc.status.value,
                    "depends_on": svc.definition.depends_on,
                    "failure_impact": svc.definition.failure_impact.value,
                    "fallback_strategy": svc.definition.fallback_strategy,
                    "last_heartbeat": svc.last_heartbeat
                }
                for name, svc in self._services.items()
            }
        }

    def check_circular_dependencies(self) -> List[List[str]]:
        def dfs(node: str, visited: set, path: List[str]) -> Optional[List[str]]:
            if node in path:
                return path[path.index(node):] + [node]
            if node in visited:
                return None
            visited.add(node)
            path.append(node)
            for dep in self.get_dependencies(node):
                cycle = dfs(dep, visited, path)
                if cycle:
                    return cycle
            path.pop()
            return None
        cycles = []
        visited = set()
        for svc_name in self._definitions:
            cycle = dfs(svc_name, visited, [])
            if cycle:
                cycles.append(cycle)
        return cycles


_registry: Optional[ServiceTopologyRegistry] = None


def get_registry() -> ServiceTopologyRegistry:
    global _registry
    if _registry is None:
        _registry = ServiceTopologyRegistry()
    return _registry
