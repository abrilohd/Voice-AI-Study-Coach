# Voice AI Study Coach

> Multi-LLM voice tutor — Socratic, adaptive, provider-agnostic.

## Week 1 ✅ Foundation complete

| Layer | Tech |
|-------|------|
| Backend | FastAPI · Python 3.11 |
| LLMs | Claude (primary) · GPT-4o (fallback) · Gemini Flash (budget) |
| Frontend | React · Vite |
| Architecture | Zero provider lock-in — swap via `.env` |

## Quick start

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in your API keys
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
cp .env.example .env
npm install && npm run dev
```

## API

| Method | Route | Description |
|--------|-------|-------------|
| GET | /health | Status + active LLM |
| POST | /chat/ | Tutor conversation |
| POST | /quiz/ | Generate MCQ quiz |

## Switch LLM (zero code changes)
```bash
PRIMARY_LLM=openai   # or gemini
FALLBACK_LLM=gemini
```

## Run tests
```bash
cd backend && pytest tests/ -v
```
