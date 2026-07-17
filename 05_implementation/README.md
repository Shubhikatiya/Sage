# Sage MVP - Setup and Run

## Prerequisites
- Python 3.8+
- Node.js 18+

## Backend Setup

1. Navigate to the backend directory:
```bash
cd 05_implementation/backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run the backend server:
```bash
python -m uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
```bash
cd 05_implementation/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Features Implemented

### Phase 1: Database Models + CRUD APIs
- Projects, Thoughts, Documents, Research Notes, Deadlines, Daily Plans
- Full CRUD operations for all entities

### Phase 2: Document Processing + Embedding
- PDF, DOCX, TXT, MD file upload and text extraction
- Automatic text chunking and embedding storage in ChromaDB

### Phase 3: Retrieval System
- Semantic search across all stored memories
- Project-scoped retrieval
- "Bring me back" context reconstruction

### Phase 4: AI Integration
- Chat endpoint with intent detection
- Retrieval-based responses (synthesis coming in future phases)
- Automatic memory embedding on creation

### Phase 5: Chat UI
- Real-time chat interface
- Project selection
- File upload support
- Loading states

### Phase 6: Dashboard
- Overview of projects, deadlines, and plans
- Quick action buttons
- Stats cards

## Project Structure

```
05_implementation/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database operations
│   ├── database.py          # DB configuration
│   ├── requirements.txt     # Python dependencies
│   └── services/
│       ├── document_processor.py
│       ├── embedding_service.py
│       └── retrieval_service.py
└── frontend/
    ├── package.json         # Node dependencies
    ├── vite.config.js       # Vite configuration
    ├── tailwind.config.js   # Tailwind CSS config
    └── src/
        ├── main.jsx         # React entry point
        ├── App.jsx            # Main app component
        ├── index.css          # Global styles
        ├── components/
        │   └── Sidebar.jsx
        ├── pages/
        │   ├── ChatPage.jsx
        │   └── DashboardPage.jsx
        └── services/
            └── api.js         # API client
```

## Next Steps

1. Install backend dependencies and verify the server starts
2. Install frontend dependencies and verify the UI loads
3. Test creating a project via the UI
4. Upload a document and verify text extraction
5. Test chat with "Bring me back to [Project]" queries
6. Add real AI integration (Anthropic Claude) for synthesis
7. Add authentication and user management
8. Deploy to cloud hosting
