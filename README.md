# 🤖 AI Chat App — DevOps Assignment (Tasks 6, 7 and 10)

A fully working **AI Chat web application** powered by the open-source **TinyLlama** LLM running via **Ollama**, with a FastAPI backend, PostgreSQL persistence, and an Nginx-served frontend.

Covers assignment tasks 6, 7, and 10.

---

## 📐 Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Docker Compose                                │
│                                                                       │
│   Browser         Nginx             FastAPI          Ollama           │
│   ──────    ─▶   (Frontend)   ─▶  (AI Model API) ─▶ (TinyLlama LLM) │
│   :3000           :80              :8000             :11434           │
│                    │                  │                               │
│                    └──────────────────▼                               │
│                                  PostgreSQL                           │
│                                   (Chat history)                      │
└───────────────────────────────────────────────────────────────────────┘
```

| Service      | Technology          | Port |
|-------------|---------------------|------|
| `ollama`    | Ollama (TinyLlama)  | 11434|
| `ai-model`  | Python / FastAPI    | 8000 |
| `postgres`  | PostgreSQL 16       | 5432 |
| `frontend`  | Nginx + HTML/CSS/JS | 80   |

---

## 📁 Project Structure

```
devops-and-git-in-ai/
├── ai-model/                  # FastAPI AI service
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/                  # Nginx chat UI
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── index.html
│       ├── style.css
│       └── app.js
├── database/
│   └── init.sql               # Schema + seed data
├── docker-compose.yml         # Task 7 – multi-container
├── jenkins/
│   └── docker-compose.yml
```

---

## ✅ Task 6 — Docker Container for AI Model

### What's built
- `ai-model/main.py` — FastAPI app that proxies chat requests to Ollama
- `ai-model/Dockerfile` — multi-stage build (builder → slim runtime, non-root user)
- Ollama (`ollama/ollama`) runs the **TinyLlama** open-source LLM (1.1B params, CPU-capable)

### Steps

```bash
# 1. Pull Ollama and run TinyLlama locally
docker run -d --name ollama -p 11434:11434 ollama/ollama:latest
docker exec ollama ollama pull tinyllama

# 2. Build the AI model image
docker build -t ai-chat/ai-model:latest ./ai-model

# 3. Run it connected to Ollama
docker run -d --name ai-model \
  -p 8000:8000 \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -e MODEL_NAME=tinyllama \
  ai-chat/ai-model:latest

# 4. Test the API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Docker?"}'
```

**Expected `/health` response:**
```json
{ "status": "healthy", "model": "tinyllama", "ollama": "healthy", "database": "unavailable" }
```

---

## ✅ Task 7 — Docker Compose (Multi-Container)

All four services (Ollama, AI Model, Postgres, Frontend) orchestrated by a single `docker-compose.yml`.

### Steps

```bash
# 1. Copy environment config
cp .env.example .env
# (edit .env if you want a different password)

# 2. Start the full stack (first run pulls TinyLlama ~600 MB)
docker compose up -d --build

# 3. Watch logs until all services are healthy (~3–5 min on first run)
docker compose logs -f

# 4. Open the chat UI
open http://localhost:3000

# 5. Check service health
docker compose ps

# 6. Tear down (keeps volumes)
docker compose down

# Tear down including volumes
docker compose down -v
```

### Service dependencies
```
postgres ──▶ ai-model ──▶ frontend
ollama   ──▶ model-puller (one-shot job: pulls tinyllama)
         ──▶ ai-model
```

---

## ✅ Task 10 — CI/CD with Jenkins

### Start Jenkins

```bash
# Start Jenkins + local Docker registry
bash scripts/setup-jenkins.sh

# Access Jenkins
open http://localhost:8080
```

### Configure Jenkins

1. **Install plugins**: Pipeline, Git

### Run a build

In Jenkins, create a **Freestyle** job and add a shell build step:
```bash
cd ai-model
pip install flake8 --quiet
flake8 main.py --max-line-length=120
```

---

## 🔧 Useful Commands

```bash
# ── Docker Compose ─────────────────────────────────────────────────
docker compose ps                              # service status
docker compose logs -f ai-model               # tail API logs
docker compose exec ai-model curl localhost:8000/health

# ── Ollama ─────────────────────────────────────────────────────────
# List available models
curl http://localhost:11434/api/tags | python3 -m json.tool

# Pull a different model (e.g. phi3:mini – better quality, needs 4GB RAM)
curl -X POST http://localhost:11434/api/pull -d '{"name": "phi3:mini"}'
```

---

## 🔄 Switching Models

Edit `MODEL_NAME` in `.env`:

| Model | Size | RAM needed | Quality |
|-------|------|-----------|---------|
| `tinyllama` | 637 MB | 2 GB | Good for demo |
| `phi3:mini` | 2.3 GB | 4 GB | Better |
| `mistral`   | 4.1 GB | 8 GB | Great |
| `llama3:8b` | 4.7 GB | 8 GB | Excellent |

---

## 📋 Requirements

| Tool | Minimum version |
|------|----------------|
| Docker Desktop | 24.x |
| docker compose | v2 |
| macOS RAM | 8 GB (16 GB recommended) |
