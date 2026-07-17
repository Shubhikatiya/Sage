# Sage — Engineering Handbook
## Phase 13: Prediction Engine

> Continues from Phase 01 (Foundation) through Phase 12 (Knowledge Extraction Pipeline).

---

## 1. Overview

Every subsystem so far is reactive — it answers questions and reconstructs context when asked. The Prediction Engine is the first genuinely proactive subsystem: it continuously scans Memory and the Knowledge Graph for patterns that predict future states — forgotten work, approaching deadlines, project bottlenecks, energy patterns, and emerging opportunities — and surfaces them before the user asks.

This is also the subsystem where the risk of being *annoying* or *wrong* is highest. A prediction engine that cries wolf (surfaces low-confidence noise as if it were a genuine risk) trains the user to ignore it, which defeats its purpose. The central design discipline here is aggressive precision-over-recall tuning: better to miss a few genuine risks than to erode trust with false positives.

## 2. Goals

- Predict forgotten work (tasks/projects with unresolved status and no recent activity) using the same dependency-graph machinery already built for Bring Me Back (Phase 06 §7), generalized to run continuously rather than only on-demand.
- Predict deadlines and risks from Temporal memory and graph structure, surfaced with enough lead time to act.
- Predict project bottlenecks via dependency centrality (Phase 06 §6) — which stalled items are blocking the most downstream work.
- Detect emerging opportunities (a specific, scoped capability — full detail in the Opportunity Detection module of the "Human Intelligence Model" companion document; this phase defines the underlying prediction machinery it depends on).
- Keep false-positive rate low enough that predictions remain trusted — every prediction ships with a confidence score and is gated before surfacing, not just generated and shown.

## 3. Responsibilities

**Owns:** pattern-detection jobs (forgotten work, bottlenecks, deadline risk), prediction confidence scoring, the surfacing/suppression gate that decides what actually reaches the user, feedback capture on prediction quality (feeding the Learning Engine, Phase 09).

**Does not own:** deciding what to do about a prediction (Execution Engine, if the user acts on it) or the underlying graph/memory data it reads (Phases 02–03).

---

## 4. Architecture Diagram

```
                    ┌───────────────────────┐
   Scheduler ──────►│   Prediction Job Runner    │
   (periodic,         │   (daily cadence, plus       │
    Phase 08 §5.7)     │    event-triggered re-runs    │
                       │    on major graph changes)      │
                       └────────────┬───────────────┘
                                    │
       ┌──────────────┬─────────────┼─────────────┬──────────────┐
       ▼              ▼             ▼             ▼              ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
  │ Forgotten  │  │ Deadline   │  │ Bottleneck │  │ Energy     │  │ Opportunity    │
  │ Work        │  │ Risk        │  │ Detection  │  │ Pattern    │  │ Signal          │
  │ Detector    │  │ Detector    │  │            │  │ Detector   │  │ Detector        │
  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────────┘
        │              │             │             │              │
        └──────────────┴─────┬───────┴─────────────┴──────────────┘
                              ▼
                   ┌─────────────────────┐
                   │   Confidence Scoring     │
                   └──────────┬─────────────┘
                              ▼
                   ┌─────────────────────┐
                   │   Surfacing Gate           │  → only high-confidence,
                   │   (precision-tuned)          │    non-redundant predictions
                   └──────────┬─────────────┘     pass through
                              ▼
                   ┌─────────────────────┐
                   │   Prediction Store          │──► surfaced to Conversation
                   │   (all predictions logged,    │     Engine (proactive nudge)
                   │    including suppressed ones,  │     or Dashboard (Phase 16)
                   │    for calibration review)       │
                   └─────────────────────────────┘
```

---

## 5. Forgotten Work Detection

Directly generalizes the "stalled, no identified blocker" pattern from Bring Me Back (Phase 06 §7), running continuously instead of only on cold-open reconstruction:

```
Daily job:
  For each Task/Goal entity with status = unresolved:
    days_since_activity = now - last_related_event.occurred_at
    if days_since_activity > type_specific_threshold
       AND no blocked_by edge to another unresolved entity:
         → candidate "forgotten work" signal

  type_specific_threshold examples:
    - fellowship application deliverable: 7 days of inactivity
      (deadline-sensitive, shorter threshold)
    - a "someday" idea entity: 60 days (low urgency by nature,
      longer threshold — don't nag about things that were never
      meant to be immediate)
```

Thresholds are per entity-type defaults, overridable per individual entity if the user has indicated urgency/priority explicitly (Phase 09 correction/feedback signals directly adjust these).

---

## 6. Deadline Risk Detection

```
For each Temporal memory item with a future deadline:
    lead_time_remaining = deadline - now
    estimated_work_remaining = (from linked unresolved Task entities'
                                  historical completion-time patterns,
                                  where available; falls back to a
                                  conservative default estimate
                                  otherwise, explicitly flagged as
                                  low-confidence when it does)
    risk_score = f(lead_time_remaining, estimated_work_remaining,
                    recent_activity_rate_on_related_entities)

    if risk_score exceeds threshold:
        → surface as deadline risk, with explicit reasoning
          ("3 of 5 required deliverables still unresolved with
           9 days remaining, and no activity on this project in
           11 days")
```

Every deadline risk prediction is required to state its reasoning in the same terms the Reasoning Engine's confidence explanation does (Phase 04 §9) — never just "this seems risky," always the specific evidence.

---

## 7. Bottleneck Detection

Reuses `dependency_centrality` exactly as defined in Phase 06 §7 — an unresolved entity with high in-degree on `blocks`/`enables` edges is flagged as a bottleneck, run continuously rather than only during reconstruction:

```
For each unresolved entity:
    centrality = count(incoming blocks/enables edges from other
                        unresolved entities)
    if centrality >= threshold AND entity itself has been stalled
       (per §5's forgotten-work logic):
        → surface as bottleneck: "resolving X would unblock N
           other stalled items" — this framing (impact-forward,
           not just "you forgot this") is deliberately more
           actionable than a generic reminder
```

---

## 8. Energy Pattern Detection

The most exploratory of the prediction types, and the one held to the highest confidence bar before surfacing anything, since it touches on inferred personal state (adjacent to Belief-memory sensitivity, Phase 02 §13):

```
Signals (all behavioral, never inferred from content sentiment
alone — that would risk the "avoid claims about the person's
mental state" constraint):
    - message frequency/length patterns by time of day/week
    - task completion rate patterns
    - session length and pacing patterns

Only ever surfaced as an OPTIONAL, user-toggleable insight
("you tend to complete the most deep-work tasks between 9-11pm" as
a factual pattern observation), NEVER as a claim about mood,
motivation, or mental state — this stays strictly within observed
behavioral pattern territory, consistent with the constraint that
Sage describes patterns, it does not diagnose or psychoanalyze.
```

This module is explicitly the most conservative in the entire Prediction Engine — it defaults **off** and requires explicit opt-in, given how easily "energy prediction" could drift into unwelcome or overreaching territory if built carelessly.

---

## 9. Confidence Scoring & the Surfacing Gate

```
confidence(prediction) = f(
    evidence_strength,        # how much data supports the pattern
                                (single data point vs. established trend)
    pattern_consistency,        # has this pattern held before, or is
                                this the first occurrence
    graph_confidence,            # is this built on reviewed (Phase 03 §6)
                                or still-tentative entities
    prior_feedback_on_similar    # has the user previously dismissed
    predictions                  similar predictions (Phase 09 outcome
                                signals) — repeated dismissal suppresses
                                that prediction category going forward
)

surfacing_gate(prediction):
    if confidence < surfacing_threshold:
        → log only, do not surface (still stored for calibration
          review, per Phase 09 §7's outcome-tracking pattern)
    if redundant with a recently-surfaced, still-unresolved prediction:
        → suppress (don't repeat the same nudge every day)
    else:
        → surface, with full evidence trace attached
```

The `prior_feedback_on_similar` input is the direct mechanism by which the Prediction Engine avoids becoming annoying over time — a category of prediction the user has dismissed repeatedly gets a progressively higher surfacing threshold, the same asymmetric-but-inverse logic as the Learning Engine's threshold gate (Phase 09 §6), applied here to suppression rather than belief confidence.

---

## 10. API Design

```
GET /predict/forgotten_work
GET /predict/deadline_risks
GET /predict/bottlenecks
GET /predict/opportunities        // underlying signal only — full
                                    // Opportunity Detection Engine
                                    // logic lives in its own module
                                    // (companion "Human Intelligence
                                    // Model" document set)
GET /predict/energy_patterns       // only returns data if user has
                                    // opted in (§8)

POST /predict/feedback
{
  "prediction_id": "...",
  "feedback": "useful" | "not_useful" | "already_knew" | "wrong"
}
→ feeds directly into Phase 09's Learning Engine as an outcome/feedback signal
```

---

## 11. Sequence Diagram — Daily Prediction Job

```
Scheduler   Job Runner   Forgotten Work   Deadline Risk   Bottleneck   Confidence    Surfacing Gate
    │           │              │               │              │            │              │
    │──trigger─►│              │               │              │            │              │
    │           │──run all detectors (parallel)─►│──────────────►│           │              │
    │           │◄──candidates───────────────────────────────────│            │              │
    │           │──score─────────────────────────────────────────────────────►│              │
    │           │◄──scored predictions───────────────────────────────────────│              │
    │           │──gate──────────────────────────────────────────────────────────────────►│
    │           │◄──surfaced subset + suppressed subset (both logged)───────────────────────│
    │           │──write Prediction Store (all)                                              │
    │           │──notify Conversation Engine of surfaced predictions only                    │
```

---

## 12. Technology Choices & Tradeoffs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Precision-tuned surfacing gate (bias toward suppressing uncertain predictions) vs. recall-tuned (surface anything plausible) | Precision-tuned (§9) | Recall-tuned | A missed prediction is a minor cost (the user might catch it themselves, or it resurfaces on the next run with more evidence); a false-positive nudge trains the user to ignore the whole feature — asymmetric cost justifies the conservative default |
| Energy pattern detection opt-in and behavior-only vs. default-on and content-inferred | Opt-in, behavior-only (§8) | Default-on, inferring from message sentiment/content | Directly respects the constraint against making claims about the user's mental state; behavioral pattern observation (timing, frequency) is factual and low-risk, content-sentiment inference is exactly the kind of psychoanalysis the system must avoid |
| Reusing dependency_centrality/forgotten-work logic from Bring Me Back vs. building separate continuous-monitoring logic | Reuse (§5, §7) | Separate implementation | Same reuse-over-duplication discipline applied throughout this handbook (Phase 05 §11, Phase 06 §12) — the pattern-detection logic is identical whether triggered on-demand (Bring Me Back) or on a schedule (Prediction Engine); only the trigger and surfacing behavior differ |

---

## 13. Scaling Strategy

Daily job cost scales with the number of unresolved graph entities, which for a single-user system stays in a manageable range (hundreds, not millions) — the main cost driver is LLM calls for confidence scoring and evidence-trace generation, not the pattern-detection queries themselves (which are straightforward graph/SQL queries, cheap to run frequently).

## 14. Security

Predictions surfaced to the user carry the same sensitivity tiering as their underlying evidence — a deadline risk built on Belief/Reflection memory (Phase 02 §13) inherits that tier's access controls. Opportunity and bottleneck predictions involving other people (e.g., a mentor relationship) apply the same third-party-data handling as Relationship memory and Knowledge Graph Person entities (Phase 03 §14).

## 15. Testing Strategy

- **Threshold tuning tests:** fixture entities at varying staleness/deadline-proximity, assert forgotten-work and deadline-risk detectors fire at the intended thresholds, not earlier or later.
- **False-positive regression suite:** a curated set of "should NOT trigger a prediction" fixtures (e.g., a low-priority someday-idea entity that's been inactive for 40 days should not trigger the 60-day threshold) — this suite is as important as the positive-case tests, given the precision-first design goal.
- **Suppression logic:** repeated dismissal feedback on a prediction category, assert the surfacing threshold for that category actually rises per §9's mechanism.
- **Energy pattern opt-in enforcement:** assert `/predict/energy_patterns` returns nothing (not even degraded output) when the user hasn't explicitly opted in.

## 16. Failure Recovery

All predictions — surfaced and suppressed — are logged in the Prediction Store, so a bug in the surfacing gate is auditable and correctable retroactively (re-running the gate logic against already-scored historical predictions doesn't require re-running the expensive detection/scoring jobs from scratch).

## 17. Future Improvements

- Learned per-user thresholds (currently static defaults per entity type; could be tuned per user based on accumulated feedback, similar to the Learning Engine's per-attribute confidence evolution, Phase 09 §16).
- Richer bottleneck impact framing (currently counts direct blocking edges; could weight by the downstream importance of what's being blocked, not just the count).
- Seasonal/cyclical pattern detection (e.g., recognizing recurring high-load periods like semester exams or fellowship application seasons) once enough multi-year history exists to detect genuine cycles rather than one-off patterns.

---

*Next: Phase 14 — Personal Model (mission, values, identity, decision patterns, skills, strengths, weaknesses, habits, interests, life goals, communication style, career).*
