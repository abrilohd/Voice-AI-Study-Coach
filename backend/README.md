# Voice AI Study Coach - Backend

Backend API for the Voice AI Study Coach application.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables (copy from `.env.example`)

3. Run the application:
```bash
uv run uvicorn app.main:app --reload
```

## Testing

```bash
uv run pytest
```

## Type Checking

```bash
uv run mypy app --strict
```
