"""
Sage Reasoning Engine — Phase 04 MVP
Multi-step reasoning with multiple modes:
- chain: Sequential step-by-step reasoning
- tree: Explore multiple hypotheses/branches
- graph: Traverse knowledge graph for evidence
- reflection: Self-critique and confidence calibration
- simulation: What-if scenario exploration
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class ReasoningMode(str, Enum):
    CHAIN = "chain"           # Step-by-step sequential reasoning
    TREE = "tree"            # Explore multiple hypotheses
    GRAPH = "graph"          # Traverse knowledge graph
    REFLECTION = "reflection"  # Self-critique and confidence calibration
    SIMULATION = "simulation"  # What-if scenario exploration


@dataclass
class ReasoningStep:
    """A single step in a reasoning trace."""
    step_number: int
    sub_question: str
    evidence_ids: List[str] = field(default_factory=list)
    evidence_sources: List[str] = field(default_factory=list)
    intermediate_conclusion: str = ""
    step_confidence: float = 0.5
    critique: Optional[str] = None  # Self-critique for reflection mode
    alternatives: List[str] = field(default_factory=list)  # For tree mode


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for a query."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    mode: ReasoningMode = ReasoningMode.CHAIN
    steps: List[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    overall_confidence: float = 0.5
    confidence_explanation: str = ""
    critique_applied: bool = False
    latency_ms: float = 0
    degraded: bool = False
    error: Optional[str] = None


class ReasoningEngine:
    """
    Multi-mode reasoning engine for Sage.
    Phase 04: Core reasoning infrastructure.
    """
    
    def __init__(self):
        self.trace_store: List[ReasoningTrace] = []
    
    async def reason(
        self,
        query: str,
        mode: ReasoningMode = ReasoningMode.CHAIN,
        context: Dict[str, Any] = None,
        max_evidence_items: int = 10,
        high_stakes: bool = False
    ) -> ReasoningTrace:
        """
        Execute reasoning with the specified mode.
        
        Args:
            query: The question or problem to reason about
            mode: Reasoning strategy to use
            context: Additional context (memories, documents, etc.)
            max_evidence_items: Maximum evidence to retrieve
            high_stakes: If True, applies stricter confidence thresholds
        """
        start_time = datetime.utcnow()
        trace = ReasoningTrace(query=query, mode=mode)
        
        try:
            if mode == ReasoningMode.CHAIN:
                trace = await self._chain_reasoning(trace, context, max_evidence_items)
            elif mode == ReasoningMode.TREE:
                trace = await self._tree_reasoning(trace, context, max_evidence_items)
            elif mode == ReasoningMode.GRAPH:
                trace = await self._graph_reasoning(trace, context, max_evidence_items)
            elif mode == ReasoningMode.REFLECTION:
                trace = await self._reflection_reasoning(trace, context, max_evidence_items)
            elif mode == ReasoningMode.SIMULATION:
                trace = await self._simulation_reasoning(trace, context, max_evidence_items)
            else:
                trace.error = f"Unknown reasoning mode: {mode}"
                trace.degraded = True
            
            # Apply confidence calibration for high-stakes queries
            if high_stakes and not trace.error:
                trace = self._calibrate_confidence(trace)
            
            # Calculate latency
            elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
            trace.latency_ms = elapsed
            
        except Exception as e:
            trace.error = str(e)
            trace.degraded = True
            trace.final_answer = f"Reasoning failed: {str(e)}"
        
        # Store trace
        self.trace_store.append(trace)
        return trace
    
    async def _chain_reasoning(
        self,
        trace: ReasoningTrace,
        context: Optional[Dict],
        max_evidence: int
    ) -> ReasoningTrace:
        """
        Chain-of-thought reasoning: Break query into sequential steps.
        """
        # Step 1: Decompose query into sub-questions
        decomposition = await self._call_llm(
            f"Break this question into 2-4 clear sub-questions:\n\n{trace.query}\n\n"
            f"Return as a JSON array of strings.",
            system_prompt="You are a reasoning assistant. Break complex questions into sequential steps."
        )
        
        try:
            sub_questions = json.loads(decomposition)
            if not isinstance(sub_questions, list):
                sub_questions = [decomposition]
        except:
            sub_questions = [trace.query]
        
        # Execute each sub-question sequentially
        intermediate_results = []
        for i, sq in enumerate(sub_questions[:4], 1):
            # Retrieve evidence for this sub-question
            evidence = await self._retrieve_evidence(sq, context, max_evidence // len(sub_questions))
            
            # Generate intermediate conclusion
            evidence_text = "\n".join([f"- {e['content'][:200]}" for e in evidence])
            prompt = f"""Sub-question: {sq}

Evidence:
{evidence_text}

Previous conclusions:
{"; ".join(intermediate_results) if intermediate_results else "None yet."}

Provide a concise intermediate conclusion (2-3 sentences):"""
            
            conclusion = await self._call_llm(
                prompt,
                system_prompt="You are a precise reasoning assistant. Draw clear conclusions from evidence."
            )
            
            step = ReasoningStep(
                step_number=i,
                sub_question=sq,
                evidence_ids=[e["id"] for e in evidence],
                evidence_sources=[e["source"] for e in evidence],
                intermediate_conclusion=conclusion,
                step_confidence=0.7  # Base confidence, refined later
            )
            trace.steps.append(step)
            intermediate_results.append(conclusion)
        
        # Final synthesis
        final_prompt = f"""Original question: {trace.query}

Reasoning steps:
{self._format_steps_for_prompt(trace.steps)}

Synthesize a final answer that directly addresses the original question:"""
        
        trace.final_answer = await self._call_llm(
            final_prompt,
            system_prompt="You are Sage, an AI Chief of Staff. Synthesize reasoning into clear, actionable answers."
        )
        
        trace.overall_confidence = self._compute_overall_confidence(trace.steps)
        trace.confidence_explanation = f"Based on {len(trace.steps)} reasoning steps with average confidence {trace.overall_confidence:.2f}"
        
        return trace
    
    async def _tree_reasoning(
        self,
        trace: ReasoningTrace,
        context: Optional[Dict],
        max_evidence: int
    ) -> ReasoningTrace:
        """
        Tree search reasoning: Explore multiple hypotheses in parallel.
        """
        # Generate multiple hypotheses
        hypotheses_prompt = f"""Question: {trace.query}

Generate 2-3 distinct hypotheses or approaches to answer this question.
Return as a JSON array of strings."""
        
        hypotheses_raw = await self._call_llm(
            hypotheses_prompt,
            system_prompt="You are a strategic analyst. Generate diverse hypotheses."
        )
        
        try:
            hypotheses = json.loads(hypotheses_raw)
            if not isinstance(hypotheses, list):
                hypotheses = [hypotheses_raw]
        except:
            hypotheses = ["Direct approach", "Alternative interpretation"]
        
        # Evaluate each hypothesis
        best_hypothesis = None
        best_score = -1
        
        for i, hypothesis in enumerate(hypotheses[:3], 1):
            evidence = await self._retrieve_evidence(hypothesis, context, max_evidence // len(hypotheses))
            
            # Evaluate hypothesis against evidence
            eval_prompt = f"""Hypothesis: {hypothesis}

Evidence:
{"; ".join([e["content"][:150] for e in evidence])}

Rate this hypothesis (0-1) and explain why:"""
            
            evaluation = await self._call_llm(
                eval_prompt,
                system_prompt="Evaluate hypotheses rigorously against evidence."
            )
            
            # Extract score
            import re
            score_match = re.search(r'(\d+(?:\.\d+)?)', evaluation)
            score = float(score_match.group(1)) / 10 if score_match and float(score_match.group(1)) > 1 else float(score_match.group(1)) if score_match else 0.5
            score = min(max(score, 0), 1)
            
            step = ReasoningStep(
                step_number=i,
                sub_question=f"Hypothesis: {hypothesis}",
                evidence_ids=[e["id"] for e in evidence],
                evidence_sources=[e["source"] for e in evidence],
                intermediate_conclusion=evaluation,
                step_confidence=score,
                alternatives=[h for j, h in enumerate(hypotheses[:3]) if j != i]
            )
            trace.steps.append(step)
            
            if score > best_score:
                best_score = score
                best_hypothesis = hypothesis
        
        # Final answer based on best hypothesis
        trace.final_answer = f"Based on analysis of {len(trace.steps)} hypotheses, the most supported answer is:\n\n{best_hypothesis or trace.query}"
        trace.overall_confidence = best_score
        trace.confidence_explanation = f"Best hypothesis scored {best_score:.2f} out of {len(trace.steps)} evaluated"
        
        return trace
    
    async def _graph_reasoning(
        self,
        trace: ReasoningTrace,
        context: Optional[Dict],
        max_evidence: int
    ) -> ReasoningTrace:
        """
        Graph traversal reasoning: Navigate knowledge graph for evidence.
        """
        # Step 1: Identify relevant entities in the query
        entities = await self._extract_entities_from_query(trace.query)
        
        # Step 2: Retrieve graph context (neighbors, paths)
        graph_context = []
        if context and "graph_nodes" in context:
            for node in context["graph_nodes"][:5]:
                graph_context.append({
                    "id": node.get("id", ""),
                    "title": node.get("title", ""),
                    "content": node.get("content", "")[:300],
                    "source": "knowledge_graph"
                })
        
        # Step 3: Trace paths between entities
        step_number = 1
        for entity in entities[:3]:
            entity_evidence = [e for e in graph_context if entity.lower() in e["title"].lower()]
            
            step = ReasoningStep(
                step_number=step_number,
                sub_question=f"What does the graph tell us about '{entity}'?",
                evidence_ids=[e["id"] for e in entity_evidence],
                evidence_sources=["knowledge_graph"],
                intermediate_conclusion=f"Found {len(entity_evidence)} graph nodes related to {entity}",
                step_confidence=0.6 if entity_evidence else 0.2
            )
            trace.steps.append(step)
            step_number += 1
        
        # Step 4: Synthesize from graph evidence
        graph_text = "\n".join([f"- {e['title']}: {e['content'][:200]}" for e in graph_context[:5]])
        
        final_prompt = f"""Question: {trace.query}

Knowledge Graph Evidence:
{graph_text}

Provide an answer based on the knowledge graph relationships:"""
        
        trace.final_answer = await self._call_llm(
            final_prompt,
            system_prompt="You are a knowledge graph navigator. Connect entities and relationships to answer questions."
        )
        
        trace.overall_confidence = self._compute_overall_confidence(trace.steps)
        trace.confidence_explanation = f"Based on traversal of {len(graph_context)} graph nodes"
        
        return trace
    
    async def _reflection_reasoning(
        self,
        trace: ReasoningTrace,
        context: Optional[Dict],
        max_evidence: int
    ) -> ReasoningTrace:
        """
        Reflection/Self-critique: Generate answer, then critique and improve.
        """
        # Step 1: Initial chain reasoning (quick draft)
        draft_trace = await self._chain_reasoning(
            ReasoningTrace(query=trace.query, mode=ReasoningMode.CHAIN),
            context,
            max_evidence
        )
        
        trace.steps = draft_trace.steps
        
        # Step 2: Self-critique
        critique_prompt = f"""Original question: {trace.query}

Draft answer: {draft_trace.final_answer}

Critique this answer. What are its weaknesses, gaps, or biases?
What evidence might be missing? How could it be improved?"""
        
        critique = await self._call_llm(
            critique_prompt,
            system_prompt="You are a critical reviewer. Identify weaknesses in reasoning."
        )
        
        critique_step = ReasoningStep(
            step_number=len(trace.steps) + 1,
            sub_question="Self-critique of reasoning",
            intermediate_conclusion=critique,
            step_confidence=0.5,
            critique=critique
        )
        trace.steps.append(critique_step)
        
        # Step 3: Revised answer addressing critiques
        revision_prompt = f"""Original question: {trace.query}

Draft answer: {draft_trace.final_answer}

Critique: {critique}

Now provide a revised, improved answer that addresses the critique:"""
        
        trace.final_answer = await self._call_llm(
            revision_prompt,
            system_prompt="You are a careful reasoner. Revise answers based on critique to be more accurate and complete."
        )
        
        # Confidence increases after reflection
        base_confidence = self._compute_overall_confidence(trace.steps[:-1])
        trace.overall_confidence = min(base_confidence + 0.1, 0.95)
        trace.confidence_explanation = f"Confidence {trace.overall_confidence:.2f} after self-critique (base: {base_confidence:.2f})"
        trace.critique_applied = True
        
        return trace
    
    async def _simulation_reasoning(
        self,
        trace: ReasoningTrace,
        context: Optional[Dict],
        max_evidence: int
    ) -> ReasoningTrace:
        """
        Simulation/What-if: Explore scenarios.
        """
        # Step 1: Identify scenario parameters
        scenario_prompt = f"""Question: {trace.query}

Identify 2-3 key variables or assumptions that could change the outcome.
Return as JSON array of strings."""
        
        variables_raw = await self._call_llm(scenario_prompt)
        try:
            variables = json.loads(variables_raw)
            if not isinstance(variables, list):
                variables = ["timeline", "resources", "approach"]
        except:
            variables = ["timeline", "resources", "approach"]
        
        # Step 2: Explore scenarios
        for i, var in enumerate(variables[:3], 1):
            scenario = f"What if {var} changes?"
            
            step = ReasoningStep(
                step_number=i,
                sub_question=f"Scenario: {scenario}",
                intermediate_conclusion=f"Exploring impact of {var}...",
                step_confidence=0.5
            )
            trace.steps.append(step)
        
        # Step 3: Synthesize scenarios
        scenarios_text = "\n".join([f"- {v}" for v in variables[:3]])
        final_prompt = f"""Question: {trace.query}

Key variables explored:
{scenarios_text}

Synthesize a recommendation that accounts for these scenarios:"""
        
        trace.final_answer = await self._call_llm(
            final_prompt,
            system_prompt="You are a strategic advisor. Consider multiple scenarios when making recommendations."
        )
        
        trace.overall_confidence = 0.6  # Simulation inherently uncertain
        trace.confidence_explanation = "Confidence reflects scenario uncertainty — real outcomes depend on variables"
        
        return trace
    
    async def _call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """Call LLM Router for reasoning steps."""
        try:
            from llm_router.router import generate_completion
            
            response = await generate_completion(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.3  # Lower temp for reasoning
            )
            
            if response.error:
                return f"[LLM unavailable: {response.error}]"
            
            return response.text.strip()
        except Exception as e:
            return f"[Error: {str(e)}]"
    
    async def _retrieve_evidence(
        self,
        query: str,
        context: Optional[Dict],
        max_items: int
    ) -> List[Dict]:
        """Retrieve evidence from context and memory."""
        evidence = []
        
        # From context documents
        if context and "documents" in context:
            for doc in context["documents"][:max_items // 2]:
                evidence.append({
                    "id": doc.get("id", ""),
                    "content": doc.get("content", ""),
                    "source": "document"
                })
        
        # From context memories
        if context and "memories" in context:
            for mem in context["memories"][:max_items // 2]:
                evidence.append({
                    "id": mem.get("id", ""),
                    "content": mem.get("content", ""),
                    "source": "memory"
                })
        
        return evidence[:max_items]
    
    async def _extract_entities_from_query(self, query: str) -> List[str]:
        """Extract key entities from query for graph traversal."""
        # Simple entity extraction — future: use NER
        import re
        # Capitalized phrases as entities
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        # Also quoted terms
        quoted = re.findall(r'"([^"]+)"', query)
        return list(set(entities + quoted))[:5]
    
    def _format_steps_for_prompt(self, steps: List[ReasoningStep]) -> str:
        """Format reasoning steps for LLM prompt."""
        lines = []
        for step in steps:
            lines.append(f"Step {step.step_number}: {step.sub_question}")
            lines.append(f"Conclusion: {step.intermediate_conclusion}")
            if step.critique:
                lines.append(f"Critique: {step.critique}")
            lines.append("")
        return "\n".join(lines)
    
    def _compute_overall_confidence(self, steps: List[ReasoningStep]) -> float:
        """Compute overall confidence from step confidences."""
        if not steps:
            return 0.3
        
        confidences = [s.step_confidence for s in steps]
        # Weight later steps more (they build on earlier ones)
        weighted = sum(c * (i + 1) for i, c in enumerate(confidences))
        total_weight = sum(i + 1 for i in range(len(confidences)))
        
        return min(weighted / total_weight, 0.95)
    
    def _calibrate_confidence(self, trace: ReasoningTrace) -> ReasoningTrace:
        """Calibrate confidence for high-stakes queries."""
        # For high-stakes, be more conservative
        trace.overall_confidence = min(trace.overall_confidence, 0.8)
        trace.confidence_explanation += " | Calibrated for high-stakes (capped at 0.8)"
        return trace
    
    def get_recent_traces(self, limit: int = 10) -> List[ReasoningTrace]:
        """Get recent reasoning traces for review."""
        return sorted(
            self.trace_store,
            key=lambda t: t.latency_ms,
            reverse=True
        )[:limit]


# Singleton
_engine: Optional[ReasoningEngine] = None


def get_reasoning_engine() -> ReasoningEngine:
    """Get or create the global Reasoning Engine."""
    global _engine
    if _engine is None:
        _engine = ReasoningEngine()
    return _engine
