#  Voice AI Study Coach

> **Production-ready AI tutor with multi-LLM support, voice I/O, RAG-ready architecture & zero provider lock-in**

![Status](https://img.shields.io/badge/status-production--ready-brightgreen?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-modern%20python%20web-009688?style=for-the-badge)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react)

---

##  What This Does

A **conversational AI study coach** that adapts to your learning style. Ask questions, get Socratic responses, take adaptive quizzes, and learn at your pace.

**Key Innovation:** Swap LLM providers (Claude → GPT-4 → Gemini) with **zero code changes**. Pure `.env` configuration.

---

##  Quick Start

### Backend Setup
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Add your API keys
uvicorn main:app --reload --port 8000
```

**Backend URL:** `http://localhost:8000`
**API Docs:** `http://localhost:8000/docs`

### Frontend Setup
```bash
cd frontend
cp .env.example .env
npm install && npm run dev
```

**Frontend URL:** `http://localhost:5173`

---

##  Features

###  Core Learning
- **Conversational Tutoring** - Ask anything, get personalized explanations
- **Socratic Method** - AI guides you to answers instead of just giving them
- **Adaptive Quizzes** - MCQ quizzes that adapt to your knowledge level
- **Study Sessions** - Track learning progress & session history
- **Multi-subject Support** - Math, Science, History, Languages, and more

###  AI Architecture
- **Multi-LLM Support** - Claude, GPT-4, Gemini, or any OpenAI-compatible API
- **Provider Agnostic** - Switch LLMs without redeploying
- **Fallback Support** - Graceful degradation if primary LLM is down
- **Cost Optimization** - Use budget models for simple queries

###  Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI · Python 3.11 · Pydantic |
| **Database** | PostgreSQL (prod) · SQLite (dev) |
| **LLMs** | Claude · GPT-4o · Gemini Flash |
| **Frontend** | React · Vite · TypeScript |
| **Voice** | Web Speech API (ready for TTS/STT) |
| **Deployment** | Docker · Railway/Render |

---

##  API Endpoints

### Health & Status
```
GET /health              # Server status + active LLM
```

### Chat & Tutoring
```
POST /chat/              # Send question, get explanation
  {
    "question": "What is photosynthesis?",
    "subject": "Biology",
    "level": "high_school"
  }
```

### Quiz Generation
```
POST /quiz/              # Generate adaptive MCQ quiz
  {
    "subject": "Physics",
    "num_questions": 5,
    "difficulty": "intermediate"
  }
```

---

##  Configuration

### Environment Variables
```env
# LLM Configuration
PRIMARY_LLM=anthropic              # or openai, gemini
FALLBACK_LLM=gemini
CLAUDE_API_KEY=your_key
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key

# Database
DATABASE_URL=postgresql://user:pass@localhost/study_coach

# Server
DEBUG=False
SECRET_KEY=your_secret_key
CORS_ORIGINS=http://localhost:5173
```

### Switch LLMs (Zero Code Changes)
```bash
PRIMARY_LLM=gemini
FALLBACK_LLM=groq
```

---

##  Deployment

This project is a strong fit for Azure Container Apps because it already uses a multi-service architecture: a FastAPI backend, a React frontend, and a PostgreSQL-backed data layer. For production, the recommended Azure pattern is to run each app in a separate container, push the images to Azure Container Registry, and connect them to an Azure-managed PostgreSQL database.

### Prerequisites

Before deploying, make sure you have:

- Azure CLI installed and authenticated (`az login`)
- Docker installed locally
- An active Azure subscription
- Application Dockerfiles ready for the backend and frontend

### 1) Push Docker images to Azure Container Registry (ACR)

Create a resource group and ACR first:

```bash
az login

az group create \
  --name study-coach-rg \
  --location eastus

az acr create \
  --resource-group study-coach-rg \
  --name mystudycoachregistry \
  --sku Basic
```

Log in to the registry:

```bash
az acr login --name mystudycoachregistry
```

Build and push the images:

```bash
docker build -t mystudycoachregistry.azurecr.io/backend:latest ./backend
docker build -t mystudycoachregistry.azurecr.io/frontend:latest ./frontend

docker push mystudycoachregistry.azurecr.io/backend:latest
docker push mystudycoachregistry.azurecr.io/frontend:latest
```

If your project uses Docker Compose, you can also do:

```bash
docker compose build
docker compose push
```

### 2) Create a managed PostgreSQL database

Use Azure Database for PostgreSQL Flexible Server instead of running a database container in production:

```bash
az postgres flexible-server create \
  --resource-group study-coach-rg \
  --name studycoach-db-server \
  --admin-user dbadmin \
  --admin-password "YourStrongPassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15
```

Configure firewall rules to allow Azure services to reach the database:

```bash
az postgres flexible-server firewall-rule create \
  --resource-group study-coach-rg \
  --server-name studycoach-db-server \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### 3) Deploy to Azure Container Apps

Create the environment:

```bash
az containerapp env create \
  --name study-coach-env \
  --resource-group study-coach-rg \
  --location eastus
```

Deploy the backend container:

```bash
az containerapp create \
  --name backend-service \
  --resource-group study-coach-rg \
  --environment study-coach-env \
  --image mystudycoachregistry.azurecr.io/backend:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server mystudycoachregistry.azurecr.io \
  --env-vars \
    DATABASE_URL="postgresql://dbadmin:YourStrongPassword123!@studycoach-db-server.postgres.database.azure.com:5432/postgres?sslmode=require" \
    PRIMARY_LLM="anthropic" \
    FALLBACK_LLM="gemini" \
    CLAUDE_API_KEY="your_key" \
    OPENAI_API_KEY="your_key" \
    GOOGLE_API_KEY="your_key"
```

Deploy the frontend container and set the frontend API base URL to the live backend URL:

```bash
az containerapp create \
  --name frontend-service \
  --resource-group study-coach-rg \
  --environment study-coach-env \
  --image mystudycoachregistry.azurecr.io/frontend:latest \
  --target-port 80 \
  --ingress external \
  --registry-server mystudycoachregistry.azurecr.io
```

### 4) Verify the deployment

Once the commands finish, Azure will output external URLs for both services. Test the backend health endpoint:

```bash
curl https://<backend-service-url>/health
```

Then open the frontend URL in a browser to validate that the app loads and calls the live backend correctly.

This is the recommended Azure deployment approach for a Dockerized, multi-service app like Voice AI Study Coach because it gives you scalable HTTP ingress, managed networking, and a production-ready database layer without running everything in a single VM.

---

##  Testing

```bash
cd backend && pytest tests/ -v
```

---

##  Security

-  JWT authentication
-  Rate limiting per user
-  Input validation (Pydantic)
-  SQL injection prevention
-  CORS configured
-  API keys never logged

---

##  Documentation

- **[Backend Docs](./backend/README.md)** - Backend architecture
- **[Frontend Guide](./frontend/README.md)** - Component structure
- **[LLM Integration](./docs/llm_integration.md)** - Add LLM providers
- **[Architecture](./docs/adr/)** - Design decisions

---

##  Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit with clear messages
4. Test thoroughly
5. Push and open a PR

---

##  License

MIT License - see [LICENSE](LICENSE)

---

##  Support

-  **Issues:** [Report bugs](https://github.com/abrilohd/Voice-AI-Study-Coach/issues)
-  **Features:** [Request features](https://github.com/abrilohd/Voice-AI-Study-Coach/issues)
-  **Email:** abrsh067@gmail.com

---

**Ready to learn? [Get started now!](./QUICK_START.md)**

Built with ❤️ for learners everywhere.
