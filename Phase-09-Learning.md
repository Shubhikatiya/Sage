# Sage — Engineering Handbook
## Phase 09: Learning Engine

> Continues from Phase 01 (Foundation) through Phase 08 (Multi-Agent System).

---

## 1. Overview

Every other engine so far retrieves, reasons over, or writes memory in response to something happening right now. The Learning Engine is different: its entire job is to look backward across many interactions and update Sage's models — importance weights, Personal Model attributes, ranking parameters — so that *future* behavior improves. It is the mechanism that makes "self-improving" (Phase 01 §1.3) an actual property of the system rather than an aspiration.

The Learning Agent (Phase 08 §5.8) is the agent that performs this work; this phase specifies the engine underneath it — what signals feed learning, how updates are computed, and critically, how the system avoids overfitting to noise or a single bad data point.

## 2. Goals

- Turn four distinct signal types (corrections, feedback, behavior, outcomes) into calibrated updates to memory importance and Personal Model attributes.
- Require an evidence threshold before revising high-confidence beliefs — a single correction should never overwrite a well-established pattern built from months of consistent signal.
- Make every learned update traceable and reversible — since Personal Model attributes are versioned (mirroring Memory Engine's versioning, Phase 02 §8.3), a bad learning update can be rolled back, and the system can explain *why* it currently believes something about the user.
- Close the loop explicitly: every reasoning output or suggestion Sage makes should be able to generate an outcome signal later, not disappear into the void once delivered.

## 3. Responsibilities

**Owns:** signal ingestion and classification, the update-computation logic (how much a given signal should move a given weight/attribute), versioned Personal Model writes, reflection-loop scheduling.

**Does not own:** the Personal Model's schema itself (Phase 15 owns structure; Learning Engine owns how it changes over time), or the actual memory importance storage (Memory Engine owns the field; Learning Engine computes the value written to it).

---

## 4. The Four Signal Types

| Signal type | Source | Example | Update target |
|---|---|---|---|
| **Corrections** | User explicitly says Sage got something wrong | "No, I don't work at SELCO, I applied but didn't take the role" | Immediate high-weight update — corrections are the strongest signal type, since they're unambiguous first-party ground truth |
| **Feedback** | Explicit approval/disapproval of an output (thumbs up/down equivalent, or verbal "that's exactly right" / "that's not quite it") | User says a resume draft nailed the tone | Moderate-weight update to the relevant style/preference attribute in the Personal Model |
| **Behavior** | Implicit signal from how the user interacts, not what they say | User consistently sends short, directive messages with no small talk during work sessions (matches the "prefers completed deliverables over process explanation" standing pattern) | Low-weight-per-instance, but accumulates — behavioral patterns need repetition before they become confident model attributes |
| **Outcomes** | What happened after Sage suggested or did something | A next-best-action from Bring Me Back (Phase 06 §9) was acted on and led to a completed task; or a Reasoning Engine recommendation was later revealed to be wrong | Updates both Memory importance (was this evidence actually useful) and, at the aggregate level, confidence calibration for the Reasoning Engine (Phase 04 §9) |

---

## 5. Architecture Diagram

```
   Correction event ──┐
   Feedback event ─────┤
   Behavior signal ─────┼──► ┌─────────────────────┐
   Outcome event ───────┘    │   Signal Classifier     │
                              │   (routes by type,       │
                              │    attaches context)      │
                              └───────────┬─────────────┘
                                          ▼
                              ┌─────────────────────┐
                              │   Evidence Accumulator │
                              │  (per-attribute signal  │
                              │   history, not instant   │
                              │   overwrite)              │
                              └───────────┬─────────────┘
                                          ▼
                              ┌─────────────────────┐
                              │   Update Threshold      │
                              │   Gate (§6)               │
                              └───────────┬─────────────┘
                         below threshold  │  above threshold
                         (accumulate,      ▼
                          don't write)  ┌─────────────────────┐
                                        │  Versioned Write        │
                                        │  (Personal Model, or     │
                                        │   Memory importance       │
                                        │   score)                   │
                                        └───────────┬─────────────┘
                                                    ▼
                                        ┌─────────────────────┐
                                        │  Reflection Loop         │
                                        │  Scheduler (§8)            │
                                        └─────────────────────────┘
```

---

## 6. Update Threshold Gate — Avoiding Overfitting

This is the most important correctness mechanism in the Learning Engine, directly addressing the failure case flagged for the Learning Agent in Phase 08 §5.8.

```
should_update(attribute, new_signal) =
    if signal.type == "correction":
        → update immediately, high confidence
          (first-party corrections are near-ground-truth by definition)

    elif signal.type == "feedback":
        → update if accumulated_feedback_count(attribute) >= 2
          OR feedback explicitly contradicts a low-confidence attribute
          (don't let one compliment or complaint overwrite a
           well-established preference; do let it update something
           barely-established)

    elif signal.type == "behavior":
        → update only if pattern observed >= N times (default N=5)
          across >= 2 distinct sessions (a single intense session
          doesn't count as a stable pattern — cross-session repetition
          is required)

    elif signal.type == "outcome":
        → update Memory importance immediately (cheap, low-risk,
          naturally decays anyway per Phase 02 §7)
        → update Reasoning confidence calibration only in aggregate,
          batched (single outcomes are too noisy to react to
          individually — see §7)
```

Existing high-confidence attributes require *more* accumulated contradicting evidence to overturn than establishing a new low-confidence attribute requires to create — this asymmetry is deliberate: stable, well-supported beliefs about the user should be sticky, not whipsawed by recent noise.

---

## 7. Outcome-Based Confidence Calibration

Individual outcomes are too noisy to update Reasoning Engine confidence scoring (Phase 04 §9) in real time, so this runs as a batched, periodic process rather than an instant reaction:

```
Weekly calibration job:
  1. Pull all reasoning traces from the past week with a recorded
     outcome (acted-on-and-succeeded / acted-on-and-failed / ignored).
  2. Bucket by stated confidence level (e.g., 0.7-0.8 bucket).
  3. Compare bucket's stated confidence to actual success rate within
     that bucket.
  4. If systematically over- or under-confident in a bucket, adjust
     the confidence-scoring formula's weights slightly (Phase 04 §9
     inputs: evidence_coverage, evidence_agreement, evidence_recency).
  5. Log the calibration adjustment with before/after weights —
     versioned, reviewable, reversible like everything else.
```

This is a slow-moving, conservative process by design — confidence calibration is infrastructure the whole Reasoning Engine depends on, so it should not swing on a handful of data points from a single week; the job accumulates across weeks before making material adjustments.

---

## 8. Reflection Loops

Two distinct cadences, both scheduled by the Scheduler Agent (Phase 08 §5.7):

```
End-of-session reflection (Reflection Agent, Phase 08 §5.5):
  - Runs after a conversation session ends.
  - Produces Reflection-type memory: meta-observations about the
    session ("user was in rapid-iteration mode," "user corrected
    Sage twice on the same fact — may indicate the extraction
    pipeline mis-classified something upstream").
  - Feeds directly into the Signal Classifier (§5) as behavior signals.

Nightly/weekly reflection (Learning Agent + Reflection Agent, combined):
  - Runs the Update Threshold Gate over the day's/week's accumulated
    signals.
  - Runs the outcome-based calibration job (§7) on its weekly cadence.
  - Produces a versioned diff of Personal Model changes — this diff
    is itself stored, so "how has Sage's model of me changed this
    month" is a directly answerable question (a natural future
    Dashboard feature, Phase 16).
```

---

## 9. API Design

```
POST /learning/signal
{
  "type": "correction" | "feedback" | "behavior" | "outcome",
  "target": { "entity_type": "belief_memory" | "personal_model_attribute" |
              "memory_importance", "id": "..." },
  "content": "...",                  // e.g., the correction text
  "source_event_id": "..."
}

GET /learning/attribute_history/{attribute_id}
→ {
    "current_value": "...",
    "confidence": 0.84,
    "version_history": [
      { "version": 3, "value": "...", "changed_at": "...",
        "triggering_signals": [...], "evidence_count_at_change": 6 }
    ]
  }

POST /learning/calibration/run    // manual trigger for the weekly job,
                                    // in addition to its scheduled run
```

---

## 10. Sequence Diagram — A Correction Updating the Personal Model

```
User      Conversation Eng.   Signal Classifier   Evidence Accumulator   Personal Model
 │              │                    │                     │                   │
 │──"I didn't   │                    │                     │                   │
 │  actually    │                    │                     │                   │
 │  take that   │                    │                     │                   │
 │  SELCO       │                    │                     │                   │
 │  role"───────►│                    │                     │                   │
 │              │──correction────────►│                     │                   │
 │              │  signal              │                     │                   │
 │              │                    │──classify: correction►│                   │
 │              │                    │  target: career_       │                   │
 │              │                    │  history attribute      │                   │
 │              │                    │                     │──threshold gate:───►│
 │              │                    │                     │  correction = update│
 │              │                    │                     │  immediately          │
 │              │                    │                     │◄──versioned write────│
 │◄──confirms understanding───────────                     │  (v_N+1, old value    │
 │              │                                            │   retained in         │
 │              │                                            │   history)             │
```

---

## 11. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Asymmetric update thresholds (easy to establish low-confidence, hard to overturn high-confidence) vs. uniform threshold | Asymmetric (§6) | Same evidence bar regardless of current confidence | Directly prevents the overfitting failure mode named in Phase 08 §5.8 — a single recent interaction should not be able to erase months of consistent pattern |
| Batched weekly confidence calibration vs. real-time per-outcome adjustment | Batched (§7) | Real-time | Per-outcome adjustment is too noisy — a single unusual outcome (a good suggestion the user happened to ignore for unrelated reasons) shouldn't move a formula every other reasoning call depends on |
| Versioned Personal Model diffs vs. in-place update | Versioned (§8) | In-place | Consistent with Memory Engine's versioning discipline (Phase 02 §8.3); also directly enables a "how has Sage's understanding of me evolved" feature, which is a meaningfully different and valuable capability, not just an audit nicety |

---

## 12. Scaling Strategy

Signal volume scales with usage, not data size — the Evidence Accumulator's per-attribute signal history is naturally bounded (old signals below the relevant time window can be summarized/pruned once an attribute has crossed its confidence threshold, similar in spirit to Memory Engine consolidation). The weekly calibration job's cost scales with reasoning trace volume, which is already bounded by normal usage patterns.

## 13. Security

Learning Engine writes are exactly the kind of inferred-about-the-user content flagged as sensitive in Phase 02 §13 — Personal Model attribute updates inherit that encryption tier. Because corrections and feedback are explicit first-party statements, they carry an audit trail distinct from inferred behavior signals, so the user can always see "this is something I told Sage directly" vs. "this is something Sage inferred from patterns."

## 14. Testing Strategy

- **Threshold gate correctness:** fixture signal sequences (e.g., 4 behavior observations, then a 5th) assert the update fires exactly at the configured threshold, not before.
- **Asymmetry regression test:** a high-confidence attribute with strong history should require materially more contradicting signal than a fresh attribute needs to establish — tested explicitly as a comparison, not just each case in isolation.
- **Calibration job correctness:** synthetic reasoning-trace/outcome fixtures with known miscalibration (e.g., stated 0.9 confidence, 50% actual success) assert the weekly job detects and adjusts appropriately, without overcorrecting from a small sample.
- **Rollback test:** confirm a bad update can be reverted to a prior version and that reversion is itself logged (not a silent overwrite of the mistake).

## 15. Failure Recovery

Because every update is versioned, recovery from a bad learning update (e.g., a mis-classified correction that shouldn't have applied) is a rollback to the prior version, not a data-loss event — this is the direct payoff of the versioning decision in §11.

## 16. Future Improvements

- Per-attribute learned thresholds (currently a fixed N=5/2-session default for behavior signals; could vary by attribute type once enough calibration history exists to justify it).
- Active learning — Sage explicitly asking a clarifying question when a behavior pattern is ambiguous, rather than passively waiting for enough signal to accumulate, closing the loop faster for attributes that matter most to current tasks.
- Cross-user pattern libraries (strictly opt-in, anonymized, and only relevant if Sage ever moves beyond single-user architecture) — explicitly deferred, consistent with the single-tenant constraint from Phase 01 §1.5.

---

*Next: Phase 10 — Execution Engine (tasks, automation, scheduling, notifications, workflows, human approval loops).*
