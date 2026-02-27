# 🎓 Student Guide — DevOps & AI in Practice
## Assignments 6, 7 and 10 — Step-by-Step Walkthrough

> **What you will build:** A complete AI Chat web application powered by the open-source
> **TinyLlama** language model, deployed progressively from a single Docker container to a
> full multi-container stack with CI/CD automation.

---

## 📋 Table of Contents

1. [Prerequisites & Setup](#0-prerequisites--setup)
2. [Task 6 — Docker Container for AI Model](#task-6--docker-container-for-ai-model)
3. [Task 7 — Docker Compose (Multi-Container App)](#task-7--docker-compose-multi-container-app)
4. [Task 10 — CI/CD Pipeline with Jenkins](#task-10--cicd-pipeline-with-jenkins)
5. [Troubleshooting](#troubleshooting)

---

## 0. Prerequisites & Setup

Before starting, you need to install the following tools on your machine.

### A. Install Required Tools (macOS)

Open Terminal and run each block one at a time:

**1. Install Homebrew** (package manager for macOS):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**2. Install Docker Desktop:**
```bash
brew install --cask docker
```
→ After install, open Docker Desktop from Applications and wait for it to start (whale icon in menu bar turns solid).


### B. Verify All Tools Are Installed

Run this single command to check everything at once:
```bash
for tool in docker; do
  if command -v "$tool" &>/dev/null; then
    echo "✅  $tool  →  $(which $tool)"
  else
    echo "❌  $tool NOT found"
  fi
done
```

**Expected output:**
```
✅  docker  →  /usr/local/bin/docker
```

### C. Clone / Open the Project

```bash
cd /Users/<your-username>/Documents
# If you already have the project folder:
cd devops-and-git-in-ai
# Verify the files are there
ls -la
```

You should see: `ai-model/`, `frontend/`, `database/`, `docker-compose.yml`, `jenkins/`

---

## Task 6 — Docker Container for AI Model

> **Goal:** Package an AI model inside a Docker container so it runs the same way on every machine.

### 📖 Concepts Introduced
| Concept | What it means |
|---------|--------------|
| **Docker Image** | A blueprint/snapshot of your app and all its dependencies |
| **Docker Container** | A running instance of an image (like a lightweight VM) |
| **Dockerfile** | A recipe that tells Docker how to build your image |
| **Multi-stage build** | Build the app in one stage, copy only what's needed to a smaller final image |

---

### Step 6.1 — Understand the Application

Open and read the files before running anything:

```bash
# Look at the AI model API code
cat ai-model/main.py
```

**Key things to notice in main.py:**
- It is a **FastAPI** web server
- It talks to **Ollama** (a tool that runs open-source LLMs)
- It saves chat history to **PostgreSQL**
- The `/health` endpoint tells you if the API and model are running

```bash
# Look at the Dockerfile
cat ai-model/Dockerfile
```

**Key things to notice in the Dockerfile:**
- `FROM python:3.11-slim AS builder` → first stage: install Python packages
- `FROM python:3.11-slim` → second stage: copy only installed packages (smaller image)
- `RUN useradd -m -u 1000 appuser` → create a non-root user (security best practice)
- `HEALTHCHECK` → Docker will automatically test if the container is healthy

---

### Step 6.2 — Start Ollama (the LLM runtime)

Ollama is the open-source tool that actually runs the AI model. Start it first:

```bash
# Pull and run the Ollama container
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama:latest
```

> **What this does:**
> - `-d` → run in background (detached mode)
> - `--name ollama` → give the container a name
> - `-p 11434:11434` → expose port 11434 on your machine
> - `-v ollama-data:/root/.ollama` → save downloaded models to a volume (so you don't re-download)

Wait about 10 seconds for Ollama to start, then verify it's running:
```bash
curl http://localhost:11434/api/tags
```

**Expected output:** `{"models":[]}` (empty list — no models downloaded yet)

---

### Step 6.3 — Pull the TinyLlama Model

```bash
# Tell Ollama to download TinyLlama (about 637 MB — takes 2–5 min depending on internet)
docker exec ollama ollama pull tinyllama
```

Watch the progress. When done:
```bash
# Verify the model is downloaded
curl http://localhost:11434/api/tags | python3 -m json.tool
```

**Expected output** (you should see `tinyllama` in the list):
```json
{
  "models": [
    {
      "name": "tinyllama:latest",
      "model": "tinyllama:latest",
      ...
    }
  ]
}
```

---

### Step 6.4 — Build the AI Model Docker Image

```bash
# From the project root directory
docker build -t ai-chat/ai-model:latest ./ai-model
```

> **What this does:** Docker reads `ai-model/Dockerfile` and creates an image named `ai-chat/ai-model:latest`

Watch the output. Each `Step X/Y` is one instruction from the Dockerfile being executed.

When finished, verify the image was created:
```bash
docker images ai-chat/ai-model
```

**Expected output:**
```
REPOSITORY          TAG       IMAGE ID       CREATED          SIZE
ai-chat/ai-model    latest    abc123def456   10 seconds ago   180MB
```

---

### Step 6.5 — Run the AI Model Container

```bash
docker run -d \
  --name ai-model \
  -p 8000:8000 \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -e MODEL_NAME=tinyllama \
  ai-chat/ai-model:latest
```

> **What this does:**
> - `-e OLLAMA_HOST=http://host.docker.internal:11434` → tells the container how to reach Ollama
>   (`host.docker.internal` is the magic hostname Docker uses to reach your Mac's localhost)

Wait ~30 seconds for the API to start, then check its health:

```bash
curl http://localhost:8000/health | python3 -m json.tool
```

**Expected output:**
```json
{
  "status": "healthy",
  "model": "tinyllama",
  "ollama": "healthy",
  "database": "unavailable"
}
```

> ℹ️ `database: unavailable` is expected — we haven't started PostgreSQL yet (that's Task 7).

---

### Step 6.6 — Test the Chat API

Send your first message to the AI:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Docker and why is it useful?"}' \
  | python3 -m json.tool
```

**Expected output** (actual text will vary):
```json
{
  "response": "Docker is a platform that allows you to package applications into containers...",
  "conversation_id": "some-uuid-here",
  "model": "tinyllama"
}
```

🎉 **Your AI model is running in a Docker container!**

---

### Step 6.7 — Inspect the Running Container

```bash
# See running containers
docker ps

# View live logs from the container
docker logs -f ai-model
# (Press Ctrl+C to stop following logs)

# See container resource usage
docker stats ai-model --no-stream
```

---

### Step 6.8 — Clean Up (Before Task 7)

```bash
# Stop and remove the containers we started manually
docker stop ai-model ollama
docker rm ai-model ollama
```

> ℹ️ The Ollama model data is still saved in the `ollama-data` volume — you won't need to re-download it.

---

## Task 7 — Docker Compose (Multi-Container App)

> **Goal:** Use Docker Compose to manage all four containers (Ollama, AI Model, Database, Frontend) together as one application.

### 📖 Concepts Introduced
| Concept | What it means |
|---------|--------------|
| **Docker Compose** | A tool to define and run multi-container apps using a YAML file |
| **Service** | Each container defined in `docker-compose.yml` |
| **Health check** | A test Docker runs inside a container to know if it's ready |
| **depends_on** | Tells Compose which containers must be healthy before starting another |
| **Volume** | Persistent storage that survives container restarts |
| **Network** | A private network so containers can talk to each other by name |

---

### Step 7.1 — Read the Docker Compose File

```bash
cat docker-compose.yml
```

**Notice the structure:**
```
ollama (LLM runtime)
  └── model-puller (one-shot job: downloads tinyllama)
  └── ai-model (FastAPI API)
        └── postgres (database)
frontend (Nginx + chat UI)
  └── depends on ai-model being healthy
```

Each service has:
- `build:` or `image:` — where to get the container
- `ports:` — which ports to expose
- `environment:` — environment variables passed to the container
- `healthcheck:` — how Docker tests if the container is ready
- `depends_on:` — startup ordering

---

### Step 7.2 — Create Your Environment File

```bash
# Copy the example config
cp .env.example .env

# View it
cat .env
```

The `.env` file lets you override settings without changing `docker-compose.yml`. For now, the defaults are fine.

---

### Step 7.3 — Start the Full Stack

```bash
docker compose up -d --build
```

> **What this does:**
> - `--build` → rebuild images from Dockerfiles (use this after code changes)
> - `-d` → start everything in the background

**The startup sequence takes about 3–5 minutes on first run** because Ollama needs to download TinyLlama. Watch the progress:

```bash
docker compose logs -f
```

You'll see something like:
```
ollama       | Ollama is running
model-puller | Pulling model tinyllama from Ollama…
model-puller | ✅ Model pulled successfully
ai-model     | INFO:     Application startup complete.
frontend     | /docker-entrypoint.sh: Configuration complete; ready for start up
```

Press `Ctrl+C` to stop following logs (containers keep running).

---

### Step 7.4 — Verify All Services Are Healthy

```bash
docker compose ps
```

**Expected output** (all should show `healthy`):
```
NAME          IMAGE                  STATUS
ollama        ollama/ollama          Up (healthy)
postgres      postgres:16-alpine     Up (healthy)
ai-model      ai-chat/ai-model       Up (healthy)
frontend      ai-chat/frontend       Up (healthy)
model-puller  curlimages/curl        Exited (0)     ← one-shot job, exit 0 = success
```

---

### Step 7.5 — Open the Chat App

```bash
open http://localhost:3000
```

You should see a dark-themed chat UI. Type a message and press Enter!

---

### Step 7.6 — Explore the Running System

```bash
# Check the AI API directly
curl http://localhost:8000/health | python3 -m json.tool
# This time "database" should say "healthy" too!

# Look at what Docker networks were created
docker network ls

# Look at the volumes
docker volume ls

# Tail logs for just the AI model
docker compose logs -f ai-model

# Inspect a specific service's config
docker compose config --services
```

---

### Step 7.7 — Make a Code Change (Hot Reload Demo)

Edit the welcome message in the frontend:
```bash
# Open the HTML file
nano frontend/src/index.html
# Change "Hello! I'm TinyLlama" to "Hello! I'm your AI assistant"
# Save with Ctrl+O, then Ctrl+X

# Rebuild and redeploy only the frontend service
docker compose up -d --build frontend
```

Refresh `http://localhost:3000` — you'll see your change immediately!

---

### Step 7.8 — Stop and Clean Up

```bash
# Stop all containers (keeps volumes = keeps your data)
docker compose down

# Stop AND delete all data (volumes too)
docker compose down -v
```

---

## Task 10 — CI/CD Pipeline with Jenkins

> **Goal:** Automate the entire build → test → push process so every code change triggers a pipeline that builds, tests, and packages the application automatically.

### 📖 Concepts Introduced
| Concept | What it means |
|---------|--------------|
| **CI (Continuous Integration)** | Automatically build and test code on every commit |
| **CD (Continuous Deployment)** | Automatically deploy passing builds to an environment |
| **Jenkins** | An open-source automation server for CI/CD |
| **Freestyle Job** | A Jenkins job where you define build steps as shell commands |
| **Build Step** | A shell command Jenkins runs as part of the job |

---

### Step 10.1 — Start Jenkins

```bash
docker compose -f jenkins/docker-compose.yml up -d
```

Get the initial admin password:
```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Then open Jenkins:
```bash
open http://localhost:8080
```

---

### Step 10.2 — Unlock Jenkins

1. Copy the admin password printed by the script
2. Paste it into the **Administrator password** field on the Jenkins welcome page
3. Click **Continue**

---

### Step 10.3 — Install Required Plugins

1. Click **"Install suggested plugins"** and wait for them to install (~3 minutes)
2. That's it — the suggested plugins include everything you need for a Freestyle job.

---

### Step 10.4 — Create Admin User

1. Fill in: Username, Password, Full name, Email
2. Click **"Save and Continue"**
3. Click **"Save and Finish"** → **"Start using Jenkins"**

---

### Step 10.5 — Create a Freestyle Job

1. Click **"New Item"** on the Jenkins home page
2. Enter name: `ai-chat-lint`
3. Select **"Freestyle project"**
4. Click **"OK"**

---

### Step 10.6 — Add a Build Step

In the job configuration:
1. Scroll down to **"Build Steps"**
2. Click **"Add build step"** → **"Execute shell"**
3. Paste this into the command box:
   ```bash
   cd ai-model
   pip install flake8 --quiet
   flake8 main.py --max-line-length=120
   ```
4. Click **"Save"**

This tells Jenkins: every time you run this job, go into the `ai-model` folder, install flake8, and lint `main.py`. If flake8 finds errors, the job turns red (❌). If it passes, it turns green (✅).

---

### Step 10.7 — Run the Job

1. Click **"Build Now"** on the `ai-chat-lint` job page
2. Click on **#1** that appears under "Build History"
3. Click **"Console Output"** to see Jenkins run the shell command

A successful run looks like:
```
+ cd ai-model
+ pip install flake8 --quiet
+ flake8 main.py --max-line-length=120
Finished: SUCCESS
```

If there are lint errors, the output shows the line and the problem, and the build turns red:
```
main.py:42:1: E302 expected 2 blank lines, found 1
Finished: FAILURE
```

---

### Step 10.8 — Introduce a Lint Error on Purpose

This is the key learning moment — see how Jenkins catches a bad commit.

1. Open `ai-model/main.py` and add a line with a deliberate error:
   ```python
   x=1  # no spaces around = (flake8 E225)
   ```
2. Commit it:
   ```bash
   git add ai-model/main.py
   git commit -m "intentional lint error"
   ```
3. Go to Jenkins → **Build Now** → watch it **fail**
4. Fix the error, commit again, build again → watch it **pass**

---

### Step 10.9 — Understand the CI/CD Flow

```
Developer commits code
         │
         ▼
    Jenkins runs the job
         │
         ▼
   ┌─────────────────────────────┐
   │  Shell step: flake8 main.py │
   └─────────────────────────────┘
         │
         ▼
   ✅ Pass → code is clean
   ❌ Fail → fix the errors, commit again
```

In a real project this job would run **automatically** on every push via a webhook — no manual "Build Now" needed.

---

## Summary — What You Built

| Task | Technology | Key Concept Learned |
|------|-----------|-------------------|
| **6** | Docker + Ollama + TinyLlama | Containerising an AI model |
| **7** | Docker Compose | Multi-container orchestration |
| **10** | Jenkins + Freestyle job | CI/CD automation with shell build steps |

---

## Troubleshooting

### ❓ "Port already in use"
```bash
# Find what's using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

### ❓ Ollama is slow to respond / timing out
The first request to TinyLlama loads the model into memory (~20–30 seconds). Subsequent requests are much faster. Be patient on the first message.

### ❓ `docker: command not found`
Docker Desktop is not running. Open the Docker Desktop app from your Applications folder and wait for the whale icon to appear in the menu bar.

### ❓ Jenkins SCM dropdown only shows "None"
The Git plugin is not installed. Go to **Manage Jenkins** → **Plugins** → **Available plugins**, search for `Git`, install it, then go back to your job configuration.

### ❓ Jenkins pipeline fails with "repository not found"
The project folder must be a git repo. Run:
```bash
git add -A && git commit -m "initial commit"
```

### ❓ Completely start over (nuclear option)
```bash
# Stop everything
docker compose down -v 2>/dev/null
docker system prune -af --volumes
# Then start from Task 6 again
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│  DOCKER COMPOSE                                              │
│  Start:   docker compose up -d --build                      │
│  Stop:    docker compose down                               │
│  Logs:    docker compose logs -f [service]                  │
│  Status:  docker compose ps                                 │
└─────────────────────────────────────────────────────────────┘
```

---

*Generated for Assignment Tasks 6, 7 and 10 | Open-source stack: TinyLlama · Ollama · FastAPI · PostgreSQL · Nginx · Docker · Jenkins*
