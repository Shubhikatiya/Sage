"""
Topology API for Sage v4 — Phase 01 Foundation
Exposes service registry and circuit breakers via REST.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v2", tags=["Topology"])


@router.get("/topology/services")
def get_services():
    """List all registered subsystems with their status."""
    from topology.registry import get_registry
    registry = get_registry()
    return {
        "success": True,
        "data": {
            "services": [
                {
                    "name": name,
                    "description": svc.definition.description,
                    "status": svc.status.value,
                    "failure_impact": svc.definition.failure_impact.value,
                    "fallback_strategy": svc.definition.fallback_strategy
                }
                for name, svc in registry._services.items()
            ]
        }
    }


@router.get("/topology/map")
def get_topology_map():
    """Export the system architecture map as structured data."""
    from topology.registry import get_registry
    registry = get_registry()
    return {
        "success": True,
        "data": registry.get_topology_map()
    }


@router.get("/topology/circuit-breakers")
def get_circuit_breakers():
    """List all circuit breaker states."""
    from topology.circuit_breaker import _BREAKERS
    return {
        "success": True,
        "data": {
            "circuit_breakers": [
                {
                    "service": name,
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time,
                    "cooldown_until": cb.cooldown_until
                }
                for name, cb in _BREAKERS.items()
            ]
        }
    }
