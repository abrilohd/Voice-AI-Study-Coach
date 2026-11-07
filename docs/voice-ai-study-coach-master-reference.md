# Voice AI Study Coach — Master Reference
**Principal Engineer Edition · Updated through Phase 1, Day 3 · 2026**
 
> Living reference for the Voice AI Study Coach build — architecture decisions, audit fixes, and current status, updated at the end of every session.

---

## 0. Project Identity

**Voice AI Study Coach** — a startup-grade, production-ready AI study coach.

- No-lock-in LLM router (Claude / OpenAI / Gemini, hot-swappable)
- Voice I/O (input + output)
- RAG-ready document ingestion
- PostgreSQL-backed persistence (async SQLAlchemy 2)
- Designed to scale to 100k users without rewriting service boundaries
- Every module independently replaceable

---

## 1. THE PATTERN — Vertical Slice (memorize once, use forever)

```
Schema → Repository → Service → Route → Tests
```

Never reverse this order. Schema is the innermost ring — everything depends on it, it depends on nothing.

| Layer | Responsibility | Never does |
|---|---|---|
| **Schema** | Define I/O contract. Pydantic v2 with `Field(description=...)` for OpenAPI. | Import from service layer |
| **Repository** | Pure async DB access. `select()`/`update()`, takes `AsyncSession`. | Commit, business logic, HTTP imports |
| **Service** | All business logic. Calls repo + LLM. Raises domain exceptions. ONE `commit()` per operation. | Touch SQLAlchemy directly, raise `HTTPException` |
| **Route** | Validate → call service → return schema. Translates domain exceptions → HTTP codes. | Contain `if` business logic |
| **Tests** | Happy path + 2 unhappy paths per endpoint. Mock LLM + repo with `AsyncMock`. | Call real APIs or real DB in unit tests |

**Why this order makes you fast**: Week 2 RAG → add `VectorRepository` + `RAGService`, route unchanged. Week 3 Voice → add `VoiceService`, route unchanged. Week 4 Agents → add `AgentService` using LangGraph, route unchanged. **The pattern is the product.**

---

## 2. The AI Framework Landscape — 2026, Honest Edition

### Tier 1 — use by default
| Tool | Role |
|---|---|
| **Anthropic SDK v0.40+** | Raw streaming, tool calling, `messages.stream()`, native prompt caching |
| **Pydantic v2** | Schema, validation, 5–50× faster than v1 |
| **SQLAlchemy 2 (async)** | `Mapped[]` + `mapped_column()`, `select()` not `session.query()` |
| **pgvector** | Vectors inside existing Postgres — default for RAG until millions of vectors |
| **FastAPI / Hono** | Thin route layer, SSE endpoints |
| **Upstash Redis** | Serverless chat history + rate limit store, no cold start |
| **LangSmith** | Tracing + evals from day one |
| **argon2-cffi** | Password hashing — won the Password Hashing Competition, memory-hard |
| **PyJWT 2.x** | JWT — `python-jose` is unmaintained, has CVEs, avoid |
| **slowapi** | Redis-backed rate limiting for FastAPI |
| **ruff** | Replaces flake8 + isort + pyupgrade + bandit, 10–100× faster |
| **anyio + pytest-anyio** | Async test runner, `asyncio_mode=auto` |
| **structlog** | JSON logs with `conversation_id`, `user_id`, `provider` fields |

### Tier 2 — add when you hit the wall
| Tool | When it earns its keep |
|---|---|
| **LangChain v0.3 (LCEL)** | Chains, memory, RAG pipelines — not for simple streaming chat |
| **LangGraph** | Stateful multi-step agents with loops/conditionals (Week 4+) |
| **Vercel AI SDK 4** | If TS stack — `streamText`, `useChat` replace raw SDK |
| **LlamaIndex v0.11** | Complex chunking, hybrid search over large doc sets |

### Tier 3 — evaluate carefully
| Tool | Note |
|---|---|
| **CrewAI** | Simpler than LangGraph, less production-hardened |
| **Pinecone / Qdrant** | Only at millions of vectors or multi-tenant hybrid search |
| **python-jose, bcrypt/passlib, session.query()** | Legacy or actively avoid in new code |

---

## 3. The Rule a Senior Engineer Uses

> **Start with the raw SDK. Add a framework when you hit the wall the framework was built for.**

| You hit this wall | Reach for this |
|---|---|
| "I need RAG over 10k documents" | LlamaIndex or LangChain |
| "My agent needs a loop with memory and tools" | LangGraph |
| "I need streaming text in my React UI fast" | Vercel AI SDK |
| "I need to evaluate prompt quality over time" | LangSmith |
| "I need background jobs for long LLM tasks" | Inngest or BullMQ |

**Your hand-rolled `LLMRouter` is the correct call for Day 3.** It's simpler, faster, fully debuggable. LangGraph earns its place at the RAG/agent layer (Week 2+) — not for basic streaming.

---

## 4. Applies to Every AI Project — The Transferable Lessons

1. **Vertical slice**: Schema → Repo → Service → Route → Test — RAG, voice, agents, quizzes, all built identically.
2. **Domain exceptions**: services raise `UserAlreadyExistsError`, routes translate to HTTP. Services stay reusable across HTTP, CLI, background jobs, WebSocket.
3. **SSE streaming**: Anthropic, OpenAI, Gemini, and emerging MCP/A2A agent protocols all use SSE over HTTP. One pattern scales to multi-agent systems.
4. **Prompt caching**: real economics — 1024-token minimum, cache writes cost more, cache reads ~10%, 5-min TTL. Naive "always cache" can cost MORE on short/single-turn prompts.
5. **httpOnly cookies**: refresh tokens never touch JS-accessible storage.
6. **Lazy client init**: app survives missing API keys; tests never accidentally hit real APIs.
7. **Real token counts**: use `message_delta.usage`, never `word_count * 1.3` heuristics.
8. **flush() vs commit()**: repository flushes, service commits once — enables atomic multi-step writes.
9. **UUID PKs everywhere**: integer IDs leak user/record counts.
10. **Constant-time auth**: same error, same timing for "user not found" and "wrong password" — prevents enumeration.

---

## 5. Senior Audit Summary — All Fixes Applied So Far

### Auth Schemas
- `id: int` → `id: UUID`
- Password validator: max 128 chars, reject email-as-substring, reject common passwords (NIST-aligned, not just "uppercase+digit")
- `Field(description=..., example=...)` on every field → free OpenAPI docs
- Added `RefreshResponse` (separate from `AuthResponse`) — token rotation returns new pair
- `ruff` + `pyright` alongside `mypy --strict`

### Auth Repository
- `user_id: int` → `UUID` everywhere
- **Removed `commit()` from repo** — `flush()` only; service owns transaction
- Added `email_exists()` (lightweight `SELECT 1`, no full ORM load)
- Added `set_refresh_token()`, `get_by_refresh_token_hash()`, `clear_refresh_token()` — store **hash**, not raw token

### Auth Service
- `tuple[User, str, str]` → typed `@dataclass AuthResult` / `TokenPair`
- `bcrypt` (implied) → **argon2-cffi** explicit
- Multiple commits → **ONE `db.commit()`** per operation
- **Timing attack fix**: always run `argon2.verify()` against a dummy hash even for missing users — constant time
- `UserNotFoundError(user_id: int)` → `UUID`

### Auth Routes
- Added **slowapi** rate limiting: `/register` 5/hour, `/login` 10/15min, `/refresh` 30/hour
- Cookie `secure` flag: `settings.ENVIRONMENT == "production"` (not hardcoded)
- **`UserNotFoundError` → 401, not 404** (404 leaks that a user existed — security issue)

### Auth Tests
- Split **unit** (AsyncMock, no DB, fast) vs **integration** (real DB, CI only)
- Added `test_login_timing_consistency` (< 150ms delta)
- Added `test_rate_limit_login` (11th request → 429)

### Chat Schemas + Repository
- All `id: int` → `UUID` for consistency with auth layer
- `add_message`: `flush()` not `commit()`
- `get_messages`: order by `(created_at, id)` — composite tiebreaker, avoids same-timestamp bugs under concurrency

### LLM Router + Chat Service (most critical fixes)
- **Never fall back to a different provider mid-stream** — only retry before first token. Mid-stream fallback = Frankenstein responses (half Claude voice, half GPT voice)
- Prompt caching: enforce **1024-token minimum** (not chars), understand cache write premium vs ~10% read cost
- Use **real token usage** from `message_delta.usage`, not `len(text.split()) * 1.3`
- **Explicit `max_tokens`** from settings on every provider call — unbounded responses = runaway cost
- `complete()` calls `messages.create()` directly — not stream-and-accumulate (avoids double latency)

### SSE Route
- **JSON-encode every SSE payload** — raw tokens containing `\n` (code blocks!) break the `data: ...\n\n` framing
- `asyncio.CancelledError` (client closed tab) = **normal**, re-raise, don't log as failure
- Rate limit `/stream` too (20/min) — every call costs real LLM money
- `X-Accel-Buffering: no` + `Cache-Control: no-cache` — without these, streaming is fake (Nginx buffers)

---

## 5.5 Foundation Files — Build Before Day 4

Every prompt audited in Section 5 reads from or calls these files. None have been built or specified yet — they are the missing plumbing under everything above. **Build order matters**: `config.py` → `database.py` → `security.py` → `main.py` → `conftest.py`. Until these exist, the audited prompts above will fail on import errors.

### Critical — nothing else works without these

| File | Why it's needed | What it must contain |
|---|---|---|
| `app/core/config.py` | Read by every service/router prompt audited so far | `pydantic-settings`: `anthropic_api_key`, `openai_api_key`, `gemini_api_key`, `primary_llm`, `fallback_llm`, `jwt_secret`, `jwt_algorithm`, `access_token_expire_minutes`, `refresh_token_expire_days`, `max_response_tokens`, `environment`, `dummy_hash`, `database_url`, `redis_url` |
| `app/core/security.py` | Auth service calls `get_password_hash`, `verify_password`, `create_access_token`, `create_refresh_token`, `verify_token` — none defined yet | `argon2-cffi` hasher reading `settings.dummy_hash` (owned by config.py, not redefined here) for timing-attack fix, PyJWT 2.x with explicit `algorithms=["HS256"]`, `create_refresh_token` returns `(raw_token, sha256_hash)` tuple |
| `app/core/database.py` | Every repository takes `AsyncSession` — `get_db` is the dependency that creates/yields it | SQLAlchemy 2 async engine, `async_sessionmaker`, `get_db` dependency with rollback-on-exception (no auto-commit), `DeclarativeBase` |
| `app/main.py` | slowapi limiter, CORS, lifespan, global exception handler all assumed by route prompts | CORS middleware (origins from settings), `app.state.limiter` + `RateLimitExceeded` handler, lifespan context manager for LLM client cleanup, global exception handler returning `ErrorResponse`, `/health` endpoint |
| `app/models/user.py`, `app/models/conversation.py`, `app/models/message.py` + Alembic migrations | Repository upgrades assume UUID PKs everywhere and a `refresh_token_hash`/`refresh_token_expires_at` column on `User` — neither exists in the original models | UUID primary keys via `Mapped[UUID]` with `default=uuid4`, add refresh token columns to `User`, regenerate Alembic migration |

> `security.py` owns refresh token generation as `create_refresh_token()`. `AuthService` calls it directly — no private `_create_refresh_token` method on the service.

### Needed — review/build soon

| File | Why it's needed | What it must contain |
|---|---|---|
| `app/core/prompts.py` | `TUTOR_SYSTEM` is the entire chat experience's system prompt — assumed to "already exist," never reviewed | Actual prompt engineering: role, tone, Socratic vs direct answers, topic-grounding instructions, and a check on whether it crosses the 1024-token prompt-caching threshold |
| `tests/conftest.py` | Both test prompts use `async_client`, `db_session`, `test_user`, `auth_headers`, `mock_repo` — none defined | `async_client` via httpx `AsyncClient` + `ASGITransport`; `db_session` with rollback-per-test for integration; `mock_repo` via `AsyncMock(spec=...)` for unit tests; `test_user` factory; `auth_headers` that registers a user and returns a Bearer header |
| `.env.example` | `config.py` reads env vars — no template of what's required, no guidance on generating secrets | List every var from `config.py` above + a setup script to generate `JWT_SECRET` (32 random bytes, base64) and `DUMMY_HASH` (argon2 hash of a random UUID) |

### Cross-cutting fix — standardize error responses

Auth routes return `{"detail": "..."}` via `HTTPException`, the SSE route returns `{"error": "..."}` as a raw dict, and slowapi has its own default shape. Define one `ErrorResponse` schema (`error_code`, `message`, `details`) and route every error — including the rate-limit handler — through the global exception handler in `app/main.py`.

---

## 6. Key Concepts the Curriculum Skipped

| Concept | Why it matters |
|---|---|
| **flush() ≠ commit()** | Repo flushes (gets IDs, keeps transaction open). Service commits once. Enables atomic multi-repo operations and clean rollback. |
| **Timing attacks** | Skipping the hash check for "user not found" lets attackers time-enumerate valid emails. Always run `argon2.verify()` against a dummy hash. |
| **Typed service returns** | `dataclass AuthResult(user, access_token, refresh_token)` > `tuple[User, str, str]`. Self-documenting, extensible without breaking callers. |
| **404 vs 401 on auth** | HTTP status codes are public information. `UserNotFoundError` → 401 always, never 404. |
| **Refresh token storage** | Store `SHA-256(token)` in DB. A DB breach with raw tokens = instant account takeover for everyone. |
| **Rate limiting is day-one** | Bots hit new public endpoints within hours. 20 minutes of `slowapi` + Redis, permanent protection. |
| **Mid-stream provider fallback = broken UX** | Fail before first token → safe retry. Fail after → graceful error + "regenerate" button, never splice providers. |
| **Prompt caching economics** | 1024-token min, write premium, ~10% read cost, 5-min TTL. Short single-turn prompts get zero benefit, sometimes a cost penalty. |
| **Real token counts** | `message_delta.usage` is free, accurate, already in the response. Estimates break cost tracking and rate limits. |
| **SSE payloads must be JSON** | Raw `\n` in LLM output (extremely common in code) breaks the SSE event boundary. |
| **Client disconnects ≠ errors** | `asyncio.CancelledError` on tab-close is normal user behavior — don't pollute error logs. |
| **Inconsistent error shapes** | Three different error JSON shapes across auth, chat, and rate limiting make the API hard for a frontend to consume. One `ErrorResponse` schema + global exception handler fixes this. |

---

## 7. Verification Commands (Day 3 — still correct)

```bash
cd voice-ai-study-coach/backend

uv run pytest tests/ -v --tb=short
uv run ruff check . && uv run ruff format . --check
uv run mypy app/
uv run uvicorn app.main:app --reload --port 8000

# Test auth
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"SecurePass1","display_name":"Abrham"}'

# Test streaming chat — --no-buffer is essential to SEE tokens arrive one by one
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"messages":[{"role":"user","content":"Explain recursion"}],"topic":"Python"}' \
  --no-buffer
```

If tests fail after agent-generated code: copy the exact pytest output, prompt the agent with *"Read CLAUDE.md. Fix the error without changing the architecture or layer separation rules."* Agents occasionally put business logic in routes — push back.

---

## 8. ROADMAP — What Comes Next (Day 4+)

Same vertical slice, new layers, route never changes.

### Day 4 Prerequisite — Frontend SSE Consumer

The backend streams correctly via curl, but the browser's native `EventSource` can't send a POST body or an `Authorization` header — both required by `/chat/stream`. Before building Week 2 features, the frontend needs a `fetch()` + `ReadableStream` reader that manually parses `data: {...}\n\n` JSON events (`text` / `usage` / `error` / `done` types from the upgraded chat service).

### Week 2 — RAG Pipeline
- `DocumentRepository` (pgvector) — store chunks + embeddings
- `RAGService` — chunking strategy, embedding generation, retrieval, re-ranking
- Schema: `DocumentUpload`, `RetrievedChunk`, augment `ChatRequest` with `use_rag: bool`
- New concept to learn: **chunking strategy** (fixed-size vs semantic), **embedding model choice** (Voyage AI / OpenAI text-embedding-3), **retrieval + re-rank before injecting into context**

### Week 3 — Voice I/O
- `VoiceService` — STT (Whisper / Deepgram) input, TTS (ElevenLabs / Cartesia) output
- Schema: `VoiceSessionCreate`, `AudioChunk`
- New concept: **WebRTC or chunked audio over SSE**, **latency budget** (STT + LLM TTFT + TTS must stay under ~1.5s for natural conversation feel)

### Week 4 — Agents / Tool Calling
- `AgentService` using **LangGraph** — this is where the framework finally earns its complexity
- Tools: quiz generator, flashcard creator, progress tracker
- New concept: **MCP (Model Context Protocol)** for tool definitions — same SSE transport pattern from Day 3 extends naturally

### Ongoing (every week)
- Add LangSmith eval cases for new prompts before shipping
- Extend `structlog` fields per new service (`document_id`, `voice_session_id`, `tool_name`)
- Rate-limit every new LLM-calling endpoint from day one

---

## 9. How to Continue 

```
We're continuing the Voice AI Study Coach project.
Phase 1 (Day 1-3) — complete. Architecture, auth, streaming chat. All audit fixes from Section 5 applied.

Foundation audit (Section 5.5) — complete. Gaps identified: config.py, security.py, database.py, main.py, conftest.py, plus models/migrations (UUID PKs, refresh token columns). Ownership decisions resolved — DUMMY_HASH lives in config.py, security.py owns create_refresh_token().

```