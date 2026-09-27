# Sage v4 — AI Chief of Staff

An intelligent, memory-augmented AI companion that acts as your Chief of Staff. Sage learns from your documents, tracks your projects, and helps you make better decisions through a knowledge graph, episodic memory, and multi-phase reasoning engine.

> **Sage is an active engineering project rather than a finished personal AI system. Several core components have been implemented, but the current system does not yet fully deliver the behavior envisioned in the complete architecture. The repository documents both the implemented infrastructure and the staged development roadmap.**

## Architecture

Sage is being built around **20 engineering phases** covering everything from event buses and memory engines to predictions, security, and infrastructure. See the `Phase-01-Foundation.md` through `Phase-20-Roadmap.md` files for the full architecture specification.

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy + SQLite + ChromaDB (vector store)
- **Frontend:** React + Vite + Tailwind CSS
- **LLM:** Ollama (local) + optional cloud providers (Anthropic, OpenAI, Groq, Moonshot)
- **Memory:** Episodic, semantic, procedural, and 9 other memory types with decay scoring
- **Knowledge Graph:** Entity-relationship store with hybrid vector+graph retrieval
- **Reasoning:** Chain, tree, graph, reflection, and simulation modes

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama (local LLM server)

### Backend

```bash
cd 05_implementation/backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys (optional — Ollama works offline)

# Run
uvicorn main_v4:app --host 0.0.0.0 --port 8020
```

### Frontend

```bash
cd 05_implementation/frontend
npm install
npm run dev
```

### One-Click Launcher (Windows)

Run `Start-Sage-v4.ps1` to launch backend, frontend, and Ollama check automatically.

## Features

| Phase | Feature | Status |
|-------|---------|--------|
| 01 | Event Bus + Topology Registry + Circuit Breaker | ✅ |
| 02 | Memory Engine (12 types, decay, ranking) | ✅ |
| 03 | Knowledge Graph (entities, relationships, hybrid search) | ✅ |
| 04 | Reasoning Engine (chain, tree, graph, simulation) | ✅ |
| 05 | Context Engine (intent detection, attention budget) | ✅ |
| 06 | Bring Me Back (context reconstruction) | ✅ |
| 07 | Research Engine (web search, document ingestion) | ✅ |
| 08 | Multi-Agent System (9 agents) | ✅ |
| 09 | Learning Engine (signals, threshold gates) | ✅ |
| 10 | Execution Engine (tasks, approvals, audit) | ✅ |
| 11 | Conversation Engine (session state, turn planning) | ✅ |
| 12 | Knowledge Pipeline (extraction, chunking, sync) | ✅ |
| 13 | Predictions & Simulation | ✅ |
| 14 | Personal Model (typed attributes, versioning) | ✅ |
| 15 | World Model & Opportunities | ✅ |
| 16 | Dashboard (10 panels, real-time) | ✅ |
| 17 | Security Engine (classifications, audit log) | ✅ |
| 18 | Infrastructure (Docker, health checks) | ✅ |
| 19 | Technology Decisions Registry | ✅ |
| 20 | Implementation Roadmap & Progress | ✅ |

## Project Structure

```
sage-core/
├── 05_implementation/          # Working code
│   ├── backend/                  # FastAPI + services
│   │   ├── api/                  # API routes (all 20 phases)
│   │   ├── services/             # Business logic
│   │   ├── models_v4.py         # SQLAlchemy models
│   │   ├── database_v4.py       # DB setup
│   │   └── main_v4.py           # FastAPI app entry
│   └── frontend/                 # React app
│       ├── src/
│       │   ├── pages/            # Dashboard, Chat, KB, etc.
│       │   ├── components/       # Sidebar, panels, etc.
│       │   └── services/         # API client
│       └── package.json
├── sage/                         # Core Python modules
│   ├── core/                     # Event bus, LLM router, topology
│   └── services/                 # Memory, context, reasoning engines

├── Phase-01-Foundation.md      # Engineering handbook (20 phases)
├── ...
└── Start-Sage-v4.ps1           # Windows launcher
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# Optional cloud providers
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GROQ_API_KEY=...
MOONSHOT_API_KEY=...
```

## License

Private — Navgunjara Foundation
