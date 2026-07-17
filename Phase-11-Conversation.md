# Sage — Engineering Handbook
## Phase 11: Conversation Engine

> Continues from Phase 01 (Foundation) through Phase 10 (Execution Engine).

---

## 1. Overview

The Conversation Engine is the thin client-facing layer named explicitly as *not* the product in Phase 01 §1.1 — but "thin" doesn't mean unimportant. It's where every other subsystem's output actually reaches the user: context gets injected, tone gets calibrated, tool calls get orchestrated within a turn, and responses stream back. A perfectly designed memory/reasoning substrate is worthless if the conversational surface mishandles context injection or tone.

The design discipline here is keeping this layer genuinely thin: it should contain no independent "intelligence" of its own beyond dialogue mechanics. Every substantive decision (what's relevant, what to say, what to do) is delegated to Context/Reasoning/Execution Engines; the Conversation Engine's job is orchestrating a single turn cleanly and presenting it well.

## 2. Goals

- Assemble a single conversation turn from: resolved context (Phase 05), any needed reasoning (Phase 04), any needed tool/agent calls (Phase 08), and produce a coherent streamed response — without the Conversation Engine itself making judgment calls that belong elsewhere.
- Maintain persona and tone consistency that reflects the Personal Model's learned communication preferences (Phase 09/15), without that consistency requiring re-deriving preferences every turn.
- Handle multi-turn state correctly — a conversation is not a sequence of independent requests; working memory (Phase 02 §4.2) and intent detection (Phase 05 §6) both depend on turn-to-turn continuity being tracked precisely.
- Support tool calling within a turn (invoking Reasoning/Research/Execution as needed) with clean streaming — the user should see progress, not a long silent wait followed by a wall of text.

## 3. Responsibilities

**Owns:** conversation session state, turn assembly/orchestration, persona and tone application, streaming response delivery, tool-call sequencing within a turn.

**Does not own:** what context is relevant (Context Engine), what the actual reasoning/answer is (Reasoning Engine), what actions get taken (Execution Engine) — the Conversation Engine calls these and presents their outputs, never substitutes its own judgment for theirs.

---

## 4. Architecture Diagram

```
   User message ──► ┌─────────────────────────┐
                    │   Session State Manager     │
                    │   (turn history, working     │
                    │    memory pointer)             │
                    └──────────────┬─────────────┘
                                   ▼
                    ┌─────────────────────────┐
                    │   Context Resolution          │──► Context Engine (Phase 05)
                    │   Call                          │
                    └──────────────┬─────────────┘
                                   ▼
                    ┌─────────────────────────┐
                    │   Turn Planner                 │──► decides: does this turn
                    │   (does this need reasoning,     │    need Reasoning Engine?
                    │    research, or a direct           │    Research/Execution via
                    │    response?)                        │    the Orchestrator?
                    └──────────────┬─────────────┘         Or just a direct,
                                   ▼                         context-grounded reply?
                    ┌─────────────────────────┐
                    │   Persona/Tone Layer            │──► Personal Model (Phase 15)
                    │   (applies learned style          │     communication preferences
                    │    preferences to generation)       │
                    └──────────────┬─────────────┘
                                   ▼
                    ┌─────────────────────────┐
                    │   Streaming Response            │──► client
                    │   Generator                        │
                    └──────────────┬─────────────┘
                                   ▼
                    ┌─────────────────────────┐
                    │   Turn Finalizer                 │──► Memory Engine
                    │   (persist turn, emit             │     (working + conversation
                    │    memory.written event)            │      memory writes)
                    └─────────────────────────────────┘
```

---

## 5. Session State

```
ConversationSession {
  id: UUID
  started_at: timestamp
  last_turn_at: timestamp
  turns: [Turn]                    # bounded working set — older turns
                                     # roll off into Memory Engine's
                                     # conversation memory (Phase 02 §4.2)
                                     # rather than staying in live session state
  active_project_hint: entity_id | null   # sticky across turns until a
                                            # pivot is detected (Phase 05 §6)
  attention_state: AttentionSignal        # from Phase 05 §4, updated per turn
}

Turn {
  turn_number: int
  user_message: text
  resolved_context_ref: UUID        # what context was injected for this turn
  tool_calls: [ToolCallRecord]       # what was invoked mid-turn
  response: text
  reasoning_trace_id: UUID | null    # if Reasoning Engine was invoked
}
```

Working memory (Phase 02) is populated from `turns` directly — the Conversation Engine doesn't maintain a separate short-term memory; it's a thin view over the same Memory Engine everything else uses, consistent with the "engines aren't duplicated across subsystems" principle established repeatedly (Phase 05 §11, Phase 06 §12, Phase 07 §12).

---

## 6. Turn Planning — Deciding What a Turn Needs

Not every message needs the full weight of Reasoning Engine + Research + Execution. The Turn Planner is a lightweight classification step (small/fast model, same cost-tiering logic as Phase 05 §11's intent detection):

```
classify_turn(message, resolved_context):
    if message is a direct factual question fully answerable from
       resolved_context alone:
        → "direct" — generate response straight from context,
          no Reasoning Engine call needed (keeps simple Q&A cheap
          and fast)

    if message requires multi-step reasoning, evidence synthesis,
       or a decision/trade-off:
        → "reasoning" — invoke Reasoning Engine (Phase 04), chosen
          mode per its own classification logic

    if message requires new external information not in Memory/Graph:
        → "research" — invoke Research Engine (Phase 07) via the
          Orchestrator, likely combined with "reasoning" once
          findings return

    if message requests an action with external effect:
        → "execution" — propose a Task (Phase 10 §4), surface for
          approval, do not execute within the turn itself unless
          already covered by a standing permission
```

This classification is what keeps ordinary conversation fast and cheap while still routing genuinely complex requests through the full machinery — directly serving the cost-ceiling constraint from Phase 01 §1.5.

---

## 7. Persona & Tone Adaptation

Tone is not hardcoded — it's read from the Personal Model's communication-style attributes (Phase 09 behavioral learning, Phase 15 schema), applied as generation guidance rather than baked into a single fixed system prompt:

```
persona_directives = PersonalModel.get("communication_preferences")
  e.g.:
    - "prefers brutal honesty over validation" → generation guidance:
      do not soften critical feedback; lead with the substantive issue
    - "prefers targeted improvements over full rewrites" → when asked
      to revise something, default to diffs/specific changes, not
      wholesale regeneration, unless a full rewrite is explicitly requested
    - "prefers completed deliverables over process explanation" →
      suppress meta-commentary about approach; deliver the output
    - "pushes back when Claude over-explains" → keep responses tight,
      avoid restating the request back before answering it
```

These directives are exactly the standing behavioral patterns the Learning Engine (Phase 09) accumulates evidence for over time — the Conversation Engine doesn't independently infer tone each session; it reads the current, versioned Personal Model state and applies it, and if the user's actual behavior in a session contradicts a stored preference, that contradiction becomes a new behavior signal (Phase 09 §4) rather than the Conversation Engine silently overriding stored preferences on a hunch.

---

## 8. Tool Calling Within a Turn

```
1. Turn Planner determines a turn needs Reasoning/Research/Execution.
2. Conversation Engine issues the call(s) — sequential if dependent
   (research findings feed reasoning), parallel if independent.
3. Streaming: partial progress is surfaced to the client as tool
   calls execute (e.g., "researching..." / "checking your active
   projects..." status markers), not a silent wait followed by a
   single blob — directly serves the "protects the user's attention"
   design principle from Phase 01 by not leaving them staring at
   nothing during a multi-second multi-agent call chain.
4. Once all needed calls resolve, the Persona/Tone Layer generates
   the final streamed response incorporating their outputs.
```

---

## 9. API Design

```
POST /chat/turn
{
  "session_id": "...",
  "message": "...",
  "stream": true
}

→ (streamed) Server-Sent Events:
  event: status
  data: { "stage": "resolving_context" }

  event: status
  data: { "stage": "researching", "detail": "..." }

  event: token
  data: { "text": "..." }

  event: done
  data: { "turn_id": "...", "reasoning_trace_id": "...",
          "pending_approvals": [...] }

GET /chat/session/{id}/history
POST /chat/session/{id}/end        // triggers end-of-session
                                     // reflection (Phase 09 §8)
```

---

## 10. Sequence Diagram — A Turn Requiring Research + Reasoning

```
User    Conversation Eng.   Turn Planner    Context Eng.   Research    Reasoning   Persona Layer
 │            │                  │               │            │           │            │
 │──message──►│                  │               │            │           │            │
 │            │──resolve────────────────────────►│            │           │            │
 │            │◄──context──────────────────────────            │           │            │
 │            │──classify───────►│               │            │           │            │
 │            │◄──"research+     │               │            │           │            │
 │            │   reasoning"      │               │            │           │            │
 │            │──stream: "researching"──────────────────────────────────────────────►(client)
 │            │──dispatch────────────────────────────────────►│           │            │
 │            │◄──findings────────────────────────────────────│           │            │
 │            │──stream: "reasoning"─────────────────────────────────────────────────►(client)
 │            │──dispatch─────────────────────────────────────────────────►│            │
 │            │◄──answer + trace────────────────────────────────────────────│            │
 │            │──apply persona───────────────────────────────────────────────────────►│
 │            │◄──toned response──────────────────────────────────────────────────────│
 │            │──stream tokens───────────────────────────────────────────────────────────►(client)
 │            │──finalize turn (write to Memory Engine)                                    │
```

---

## 11. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Lightweight Turn Planner classification vs. always invoking full Reasoning Engine | Classify first (§6) | Route every message through Reasoning Engine | Most conversational turns are simple context-grounded Q&A; always invoking full reasoning wastes cost/latency and works against the Phase 01 cost-ceiling constraint |
| Persona as data (Personal Model attributes) vs. persona as a fixed system prompt | Data-driven (§7) | Fixed prompt | A fixed prompt can't reflect the Learning Engine's evolving understanding of communication preferences without a manual prompt-editing step every time; reading from the versioned Personal Model keeps tone current automatically |
| Streaming status markers during tool calls vs. silent wait + single response | Streaming status (§8) | Silent wait | Directly serves the "protects the user's attention" principle — visible progress during multi-second agent chains is a materially better experience than an unexplained delay |
| Working memory as a thin view over Memory Engine vs. Conversation Engine maintaining its own short-term store | Thin view (§5) | Separate short-term memory store | Avoids the two-sources-of-truth problem already ruled out for Bring Me Back (Phase 06 §12) and Research Notebooks (Phase 07 §12) — same principle applied consistently at this layer |

---

## 12. Scaling Strategy

Conversation Engine load scales with concurrent sessions, which for a single-user system is inherently small (one user, at most a handful of devices/sessions at once) — this is the one subsystem in the handbook where "scale" mostly means "don't be slow," not "handle high concurrency." Streaming and the lightweight Turn Planner classification (§6) are the primary latency levers.

## 13. Security

Session state does not persist raw credentials or execution-adapter secrets (those live in the Execution Engine's integration layer, Phase 10 §14) — the Conversation Engine only ever sees task proposals and approval prompts, never the underlying integration credentials directly.

## 14. Testing Strategy

- **Turn classification accuracy:** labeled test set of messages with expected classification (direct/reasoning/research/execution), regression-tested on every Turn Planner change.
- **Persona consistency:** given a fixed Personal Model state with known communication preferences, assert generated responses reflect them (e.g., a response to a flawed draft should lead with substantive critique, not hedge it away, when "prefers brutal honesty" is an active preference).
- **Session continuity:** multi-turn fixture conversations, assert working memory and `active_project_hint` carry correctly across turns and reset appropriately on detected pivots (Phase 05 §6).
- **Streaming correctness:** assert status events arrive before their corresponding tool call completes (not after, which would defeat the purpose), and that token streaming doesn't block on trailing async writes (Turn Finalizer's memory write happens after the response is already delivered, mirroring the non-blocking write pattern from Phase 02 §10).

## 15. Failure Recovery

If a mid-turn tool call fails (Reasoning/Research/Execution unavailable), the Conversation Engine degrades per each subsystem's own documented degradation mode (Phase 01 §2.4) and surfaces this honestly in the response rather than presenting a confident answer built on a silent fallback — consistent with the explainability principle applied at the conversational surface specifically.

## 16. Future Improvements

- Adaptive turn-planning confidence (currently a fixed classifier; could route to a confirmation step for genuinely ambiguous classifications rather than guessing, once real usage reveals how often misclassification actually causes friction).
- Multi-modal turns (voice input/output) — the streaming architecture here is designed to extend to audio without a structural rework, but audio-specific latency/UX work is explicitly deferred.
- Cross-session conversational continuity cues (explicitly referencing "last time we spoke about X" naturally within ordinary conversation, not just in an explicit Bring Me Back invocation) — a refinement once the underlying Context Engine layering (Phase 05) has enough real usage to tune well.

---

*Next: Phase 12 — Knowledge Extraction Pipeline (PDF, images, videos, audio, emails, notes, GitHub, Notion, Obsidian, calendar, messages, code repositories, research papers → structured knowledge).*
