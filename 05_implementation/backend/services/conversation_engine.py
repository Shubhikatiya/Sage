"""
Sage Conversation Engine — Phase 11
Turn planning, streaming responses, tool calling, persona consistency.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class ToolName(str, Enum):
    """Available tools for the Conversation Engine."""
    BRING_ME_BACK = "bring_me_back"
    RESEARCH = "research"
    REASON = "reason"
    MEMORY_SEARCH = "memory_search"
    EXECUTE_TASK = "execute_task"
    LEARN_FEEDBACK = "learn_feedback"


class TurnType(str, Enum):
    """Classified turn types."""
    GREETING = "greeting"
    QUESTION = "question"
    COMMAND = "command"
    REFLECTION = "reflection"
    UPDATE = "update"
    PLANNING = "planning"
    CHITCHAT = "chitchat"


@dataclass
class ToolCall:
    """A tool call made during conversation."""
    tool_name: ToolName
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    latency_ms: float = 0


@dataclass
class TurnPlan:
    """Plan for how to handle a conversation turn."""
    turn_type: TurnType
    detected_intent: str = ""
    needs_tools: List[ToolName] = field(default_factory=list)
    expected_response_length: str = "medium"  # short, medium, long
    tone: str = "conversational"  # conversational, formal, concise
    should_stream: bool = True
    confidence: float = 0.7


@dataclass
class ConversationTurn:
    """One turn in the conversation."""
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_message: str = ""
    plan: Optional[TurnPlan] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    assistant_response: str = ""
    streaming_chunks: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0


class ConversationEngine:
    """
    Phase 11: Conversation Engine.
    Plans turns, manages streaming, calls tools, maintains persona consistency.
    """
    
    def __init__(self):
        self.turns: List[ConversationTurn] = []
        self.tool_handlers = {
            ToolName.BRING_ME_BACK: self._handle_bring_me_back,
            ToolName.RESEARCH: self._handle_research,
            ToolName.REASON: self._handle_reason,
            ToolName.MEMORY_SEARCH: self._handle_memory_search,
            ToolName.EXECUTE_TASK: self._handle_execute_task,
            ToolName.LEARN_FEEDBACK: self._handle_learn_feedback,
        }
    
    async def process_turn(
        self,
        user_message: str,
        conversation_history: List[Dict] = None,
        context: Optional[Dict] = None
    ) -> ConversationTurn:
        """
        Process a conversation turn with full planning and tool calling.
        """
        start_time = datetime.utcnow()
        turn = ConversationTurn(user_message=user_message)
        
        # Step 1: Plan the turn
        turn.plan = await self._plan_turn(user_message, conversation_history)
        
        # Step 2: Execute tools if needed
        tool_results = []
        for tool_name in turn.plan.needs_tools:
            result = await self._execute_tool(tool_name, user_message, context)
            turn.tool_calls.append(result)
            tool_results.append(result)
        
        # Step 3: Generate response (streaming simulated)
        response = await self._generate_response(
            user_message,
            turn.plan,
            tool_results,
            conversation_history,
            context
        )
        turn.assistant_response = response
        
        turn.latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        self.turns.append(turn)
        
        return turn
    
    async def process_turn_streaming(
        self,
        user_message: str,
        conversation_history: List[Dict] = None,
        context: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a turn with streaming response.
        Yields response chunks as they're generated.
        """
        turn = ConversationTurn(user_message=user_message)
        
        # Plan
        turn.plan = await self._plan_turn(user_message, conversation_history)
        
        # Execute tools
        tool_results = []
        for tool_name in turn.plan.needs_tools:
            result = await self._execute_tool(tool_name, user_message, context)
            turn.tool_calls.append(result)
            tool_results.append(result)
        
        # Generate streaming response
        full_response = ""
        async for chunk in self._stream_response(
            user_message,
            turn.plan,
            tool_results,
            conversation_history,
            context
        ):
            full_response += chunk
            turn.streaming_chunks.append(chunk)
            yield chunk
        
        turn.assistant_response = full_response
        self.turns.append(turn)
    
    async def _plan_turn(
        self,
        user_message: str,
        conversation_history: List[Dict] = None
    ) -> TurnPlan:
        """
        Analyze message and plan the turn.
        Determines: type, tools needed, response length, tone.
        """
        msg_lower = user_message.lower().strip()
        
        # Detect turn type
        if any(w in msg_lower for w in ['hi', 'hello', 'hey', 'good morning']):
            turn_type = TurnType.GREETING
        elif any(w in msg_lower for w in ['bring me back', 'what did i miss', 'briefing']):
            turn_type = TurnType.REFLECTION
        elif any(w in msg_lower for w in ['research', 'find', 'search', 'look up']):
            turn_type = TurnType.QUESTION
        elif any(w in msg_lower for w in ['plan', 'schedule', 'when should', 'roadmap']):
            turn_type = TurnType.PLANNING
        elif any(w in msg_lower for w in ['do', 'execute', 'run', 'task']):
            turn_type = TurnType.COMMAND
        elif any(w in msg_lower for w in ['remember', 'save', 'note']):
            turn_type = TurnType.UPDATE
        else:
            turn_type = TurnType.CHITCHAT
        
        # Determine tools needed
        tools = []
        if turn_type == TurnType.REFLECTION or 'bring me back' in msg_lower:
            tools.append(ToolName.BRING_ME_BACK)
        if turn_type == TurnType.QUESTION or any(w in msg_lower for w in ['research', 'find', 'search']):
            tools.append(ToolName.RESEARCH)
        if any(w in msg_lower for w in ['think', 'analyze', 'reason', 'why']):
            tools.append(ToolName.REASON)
        if any(w in msg_lower for w in ['remember', 'what did we', 'past']):
            tools.append(ToolName.MEMORY_SEARCH)
        if turn_type == TurnType.COMMAND:
            tools.append(ToolName.EXECUTE_TASK)
        
        # Determine response length
        if turn_type == TurnType.GREETING:
            length = "short"
        elif turn_type == TurnType.REFLECTION:
            length = "long"
        elif '?' in user_message and len(user_message) > 50:
            length = "medium"
        else:
            length = "short"
        
        # Determine tone based on conversation history
        tone = "conversational"
        if conversation_history:
            # Check if user prefers formal tone
            formal_indicators = sum(1 for msg in conversation_history if any(w in msg.get('content', '').lower() for w in ['please', 'thank you', 'kindly']))
            if formal_indicators >= 3:
                tone = "formal"
            # Check if user prefers brevity
            short_msgs = sum(1 for msg in conversation_history if len(msg.get('content', '')) < 30)
            if short_msgs >= len(conversation_history) * 0.7:
                tone = "concise"
        
        return TurnPlan(
            turn_type=turn_type,
            detected_intent=turn_type.value,
            needs_tools=tools,
            expected_response_length=length,
            tone=tone,
            should_stream=True,
            confidence=0.8 if len(tools) <= 2 else 0.6
        )
    
    async def _execute_tool(
        self,
        tool_name: ToolName,
        user_message: str,
        context: Optional[Dict]
    ) -> ToolCall:
        """Execute a tool and return results."""
        start = datetime.utcnow()
        handler = self.tool_handlers.get(tool_name)
        
        if handler:
            result = await handler(user_message, context)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
        
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        
        return ToolCall(
            tool_name=tool_name,
            arguments={"query": user_message},
            result=result,
            latency_ms=latency
        )
    
    # Tool handlers
    async def _handle_bring_me_back(self, query: str, context: Optional[Dict]) -> Dict:
        """Handle bring_me_back tool call."""
        try:
            from services.bring_me_back_v2 import BringMeBackEngineV2
            # This would need db session in real usage
            return {"status": "success", "note": "Bring Me Back reconstruction triggered"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_research(self, query: str, context: Optional[Dict]) -> Dict:
        """Handle research tool call."""
        try:
            from services.research_engine import get_research_engine
            engine = get_research_engine()
            # Notebook would be created in real usage
            return {"status": "success", "note": "Research session started"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_reason(self, query: str, context: Optional[Dict]) -> Dict:
        """Handle reasoning tool call."""
        try:
            from services.reasoning_engine import get_reasoning_engine, ReasoningMode
            engine = get_reasoning_engine()
            # Trace would be generated in real usage
            return {"status": "success", "note": "Reasoning chain initiated"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_memory_search(self, query: str, context: Optional[Dict]) -> Dict:
        """Handle memory search tool call."""
        try:
            from services.memory_engine import MemoryQuery, MemoryType, get_memory_store
            store = get_memory_store()
            mem_query = MemoryQuery(query_text=query, max_results=5)
            result = store.search(mem_query)
            return {
                "status": "success",
                "memories_found": len(result.memories),
                "memories": [
                    {"content": m.content[:200], "score": m.current_score}
                    for m in result.memories
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_execute_task(self, query: str, context: Optional[Dict]) -> Dict:
        """Handle execute task tool call."""
        return {"status": "needs_approval", "note": "Task requires user approval"}
    
    async def _handle_learn_feedback(self, query: str, context: Optional[Dict]) -> Dict:
        """Handle learn feedback tool call."""
        return {"status": "feedback_recorded"}
    
    async def _generate_response(
        self,
        user_message: str,
        plan: TurnPlan,
        tool_results: List[ToolCall],
        conversation_history: List[Dict] = None,
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate the final assistant response.
        In MVP: returns structured response including tool results.
        Future: Uses LLM to synthesize natural response from tool results.
        """
        # Build response parts
        parts = []
        
        # Add tool result summaries
        if tool_results:
            for tc in tool_results:
                if tc.result and isinstance(tc.result, dict):
                    if tc.result.get("status") == "success":
                        parts.append(f"[{tc.tool_name.value}] {tc.result.get('note', 'Done')}")
                    elif tc.result.get("status") == "needs_approval":
                        parts.append(f"[{tc.tool_name.value}] This requires your approval.")
        
        # Add persona-aware response
        if plan.turn_type == TurnType.GREETING:
            if plan.tone == "formal":
                parts.insert(0, "Good day. How may I assist you today?")
            else:
                parts.insert(0, "Hey there! What's on your mind?")
        
        elif plan.turn_type == TurnType.REFLECTION:
            parts.insert(0, "Let me reconstruct what happened while you were away...")
        
        elif tool_results:
            parts.insert(0, f"I've processed your request. Here's what I found:")
        
        else:
            parts.insert(0, f"I understand: '{user_message[:50]}...'")
        
        # Adjust length
        response = "\n\n".join(parts)
        if plan.expected_response_length == "short":
            response = response.split("\n")[0]
        
        return response
    
    async def _stream_response(
        self,
        user_message: str,
        plan: TurnPlan,
        tool_results: List[ToolCall],
        conversation_history: List[Dict] = None,
        context: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response chunks.
        In MVP: yields sentence by sentence.
        Future: True streaming from LLM.
        """
        response = await self._generate_response(
            user_message, plan, tool_results, conversation_history, context
        )
        
        # Split into sentences for streaming simulation
        sentences = response.split('. ')
        for sentence in sentences:
            if sentence.strip():
                yield sentence.strip() + '. '
                await asyncio.sleep(0.05)  # Simulate generation delay
    
    def get_turn_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        return {
            "total_turns": len(self.turns),
            "avg_latency_ms": sum(t.latency_ms for t in self.turns) / len(self.turns) if self.turns else 0,
            "tool_usage": {
                tool.value: sum(1 for t in self.turns for tc in t.tool_calls if tc.tool_name == tool)
                for tool in ToolName
            },
            "turn_types": {
                tt.value: sum(1 for t in self.turns if t.plan and t.plan.turn_type == tt)
                for tt in TurnType
            }
        }


# Singleton
_conversation_engine: Optional[ConversationEngine] = None


def get_conversation_engine() -> ConversationEngine:
    """Get or create the global Conversation Engine."""
    global _conversation_engine
    if _conversation_engine is None:
        _conversation_engine = ConversationEngine()
    return _conversation_engine
