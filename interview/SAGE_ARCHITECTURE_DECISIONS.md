# Sage Architecture Decisions & Design Patterns

> **Purpose:** Document every major architectural decision in Sage --- the decision itself, why it was made, alternatives considered, trade-offs, benefits, drawbacks, and future improvements. Also covers design patterns used in the system.

---

# Part A: Architecture Decisions

## Table of Decisions

1. [Why FastAPI instead of Flask/Django](#decision-1-why-fastapi-instead-of-flask-or-django)
2. [Why RAG instead of Fine-Tuning](#decision-2-why-rag-instead-of-fine-tuning)
3. [Why Vector Search](#decision-3-why-vector-search)
4. [Why SQLite instead of PostgreSQL](#decision-4-why-sqlite-instead-of-postgresql)
5. [Why ChromaDB instead of Pinecone/Qdrant](#decision-5-why-chromadb-instead-of-pinecone-or-qdrant)
6. [Why Local Models (Sentence Transformers) instead of API Embeddings](#decision-6-why-local-models-for-embeddings)
7. [Why Multi-Provider LLM instead of Single Provider](#decision-7-why-multi-provider-llm)
8. [Why Dual-Store Architecture (SQL + Vector)](#decision-8-why-dual-store-architecture)
9. [Why Synchronous SQLAlchemy (for now)](#decision-9-why-synchronous-sqlalchemy)
10. [Why Hardcoded Founder Context](#decision-10-why-hardcoded-founder-context)

---

## Decision 1: Why FastAPI instead of Flask or Django

### The Decision
Use FastAPI as the web framework for Sage's backend.

### Why It Was Made

1. **Automatic validation is non-negotiable:** With 15+ entities (LifeDomain, Thought, Document, ResearchNote, etc.), manual validation in Flask would be hundreds of lines of boilerplate. FastAPI + Pydantic reduces this to type annotations.

2. **Async readiness:** While we use synchronous SQLAlchemy today, FastAPI's native async support means we can migrate to async database drivers without changing frameworks.

3. **API documentation:** Swagger UI is auto-generated. For an MVP where the frontend and backend are developed in parallel, this eliminates the need to maintain separate API docs.

4. **Dependency injection:** The `Depends(get_db)` pattern is cleaner than Flask's global `g` object or Django's middleware.

### Alternatives Considered

| Framework | Why Rejected |
|-----------|--------------|
| Flask | Would require Flask-RESTful or manual validation. No native async. |
| Django | Overkill for an API-only service. ORM is heavier than SQLAlchemy. |
| Tornado | Async but complex. Smaller ecosystem. FastAPI is the modern successor. |
| Express.js (Node) | Different language. Team expertise is Python/AI. |

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Auto-validation and docs | Smaller ecosystem than Flask/Django |
| Async-native | Mixing sync/async can cause issues |
| Type safety | Steeper learning curve for beginners |

### Future Improvements

- Add middleware for request logging, rate limiting, and authentication.
- Implement background tasks using FastAPI's `BackgroundTasks` or Celery.

---

## Decision 2: Why RAG instead of Fine-Tuning

### The Decision
Use Retrieval-Augmented Generation (RAG) to ground LLM responses in user-provided documents, rather than fine-tuning a model on user data.

### Why It Was Made

1. **Data privacy:** Fine-tuning requires sending user data to a model provider's training pipeline. RAG keeps data local (embeddings are generated locally, stored locally).

2. **Cost:** Fine-tuning costs dollars per million tokens and requires retraining for new data. RAG is effectively free after initial embedding.

3. **Real-time updates:** New documents are immediately searchable. With fine-tuning, you'd need to retrain the model.

4. **Attribution:** RAG can cite which document the answer came from. Fine-tuning bakes knowledge into weights, making attribution impossible.

5. **MVP speed:** RAG works with off-the-shelf models. Fine-tuning requires infrastructure, expertise, and time.

### When Fine-Tuning Would Be Better

- If Sage needed to learn the founder's writing style for content generation.
- If the knowledge base were static and small (e.g., a FAQ).
- If retrieval latency were unacceptable (though caching solves this).

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Keeps data private | Retrieval quality depends on embeddings |
| No training costs | Requires vector database infrastructure |
| Instant updates | Context window limits how much can be retrieved |
| Attributable answers | More complex architecture |

### Future Improvements

- Implement reranking (e.g., Cohere Rerank) to improve retrieval quality.
- Add query expansion to improve recall.
- Explore hybrid search (sparse + dense) for better results.

---

## Decision 3: Why Vector Search

### The Decision
Use dense vector embeddings and approximate nearest neighbor (ANN) search for memory retrieval.

### Why It Was Made

Traditional search (SQL `LIKE`, Elasticsearch, inverted indexes) finds exact word matches. Vector search finds **semantic matches** --- "dog" and "puppy" are close in vector space even though they share no letters.

For Sage, this is critical because:
- Users ask questions using different words than they used when storing information.
- "What do I know about agency?" should match a document about "personal control and self-determination."
- "Bring me back" queries are vague and require semantic understanding.

### Alternatives Considered

| Approach | Why Rejected |
|----------|--------------|
| SQL Full-Text Search | No semantic understanding. "AI" won't match "artificial intelligence." |
| Elasticsearch | Good for keyword search, but semantic search requires additional plugins. |
| BM25 (sparse vectors) | Good for exact term matching, poor for semantic similarity. |
| Manual keyword tagging | Requires user effort, doesn't scale, misses implicit connections. |

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Semantic understanding | Embeddings can be biased or ambiguous |
| Handles paraphrasing | Requires vector database (added infrastructure) |
| Scales to millions of docs | ANN is approximate, not exact |
| Language-agnostic (mostly) | Quality depends on model choice |

---

## Decision 4: Why SQLite instead of PostgreSQL

### The Decision
Use SQLite as the primary relational database for the MVP.

### Why It Was Made

1. **Zero configuration:** SQLite is a file. No server to install, no port to configure, no user to create.
2. **Single-user MVP:** SQLite handles single-user local usage perfectly. Concurrency limits do not matter yet.
3. **Portability:** The database file can be moved, backed up, or versioned (with care).
4. **Migration path:** SQLAlchemy abstracts the database. Changing `sqlite:///./sage_v3.db` to `postgresql://...` is trivial.

### When to Migrate to PostgreSQL

- Multi-user concurrent access.
- Need for advanced features: JSONB, full-text search, user management.
- Horizontal scaling requirements.
- Need for replication/backup strategies.

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Zero setup | No concurrent writes |
| Single file | No network access |
| Easy backup | Limited data types |
| SQLAlchemy-compatible | Not suitable for production multi-user |

---

## Decision 5: Why ChromaDB instead of Pinecone or Qdrant

### The Decision
Use ChromaDB as the vector database.

### Why It Was Made

1. **Local-first:** ChromaDB runs locally with no API keys, no network calls, and no usage limits.
2. **Simplicity:** pip install, create client, store/query. No cluster configuration, no shards, no replicas.
3. **Metadata support:** Can filter by metadata (domain ID, type) during queries.
4. **Persistent:** Data survives restarts.

### Alternatives Considered

| Database | Pros | Cons | Why Rejected |
|----------|------|------|--------------|
| Pinecone | Managed, fast, scalable | API keys, paid, network dependency | Wanted local-first |
| Weaviate | GraphQL, modular, fast | More complex setup | Chroma is simpler |
| Qdrant | Rust-based, filterable | Newer, smaller community | Chroma is more mature |
| FAISS | Meta's library, extremely fast | No persistence, no metadata | Chroma wraps FAISS with persistence |

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Local and free | Single-node only |
| Simple API | Less performant at massive scale |
| Metadata filtering | Smaller ecosystem |
| Python-native | No distributed mode yet |

### Future Improvements

- Migrate to Pinecone or Weaviate for cloud deployment.
- Or use Chroma's server mode with replication.

---

## Decision 6: Why Local Models for Embeddings

### The Decision
Use `sentence-transformers/all-MiniLM-L6-v2` running locally for embeddings instead of API-based embedding services (OpenAI, Cohere).

### Why It Was Made

1. **Cost:** API embeddings cost money per token. Local embeddings are free.
2. **Latency:** No network round-trip. Embedding happens in-process.
3. **Privacy:** User documents never leave the machine during embedding.
4. **Offline capability:** Sage works without internet after initial setup.

### Alternatives Considered

| Service | Cost | Latency | Why Rejected |
|---------|------|---------|--------------|
| OpenAI text-embedding-3 | $0.02/1M tokens | Network | Cost and privacy |
| Cohere embed | $0.10/1M tokens | Network | Cost and privacy |
| Google Vertex AI | Varies | Network | Complexity |

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Free | Requires CPU/GPU resources |
| Private | Model quality is fixed (unless fine-tuned) |
| Fast (local) | Must manage model updates |
| Offline | More memory usage |

---

## Decision 7: Why Multi-Provider LLM

### The Decision
Abstract multiple LLM providers (Groq, Anthropic, OpenAI, Moonshot) behind a single interface.

### Why It Was Made

1. **Redundancy:** If one provider is down or rate-limited, another is tried.
2. **Cost optimization:** Use free tiers and cheaper providers for simple tasks.
3. **Speed:** Groq offers the fastest inference (tokens per second) in the industry.
4. **Flexibility:** Users can choose their preferred provider via environment variable.

### How It Works

```python
PREFERRED_PROVIDER = os.environ.get('LLM_PROVIDER', 'groq').lower()

def generate_response(user_message, context_data=None):
    if PREFERRED_PROVIDER == 'anthropic' and get_anthropic_client():
        return _call_anthropic(prompt, system_prompt)
    elif get_groq_client():
        return _call_groq(prompt, system_prompt)
    elif get_openai_client():
        return _call_openai(prompt, system_prompt)
    else:
        return _fallback_response(user_message, context_data)
```

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Redundancy | Must handle different APIs |
| Cost optimization | Each provider has different rate limits |
| Speed | Must normalize response formats |
| User choice | More configuration complexity |

---

## Decision 8: Why Dual-Store Architecture

### The Decision
Use SQLite for structured data and ChromaDB for vector data.

### Why It Was Made

This is the classic "polyglot persistence" pattern --- using the right database for the right job.

**SQLite handles:**
- Relationships (LifeDomain has many Thoughts)
- Constraints (foreign keys, NOT NULL)
- Transactions (ACID guarantees)
- Structured queries (get all documents for a domain)

**ChromaDB handles:**
- Semantic similarity (find documents about "agency")
- High-dimensional search (384-dimension vectors)
- Approximate nearest neighbors (fast, scalable)

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Right tool for each job | Data consistency across stores |
| Optimized performance | Two systems to maintain |
| Separation of concerns | Backup strategy must cover both |

### Future Improvements

- Use PostgreSQL with pgvector extension to unify structured and vector storage.
- Or keep dual-store but add a synchronization layer.

---

## Decision 9: Why Synchronous SQLAlchemy

### The Decision
Use SQLAlchemy 1.x synchronous ORM in FastAPI endpoints.

### Why It Was Made

1. **Simplicity:** Synchronous code is easier to debug and reason about.
2. **MVP pragmatism:** For a single-user local app, async provides no measurable benefit.
3. **Library compatibility:** Many Python libraries (including some document processors) are sync-only.

### The Async Migration Path

SQLAlchemy 2.0 introduces `create_async_engine()` with async drivers like `aiosqlite` and `asyncpg`. The migration involves:
1. Upgrading SQLAlchemy to 2.0.
2. Changing the engine to async.
3. Adding `await` to all database calls.
4. Using `async`/`await` in FastAPI endpoints.

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Simple, debuggable | Blocks the event loop during DB calls |
| Works with sync libraries | Lower throughput under load |
| Faster development | Not suitable for high-concurrency |

---

## Decision 10: Why Hardcoded Founder Context

### The Decision
Store the founder's project knowledge in a Python dictionary (`founder_context.py`) rather than deriving it from documents.

### Why It Was Made

1. **Reliability:** In the MVP, documents may be sparse or ambiguous. Hardcoded knowledge ensures Sage always has something meaningful to say.
2. **Founder's explicit intent:** The founder knows their projects better than any automatic extraction.
3. **Speed:** No need to parse documents at runtime. The context is loaded instantly.
4. **Fallback:** When the LLM fails, the fallback synthesizer uses this hardcoded knowledge.

### Future Improvements

- Move founder knowledge to the database so it can be edited via UI.
- Add versioning to track how understanding evolves.
- Eventually replace with fully automatic extraction as document volume grows.

### Trade-offs

| Benefit | Drawback |
|---------|----------|
| Always reliable | Requires code changes to update |
| Fast | Not scalable to many users |
| Founder's true intent | Static unless manually updated |

---

# Part B: Design Patterns

## Pattern 1: Repository Pattern (CRUD Module)

### Definition
The Repository Pattern abstracts data access logic into a separate layer. The rest of the application interacts with repositories, not the database directly.

### Problem Solved
Without this pattern, database queries are scattered across endpoint handlers. This leads to duplication, tight coupling, and difficulty testing.

### Implementation in Sage

```python
# crud.py --- The repository layer
def create_life_domain(db: Session, domain: schemas.LifeDomainCreate):
    db_domain = models.LifeDomain(**domain.model_dump())
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    return db_domain

def get_life_domains(db: Session, layer: Optional[str] = None):
    query = db.query(models.LifeDomain)
    if layer:
        query = query.filter(models.LifeDomain.layer == layer)
    return query.order_by(desc(models.LifeDomain.updated_at)).all()
```

The endpoint handlers in `main.py` call these functions instead of writing SQL directly.

### Advantages
- **Testability:** Mock the repository layer for unit tests.
- **Maintainability:** Change database logic in one place.
- **Readability:** Endpoint handlers focus on HTTP concerns, not SQL.

### Disadvantages
- **Indirection:** Adds a layer of abstraction.
- **Boilerplate:** Each entity needs CRUD functions.

### Interview Questions
- "Why use a repository pattern instead of writing SQL in the endpoint?"
- "How would you test a repository layer?"
- "What are the alternatives?" (Active Record pattern, DAO pattern)

---

## Pattern 2: Dependency Injection (FastAPI `Depends`)

### Definition
Dependency Injection is a technique where objects receive their dependencies from external sources rather than creating them internally.

### Problem Solved
Without DI, database connections would be global variables or singletons. This makes testing impossible and creates hidden dependencies.

### Implementation in Sage

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post('/api/chat')
def chat(message: ChatMessage, db: Session = Depends(get_db)):
    # db is injected automatically
    pass
```

### Advantages
- **Testability:** Pass a mock database session in tests.
- **Resource management:** `get_db()` handles session lifecycle.
- **Decoupling:** Endpoints don't know how to create sessions.

### Interview Questions
- "What is dependency injection and why is it useful?"
- "How does FastAPI's `Depends` work under the hood?"
- "What would break if you used a global database connection instead?"

---

## Pattern 3: Strategy Pattern (Multi-Provider LLM)

### Definition
The Strategy Pattern defines a family of algorithms, encapsulates each one, and makes them interchangeable.

### Problem Solved
Different LLM providers have different APIs, pricing, and capabilities. The application should not be tightly coupled to one provider.

### Implementation in Sage

```python
def generate_response(user_message, context_data=None):
    if PREFERRED_PROVIDER == 'anthropic' and get_anthropic_client():
        return _call_anthropic(prompt, system_prompt)
    elif get_groq_client():
        return _call_groq(prompt, system_prompt)
    elif get_openai_client():
        return _call_openai(prompt, system_prompt)
    else:
        return _fallback_response(user_message, context_data)
```

Each `_call_*` function is a strategy. The caller (`generate_response`) does not care which strategy is used.

### Advantages
- **Flexibility:** Add new providers without changing the caller.
- **Testability:** Test with a mock strategy.
- **Resilience:** Fallback to another strategy on failure.

### Interview Questions
- "Name a design pattern that allows interchangeable algorithms."
- "How would you add a new LLM provider to Sage?"
- "What is the difference between Strategy and Factory patterns?"

---

## Pattern 4: Pipeline Pattern (Document Processing)

### Definition
The Pipeline Pattern chains together a sequence of processing steps, where the output of one step is the input of the next.

### Problem Solved
Document processing involves many steps (extract, summarize, classify, embed, store). Each step can fail independently and needs different resources.

### Implementation in Sage

```
Upload -> Extract Text -> Summarize -> Classify -> Store Document
                                            |
                                            v
                                    Generate Embedding
                                            |
                                            v
                                    Store in ChromaDB
                                            |
                                            v
                                    Extract Topics
                                            |
                                            v
                                    Update Domain Profile
```

### Advantages
- **Modularity:** Each step is independently testable.
- **Reusability:** The same summarizer is used for chat and documents.
- **Observability:** Log each step's duration and success/failure.

### Interview Questions
- "How would you make the document processing pipeline asynchronous?"
- "What happens if the embedding step fails? How do you ensure consistency?"
- "How would you add a step to the pipeline without breaking existing code?"

---

## Pattern 5: Fallback Pattern (LLM Fallback Synthesizer)

### Definition
The Fallback Pattern provides a secondary implementation that is used when the primary implementation fails.

### Problem Solved
LLM APIs are unreliable --- rate limits, outages, network issues. The system must work even when the LLM does not.

### Implementation in Sage

```python
def generate_response(user_message, context_data=None):
    llm_response = None
    # Try LLM strategies...
    if llm_response and len(llm_response) > 10:
        return llm_response
    # Fallback
    return _fallback_response(user_message, context_data)
```

The fallback synthesizer constructs responses from:
- Founder knowledge (`founder_context.py`)
- Domain profiles (stored in SQLite)
- Structured data (recent documents, topics)

### Advantages
- **Reliability:** System works without any LLM API.
- **Cost savings:** Can choose not to call LLMs for simple queries.
- **Transparency:** Fallback responses are deterministic and explainable.

### Interview Questions
- "How do you ensure your AI system works when the LLM is down?"
- "What are the trade-offs between LLM responses and rule-based responses?"
- "How would you monitor LLM failure rates?"

---

## Pattern 6: Observer Pattern (Topic Extraction & Profile Update)

### Definition
The Observer Pattern defines a one-to-many dependency between objects. When one object changes state, all dependents are notified and updated automatically.

### Problem Solved
When a document is uploaded, many things need to happen: store embedding, extract topics, update profile. These should not be hardcoded in the upload handler.

### Implementation in Sage

While Sage currently calls these sequentially, the architecture supports decoupling:

```python
# After document upload:
store_embedding(...)       # Observer 1
extract_and_store_topics(...)  # Observer 2
update_domain_profile(...)     # Observer 3
```

### Future Improvement
Use an event bus (Redis Pub/Sub, RabbitMQ) so observers run asynchronously.

### Interview Questions
- "How would you decouple document upload from profile updates?"
- "What are the benefits of async event processing?"
- "Name three message brokers and their trade-offs."

---

*This document is a living reference. Every new architectural decision should be added here with full depth.*
