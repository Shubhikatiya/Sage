# Sage MVP — Implementation Plan

## Status
- Version: 1.0
- Date: 2026-07-08
- Source: MVP_SPEC.md

---

## Phase 0: Project Setup (Day 1)

### Backend Setup
1. Create Python virtual environment
2. Install requirements (FastAPI, SQLAlchemy, ChromaDB, Anthropic/OpenAI SDKs)
3. Create basic FastAPI app structure
4. Setup SQLite database with SQLAlchemy models
5. Test API server starts without errors

### Frontend Setup
1. Create React app with Vite
2. Install Tailwind CSS
3. Create basic folder structure (components, pages, services)
4. Setup proxy for API calls to backend
5. Test dev server starts without errors

---

## Document Upload Feature

Sage must make it effortless for users to feed their knowledge. Upload is a first-class feature, not an afterthought.

### Supported Upload Types
- **PDF** — Books, research papers, reports, articles
- **TXT / MD** — Plain text notes, markdown files
- **DOCX** — Word documents
- **Images** — Screenshots, scanned pages (future: OCR)
- **Voice Notes** — Audio recordings (future: transcription)

### Upload Flow

**In Chat:**
- User drags and drops a file into the chat window
- Or clicks an upload button (paperclip icon)
- Sage immediately acknowledges: "Received [filename]. Processing..."

**In Dashboard:**
- Dedicated "Upload Documents" section
- Bulk upload supported (drop multiple files)
- Progress bar shows extraction and embedding status

### Processing Pipeline

1. **Receive file** — FastAPI endpoint accepts multipart upload
2. **Extract text** — PDF → text, DOCX → text, TXT → direct read
3. **Chunk text** — Split into ~500-1000 character chunks with overlap
4. **Generate embeddings** — Each chunk gets a vector embedding
5. **Store in ChromaDB** — With metadata: project_id, filename, chunk_index
6. **Store in Documents table** — Original file reference, extracted text preview
7. **Confirm to user** — "[Filename] processed. [N] chunks stored in [Project]."

### User Experience

**Single File Upload:**
```
User: [drops "Atomic_Habits.pdf" into chat]
Sage: 📄 Received Atomic_Habits.pdf (2.4 MB). Extracting text and storing...
Sage: ✅ Done! 847 chunks stored under "Books/Atomic Habits". You can now ask me about anything in this book.
```

**Bulk Upload:**
```
User: [drops 5 PDFs into dashboard upload area]
Sage: 📄 Processing 5 files...
Sage: ✅ All done!
  - ReRoot_Business_Plan.pdf (124 chunks)
  - Psychology_of_Money.pdf (312 chunks)
  - Meeting_Notes_June.pdf (45 chunks)
  - Research_Paper_AI.pdf (89 chunks)
  - Resume_2024.pdf (12 chunks)
```

**Retrieval After Upload:**
```
User: "What does Atomic Habits say about identity?"
Sage: "From your uploaded book Atomic Habits by James Clear, Chapter 2:

'You do not rise to the level of your goals. You fall to the level of your systems...'

You have 7 other highlights about identity from this book. Want me to show them all?"
```

### Document Management

- **View uploaded documents:** List all docs with metadata (filename, size, project, upload date)
- **Delete documents:** Remove from database + ChromaDB
- **Re-process:** If extraction failed, retry with different settings
- **Search within documents:** "Find the part about X in Atomic Habits"

---

## Phase 1: Core Data Layer (Day 1-2)

### Database Models (SQLite)
Create SQLAlchemy models for:
- Project
- Thought
- Document
- Conversation
- Research Note
- Deadline
- Daily Plan
- Memory Vector

### CRUD APIs
Create REST endpoints:
- POST /api/projects — Create project
- GET /api/projects — List projects
- GET /api/projects/:id — Get project details
- POST /api/thoughts — Create thought
- POST /api/documents/upload — Upload document
- POST /api/research/notes — Create research note
- POST /api/deadlines — Create deadline
- GET /api/deadlines — List deadlines
- POST /api/plans — Create daily plan
- GET /api/plans — List plans

### ChromaDB Setup
- Initialize ChromaDB client
- Create collection for memory vectors
- Test embedding storage and retrieval

---

## Phase 2: Document Processing (Day 2)

### Text Extraction
- PDF text extraction (PyPDF2 or pdfplumber)
- TXT/MD direct reading
- DOCX support (python-docx)
- Store extracted text in Document model

### Embedding Pipeline
- Split documents into chunks (500-1000 chars)
- Generate embeddings (OpenAI text-embedding-3-small or local model)
- Store in ChromaDB with metadata (project_id, source_type, source_id)
- Same pipeline for research notes and thoughts

---

## Phase 3: Retrieval System (Day 3)

### Vector Search
- Query embedding generation
- ChromaDB similarity search
- Filter by project_id
- Return top_k results with metadata

### Context Assembly
- Fetch project metadata
- Fetch recent thoughts/conversations
- Combine with vector search results
- Format as context string for LLM

### "Bring Me Back" Logic
- Special handling for "Bring me back" queries
- Fetch ALL project context (not just top_k)
- Prioritize: recent activity > key decisions > documents > thoughts

---

## Phase 4: AI Integration (Day 3-4)

### LLM Setup
- Claude 3.5 Sonnet via Anthropic API
- Fallback to GPT-4o-mini
- System prompt with retrieval-only philosophy
- Source attribution requirements

### Chat Endpoint
- POST /api/chat — Main chat endpoint
- Retrieve context from memory
- Build prompt: system + context + user message
- Call LLM with streaming response
- Store conversation in database

### Cross-Domain Retrieval
- When user asks about a topic (e.g., "confidence")
- Search across ALL projects and research notes
- Group results by source type
- Present without forced connections

---

## Phase 5: Frontend — Chat Interface (Day 4-5)

### Chat UI Components
- MessageList — displays conversation history
- MessageInput — text input with send button
- DocumentUploader — drag-and-drop file upload
- Sidebar — project list, new project button

### Chat Features
- Send message → display user message immediately
- Show loading state while waiting for Sage
- Display Sage response with markdown formatting
- Show source citations in response
- Auto-scroll to newest message

### Project Context
- Select project in sidebar → filters retrieval to that project
- Show active project in chat header
- Easy switch between projects

---

## Phase 6: Frontend — Dashboard (Day 5-6)

### Dashboard Components
- ProjectCards — active projects with status
- DeadlinePanel — upcoming deadlines with countdown
- DailyPlan — today's tasks with checkboxes
- QuickActions — "Plan my day", "Weekend review" buttons
- RecentActivity — last 5 things that happened

### Dashboard Features
- Load on app open (or via route)
- Real-time updates when tasks are completed
- Show completion percentage
- Display idea capture count for the week

### Task Completion Flow
- Checkbox next to each task
- Click → sends update to backend → updates status
- Completed tasks show ✅, incomplete show ⏳
- End of day: summary view with ✅ and ❌

---

## Phase 7: Idea Capture + Focus Guidance (Day 6-7)

### Idea Detection
- When user shares something that looks like an idea
- Classify: idea vs question vs command vs thought
- Store in special "Captured Ideas" bucket

### Connection Checking
- After storing idea, check vector similarity to existing content
- If match > threshold: "This connects to your work on X"
- If no match: "New idea saved to unassigned"
- If multiple matches: "This connects to X, Y, and Z"

### Focus Guidance Response
- After capturing idea, propose options:
  - Continue current work
  - Explore now
  - Add to weekend review
- Default: "Save and continue current focus"

### Weekend Review
- Special command: "Weekend review" or "What did I capture?"
- Group ideas by project
- Show count per project
- Allow user to select which to explore

---

## Phase 8: Deadline + Daily Planning (Day 7-8)

### Deadline Management
- Create deadline: title, project, due date, description
- Automatic reminders at 7, 3, 1 days before
- Show in dashboard with countdown
- Link to project context for "what needs to be prepared"

### Daily Plan Generation
- Command: "Plan my day"
- Backend reviews:
  - Active projects
  - Approaching deadlines
  - Pending tasks from yesterday
  - User's stated focus
- Generates structured plan with priorities
- Returns to frontend for display

### Iterative Plan Refinement
- User can request changes via chat
- "Move this to afternoon"
- "Cut this in half"
- "I'm low energy today"
- Sage updates plan and re-proposes
- Finalize with "Looks good"

### Progress Tracking
- User marks tasks complete via chat or dashboard
- "Done: [task name]"
- Backend updates status
- Dashboard shows real-time progress
- End of day: summary with completion rate

---

## Phase 9: Research Notes (Day 8-9)

### Note Creation Form
- Title, content, source, source_title, source_author
- Tags input (comma-separated)
- Optional: page number, URL
- Link to project (optional)

### Note Display
- Show in chat when retrieved
- Group by source type in cross-domain queries
- Show full metadata: "From Atomic Habits by James Clear, page 47"

### Note Retrieval
- Same vector search pipeline as documents
- Stored as "research_note" source_type
- Retrieved alongside documents and thoughts

---

## Phase 10: Testing + Iteration (Day 9-14)

### Founder Testing
1. Create real projects (ReRoot, Sage, AI Career)
2. Upload actual documents
3. Save real research notes
4. Chat for 30 minutes about each project
5. Wait 2-3 days
6. Test "Bring me back" for each project
7. Test cross-domain retrieval ("What do I know about confidence?")
8. Test idea capture and weekend review
9. Test daily planning and progress tracking

### Iterate Based on Feedback
- Fix retrieval accuracy issues
- Adjust system prompt based on response quality
- Add missing features discovered during testing
- Improve UI based on usage patterns

### Performance Optimization
- Query response time < 3 seconds
- Vector search accuracy > 80%
- Frontend loads in < 2 seconds

---

## File Structure

```
sage-core/
├── 05_implementation/
│   ├── backend/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # Database models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── crud.py              # Database operations
│   │   ├── vector_store.py      # ChromaDB operations
│   │   ├── ai_service.py        # LLM integration
│   │   ├── retrieval.py         # Context retrieval logic
│   │   ├── api/
│   │   │   ├── projects.py      # Project endpoints
│   │   │   ├── chat.py          # Chat endpoint
│   │   │   ├── documents.py     # Upload endpoints
│   │   │   ├── research.py      # Research note endpoints
│   │   │   ├── deadlines.py     # Deadline endpoints
│   │   │   ├── plans.py         # Daily plan endpoints
│   │   │   └── ideas.py         # Idea capture endpoints
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── App.jsx
│   │   │   ├── main.jsx
│   │   │   ├── index.css
│   │   │   ├── components/
│   │   │   │   ├── Chat.jsx
│   │   │   │   ├── MessageList.jsx
│   │   │   │   ├── MessageInput.jsx
│   │   │   │   ├── Sidebar.jsx
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── ProjectCard.jsx
│   │   │   │   ├── DeadlinePanel.jsx
│   │   │   │   ├── DailyPlan.jsx
│   │   │   │   ├── DocumentUploader.jsx
│   │   │   │   └── IdeaCapture.jsx
│   │   │   ├── pages/
│   │   │   │   ├── ChatPage.jsx
│   │   │   │   └── DashboardPage.jsx
│   │   │   └── services/
│   │   │       ├── api.js         # API calls
│   │   │       └── ai.js          # AI streaming
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   └── tailwind.config.js
│   └── README.md                  # Setup instructions
```

---

## Environment Variables

Create `.env` file in backend directory:
```
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./sage.db
CHROMA_DB_PATH=./chroma_db
```

---

## Running the MVP

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open browser to `http://localhost:5173`

---

## Post-MVP Features (Not in Phase 1-10)

- Mind map visualization
- Voice note upload and transcription
- Advanced agent actions (email, scheduling)
- Web search (prompt-triggered)
- Multi-user support
- Cloud hosting
- Mobile app
- Cross-domain synthesis (AI-suggested connections)

---

*This plan assumes 10-14 days of focused development. Adjust based on actual progress.*
