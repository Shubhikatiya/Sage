# Sage MVP Technical Specification

## Status
- Version: 0.1
- Scope: Minimal viable product
- Goal: Chat + Upload + "Bring me back" works reliably

---

## What the MVP Does

1. **You chat with Sage.** Type anything. Share thoughts. Upload documents. Save research notes.
2. **Sage remembers everything.** Every thought, every document, every conversation, every research note — tied to projects you create.
3. **You ask "Bring me back to ReRoot."** Sage reconstructs everything about ReRoot: what you said, what you uploaded, what you researched, where you stopped, what ideas you had.
4. **You ask "What do I know about confidence?"** Sage fetches everything you've saved about confidence from ALL domains:
   - Psychology: "Self-efficacy theory by Bandura..."
   - Ancient wisdom: "Stoic view on inner strength..."
   - Philosophy: "Nietzsche on self-overcoming..."
   - Your own thought: "Confidence is built through action, not affirmation"
   - Book highlight: "From Atomic Habits: Identity-based habits..."
   
   Sage presents them grouped by source. YOU make the connections. YOU synthesize the meaning.

That's it. No deep synthesis. No hidden meaning. Just: ask a topic, get everything from everywhere. The human connects the dots.

---

## Core Philosophy: Retrieval, Not Synthesis

Sage does NOT (in the MVP):
- Find hidden meaning in your notes
- Force connections that aren't there
- Pretend to understand the "deeper truth"
- Synthesize across domains and present conclusions

Sage DOES (in the MVP):
- Retrieve every note, thought, and highlight related to your query
- Group them by source so you can see patterns yourself
- Present them clearly so YOU can decide what connects
- Stay humble: "Here is everything I found. You decide what it means."

### Future: Synthesis After Learning

After Sage has learned your patterns, vocabulary, and preferences over months (or years), synthesis can be added as an **opt-in, user-controlled** capability.

This is NOT the MVP. This is a Phase 3+ feature.

When activated:
- Sage might suggest: "You have thought X and note Y. They seem related. Would you like me to connect them?"
- The user ALWAYS approves or rejects
- Sage NEVER synthesizes without explicit permission
- The user can disable synthesis at any time

Until then: retrieval only.

---

## Idea Capture + Focus Guidance Flow

### The Problem

When working on a project, new ideas constantly appear. Some connect to current work. Some are entirely new. Without a system, the user either:

- Drops the current project to chase the new idea
- Forgets the new idea entirely
- Loses focus and momentum

### The Solution

Sage handles new ideas gracefully without derailing current work.

**How it works:**

1. **User shares a new idea.**
   - "I just thought of a way to monetize ReRoot through workshops"
   - "What if we built a version of Sage for students?"
   - "I read something about neuroplasticity that relates to our project"

2. **Sage captures and stores it immediately.**
   - Creates a note with full context
   - Tags it with the project if relevant
   - Stores it as a standalone idea if unclear
   - Never says "that's not important right now"

3. **Sage checks for connections.**
   - "This connects to your existing work on ReRoot revenue models"
   - "This is a completely new idea — no existing project match"
   - "This connects to 3 different projects"

4. **Sage gently guides back to current focus.**
   - "I've saved your idea under ReRoot/Revenue. You currently have 4 active projects. Your stated focus this week is [Current Focus]. Would you like to:
     - A) Continue current work and review this idea this weekend
     - B) Switch focus to explore this idea now
     - C) Add it to your 'Weekend Review' list"

5. **Weekend review.** Sage brings back all captured ideas:
   - "You captured 7 ideas this week. Here they are, grouped by project:
     - ReRoot: 3 ideas (including revenue model, partnerships, content)
     - Sage: 2 ideas (student version, AI integration)
     - Personal: 2 ideas (reading list, new research direction)
   - Which ones would you like to explore?"

### Key Principles

- **Never judge an idea.** Every idea is captured. Relevance is determined later.
- **Never lose an idea.** Capture is instant and automatic.
- **Preserve focus.** The default is "save and continue current work."
- **User chooses when to explore.** Weekend review is the norm. Immediate exploration is the exception.
- **Ideas accumulate context.** Over time, Sage shows: "You have 12 ideas about ReRoot revenue. Here they are in chronological order."

### Example Interactions

**Scenario 1: Idea connects to current project**

User: "Idea: ReRoot could offer certification programs for rural educators"

Sage: "Captured under ReRoot/Revenue-Models. This connects to your earlier thought about training programs. I've added it to your ReRoot idea list (now 8 ideas). Your current focus is finishing the ReRoot business plan. Would you like to explore this now, or review it this weekend?"

User: "Weekend"

Sage: "Saved. I'll include it in your weekend review. Current focus remains: ReRoot business plan."

**Scenario 2: Idea is completely new**

User: "What if we built a meditation app specifically for founders?"

Sage: "Captured as a new idea: 'Founder Meditation App.' No existing project match found. This is idea #23 in your unassigned ideas list. Your current focus is Sage-MVP. Would you like to:
- Start a new project for this?
- Keep it in ideas list for weekend review?
- Explore it now?"

User: "Ideas list"

Sage: "Saved. Added to your weekend review list. Current focus remains: Sage-MVP."

**Scenario 3: Weekend review**

User: "What did I capture this week?"

Sage: "You captured 9 ideas this week:

**ReRoot (4 ideas)**
- Certification programs for rural educators
- Partnership with local NGOs
- Subscription model for schools
- Government grant application

**Sage (3 ideas)**
- Student version of Sage
- Voice note integration
- Mind map visualization

**New Ideas (2 ideas)**
- Founder meditation app
- AI-powered journaling tool

Your active projects: ReRoot, Sage, AI Career.

Would you like to:
- Review ideas by project?
- See all ideas with connections?
- Pick one idea to explore now?"

---

## Deadlines + Daily Planning

### Deadline Tracking

**Purpose:** Sage reminds you as deadlines approach so nothing falls through the cracks.

**How it works:**

1. **You add a deadline.**
   - "Sage, my incubator pitch for ReRoot is due on July 15"
   - "Navgunjara grant application deadline is August 1"
   - "Sage MVP target: August 30"

2. **Sage stores it with context.**
   - Links it to the relevant project
   - Notes what needs to be prepared
   - Tracks how complete the submission is

3. **Sage reminds you as the deadline approaches.**
   - 7 days before: "Your ReRoot incubator application is due in 1 week. Here's your current progress: [summary]"
   - 3 days before: "3 days left. These items are still incomplete: [list]"
   - 1 day before: "Your application is due tomorrow. Here's a final checklist."

4. **You can ask anytime:**
   - "What deadlines do I have this month?"
   - "What do I need to prepare for the ReRoot pitch?"
   - "Am I on track for the Navgunjara grant?"

### Daily Planning

**Purpose:** Sage helps you plan your day based on your active projects, deadlines, and stated focus.

**How it works:**

1. **Ask "Plan my day"** (or Sage offers on morning load).

2. **Sage reviews:**
   - Active projects and their current state
   - Approaching deadlines
   - Pending decisions
   - Blocked work
   - Your stated focus for the week

3. **Sage suggests a daily structure:**
   ```
   Good morning. Based on your active projects:

   🔥 HIGH PRIORITY (Deadline approaching)
   - ReRoot incubator pitch (due in 3 days)
     → Finalize financial projections
     → Complete team slide

   📌 FOCUSED WORK (Your stated priority)
   - Sage-MVP: Complete backend API
     → Test document upload endpoint
     → Fix retrieval accuracy issue

   💡 REVIEW (Quick wins)
   - 2 captured ideas awaiting review
   - 1 meeting note to process

   ⚠ WAITING FOR
   - NGO partnership response (3 days pending)
   - Resume review from mentor

   Would you like me to adjust this plan?
   ```

4. **You can adjust or tell Sage how you feel.**
   - "Move Sage-MVP to afternoon"
   - "Add gym session at 5pm"
   - "Looks good"
   - **"I'm feeling low energy today"** → Sage reduces workload, moves non-essential tasks
   - **"I'm energized and focused"** → Sage prioritizes deep work, moves challenging tasks forward
   - **"I'm overwhelmed"** → Sage cuts the plan to essentials, suggests a short walk or break
   - **"I only have 3 hours today"** → Sage adjusts expectations, focuses on one critical task

5. **Sage tracks progress.**
   - "You planned to finish ReRoot financial projections today. Status?"
   - "You completed 3/5 items. Carry over the rest?"

**Iterative Planning Loop:**

Sage does not dictate your day. It proposes, you refine, together you finalize.

**How it works:**

1. **Sage proposes a plan.**

2. **You ask for changes.**
   - "Move this to afternoon"
   - "I don't have time for all of this, cut it in half"
   - "Add a break after lunch"
   - "Swap these two tasks"
   - "I want to focus on ReRoot today, deprioritize everything else"

3. **Sage updates and re-proposes.**
   - "Updated plan. I moved X to afternoon and cut Y. Does this work?"

4. **You approve or ask for more changes.**
   - This loop continues until you say "Looks good" or "Finalize this plan"

5. **Finalized plan appears on dashboard.**
   - Shows all tasks for today
   - Each task has a checkbox or status indicator
   - Tasks are ordered by time or priority

6. **You update Sage via chat as you complete tasks.**
   - "Done: ReRoot financial projections"
   - "Finished: Sent email to partner"
   - "Couldn't do: Team slide — ran out of time"
   - "Skipped: Reading — not in the mood"

7. **Sage updates the dashboard in real-time.**
   - Completed tasks get a ✅
   - Skipped/incomplete tasks get a ❌ or ⏳
   - Progress bar shows % complete

8. **End of day: Sage shows the final dashboard.**
   ```
   📊 TODAY'S PROGRESS

   ✅ Completed (4)
   - ReRoot financial projections
   - Sent email to partner
   - Reviewed captured ideas
   - Updated project status

   ❌ Not Completed (2)
   - Team slide for pitch (ran out of time)
   - Read research paper (skipped)

   ⏳ Carried to Tomorrow
   - Team slide for pitch
   - Read research paper

   📈 Completion Rate: 67%

   📝 Notes:
   You mentioned feeling low energy after lunch.
   Tomorrow might benefit from a lighter morning.
   ```

**Key Principles:**

- **Never dictate.** Sage suggests. You decide.
- **User controls energy context.** Sage does NOT assess your mood automatically. You tell Sage how you feel, and it adjusts.
- **Iterative refinement.** Plans are proposed, discussed, and finalized together.
- **Real-time updates.** Dashboard reflects your progress as you report it via chat.
- **End-of-day review.** Clear summary of what was done, what wasn't, and what carries forward.
- **No guilt.** Incomplete tasks are noted neutrally. Tomorrow is a new day.

---

## Data Model

### Project
```
project_id (string, uuid)
name (string) — "ReRoot", "Sage", "AI Career"
created_at (timestamp)
updated_at (timestamp)
status (string) — "active", "archived", "completed"
```

### Thought
```
thought_id (string, uuid)
project_id (string, foreign key)
content (text) — the actual thought/message
source (string) — "user_chat", "document_upload", "voice_note"
created_at (timestamp)
conversation_id (string, nullable) — ties thoughts to conversations
```

### Document
```
document_id (string, uuid)
project_id (string, foreign key)
filename (string)
content (text) — extracted text from PDF/txt/etc.
file_type (string) — "pdf", "txt", "md", "docx"
file_url (string) — where stored (S3/local)
created_at (timestamp)
```

### Conversation
```
conversation_id (string, uuid)
project_id (string, nullable) — if tied to a project
messages (json array) — [{role: "user", content: "..."}, {role: "sage", content: "..."}]
created_at (timestamp)
updated_at (timestamp)
```

### Research Note
```
note_id (string, uuid)
project_id (string, foreign key, nullable) — if tied to a project
title (string) — "Stoicism and Growth Mindset"
content (text) — full research note
source (string) — "book", "article", "podcast", "video", "own_thought", "conversation"
source_title (string) — e.g., "Atomic Habits" or "Huberman Lab Podcast"
source_author (string, nullable) — e.g., "James Clear"
page_number (string, nullable)
url (string, nullable) — link to original source
tags (json array) — ["psychology", "habits", "growth"]
created_at (timestamp)
updated_at (timestamp)
```

### Memory Vector (for RAG retrieval)
```
memory_id (string, uuid)
project_id (string)
content (text) — chunk of text for embedding
embedding (vector) — 1536 dimensions (OpenAI/text-embedding-3-small)
source_type (string) — "thought", "document", "conversation", "research_note"
source_id (string) — points to original thought/doc/convo/note
created_at (timestamp)
```

### Deadline
```
deadline_id (string, uuid)
project_id (string, foreign key) — which project this belongs to
title (string) — "Incubator Pitch Submission"
description (text) — what needs to be prepared
due_date (timestamp) — when it's due
status (string) — "not_started", "in_progress", "submitted", "completed"
priority (string) — "low", "medium", "high", "critical"
reminder_days (json array) — [7, 3, 1] — days before to remind
completed_at (timestamp, nullable)
created_at (timestamp)
```

### Daily Plan
```
plan_id (string, uuid)
date (date) — the day this plan is for
focus_areas (json array) — what the user wants to focus on
tasks (json array) — [{project_id, task, status, priority}]
completed_tasks (integer) — how many done
total_tasks (integer) — how many total
notes (text) — any end-of-day reflections
created_at (timestamp)
updated_at (timestamp)
```

---

## API Endpoints

### Projects
```
POST /api/projects
  body: { name: "ReRoot" }
  response: { project_id, name, created_at }

GET /api/projects
  response: [{ project_id, name, status, updated_at }]

GET /api/projects/:id
  response: { project_id, name, thoughts_count, documents_count, last_updated }
```

### Chat
```
POST /api/chat
  body: { project_id?: "...", message: "Bring me back to ReRoot" }
  response: { sage_response, conversation_id }
  
  — If project_id provided: retrieve project context first
  — If no project_id: Sage figures out which project from the message
  — Backend retrieves relevant memories via vector search
  — Sends to LLM with system prompt + retrieved context
  — Returns response + stores conversation
```

### Thoughts (Create)
```
POST /api/thoughts
  body: { project_id: "...", content: "Idea about rural distribution" }
  response: { thought_id, project_id, content, created_at }
  
  — Also creates a Memory Vector entry (chunked + embedded)
```

### Documents (Upload)
```
POST /api/documents/upload
  body: multipart/form-data { project_id: "...", file: <pdf/txt/md> }
  response: { document_id, filename, content_preview }
  
  — Extract text from file
  — Store in Documents table
  — Chunk text, create embeddings, store in Memory Vector table
```

### Retrieval (Internal)
```
POST /api/retrieve (internal endpoint, called by /api/chat)
  body: { project_id: "...", query: "Bring me back to ReRoot", top_k: 10 }
  response: { memories: [{content, source_type, source_id, similarity}] }
  
  — Vector search against Memory Vectors filtered by project_id
  — Return top_k most relevant chunks
```

### Deadlines
```
POST /api/deadlines
  body: { project_id: "...", title: "Incubator Pitch", due_date: "2024-07-15", priority: "high" }
  response: { deadline_id, project_id, title, due_date, status }

GET /api/deadlines
  response: [{ deadline_id, project_id, title, due_date, status, days_remaining }]

GET /api/deadlines/upcoming
  response: [{ deadline_id, project_id, title, due_date, days_remaining }]
  — Returns deadlines sorted by due_date (nearest first)
  — Default: next 30 days
```

### Daily Planning
```
POST /api/daily-plan
  body: { date: "2024-07-08", focus_areas: ["Sage-MVP", "ReRoot-pitch"], tasks: [...] }
  response: { plan_id, date, tasks, status }

GET /api/daily-plan/:date
  response: { plan_id, date, focus_areas, tasks, completed_tasks, total_tasks }

PUT /api/daily-plan/:plan_id/tasks/:task_id
  body: { status: "completed" }
  response: { task_id, status, completed_at }
```

---

## AI Integration

### System Prompt (for every chat)

```
You are Sage, an AI Chief of Staff with infinite memory.
You help the user manage their projects by remembering everything they share.

YOUR JOB IS RETRIEVAL, NOT SYNTHESIS.

When the user asks about a topic, you fetch everything related from their knowledge base.
You present it grouped by source. The user makes the connections. The user synthesizes.

RULES:
1. Answer ONLY from the user's own data (projects, thoughts, documents, conversations, research notes).
2. If the user asks "Bring me back to [Project]," reconstruct the project state from the provided context.
3. If the user asks about a topic (e.g., "confidence"), fetch ALL related entries from ALL domains.
   - Group them by source: "From your psychology notes...", "From your ancient wisdom research...", "From your own thoughts..."
   - Present each entry clearly with its source
   - Do NOT force connections. Do NOT say "this connects to that." Let the user decide.
4. Always cite your sources: "Based on your note from June 1..." or "You mentioned in a conversation last week..."
5. If you don't know, say "I don't see that in your data."
6. Never invent information. Never hallucinate.
7. Keep responses structured: use bullet points, headers, and clear sections.

IMPORTANT: Do not try to be clever. Do not find hidden patterns.
Just retrieve. Just present. The user is smarter than you about their own knowledge.

The user currently has these projects: [PROJECT_LIST]
```

### Retrieval + Synthesis Flow

1. User sends message: "Bring me back to ReRoot"
2. Backend:
   - Identify project_id for "ReRoot"
   - Generate embedding for the query
   - Search Memory Vectors: top 10 chunks where project_id = ReRoot
   - Also fetch: latest thoughts, latest documents, project metadata
3. Build prompt:
   ```
   System prompt + Project context + Retrieved memories
   ```
4. Send to LLM (Claude 3.5 Sonnet or GPT-4o-mini)
5. Return response to user
6. Store conversation in Conversations table
7. Store user's message + Sage's response as Thoughts (linked to project)

---

## Frontend (Chat Interface)

### Simple React App

```
+------------------+
| Sidebar          |
| - Projects list  |
| - New Project    |
+------------------+----+
| Chat Area             |
|                       |
| User: Bring me back   |
| to ReRoot             |
|                       |
| Sage: [structured     |
|  response]            |
|                       |
| +------------------+  |
| | Upload button    |  |
| | Text input       |  |
| | Send button      |  |
| +------------------+  |
+-----------------------+
```

### Features
- Left sidebar: list of projects, click to filter chat to that project
- Main area: chat messages (user right-aligned, Sage left-aligned)
- Input box at bottom: text + upload button (documents only)
- Sage responses: structured with headers, bullets, and source citations

### No Dashboard. No Mind Map. No Fancy UI.
Just a clean, functional chat that proves the memory works.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite + Tailwind CSS |
| Backend | Python + FastAPI |
| Database | SQLite (for MVP — single user) |
| Vector DB | ChromaDB (local, no external service) |
| AI Model | Claude 3.5 Sonnet via API (or GPT-4o-mini for cost) |
| Embeddings | OpenAI text-embedding-3-small |
| File Storage | Local filesystem (for MVP) |
| Deployment | Local first, then simple cloud host |

---

## MVP Success Criteria

1. Create a project named "ReRoot"
2. Upload 3-5 documents about ReRoot
3. Save 5-10 research notes from different domains (psychology, philosophy, ancient wisdom, personal thoughts)
4. Have 5-10 chat messages about ReRoot
5. Wait 1 week (or simulate by clearing context)
6. Ask: "Bring me back to ReRoot"
7. Sage reconstructs: what ReRoot is, where you stopped, key decisions, important documents, research collected
8. Ask: "What do I know about confidence?"
9. Sage fetches and presents:
   - All research notes mentioning confidence (grouped by domain)
   - Your own thoughts on confidence
   - Book highlights about confidence
   - Each entry clearly cited with its source
   - NO forced connections. NO "this connects to that." Just retrieval.
10. **Deadline reminder:** Sage notices an approaching deadline and reminds: "Your incubator application for ReRoot is due in 3 days. Here's what you've prepared so far..."
11. **Daily planning:** Ask "Plan my day" and Sage suggests priorities based on active projects, deadlines, and your focus
12. If Sage can do all of these reliably (80%+ accuracy), MVP succeeds

---

## Out of Scope (Explicitly)

- Dashboard / visual overview
- Mind maps
- Agent actions (email, scheduling)
- Web search
- Multi-user
- Mobile app
- Advanced AI agents
- Real-time sync
- Complex authentication

---

## Development Order

1. **Day 1-2:** Backend scaffold (FastAPI, SQLite, ChromaDB setup)
2. **Day 3-4:** Data model + API endpoints (projects, thoughts, documents)
3. **Day 5-6:** AI integration (retrieval + synthesis + system prompt)
4. **Day 7-8:** Frontend (React chat interface)
5. **Day 9-10:** Upload + embedding pipeline
6. **Day 11-12:** Testing with founder's actual data
7. **Day 13-14:** Polish, fix retrieval accuracy, iterate

---

*This is a living spec. It will change as we build.*
