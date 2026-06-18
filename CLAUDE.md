# Voice AI Study Coach — Project Context for AI Agents

## Project Overview

Voice AI Study Coach is a production-grade AI-powered study assistant with real-time voice interaction. Built with FastAPI backend, React + TypeScript frontend, PostgreSQL database, and multi-LLM support (Claude, OpenAI, Gemini).

## Test Files Created

The following test files have been created following the requested structure:

### 1. Unit Tests (`tests/unit/`)
- `tests/unit/conftest.py` - Mock fixtures with AsyncMock for fast testing without database
  - `fake_user()` - Helper function to create fake User objects
  - `mock_repo` - AsyncMock fixture for UserRepository
  - `mock_db` - AsyncMock fixture for AsyncSession
  
- `tests/unit/test_auth_service.py` - Unit tests for AuthService with AsyncMock (no database)
  - Tests for registration (success, duplicate email, without display name)
  - Tests for login (structure demonstrated, requires full argon2 mocking for complete implementation)

### 2. Integration Tests (`tests/integration/`)
- `tests/integration/test_auth.py` - Integration tests with real database via SQLite
  - **`test_login_timing_consistency`** - ✅ Security test that verifies login timing is consistent between non-existent user and wrong password scenarios (within 150ms) to prevent timing attacks
  - **`test_rate_limit_login`** - ✅ Rate limit test that fires 11 rapid requests and verifies the 11th is rate-limited with 429 status and retry-after header
  - Additional comprehensive tests for:
    - Registration (success, duplicate email)
    - Login (success, invalid credentials, inactive user)
    - Token refresh (success, invalid token)

### Test Infrastructure

**Test Database Setup (`tests/conftest.py`):**
- Creates a temporary SQLite database file for tests
- Patches `app.core.database` module BEFORE importing `app.main` to ensure the FastAPI app uses the test database
- `setup_database` fixture (autouse) creates/drops tables for each test and resets rate limiter state
- `async_client` fixture provides HTTP client for API testing
- `test_user` fixture creates a standard test user
- `auth_headers` fixture provides authentication headers

**Key Implementation Details:**
1. Database engine must be patched BEFORE `app.main` is imported (app's lifespan captures the AsyncSessionLocal at import time)
2. Rate limiter state is reset between tests to prevent rate limits from affecting subsequent tests
3. Custom rate limit handler in `app/main.py` adds `Retry-After` header (slowapi's default handler doesn't include it)

### Test Results

✅ **All 17 tests passing** (9 integration + 8 unit tests)

**Critical security tests verified:**
- ✅ Timing attack prevention - login response times are consistent (within 150ms threshold)
- ✅ Rate limiting - 429 status with Retry-After header after 11 requests

### Test Structure Notes

- **Unit tests** use `AsyncMock` with no database - designed for fast feedback
- **Integration tests** use real SQLite database via conftest fixtures
- **Separation of concerns**: Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Tests follow pytest-asyncio patterns with proper async/await usage
- All tests are independent and isolated (no test depends on another)

---

## Backend Stack

- **Python 3.12** with **FastAPI 0.115**
- **SQLAlchemy 2.0** (async engine) + **asyncpg** driver
- **Alembic** for migrations
- **Pydantic v2** for schemas + **pydantic-settings** for config
- **uv** as package manager (replaces pip/poetry)
- **Ruff** for linting/formatting + **mypy** for type checking
- **pytest** + **pytest-asyncio** + **httpx** for testing

---

## Frontend Stack

- **React 18** with **TypeScript 5**
- **Vite** as build tool
- **Tailwind CSS v4** + **shadcn/ui** for UI components
- **TanStack Query v5** for server state management
- **Zustand** for client state management
- **React Router v6** for routing
- **Axios** for HTTP requests

---

## Architecture Rules (CRITICAL — ALWAYS FOLLOW)

### Layer Separation

**Routes** (`app/api/v1/routers/`)
- **Zero business logic**
- Call service layer only
- Return response directly
- Handle HTTP-specific concerns (status codes, headers)

**Services** (`app/services/`)
- **All business logic lives here**
- Call repository layer only
- **Never use SQLAlchemy directly**
- No HTTP or database concerns

**Repositories** (`app/repositories/`)
- **All database queries**
- Use **SQLAlchemy async sessions only**
- No business logic
- Return ORM models (converted to schemas in service layer)

**Schemas** (`app/schemas/`)
- **Pydantic v2 with `model_config = ConfigDict(...)`**
- **Never expose SQLAlchemy ORM models in API responses**
- Use `from_attributes=True` for ORM → Pydantic conversion

**AI Modules** (`app/ai/`)
- **Everything AI-related lives here only**
- LLM clients, prompts, embeddings, RAG logic
- Called by services, never by routes

### Testing Requirements

- **Every new service method gets a unit test**
- **Every new route gets an integration test**
- Use **pytest-asyncio** with **AsyncClient** for async route testing
- Use **fixtures** for database setup/teardown

### Database Rules

- **Always use async SQLAlchemy** — never sync
- **Use dependency injection** for database sessions
- **Never commit in repositories** — commit in services
- **Use `.scalars()` for query results** — not `.execute()`

### Security Rules

- **Never store JWT access tokens in localStorage**
- **Use httpOnly cookies for refresh tokens**
- **Never hardcode API keys** — use pydantic-settings from `.env`
- **Always validate user input** with Pydantic schemas

---

## Dev Commands

### Backend

```bash
# Start development server
uv run uvicorn app.main:app --reload --port 8000

# Run all tests
uv run pytest -v

# Run tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy app/

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1
```

### Frontend

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Run linting
npm run lint

# Type check
npm run type-check
```

---

## Folder Structure

```
backend/app/
├── __init__.py
├── main.py                 # FastAPI app entry point
├── ai/                     # All AI logic (LLMs, prompts, embeddings)
│   └── __init__.py
├── api/                    # API routes
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       └── routers/        # Route handlers (no business logic)
├── core/                   # Core configurations
│   ├── __init__.py
│   ├── config.py           # pydantic-settings config
│   ├── database.py         # Async SQLAlchemy engine/session
│   ├── dependencies.py     # Dependency injection
│   └── security.py         # JWT, password hashing
├── integrations/           # External service integrations
│   └── __init__.py
├── middleware/             # Custom middleware
│   └── __init__.py
├── models/                 # SQLAlchemy ORM models
│   └── __init__.py
├── repositories/           # Database queries (SQLAlchemy only)
│   └── __init__.py
├── schemas/                # Pydantic schemas for request/response
│   └── __init__.py
├── services/               # Business logic (calls repositories)
│   └── __init__.py
└── workers/                # Background tasks (Celery/ARQ)
    └── __init__.py
```

---

## What NOT to Do (Common AI Mistakes)

### ❌ Database Layer Violations

```python
# ❌ NEVER put DB queries in routes
@router.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one()

# ❌ NEVER put DB queries in services
async def get_user_service(user_id: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one()
```

✅ **Correct pattern:**
```python
# Repository (app/repositories/user.py)
async def get_by_id(self, user_id: int) -> User | None:
    result = await self.db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# Service (app/services/user.py)
async def get_user(self, user_id: int) -> UserSchema:
    user = await self.user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserSchema.model_validate(user)

# Route (app/api/v1/routers/users.py)
@router.get("/{user_id}", response_model=UserSchema)
async def get_user(user_id: int, user_service: UserService = Depends()):
    return await user_service.get_user(user_id)
```

### ❌ Business Logic Violations

```python
# ❌ NEVER put business logic in repositories
async def create_user(self, user_data: dict) -> User:
    if user_data["age"] < 18:  # Business logic!
        raise ValueError("Must be 18+")
    # ...
```

### ❌ Async/Sync Violations

```python
# ❌ NEVER use synchronous SQLAlchemy
from sqlalchemy.orm import Session

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()
```

### ❌ Security Violations

```python
# ❌ NEVER hardcode secrets
OPENAI_API_KEY = "sk-proj-abc123..."

# ❌ NEVER expose ORM models in API
@router.get("/users/{user_id}", response_model=User)  # User is ORM model!
```

### ❌ Schema Violations

```python
# ❌ NEVER use old Pydantic v1 Config class
class UserSchema(BaseModel):
    class Config:  # Old style!
        from_attributes = True

# ✅ Use Pydantic v2 model_config
class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

---

## Important Notes

- **Always check `.env.example` before adding new environment variables**
- **Use dependency injection** for services and repositories
- **Follow existing patterns** in the codebase — consistency matters
- **Write docstrings** for public methods
- **Use type hints** everywhere — mypy must pass
- **Keep routes thin** — 5 lines max per route handler
- **Keep services focused** — single responsibility principle
