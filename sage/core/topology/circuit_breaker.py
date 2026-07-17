"""
Sage Circuit Breaker
Phase 01: Foundation — Failure isolation per subsystem.

Prevents cascading failures by temporarily rejecting requests
to a failing downstream service.
"""
import time
from typing import Dict, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, rejecting requests
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Failures before opening
    cooldown_seconds: float = 30.0      # Seconds before half-open test
    half_open_max_calls: int = 3        # Test calls in half-open state
    success_threshold: int = 2          # Successes to close


class CircuitBreaker:
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.cooldown_until: Optional[float] = None
        self.half_open_calls = 0
        self.success_count = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() < self.cooldown_until:
                raise CircuitBreakerOpen(f"Circuit {self.name} is OPEN")
            self.state = CircuitState.HALF_OPEN
            self.half_open_calls = 0
            self.success_count = 0

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1
            if self.success_count >= self.config.success_threshold:
                self.reset()
        else:
            self.failure_count = 0

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.cooldown_until = time.time() + self.config.cooldown_seconds
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.cooldown_until = time.time() + self.config.cooldown_seconds

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.cooldown_until = None
        self.half_open_calls = 0
        self.success_count = 0


class CircuitBreakerOpen(Exception):
    pass


_BREAKERS: Dict[str, CircuitBreaker] = {}


def get_breaker(service_name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    if service_name not in _BREAKERS:
        _BREAKERS[service_name] = CircuitBreaker(service_name, config)
    return _BREAKERS[service_name]
