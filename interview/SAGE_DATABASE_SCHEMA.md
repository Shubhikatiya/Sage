# Sage Database Schema Documentation

> **Purpose:** Explain the complete database schema, relationships, storage strategy, indexing, query flow, and performance considerations.

---

## Overview

Sage uses **SQLite** as its primary relational database, accessed through **SQLAlchemy** ORM. The database stores structured data about users, life domains, thoughts, documents, research notes, chat messages, deadlines, daily plans, topics, and editable domain documents.

**Why SQLite for the MVP:** See [Architecture Decisions](./SAGE_ARCHITECTURE_DECISIONS.md#decision-4-why-sqlite-instead-of-postgresql).

**Migration Path:** The database URL is configured via environment variable. Changing from `sqlite:///./sage_v3.db` to `postgresql://...` is a one-line change because SQLAlchemy abstracts the dialect.

---

## Entity Relationship Diagram

```mermaid
erDiagram
    USER ||--o{ LIFE_DOMAIN : "creates"
    USER {
        string id PK
        string name
        string email
        string timezone
        json preferences
        datetime created_at
        datetime updated_at
    }

    LIFE_DOMAIN ||--o{ THOUGHT : "has"
    LIFE_DOMAIN ||--o{ DOCUMENT : "has"
    LIFE_DOMAIN ||--o{ RESEARCH_NOTE : "has"
    LIFE_DOMAIN ||--o{ DEADLINE : "has"
    LIFE_DOMAIN ||--o{ DAILY_PLAN : "has"
    LIFE_DOMAIN ||--o{ TOPIC : "has"
    LIFE_DOMAIN ||--o{ DOMAIN_DOCUMENT : "has"
    LIFE_DOMAIN ||--o{ MEMORY_VECTOR : "has"
    LIFE_DOMAIN {
        string id PK
        string name
        text description
        string layer
        string status
        string parent_id FK
        text profile
        datetime created_at
        datetime updated_at
    }

    LIFE_DOMAIN ||--o{ LIFE_DOMAIN : "parent_of"

    THOUGHT {
        string id PK
        string life_domain_id FK
        text content
        string source
        string conversation_id
        datetime created_at
    }

    DOCUMENT {
        string id PK
        string life_domain_id FK
        string filename
        text content
        string file_type
        string file_path
        datetime created_at
    }

    RESEARCH_NOTE {
        string id PK
        string life_domain_id FK
        string title
        text content
        string source
        string source_title
        string source_author
        string page_number
        string url
        json tags
        datetime created_at
        datetime updated_at
    }

    CHAT_MESSAGE {
        string id PK
        string layer
        string role
        text content
        json context_data
        datetime created_at
    }

    DEADLINE {
        string id PK
        string life_domain_id FK
        string title
        text description
        datetime due_date
        string status
        string priority
        json reminder_days
        datetime completed_at
        datetime created_at
    }

    DAILY_PLAN {
        string id PK
        string life_domain_id FK
        datetime date
        json focus_areas
        json tasks
        int completed_tasks
        int total_tasks
        text notes
        datetime created_at
        datetime updated_at
    }

    MEMORY_VECTOR {
        string id PK
        string life_domain_id FK
        text content
        json embedding
        string source_type
        string source_id
        datetime created_at
    }

    TOPIC {
        string id PK
        string name
        text description
        string life_domain_id FK
        string source_type
        string source_id
        int frequency
        json extra_data
        datetime created_at
        datetime updated_at
    }

    DOMAIN_DOCUMENT {
        string id PK
        string life_domain_id FK
        string title
        text content
        string document_type
        int version
        datetime created_at
        datetime updated_at
    }
```

---

## Table-by-Table Documentation

### 1. `users`

**Purpose:** Store the single user's profile. Sage is currently a single-user system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `name` | String | Not null, default "Shubhi" | User's display name |
| `email` | String | Nullable | Contact email |
| `timezone` | String | Default "Asia/Kolkata" | For time-aware greetings |
| `preferences` | JSON | Default `{}` | User settings (future) |
| `created_at` | DateTime | Default utcnow | Account creation time |
| `updated_at` | DateTime | Default utcnow | Last update time |

**Indexes:** Primary key on `id`.

**Query Pattern:**
```python
# Get or create user
user = db.query(User).first()
if not user:
    user = User(name="Shubhi Katiyar")
```

**Interview Note:** The single-user design is intentional for the MVP. Multi-user would require adding `user_id` foreign keys to all tables and implementing authentication.

---

### 2. `life_domains`

**Purpose:** The central organizational unit. Everything in Sage belongs to a life domain.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `name` | String | Not null | Domain name (e.g., "Sage", "Career") |
| `description` | Text | Nullable | Human-readable description |
| `layer` | String | Default "life" | One of: life, project, knowledge, system |
| `status` | String | Default "active" | active, archived, dormant |
| `parent_id` | String | FK -> life_domains.id | Self-referential for subdomains |
| `profile` | Text | Nullable | Synthesized markdown understanding |
| `created_at` | DateTime | Default utcnow | Creation time |
| `updated_at` | DateTime | Default utcnow | Last update time |

**Relationships:**
- One-to-many with `thoughts`, `documents`, `research_notes`, `deadlines`, `daily_plans`, `topics`, `domain_documents`.
- Self-referential: one domain can have many child domains.

**Cascade Behavior:**
```python
thoughts = relationship("Thought", back_populates="life_domain", cascade="all, delete-orphan")
```
Deleting a domain deletes all associated thoughts, documents, notes, etc.

**Indexes:**
- Primary key on `id`.
- Implicit index on `parent_id` (foreign key).
- Query pattern filters on `layer` frequently.

**Storage Strategy:**
- Domains are relatively static (tens to hundreds of rows).
- The `profile` column stores synthesized markdown, which can be large (up to several KB per domain).

**Query Flow:**
```sql
-- Get all active project domains
SELECT * FROM life_domains
WHERE layer = 'project' AND status = 'active'
ORDER BY updated_at DESC;
```

---

### 3. `thoughts`

**Purpose:** Store user-generated insights, ideas, and observations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Not null | Belongs to which domain |
| `content` | Text | Not null | The thought text |
| `source` | String | Default "user_chat" | Origin (user_chat, import, etc.) |
| `conversation_id` | String | Nullable | Links to a specific chat session |
| `created_at` | DateTime | Default utcnow | When the thought was captured |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- Thoughts are frequent writes (every user message in chat is potentially stored as a thought).
- Content is indexed in ChromaDB for semantic search.
- SQLite stores the canonical data; ChromaDB stores the searchable vectors.

**Query Pattern:**
```sql
-- Get recent thoughts for a domain
SELECT * FROM thoughts
WHERE life_domain_id = ?
ORDER BY created_at DESC
LIMIT 100;
```

---

### 4. `documents`

**Purpose:** Store uploaded files and their extracted text content.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Not null | Assigned domain |
| `filename` | String | Not null | Original filename |
| `content` | Text | Not null | Extracted text |
| `file_type` | String | Not null | Extension (pdf, docx, txt, md) |
| `file_path` | String | Nullable | Path to stored file on disk |
| `created_at` | DateTime | Default utcnow | Upload time |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- `content` can be very large (full text of a PDF). This is acceptable for MVP but may need pagination or chunking for scale.
- The actual file is stored on disk in `uploads/` with a UUID filename. `file_path` points to this location.

**Security Note:** UUID filenames prevent path traversal attacks. The original filename is stored separately for display.

---

### 5. `research_notes`

**Purpose:** Structured summaries and insights, often derived from documents or user input.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Nullable | May be unassigned |
| `title` | String | Not null | Note title |
| `content` | Text | Not null | Note body |
| `source` | String | Nullable | Original source |
| `source_title` | String | Nullable | Book/paper title |
| `source_author` | String | Nullable | Author name |
| `page_number` | String | Nullable | Page reference |
| `url` | String | Nullable | Web link |
| `tags` | JSON | Default `[]` | Array of tags |
| `created_at` | DateTime | Default utcnow | Creation time |
| `updated_at` | DateTime | Default utcnow | Last update time |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- Research notes are the primary source for domain profile synthesis.
- The `content` is embedded in ChromaDB for semantic search.
- JSON `tags` allows flexible categorization without a separate tags table.

---

### 6. `chat_messages`

**Purpose:** Store conversation history for layer-based chat.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `layer` | String | Not null | general, life, project, knowledge, system |
| `role` | String | Not null | user, assistant |
| `content` | Text | Not null | Message text |
| `context_data` | JSON | Nullable | Domain name, profile used for response |
| `created_at` | DateTime | Default utcnow | Message timestamp |

**Relationships:** None (standalone table).

**Storage Strategy:**
- Chat messages are append-only.
- No foreign key to `life_domains` because a single chat can span multiple domains.
- `context_data` JSON stores what the LLM knew when generating the response (useful for debugging and reproducibility).

**Query Pattern:**
```sql
-- Get recent messages for a layer
SELECT * FROM chat_messages
WHERE layer = 'project'
ORDER BY created_at ASC
LIMIT 50;
```

**Index Recommendation:** Add an index on `(layer, created_at)` for chat history queries.

---

### 7. `deadlines`

**Purpose:** Track time-bound tasks and commitments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Not null | Associated domain |
| `title` | String | Not null | Task name |
| `description` | Text | Nullable | Details |
| `due_date` | DateTime | Not null | Deadline |
| `status` | String | Default "not_started" | not_started, in_progress, completed |
| `priority` | String | Default "medium" | low, medium, high, urgent |
| `reminder_days` | JSON | Default `[7,3,1]` | Days before to remind |
| `completed_at` | DateTime | Nullable | Completion timestamp |
| `created_at` | DateTime | Default utcnow | Creation time |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- `reminder_days` is stored as JSON for flexibility.
- Queries typically filter by `status` and order by `due_date`.

---

### 8. `daily_plans`

**Purpose:** Track daily focus areas and task lists.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Not null | Primary domain for the day |
| `date` | DateTime | Not null | Plan date |
| `focus_areas` | JSON | Default `[]` | Array of focus strings |
| `tasks` | JSON | Default `[]` | Array of task objects |
| `completed_tasks` | Integer | Default 0 | Count completed |
| `total_tasks` | Integer | Default 0 | Total task count |
| `notes` | Text | Nullable | Free-form notes |
| `created_at` | DateTime | Default utcnow | Creation time |
| `updated_at` | DateTime | Default utcnow | Last update time |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- `tasks` is a JSON array of objects: `[{"title": "Task 1", "completed": true}, ...]`
- This avoids a separate tasks table for the MVP. Future: normalize into a dedicated `tasks` table.

---

### 9. `memory_vectors`

**Purpose:** Store embeddings for redundancy (ChromaDB is primary). Currently used as a backup/audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Not null | Associated domain |
| `content` | Text | Not null | Original text |
| `embedding` | JSON | Not null | Vector array (384 dims) |
| `source_type` | String | Not null | thought, document, research_note |
| `source_id` | String | Not null | Original table row ID |
| `created_at` | DateTime | Default utcnow | Creation time |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- Storing embeddings as JSON in SQLite is inefficient (text serialization of float arrays).
- This table exists as a fallback. The primary vector store is ChromaDB.
- Future: remove this table and rely entirely on ChromaDB, or use a proper vector database.

---

### 10. `topics`

**Purpose:** Store extracted themes and concepts from documents and conversations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `name` | String | Not null | Topic name (e.g., "Revenue Model") |
| `description` | Text | Nullable | Longer description |
| `life_domain_id` | String | FK, Nullable | May be global |
| `source_type` | String | Default "auto_extracted" | auto_extracted, user_defined |
| `source_id` | String | Nullable | Document ID it came from |
| `frequency` | Integer | Default 1 | How many times seen |
| `extra_data` | JSON | Default `{}` | Additional metadata |
| `created_at` | DateTime | Default utcnow | First seen |
| `updated_at` | DateTime | Default utcnow | Last updated |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- Topics are deduplicated by name + domain. If the same topic appears again, `frequency` is incremented.
- This allows "trending topics" queries.

**Query Pattern:**
```sql
-- Get top topics for a domain
SELECT * FROM topics
WHERE life_domain_id = ?
ORDER BY frequency DESC
LIMIT 20;
```

---

### 11. `domain_documents`

**Purpose:** Editable markdown documents attached to life domains. These are the PRIMARY knowledge source for LLM context.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | String | PK, UUID | Unique identifier |
| `life_domain_id` | String | FK, Not null | Belongs to domain |
| `title` | String | Not null | Document title |
| `content` | Text | Not null, default "" | Markdown content |
| `document_type` | String | Default "overview" | overview, notes, sources, timeline |
| `version` | Integer | Default 1 | Incremented on each update |
| `created_at` | DateTime | Default utcnow | Creation time |
| `updated_at` | DateTime | Default utcnow | Last update time |

**Relationships:** Many-to-one with `life_domains`.

**Storage Strategy:**
- Content is markdown and can be large (15,000+ characters).
- Auto-appended by the chat system with semantic formatting.
- Version tracking allows rollback (though no rollback endpoint exists yet).

---

## Relationships Summary

```
User
  └── LifeDomain (1:N)
        ├── Thought (1:N, cascade delete)
        ├── Document (1:N, cascade delete)
        ├── ResearchNote (1:N, cascade delete)
        ├── Deadline (1:N, cascade delete)
        ├── DailyPlan (1:N, cascade delete)
        ├── Topic (1:N)
        ├── DomainDocument (1:N, cascade delete)
        ├── MemoryVector (1:N)
        └── LifeDomain (self-reference, 1:N for subdomains)

ChatMessage (standalone, no FKs)
```

---

## Indexing Strategy

### Current Indexes (Implicit)
- Primary keys on all tables (B-tree index automatically created).
- Foreign keys create implicit indexes in SQLite.

### Recommended Future Indexes

```sql
-- Chat history queries
CREATE INDEX idx_chat_layer_created ON chat_messages(layer, created_at);

-- Domain lookup by name (used in classifier)
CREATE INDEX idx_life_domain_name ON life_domains(name);

-- Thoughts by domain (frequent query)
CREATE INDEX idx_thoughts_domain ON thoughts(life_domain_id, created_at DESC);

-- Documents by domain
CREATE INDEX idx_documents_domain ON documents(life_domain_id);

-- Topics by domain and frequency
CREATE INDEX idx_topics_domain_freq ON topics(life_domain_id, frequency DESC);

-- Deadlines by due date
CREATE INDEX idx_deadlines_due ON deadlines(due_date);
```

**Why not added yet:** SQLite performs well for single-user local access even without explicit indexes. Adding them would only benefit multi-user or large datasets.

---

## Query Flow Examples

### Q1: "Get the complete state of a domain"

```sql
-- Get domain with profile
SELECT * FROM life_domains WHERE id = 'domain-uuid';

-- Get recent thoughts
SELECT * FROM thoughts 
WHERE life_domain_id = 'domain-uuid' 
ORDER BY created_at DESC LIMIT 10;

-- Get recent documents
SELECT * FROM documents 
WHERE life_domain_id = 'domain-uuid' 
ORDER BY created_at DESC LIMIT 5;

-- Get top topics
SELECT * FROM topics 
WHERE life_domain_id = 'domain-uuid' 
ORDER BY frequency DESC LIMIT 8;

-- Get domain document
SELECT * FROM domain_documents 
WHERE life_domain_id = 'domain-uuid' AND document_type = 'overview';
```

### Q2: "Find all content across all domains for a user query"

This is done via ChromaDB vector search, not SQL. See [RAG Pipeline](./SAGE_DOCUMENTATION.md#27-rag-pipeline).

### Q3: "Get upcoming deadlines"

```sql
SELECT d.*, ld.name as domain_name
FROM deadlines d
JOIN life_domains ld ON d.life_domain_id = ld.id
WHERE d.status != 'completed'
  AND d.due_date > datetime('now')
ORDER BY d.due_date ASC;
```

---

## Performance Considerations

1. **SQLite concurrency:** SQLite locks the entire database on writes. With a single user, this is fine. For multi-user, migrate to PostgreSQL.

2. **Large text columns:** `documents.content`, `domain_documents.content`, and `life_domains.profile` can be large. SQLite handles this, but queries should avoid `SELECT *` when only metadata is needed.

3. **JSON columns:** SQLite JSON is stored as text and parsed on access. Frequent JSON queries would benefit from PostgreSQL's native JSONB.

4. **No pagination:** Many queries use `.all()` without limits. For large datasets, add pagination.

5. **Embedding storage:** `memory_vectors.embedding` stores 384-dimensional float arrays as JSON text. This is ~10KB per row and inefficient. ChromaDB handles this properly.

---

## Migration Strategy to PostgreSQL

1. **Install PostgreSQL:** `pip install psycopg2-binary`
2. **Update connection string:**
   ```python
   DATABASE_URL = "postgresql://user:pass@localhost/sage"
   ```
3. **Enable JSONB:** Change JSON columns to use PostgreSQL's native JSONB for better performance.
4. **Add indexes:** Create the recommended indexes above.
5. **Add user_id columns:** For multi-user support.
6. **Migrate data:** Use SQLAlchemy's `create_all()` or Alembic migrations.

**Key insight:** Because Sage uses SQLAlchemy ORM, the code barely changes. The migration is primarily operational.

---

*This schema documentation should be updated whenever models change.*
