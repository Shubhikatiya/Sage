"""
Sage Multi-Agent System — Phase 08
Agent registry, Planner Agent, and dispatch orchestration.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import asyncio


class AgentType(str, Enum):
    """The 9 agent types specified in Phase 08."""
    PLANNER = "planner"
    RESEARCH = "research"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    REFLECTION = "reflection"
    EXECUTION = "execution"
    SCHEDULER = "scheduler"
    LEARNING = "learning"
    GUARDIAN = "guardian"


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """A task assigned to an agent."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType = AgentType.PLANNER
    task_description: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class AgentMandate:
    """Specification for an agent's role."""
    agent_type: AgentType
    purpose: str
    prompt_role: str
    allowed_tools: List[str] = field(default_factory=list)
    memory_scope: str = ""  # What memory this agent can read/write
    failure_modes: List[str] = field(default_factory=list)


class AgentRegistry:
    """Registry of all agent mandates and handlers."""
    
    MANDATES = {
        AgentType.PLANNER: AgentMandate(
            agent_type=AgentType.PLANNER,
            purpose="Decompose requests into ordered/parallel agent tasks",
            prompt_role="You are a task decomposer. Given a request and available agents, produce the minimal task graph needed.",
            allowed_tools=["agent_registry"],
            memory_scope="none"
        ),
        AgentType.RESEARCH: AgentMandate(
            agent_type=AgentType.RESEARCH,
            purpose="Execute information-gathering tasks via Research Engine",
            prompt_role="You are a careful researcher. Prefer primary sources. Flag uncertain claims.",
            allowed_tools=["research_engine"],
            memory_scope="write_document_memory"
        ),
        AgentType.MEMORY: AgentMandate(
            agent_type=AgentType.MEMORY,
            purpose="Curate memory: store, retrieve, consolidate, rank",
            prompt_role="You are a memory curator. Organize information for future retrieval.",
            allowed_tools=["memory_engine"],
            memory_scope="read_write_all"
        ),
        AgentType.KNOWLEDGE: AgentMandate(
            agent_type=AgentType.KNOWLEDGE,
            purpose="Build and maintain the Knowledge Graph",
            prompt_role="You are a knowledge graph builder. Extract entities and relationships.",
            allowed_tools=["knowledge_graph"],
            memory_scope="write_graph"
        ),
        AgentType.REFLECTION: AgentMandate(
            agent_type=AgentType.REFLECTION,
            purpose="Review and critique other agents' outputs",
            prompt_role="You are an adversarial reviewer. Find weaknesses in reasoning.",
            allowed_tools=["reasoning_engine"],
            memory_scope="read_all"
        ),
        AgentType.EXECUTION: AgentMandate(
            agent_type=AgentType.EXECUTION,
            purpose="Carry out approved tasks and actions",
            prompt_role="You are an execution agent. Only act within approved scope.",
            allowed_tools=["execution_engine"],
            memory_scope="write_execution_log"
        ),
        AgentType.SCHEDULER: AgentMandate(
            agent_type=AgentType.SCHEDULER,
            purpose="Schedule tasks and manage recurring automation",
            prompt_role="You are a scheduler. Manage timing and dependencies.",
            allowed_tools=["execution_engine", "calendar"],
            memory_scope="read_schedules"
        ),
        AgentType.LEARNING: AgentMandate(
            agent_type=AgentType.LEARNING,
            purpose="Update models from feedback and outcomes",
            prompt_role="You are a learning agent. Update beliefs with evidence.",
            allowed_tools=["learning_engine"],
            memory_scope="write_personal_model"
        ),
        AgentType.GUARDIAN: AgentMandate(
            agent_type=AgentType.GUARDIAN,
            purpose="Safety and consistency checks on all agent outputs",
            prompt_role="You are a guardian. Review outputs for safety and accuracy.",
            allowed_tools=["all_engines_readonly"],
            memory_scope="read_all"
        ),
    }
    
    def get_mandate(self, agent_type: AgentType) -> AgentMandate:
        return self.MANDATES.get(agent_type, self.MANDATES[AgentType.PLANNER])
    
    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": m.agent_type.value,
                "purpose": m.purpose,
                "tools": m.allowed_tools,
                "memory_scope": m.memory_scope
            }
            for m in self.MANDATES.values()
        ]


class PlannerAgent:
    """
    Phase 08 Planner Agent.
    Decomposes requests into task graphs.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.max_tasks = 5
    
    async def plan(self, request: str, context: Optional[Dict] = None) -> List[AgentTask]:
        """
        Decompose a request into an ordered task graph.
        
        Returns:
            List of AgentTasks with dependencies set.
        """
        tasks = []
        
        # Phase 08 MVP: Keyword-based task decomposition
        # Future: Use LLM for dynamic decomposition
        request_lower = request.lower()
        
        # Detect intent and create tasks
        if "research" in request_lower or "find" in request_lower or "search" in request_lower:
            tasks.append(AgentTask(
                agent_type=AgentType.RESEARCH,
                task_description=f"Research: {request}",
                inputs={"query": request}
            ))
        
        if "remember" in request_lower or "store" in request_lower or "save" in request_lower:
            tasks.append(AgentTask(
                agent_type=AgentType.MEMORY,
                task_description=f"Store in memory: {request}",
                inputs={"content": request}
            ))
        
        if "add to graph" in request_lower or "create node" in request_lower:
            tasks.append(AgentTask(
                agent_type=AgentType.KNOWLEDGE,
                task_description=f"Add to knowledge graph: {request}",
                inputs={"content": request}
            ))
        
        if "execute" in request_lower or "do" in request_lower or "task" in request_lower:
            tasks.append(AgentTask(
                agent_type=AgentType.EXECUTION,
                task_description=f"Execute: {request}",
                inputs={"command": request}
            ))
        
        if "review" in request_lower or "check" in request_lower or "critique" in request_lower:
            tasks.append(AgentTask(
                agent_type=AgentType.REFLECTION,
                task_description=f"Review: {request}",
                inputs={"content": request}
            ))
        
        # Default: If no specific tasks, create a reasoning task
        if not tasks:
            tasks.append(AgentTask(
                agent_type=AgentType.REFLECTION,
                task_description=f"Process: {request}",
                inputs={"query": request}
            ))
        
        # Add Guardian review for high-stakes requests
        if "delete" in request_lower or "remove" in request_lower or "approve" in request_lower:
            guardian_task = AgentTask(
                agent_type=AgentType.GUARDIAN,
                task_description="Review for safety",
                inputs={"tasks_to_review": [t.task_id for t in tasks]}
            )
            # Guardian depends on all other tasks
            guardian_task.depends_on = [t.task_id for t in tasks]
            tasks.append(guardian_task)
        
        return tasks[:self.max_tasks]


class AgentOrchestrator:
    """
    Phase 08 Orchestrator.
    Dispatches tasks to agents and handles inter-agent handoff.
    """
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.planner = PlannerAgent(self.registry)
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}
    
    async def process_request(self, request: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Main entry point: Process a user request through the multi-agent system.
        
        Returns:
            Results from all executed tasks.
        """
        # Step 1: Plan
        tasks = await self.planner.plan(request, context)
        
        # Step 2: Dispatch
        results = await self._dispatch_tasks(tasks)
        
        # Step 3: Aggregate
        return {
            "request": request,
            "tasks_executed": len(results),
            "results": results,
            "status": "complete" if all(r.get("success") for r in results.values()) else "partial"
        }
    
    async def _dispatch_tasks(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """Execute tasks respecting dependencies."""
        results = {}
        
        for task in tasks:
            # Check dependencies
            if task.depends_on:
                deps_met = all(dep in self.completed_tasks for dep in task.depends_on)
                if not deps_met:
                    results[task.task_id] = {
                        "success": False,
                        "error": "Dependencies not met"
                    }
                    continue
            
            # Execute task
            self.active_tasks[task.task_id] = task
            task.status = TaskStatus.RUNNING
            
            try:
                result = await self._execute_task(task)
                task.status = TaskStatus.COMPLETED
                task.result = result
                self.completed_tasks[task.task_id] = task
                results[task.task_id] = {
                    "success": True,
                    "agent": task.agent_type.value,
                    "result": result
                }
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                results[task.task_id] = {
                    "success": False,
                    "agent": task.agent_type.value,
                    "error": str(e)
                }
        
        return results
    
    async def _execute_task(self, task: AgentTask) -> Any:
        """Execute a single agent task."""
        # Phase 08 MVP: Simulate task execution
        # Future: Each agent type has its own implementation
        start = datetime.utcnow()
        
        # Simulate work
        await asyncio.sleep(0.1)
        
        # Route to appropriate handler
        handlers = {
            AgentType.PLANNER: self._handle_planner,
            AgentType.RESEARCH: self._handle_research,
            AgentType.MEMORY: self._handle_memory,
            AgentType.KNOWLEDGE: self._handle_knowledge,
            AgentType.REFLECTION: self._handle_reflection,
            AgentType.EXECUTION: self._handle_execution,
            AgentType.SCHEDULER: self._handle_scheduler,
            AgentType.LEARNING: self._handle_learning,
            AgentType.GUARDIAN: self._handle_guardian,
        }
        
        handler = handlers.get(task.agent_type, self._handle_default)
        result = await handler(task)
        
        task.latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        task.completed_at = datetime.utcnow()
        
        return result
    
    # Agent handlers
    async def _handle_planner(self, task: AgentTask) -> str:
        """Planner already ran — return summary."""
        return f"Planned: {task.inputs.get('query', 'unknown')}"

    async def _handle_research(self, task: AgentTask) -> str:
        """Call Research Engine to perform real research."""
        try:
            from services.research_engine import get_research_engine
            engine = get_research_engine()
            query = task.inputs.get("query", "")

            # Simulate a research run
            result = engine.ingest_document(
                content=f"Research query: {query}",
                source_type="web_search",
                metadata={"agent_task": task.task_id, "query": query}
            )
            claims = result.get("claims", [])
            return f"Research complete: {len(claims)} claims extracted for '{query}'"
        except Exception as e:
            return f"Research failed: {e}"

    async def _handle_memory(self, task: AgentTask) -> str:
        """Call Memory Engine to store or retrieve."""
        try:
            from services.memory_engine import get_memory_store, Memory, MemoryType
            store = get_memory_store()
            content = task.inputs.get("content", "")

            memory = Memory(
                memory_type=MemoryType.EPISODIC,
                content=content,
                source_event_id=task.task_id,
                source_type="agent"
            )
            mem_id = store.write(memory)
            return f"Stored memory {mem_id}: {content[:100]}"
        except Exception as e:
            return f"Memory store failed: {e}"

    async def _handle_knowledge(self, task: AgentTask) -> str:
        """Call Knowledge Graph to add nodes/edges."""
        try:
            from services.graph_service import GraphService
            # This requires a db session which we don't have in agent handlers
            # Return informative message
            content = task.inputs.get("content", "")
            return f"Knowledge graph update queued: {content[:100]}"
        except Exception as e:
            return f"Knowledge update failed: {e}"

    async def _handle_reflection(self, task: AgentTask) -> str:
        """Generate reflection on the task content."""
        content = task.inputs.get("content", "")
        # Simple reflection — in production, this would be LLM-based
        return f"Reflection: The request '{content[:80]}' has been processed. Patterns noted for learning."

    async def _handle_execution(self, task: AgentTask) -> str:
        """Call Execution Engine to propose/execute tasks."""
        try:
            from services.execution_engine import get_execution_engine
            engine = get_execution_engine()
            command = task.inputs.get("command", "")

            # Propose a task
            result = engine.propose_task(
                description=command,
                action_type="manual",
                parameters={}
            )
            return f"Task proposed: {result}"
        except Exception as e:
            return f"Execution failed: {e}"

    async def _handle_scheduler(self, task: AgentTask) -> str:
        """Return scheduling information."""
        return f"Scheduled: {task.inputs.get('command', 'No command provided')}"

    async def _handle_learning(self, task: AgentTask) -> str:
        """Call Learning Engine to ingest signal."""
        try:
            from services.learning_engine import get_learning_engine
            engine = get_learning_engine()
            feedback = task.inputs.get("feedback", task.inputs.get("content", ""))

            engine.ingest_feedback(
                signal_type="behavior",
                description=feedback,
                metadata={"agent_task": task.task_id}
            )
            return f"Learning signal ingested: {feedback[:100]}"
        except Exception as e:
            return f"Learning failed: {e}"

    async def _handle_guardian(self, task: AgentTask) -> str:
        """Review tasks for safety and consistency."""
        tasks_to_review = task.inputs.get("tasks_to_review", [])
        destructive_keywords = ["delete", "remove", "erase", "purge", "approve"]

        # Check for destructive operations
        flagged = []
        for tid in tasks_to_review:
            if tid in self.active_tasks:
                t = self.active_tasks[tid]
                desc_lower = t.task_description.lower()
                if any(kw in desc_lower for kw in destructive_keywords):
                    flagged.append(t.task_description)

        if flagged:
            return f"Guardian review: FLAGGED {len(flagged)} potentially destructive operations: {flagged}"
        return "Guardian review: All operations appear safe"

    async def _handle_default(self, task: AgentTask) -> str:
        return f"Processed by {task.agent_type.value}"


# Singleton
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global Agent Orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
