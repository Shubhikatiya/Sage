# Sage — Engineering Handbook
## Phase 10: Execution Engine

> Continues from Phase 01 (Foundation) through Phase 09 (Learning Engine).

---

## 1. Overview

Every engine up to this point produces information, understanding, or recommendations. The Execution Engine is where Sage crosses from advisor into actor — creating tasks, running workflows, sending notifications, and taking actions in external systems (calendar, email, file systems). This is architecturally the highest-risk subsystem in Sage, because it's the only one whose mistakes have consequences outside Sage's own data model.

The governing design constraint, carried from Phase 01's subsystem inventory and reinforced by the Execution Agent's spec in Phase 08 §5.6: **every externally-visible action requires an explicit approval boundary**, whether that's a one-time human click or a pre-authorized, narrowly-scoped standing permission. Nothing executes on inferred intent alone.

## 2. Goals

- Provide a task/workflow model expressive enough for real multi-step work (not just single reminders) while keeping every step auditable.
- Make the approval boundary a first-class architectural concept, not a UI afterthought — approval state lives in the data model, not just in a confirmation dialog.
- Support both explicit one-off actions ("send this email") and scheduled/recurring automation ("every Sunday, draft a weekly ReRoot field summary from the week's episodic memory") through the same execution model.
- Fail safely: an execution failure should never leave external state (a half-sent email, a partially-created calendar series) in an ambiguous condition without a clear record of what happened.

## 3. Responsibilities

**Owns:** task and workflow schema, the approval-state machine, scheduling of recurring executions (in coordination with the Scheduler Agent, Phase 08 §5.7), execution audit logging, integration adapters (calendar, email, notifications).

**Does not own:** deciding *what* should be done (Reasoning Engine's next-best-actions, Phase 06 §9, or explicit user requests) — Execution Engine carries out approved plans, it doesn't originate them.

---

## 4. Task & Workflow Model

```
Task {
  id: UUID
  description: text
  status: "proposed" | "approved" | "in_progress" | "completed" |
          "failed" | "rejected" | "cancelled"
  origin: "user_request" | "next_best_action" | "scheduled_automation"
  origin_ref: UUID              # the reasoning trace or schedule that produced it
  approval: ApprovalRecord | null
  scope: jsonb                   # explicit bounds — what this task is and
                                   # is NOT authorized to do
  due_date: timestamp | null
  depends_on: [task_id]
  execution_log: [ExecutionLogEntry]
}

Workflow {
  id: UUID
  name: text
  trigger: "manual" | "scheduled" | "event_driven"
  steps: [Task]                  # ordered or DAG-structured
  status: "active" | "paused" | "completed"
}

ApprovalRecord {
  approved_by: "user" | "standing_permission"
  approved_at: timestamp
  approval_scope: text            # what exactly was approved, verbatim
                                    # or structured — must match `scope`
                                    # on the Task it's attached to
  standing_permission_ref: UUID | null   # if pre-authorized, points to
                                           # the permission grant (§6)
}
```

The `scope` field is deliberately explicit and narrow — this is the direct implementation of the Execution Agent's mandate in Phase 08 §5.6 that it "does not improvise scope." A task to "send the finalized resume to [contact]" has a scope that does not implicitly cover "and also mention the ACT fellowship deadline" even if that seems helpful — additions require their own approval.

---

## 5. Architecture Diagram

```
   Reasoning Engine's       User's direct        Scheduler Agent's
   next-best-actions         request              recurring trigger
   (Phase 06 §9)                │                       │
        │                       │                       │
        └───────────────┬───────┴───────────────────────┘
                        ▼
              ┌─────────────────────┐
              │   Task Proposal Layer  │
              │   (creates Task, status │
              │    = "proposed")          │
              └──────────┬─────────────┘
                        ▼
              ┌─────────────────────┐
              │   Approval Gate (§6)    │
              └──────────┬─────────────┘
              approved   │   rejected → status="rejected", logged, done
                        ▼
              ┌─────────────────────┐
              │   Execution Agent       │──► Integration Adapters
              │   (Phase 08 §5.6)         │     (Calendar, Email,
              │                           │      Notifications, File ops)
              └──────────┬─────────────┘
                        ▼
              ┌─────────────────────┐
              │   Execution Log         │──► Memory Engine (episodic +
              │   (append-only)           │     temporal writes, Phase 02)
              └─────────────────────────┘
```

---

## 6. The Approval Gate

Two paths, both producing an `ApprovalRecord`:

```
Path A — One-time explicit approval:
  Task proposed → surfaced to user with full scope shown →
  user approves/rejects this specific instance →
  ApprovalRecord created, approved_by="user"

Path B — Standing permission:
  User pre-authorizes a narrow, recurring class of action once
  ("you may always create calendar holds for fellowship deadlines
  you detect, but never send emails without asking each time") →
  StandingPermission { scope_pattern: text, granted_at: timestamp,
                        revocable: true, revoked_at: timestamp | null } →
  matching future tasks auto-approve via this record, but every
  auto-approval is still logged with a reference back to the
  original grant — traceable, revocable, never silent
```

Standing permissions are scoped as narrowly as the user grants them — "create calendar holds for detected deadlines" does not implicitly cover "reschedule existing events" or "delete calendar holds." Scope expansion always requires a new, explicit grant. This is the execution-layer application of the same least-privilege principle used for per-agent tool scoping in Phase 08 §10.

### 6.1 Approval UI Contract

Whatever surfaces an approval request (chat, dashboard) must show, at minimum: the task description, the explicit scope, which integration/external system it touches, and — if it originated from a next-best-action (Phase 06 §9) — the evidence trace it's based on, so approval is never a blind click.

---

## 7. Scheduled & Recurring Automation

Coordinates directly with the Scheduler Agent (Phase 08 §5.7):

```
1. Workflow defined with trigger="scheduled" (e.g., weekly ReRoot
   field summary draft, every Sunday).
2. Scheduler Agent's persisted trigger state (Phase 08 §5.7 — survives
   restarts) fires the workflow at the scheduled time.
3. Each step in the workflow still goes through the Task Proposal
   Layer and Approval Gate individually — a recurring workflow is
   not a blanket standing permission for everything it contains;
   each step's scope is evaluated against existing standing
   permissions or requires fresh approval, same as any other task.
4. If a scheduled workflow's step requires approval that hasn't been
   granted, it surfaces as a pending approval rather than either
   silently skipping or silently executing.
```

---

## 8. Execution Log & Audit Trail

```
ExecutionLogEntry {
  task_id: UUID
  attempted_at: timestamp
  outcome: "success" | "failure" | "partial"
  external_reference: text | null    # e.g., calendar event ID, email
                                       # message ID — for verifying/
                                       # undoing the actual external effect
  error_detail: text | null
}
```

Every execution attempt — successful or not — is logged and, per Phase 09 §4, generates an outcome signal fed back into the Learning Engine. This is the concrete mechanism that closes the loop described in Phase 09 §1: a next-best-action that gets approved, executed, and succeeds reinforces the memory/reasoning that produced it; one that fails or gets rejected repeatedly is itself a learning signal about miscalibrated suggestions.

---

## 9. Failure Handling ("Fail Safely")

```
On execution failure mid-workflow:
  1. Halt the workflow at the failed step — do not proceed to
     dependent steps assuming success.
  2. Log outcome="failure" with full error_detail.
  3. If the failed step had an external side effect that partially
     completed (e.g., a calendar event was created but a follow-up
     notification failed), the external_reference is still recorded
     so the partial state is known and inspectable, not orphaned.
  4. Surface the failure to the user with the task's current real
     state — never report "done" when it wasn't, and never silently
     retry an action with external side effects without new approval
     (retrying "send email" without checking whether it actually
     sent could double-send).
```

---

## 10. API Design

```
POST /execute/propose_task
{
  "description": "...",
  "scope": { "action": "send_email", "recipient": "...",
             "constraints": "..." },
  "origin": "next_best_action",
  "origin_ref": "reasoning_trace_id"
}
→ { "task_id": "...", "status": "proposed", "requires_approval": true }

POST /execute/approve/{task_id}
{ "approved": true, "note": "..." }

POST /execute/standing_permission
{
  "scope_pattern": "create_calendar_hold WHERE category=fellowship_deadline",
  "revocable": true
}

GET /execute/task/{task_id}      // status + full execution log
POST /execute/task/{task_id}/cancel
```

---

## 11. Sequence Diagram — Next-Best-Action to Executed Task

```
Bring Me Back      Task Proposal    Approval Gate       User      Execution Agent   Memory Engine
     │                  │                 │                │             │                │
     │──suggested action►│                 │                │             │                │
     │  + evidence trace  │                 │                │             │                │
     │                  │──propose task────►│                │             │                │
     │                  │  (status=proposed) │                │             │                │
     │                  │                 │──surface for───►│             │                │
     │                  │                 │  approval        │             │                │
     │                  │                 │◄──approved───────│             │                │
     │                  │                 │──dispatch────────────────────►│                │
     │                  │                 │                                │──execute──────►│
     │                  │                 │                                │  (external)     │
     │                  │                 │◄──outcome: success─────────────│                │
     │                  │                 │                                │──write episodic►│
     │                  │                 │                                │  + outcome signal│
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Explicit `scope` field on every Task vs. free-text task description only | Explicit, structured scope | Free-text | Structured scope is what makes the Execution Agent's "never improvise beyond approved scope" mandate (Phase 08 §5.6) mechanically enforceable rather than just a prompt instruction hoping the model behaves |
| Standing permissions with narrow scope_pattern vs. broad "trust this workflow" toggles | Narrow, pattern-scoped | Broad per-workflow trust toggle | Broad toggles are how automation quietly does more than intended over time; narrow patterns keep every auto-approval traceable to a specific, deliberately-granted permission |
| Halt-on-failure vs. best-effort continue-through-workflow-failures | Halt (§9) | Continue, skip failed steps | Continuing past a failure risks executing dependent steps on a false assumption of prior success — halting and surfacing is slower but never silently wrong |

---

## 13. Scaling Strategy

Execution volume scales with how much the user chooses to automate — the architecture doesn't need to anticipate high throughput (this is a single-user system), so the priority is correctness and auditability over raw performance. The main scaling consideration is standing-permission pattern matching staying fast and unambiguous as the number of granted permissions grows; patterns are kept simple (attribute-match style, not arbitrary code) specifically to keep this tractable and auditable by inspection.

## 14. Security

- Integration adapters (calendar, email) hold credentials scoped as narrowly as the underlying API allows (e.g., calendar write-only where possible, not full account access).
- Every external action is logged with enough detail to manually verify/undo it — this is a security property as much as a UX one: if Sage's execution layer were ever compromised or malfunctioning, the audit log is what allows a full accounting of what actually happened externally.
- Standing permissions are revocable at any time via `DELETE /execute/standing_permission/{id}`, and revocation is immediate (in-flight tasks already approved under the permission complete, but no new tasks can auto-approve against a revoked grant).

## 15. Testing Strategy

- **Scope enforcement:** fixture tasks with a defined scope, assert the Execution Agent's tool calls never exceed it — this should be tested as a hard invariant, not a spot check.
- **Approval gate correctness:** standing-permission pattern matching tested against both matching and deliberately-adjacent-but-not-matching scopes (the near-miss cases are where scope creep bugs hide).
- **Failure handling:** simulated mid-workflow failure, assert halt behavior, correct logging of partial external state, and that dependent steps never execute.
- **Idempotency checks:** for actions with external side effects, assert retries (where they do occur, under fresh approval) don't double-execute against the same external reference.

## 16. Failure Recovery

Task and workflow state persists in Postgres (same pattern as the Multi-Agent task graph, Phase 08 §12); a system restart resumes in-progress workflows from their last logged state rather than either silently dropping them or blindly re-executing from the start.

## 17. Future Improvements

- Richer workflow branching (conditional steps based on execution outcomes) beyond the current linear/DAG dependency model, once real usage patterns justify the added complexity.
- Undo/compensating-action support for a wider range of integrations (currently, undo is manual — the audit log tells the user what to undo, but doesn't automate it).
- Batch approval UX for reviewing several pending standing-permission-eligible tasks at once, if automation volume grows enough that per-task approval becomes friction rather than useful oversight.

---

*Next: Phase 11 — Conversation Engine (natural dialogue, persona, tone adaptation, memory injection, tool calling, streaming, conversation state).*
