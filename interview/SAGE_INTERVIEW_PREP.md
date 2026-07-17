# Sage Interview Preparation Guide

> **Purpose:** A comprehensive list of interview questions based on Sage, organized by difficulty and topic. Each question has a detailed answer you can use in technical interviews. Also includes a technical glossary.

---

## Table of Contents

- [11. Interview Questions](#11-interview-questions)
  - [Beginner](#beginner)
  - [Intermediate](#intermediate)
  - [Advanced](#advanced)
  - [System Design](#system-design)
  - [Architecture](#architecture)
  - [LLM](#llm)
  - [RAG](#rag)
  - [Backend](#backend)
  - [Python](#python)
- [12. Technical Glossary](#12-technical-glossary)

---

# 11. Interview Questions

## Beginner

### Q1: What is Sage?

**Answer:**
Sage is an AI Chief of Staff --- an agentic AI system with infinite memory designed for knowledge workers who manage complex, multi-year careers across many projects. Its core purpose is not productivity but **decision quality**. When a user returns to a project after weeks away, Sage reconstructs their context within minutes, eliminating the cognitive tax of saying "let me explain from the beginning."

### Q2: What tech stack does Sage use?

**Answer:**
- **Frontend:** React 18 + Vite + Tailwind CSS
- **Backend:** FastAPI (Python) with SQLAlchemy ORM
- **Database:** SQLite for structured data, ChromaDB for vector embeddings
- **LLM:** Multi-provider abstraction (Groq, Anthropic, OpenAI, Moonshot)
- **Embeddings:** Sentence Transformers (`all-MiniLM-L6-v2`)
- **Document Processing:** pdfplumber, PyPDF2, python-docx

### Q3: What is a Life Domain?

**Answer:**
A Life Domain is Sage's organizational unit. It represents a project, life area, knowledge topic, or system component. Domains belong to one of four layers:
- **Life:** Personal areas (Self, Career, Finance)
- **Project:** Active builds (Sage, Kaal, ReRoot)
- **Knowledge:** Research topics (AI, Human Development)
- **System:** Infrastructure (Memory, Tasks, Dashboard)

### Q4: How does Sage store memories?

**Answer:**
Sage uses a dual-store architecture:
1. **SQLite** stores structured data (domain names, document metadata, chat history).
2. **ChromaDB** stores vector embeddings of every thought, document, and note for semantic search.

When a user asks a question, Sage converts it to an embedding, searches ChromaDB for similar vectors, retrieves the original text, and uses it as context for the LLM.

---

## Intermediate

### Q5: Explain the RAG pipeline in Sage.

**Answer:**
RAG stands for Retrieval-Augmented Generation. Sage's pipeline works like this:

1. **Ingestion:** When a user uploads a document or types a thought, Sage extracts text, generates an embedding using Sentence Transformers, and stores it in ChromaDB.
2. **Query:** When the user asks a question, Sage embeds the query.
3. **Retrieval:** Sage performs approximate nearest neighbor search in ChromaDB to find the most semantically similar stored memories.
4. **Context Assembly:** The retrieved memories are formatted into a context string.
5. **Generation:** The context string is sent to an LLM along with a system prompt. The LLM is instructed to use the retrieved PROJECT DOCUMENTS as primary sources.
6. **Response:** The LLM generates an answer grounded in the user's actual data.

**Key advantage:** The LLM answers from the user's data, not its training data. This reduces hallucinations and keeps answers private.

### Q6: Why does Sage use two databases (SQLite + ChromaDB)?

**Answer:**
This is polyglot persistence --- using the right tool for each job.

**SQLite handles:**
- Relationships (domains have many thoughts)
- Transactions (ACID guarantees)
- Structured queries (get all documents for a domain)
- Constraints (NOT NULL, foreign keys)

**ChromaDB handles:**
- Semantic similarity search (find documents about "agency")
- High-dimensional vectors (384-dimensional embeddings)
- Approximate nearest neighbor queries (fast, scalable)

**Trade-off:** Data exists in two places, so consistency requires careful handling. For production, PostgreSQL with the `pgvector` extension could unify both.

### Q7: How does Sage classify uploaded documents?

**Answer:**
Sage uses semantic classification via embeddings:

1. Extract text from the uploaded document.
2. Generate an embedding of the document text (first 2000 characters).
3. For each life domain, generate an embedding of `name + description`.
4. Compute cosine similarity between the document embedding and each domain embedding.
5. Select the domain with the highest similarity score above a threshold (0.15).
6. Apply override rules: if a document contains financial content AND mentions a project name (e.g., "Sage funding"), it goes to the Sage project domain, not the Finance life domain.

**Why embeddings instead of keywords?** Keywords miss semantic relationships. "Revenue model" and "how we make money" should match even though they share no words.

### Q8: What happens when the LLM is unavailable?

**Answer:**
Sage has a **fallback synthesizer** (`_fallback_response` in `llm_service.py`). When no LLM provider is available:

1. It loads the founder's hardcoded knowledge about the project (`founder_context.py`).
2. It loads the domain's synthesized profile from SQLite.
3. It constructs a natural-language response from these structured sources.
4. The response mentions the project's essence, why it exists, current status, key concepts, and connections.

**This is critical for production reliability.** The system must work even when third-party APIs fail.

### Q9: Explain the multi-provider LLM abstraction.

**Answer:**
Sage supports Groq, Anthropic, OpenAI, and Moonshot through a unified interface:

```python
def generate_response(user_message, context_data=None):
    if PREFERRED_PROVIDER == 'anthropic':
        return _call_anthropic(prompt, system_prompt)
    elif get_groq_client():
        return _call_groq(prompt, system_prompt)
    elif get_openai_client():
        return _call_openai(prompt, system_prompt)
    else:
        return _fallback_response(user_message, context_data)
```

**Benefits:**
- **Redundancy:** If one provider fails, another is tried.
- **Cost optimization:** Use cheaper providers for simple tasks.
- **Speed:** Groq offers the fastest inference.
- **Flexibility:** Users configure their preferred provider via `LLM_PROVIDER` env var.

### Q10: How does Sage prevent the LLM from repeating the user's name on every message?

**Answer:**
This is solved through **dynamic prompt engineering** and **post-processing**:

1. **Dynamic system prompt:** Based on `conversation_length`, Sage appends instructions:
   - If length <= 1: "This is the first message. Greet warmly."
   - If length > 1: "This is a follow-up. DO NOT greet by name. Answer directly."

2. **Post-processing regex:** After generation, a regex strips any remaining name greetings:
   ```python
   llm_response = re.sub(r'^(Hey\s+Shubhi[,!]?\s+|Hi\s+Shubhi[,!]?\s+)', '', llm_response, flags=re.IGNORECASE)
   ```

**Key insight:** LLMs don't inherently understand conversation state. You must explicitly signal it in the prompt.

---

## Advanced

### Q11: How would you scale Sage's embedding generation to millions of documents?

**Answer:**
Current state: Synchronous, single-process, local model.

**Scaling strategy:**
1. **Async task queue:** Use Celery + Redis to offload embedding jobs. The API returns immediately; embedding happens in the background.
2. **Batch processing:** Process multiple documents in parallel instead of one at a time.
3. **GPU inference:** Move from CPU to GPU for 10-50x speedup. Use ONNX Runtime or TensorRT for further optimization.
4. **Model selection:** For massive scale, consider smaller models or distillation. Or use a hosted embedding API (OpenAI, Cohere) with caching.
5. **Distributed processing:** Use a worker pool (Kubernetes Jobs, AWS Batch) to horizontally scale embedding workers.
6. **Caching:** Cache embeddings for identical documents to avoid recomputation.

### Q12: How would you implement multi-user support in Sage?

**Answer:**
1. **Authentication:** Add JWT-based auth (OAuth2 with Password flow).
2. **User isolation:** Add `user_id` foreign key to all tables. Every query filters by `user_id`.
3. **Vector isolation:** Use separate ChromaDB collections per user, or add `user_id` to metadata and filter queries.
4. **Authorization:** Implement role-based access control (owner, viewer, editor).
5. **Database migration:** Migrate from SQLite to PostgreSQL for concurrent access.
6. **Shared domains:** Some domains (e.g., "Sage / Documentation") might be shared across users. Add a `shared` flag.

### Q13: How would you improve the document classification accuracy?

**Answer:**
Current approach: Embedding cosine similarity with keyword overrides.

**Improvements:**
1. **Few-shot classification:** Provide the LLM with examples of each domain's documents and ask it to classify.
2. **Hybrid scoring:** Combine embedding similarity with TF-IDF keyword matching and LLM confidence.
3. **User feedback loop:** When the user corrects a classification, store the feedback and retrain/fine-tune the classifier.
4. **Hierarchical classification:** First classify by layer (life/project/knowledge/system), then by domain within the layer. This narrows the candidate set.
5. **Document structure:** Use headings, first paragraph, and metadata (not just raw text) for classification.

### Q14: How would you handle long-term memory in Sage?

**Answer:**
Current state: All embeddings are stored indefinitely.

**Challenges:**
- Storage grows unbounded.
- Old memories may become irrelevant.
- Retrieval quality degrades as the corpus grows.

**Solutions:**
1. **Memory pruning:** Remove unreferenced memories after a threshold. Or mark as "archived."
2. **Hierarchical summarization:** Summarize old conversations into higher-level embeddings. The original messages are archived; the summary lives in active memory.
3. **Importance scoring:** Use LLM to score memory importance. High-importance memories are retained longer.
4. **Time decay:** Recent memories are weighted higher in retrieval.
5. **Explicit forgetting:** Let users mark memories as "forget this."

### Q15: How would you add real-time collaboration to Sage?

**Answer:**
1. **WebSockets:** Use FastAPI's WebSocket support for real-time chat and document editing.
2. **Operational Transform / CRDT:** For collaborative document editing, use CRDTs (Yjs, Automerge) or operational transforms.
3. **Presence:** Show who's online and what they're viewing.
4. **Conflict resolution:** When two users edit the same domain document, merge changes or show conflicts.
5. **Notifications:** Real-time updates when a collaborator adds a thought or uploads a document.

---

## System Design

### Q16: Design a system like Sage from scratch.

**Answer Framework:**

**Requirements:**
- Store and retrieve user-generated content (documents, thoughts, notes).
- Semantic search across all content.
- LLM-powered responses grounded in retrieved context.
- Multi-layer chat (general, life, project, knowledge, system).
- Domain organization with auto-classification.
- Profile synthesis and briefing generation.

**High-Level Design:**

```
Client (React SPA)
    |
    | HTTPS / WebSocket
    v
Load Balancer
    |
    +---> FastAPI App (x3 replicas)
    |       |
    |       +--> SQLAlchemy --> PostgreSQL (structured data)
    |       |
    |       +--> ChromaDB / Weaviate (vector search)
    |       |
    |       +--> Redis (caching, session store, task queue)
    |       |
    |       +--> Celery Workers (embedding, summarization)
    |
    +---> Static Files (CDN)
```

**Key Design Decisions:**
- Separate read/write paths: Writes go to PostgreSQL + async workers for embedding. Reads query PostgreSQL + vector DB.
- Caching layer: Cache frequent queries (domain profiles, recent messages) in Redis.
- Async workers: Document processing and embedding are CPU-intensive. Offload to workers.
- Multi-tenant: Each user gets isolated collections in the vector DB.

### Q17: How would you handle 10,000 users uploading documents simultaneously?

**Answer:**
1. **Rate limiting:** 10 uploads/minute per user to prevent abuse.
2. **Queue:** Upload requests go to a message queue (RabbitMQ, SQS). API returns a job ID immediately.
3. **Workers:** A pool of Celery workers processes the queue. Workers can scale horizontally.
4. **Progress tracking:** Store job status in Redis. Client polls for status.
5. **Storage:** Use S3 / GCS for file storage, not local disk.
6. **Database:** PostgreSQL with connection pooling (PgBouncer).
7. **Vector DB:** Pinecone or Weaviate Cloud (managed, auto-scaling).

---

## Architecture

### Q18: Why RAG instead of fine-tuning?

**Answer:**
1. **Privacy:** RAG keeps user data local. Fine-tuning sends data to model providers.
2. **Cost:** RAG is free after initial embedding. Fine-tuning costs dollars per million tokens.
3. **Real-time updates:** New documents are immediately searchable. Fine-tuning requires retraining.
4. **Attribution:** RAG can cite sources. Fine-tuning bakes knowledge into weights.
5. **MVP speed:** RAG works with off-the-shelf models. Fine-tuning requires infrastructure and expertise.

**When fine-tuning is better:** If Sage needed to learn the founder's writing style for content generation, or if the knowledge base were small and static.

### Q19: Why did you choose ChromaDB over Pinecone?

**Answer:**
For the MVP, ChromaDB was chosen because:
1. **Local-first:** No API keys, no network calls, no usage limits.
2. **Simplicity:** pip install, create client, store/query. Zero configuration.
3. **Metadata filtering:** Can filter by domain ID and type during queries.
4. **Persistence:** Data survives restarts.

**Trade-off:** ChromaDB is single-node and will not scale to millions of users. For production, we would migrate to Pinecone, Weaviate, or Qdrant.

### Q20: How do you ensure data consistency between SQLite and ChromaDB?

**Answer:**
Currently, Sage does not implement distributed transactions. The strategy is:

1. **Write SQLite first:** The structured data is the source of truth.
2. **Then write ChromaDB:** If ChromaDB fails, the document is still in SQLite. A background job can retry the embedding.
3. **Idempotent writes:** ChromaDB overwrites on duplicate IDs, so retries are safe.
4. **Reconciliation:** A periodic job can scan SQLite and ensure all documents have embeddings in ChromaDB.

**Future:** Use a message queue with at-least-once delivery guarantees. Or use PostgreSQL + pgvector to unify both stores.

---

## LLM

### Q21: How do you reduce LLM hallucinations in Sage?

**Answer:**
1. **RAG grounding:** The LLM is instructed to use retrieved PROJECT DOCUMENTS as primary sources.
2. **Explicit instruction:** System prompt says "If the PROJECT DOCUMENT doesn't contain the answer, say so honestly --- don't make things up."
3. **Fallback synthesizer:** When LLM is unavailable, deterministic rule-based responses prevent hallucinations entirely.
4. **Temperature control:** Use temperature 0.7 (balanced between creativity and consistency).
5. **Context limitation:** Only send retrieved memories, not the LLM's parametric knowledge.

### Q22: How do you handle LLM rate limits?

**Answer:**
1. **Multi-provider fallback:** If Groq is rate-limited, try Anthropic, then OpenAI.
2. **Exponential backoff:** Retry failed requests with increasing delays.
3. **Circuit breaker:** If a provider fails repeatedly, temporarily stop trying it.
4. **Fallback:** The fallback synthesizer ensures the system works even when all LLMs are down.

---

## RAG

### Q23: What is the difference between dense and sparse retrieval?

**Answer:**
- **Dense retrieval** uses neural embeddings to capture semantic meaning. "Dog" and "puppy" are close in vector space. Used by Sage via Sentence Transformers + ChromaDB.
- **Sparse retrieval** uses keyword matching (BM25, TF-IDF). Fast and interpretable but misses semantic relationships.

**Hybrid approach:** Combine both. Use BM25 for exact keyword matches and dense retrieval for semantic similarity. Rerank combined results.

### Q24: How would you evaluate RAG quality in Sage?

**Answer:**
1. **Retrieval metrics:**
   - **Recall@K:** Is the relevant document in the top K results?
   - **Mean Reciprocal Rank (MRR):** How high is the first relevant result ranked?
   - **NDCG:** Accounts for graded relevance.

2. **Generation metrics:**
   - **Faithfulness:** Does the answer match the retrieved context?
   - **Answer relevance:** Is the answer relevant to the question?
   - **Hallucination rate:** Percentage of answers containing unsupported claims.

3. **Human evaluation:** Have users rate response quality on a 1-5 scale.

---

## Backend

### Q25: Why FastAPI over Flask?

**Answer:**
1. **Auto-validation:** Pydantic models validate requests automatically. No manual validation code.
2. **Auto-docs:** Swagger UI is generated from type hints.
3. **Async-native:** Built on Starlette, supports async/await out of the box.
4. **Dependency injection:** `Depends(get_db)` is cleaner than Flask's global objects.
5. **Type safety:** Type hints give editor support and catch errors early.

### Q26: How would you make Sage's backend async?

**Answer:**
1. Upgrade SQLAlchemy to 2.0 with async support.
2. Change `create_engine` to `create_async_engine` with `aiosqlite` or `asyncpg`.
3. Add `await` to all database calls.
4. Use `async def` for FastAPI endpoints.
5. Use `asyncio.gather()` for parallel operations (e.g., embedding + topic extraction).

---

## Python

### Q27: What Python design patterns did you use in Sage?

**Answer:**
1. **Repository Pattern:** `crud.py` abstracts all database access.
2. **Dependency Injection:** `Depends(get_db)` in FastAPI.
3. **Strategy Pattern:** Multi-provider LLM abstraction.
4. **Pipeline Pattern:** Document processing (extract -> summarize -> classify -> embed).
5. **Fallback Pattern:** LLM fallback synthesizer.

### Q28: How do you handle Python's Global Interpreter Lock (GIL) in Sage?

**Answer:**
Currently, Sage runs synchronously. For CPU-bound tasks like embedding:
1. **Process pools:** Use `ProcessPoolExecutor` to offload to separate processes (bypasses GIL).
2. **C extensions:** NumPy operations (in cosine similarity) release the GIL.
3. **Future:** Use `asyncio` with thread pools for I/O-bound operations, process pools for CPU-bound.

---

# 12. Technical Glossary

### Agentic AI
**Definition:** AI systems that can take actions autonomously on behalf of users, not just generate text.
**Why it exists:** Chatbots answer questions; agents do things.
**Analogy:** A chatbot is a librarian (finds information). An agent is a chief of staff (finds information AND takes action).
**Real-world example:** AutoGPT, Devin (AI software engineer).
**How Sage uses it:** Sage stores and retrieves context, classifies documents, synthesizes profiles, and will eventually take actions (send emails, create documents).

### Approximate Nearest Neighbor (ANN)
**Definition:** Algorithms that find close matches in high-dimensional space without checking every item.
**Why it exists:** Exact nearest neighbor in 384 dimensions is O(n) and too slow for large datasets.
**Analogy:** Finding a friend's house in a city. Instead of checking every house, you use neighborhood and street signs (approximate) to narrow down quickly.
**Real-world example:** Google Search, Spotify recommendations.
**How Sage uses it:** ChromaDB uses HNSW (Hierarchical Navigable Small World) for fast vector search.

### ChromaDB
**Definition:** An open-source embedding database for storing and querying vector embeddings.
**Why it exists:** Traditional databases cannot efficiently search high-dimensional vectors by semantic similarity.
**Analogy:** A library catalog that finds books by "vibe" rather than exact title matches.
**How Sage uses it:** Stores embeddings of thoughts, documents, and research notes for "Bring me back" retrieval.

### Cosine Similarity
**Definition:** A measure of similarity between two vectors based on the angle between them. Range: -1 (opposite) to 1 (identical).
**Formula:** `cos(θ) = (A · B) / (||A|| × ||B||)`
**Why it exists:** Euclidean distance is affected by vector magnitude. Cosine similarity ignores magnitude and measures orientation.
**Analogy:** Two arrows pointing in similar directions are "similar" even if one is longer than the other.
**How Sage uses it:** Document classification compares document embeddings to domain embeddings using cosine similarity.

### Embedding
**Definition:** A dense vector representation of text (or images) that captures semantic meaning.
**Why it exists:** Computers understand numbers, not words. Embeddings convert text into vectors where similar meanings are close together.
**Analogy:** Translating a poem into a painting. Different poems about love produce similar paintings.
**How Sage uses it:** `all-MiniLM-L6-v2` converts text into 384-dimensional vectors. Similar thoughts are close in this 384D space.

### FastAPI
**Definition:** A modern Python web framework for building APIs with automatic validation and documentation.
**Why it exists:** Before FastAPI, Python API development required manual validation, lacked async support, or was too heavy.
**How Sage uses it:** All REST endpoints are defined in FastAPI with Pydantic schemas for request/response validation.

### HNSW (Hierarchical Navigable Small World)
**Definition:** A graph-based algorithm for approximate nearest neighbor search.
**Why it exists:** Enables sub-linear time search in high-dimensional spaces.
**Analogy:** A road network where you can quickly navigate from any point to any other by following highway connections.
**How Sage uses it:** ChromaDB's default indexing algorithm for vector search.

### LLM (Large Language Model)
**Definition:** A neural network trained on vast text corpora to generate human-like text.
**Why it exists:** Enables natural language understanding and generation at scale.
**How Sage uses it:** Not as the primary intelligence, but as a component that synthesizes retrieved context into human-like responses.

### Polyglot Persistence
**Definition:** Using multiple database technologies within the same application, each for its strengths.
**Why it exists:** No single database is optimal for all workloads.
**How Sage uses it:** SQLite for structured relational data + ChromaDB for vector embeddings.

### RAG (Retrieval-Augmented Generation)
**Definition:** An architecture that retrieves relevant documents before generating text, grounding LLM responses in external knowledge.
**Why it exists:** LLMs hallucinate and have static knowledge. RAG grounds them in real, up-to-date data.
**Analogy:** An open-book exam. The student (LLM) can look up answers in a textbook (retrieved context) instead of relying only on memory (training data).
**How Sage uses it:** Core architecture. Every LLM response is preceded by vector retrieval from the user's knowledge base.

### Semantic Search
**Definition:** Search based on meaning rather than exact keyword matches.
**Why it exists:** Users query with different words than they used when storing information.
**Analogy:** Asking a friend "What was that movie with the space cowboy?" and getting "Firefly" even though "cowboy" was never in the title.
**How Sage uses it:** The "Bring me back" feature relies on semantic search to find relevant context across time.

### Sentence Transformers
**Definition:** A Python library for generating sentence-level embeddings.
**Why it exists:** Word embeddings (Word2Vec) represent individual words. Sentence transformers represent entire sentences and paragraphs.
**How Sage uses it:** `all-MiniLM-L6-v2` generates 384-dimensional embeddings for all stored content and user queries.

### SQLAlchemy
**Definition:** Python's most widely used SQL toolkit and ORM.
**Why it exists:** Abstracts database operations into Python objects while still allowing raw SQL when needed.
**How Sage uses it:** All database models, relationships, and queries are defined via SQLAlchemy ORM.

### Vector Database
**Definition:** A database optimized for storing and querying high-dimensional vectors.
**Why it exists:** Traditional databases index by exact match. Vector databases index by semantic similarity.
**How Sage uses it:** ChromaDB stores embeddings and supports metadata-filtered similarity search.

---

*This document should grow with every feature. Add new questions and glossary terms as Sage evolves.*
