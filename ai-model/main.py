"""
AI Chat API - FastAPI wrapper around Ollama for open-source LLM serving.
Task 6: Dockerized AI model service
"""

import os
import uuid
import logging
from typing import Optional, List

import httpx
import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://ollama:11434")
MODEL_NAME   = os.getenv("MODEL_NAME",   "tinyllama")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/chatdb")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Chat API",
    description="Open-source LLM Chat API powered by Ollama + TinyLlama",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_pool: Optional[asyncpg.Pool] = None

# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    global db_pool
    # Connect to Postgres
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        logger.info("✅ Database connection pool established")
    except Exception as exc:
        logger.warning(f"⚠️  Database unavailable – running without persistence: {exc}")

    # Pre-pull the model so first request is fast
    await _ensure_model()


@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()


async def _ensure_model():
    """Pull the configured model if it is not already cached in Ollama."""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            logger.info(f"🔄 Pulling model '{MODEL_NAME}' from Ollama …")
            resp = await client.post(
                f"{OLLAMA_HOST}/api/pull",
                json={"name": MODEL_NAME, "stream": False},
            )
            if resp.status_code == 200:
                logger.info(f"✅ Model '{MODEL_NAME}' ready")
            else:
                logger.warning(f"Model pull returned {resp.status_code}: {resp.text}")
    except Exception as exc:
        logger.warning(f"⚠️  Could not pull model (Ollama may not be up yet): {exc}")


# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    model: str


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama: str
    database: str


class Message(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None


# ── Helper – build prompt with history ───────────────────────────────────────
def _build_prompt(history: List[dict], user_message: str) -> str:
    prompt = (
        "You are a helpful, friendly AI assistant. "
        "Answer concisely and accurately.\n\n"
    )
    for msg in history:
        prefix = "User" if msg["role"] == "user" else "Assistant"
        prompt += f"{prefix}: {msg['content']}\n"
    prompt += f"User: {user_message}\nAssistant:"
    return prompt


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health():
    # Check Ollama
    ollama_status = "unreachable"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            ollama_status = "healthy" if r.status_code == 200 else "unhealthy"
    except Exception:
        pass

    # Check DB
    db_status = "unavailable"
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_status = "healthy"
        except Exception:
            db_status = "unhealthy"

    return HealthResponse(
        status="healthy",
        model=MODEL_NAME,
        ollama=ollama_status,
        database=db_status,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    history: List[dict] = []

    # ── Load conversation history ─────────────────────────────────────────
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                # Upsert conversation
                await conn.execute(
                    "INSERT INTO conversations(id) VALUES($1) ON CONFLICT DO NOTHING",
                    uuid.UUID(conversation_id),
                )
                rows = await conn.fetch(
                    """SELECT role, content
                       FROM messages
                       WHERE conversation_id = $1
                       ORDER BY created_at DESC
                       LIMIT 10""",
                    uuid.UUID(conversation_id),
                )
                history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception as exc:
            logger.warning(f"DB read error: {exc}")

    # ── Call Ollama ───────────────────────────────────────────────────────
    prompt = _build_prompt(history, req.message)
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 512,
                    },
                },
            )
            resp.raise_for_status()
            ai_text: str = resp.json().get("response", "").strip()
    except httpx.HTTPStatusError as exc:
        logger.error(f"Ollama HTTP error: {exc.response.status_code}")
        raise HTTPException(status_code=502, detail="AI service error")
    except Exception as exc:
        logger.error(f"Ollama error: {exc}")
        raise HTTPException(status_code=503, detail="AI service unavailable")

    # ── Persist messages ──────────────────────────────────────────────────
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO messages(conversation_id, role, content) VALUES($1,$2,$3)",
                    uuid.UUID(conversation_id), "user", req.message,
                )
                await conn.execute(
                    "INSERT INTO messages(conversation_id, role, content) VALUES($1,$2,$3)",
                    uuid.UUID(conversation_id), "assistant", ai_text,
                )
        except Exception as exc:
            logger.warning(f"DB write error: {exc}")

    return ChatResponse(
        response=ai_text,
        conversation_id=conversation_id,
        model=MODEL_NAME,
    )


@app.get("/conversations/{conversation_id}/messages", response_model=List[Message])
async def get_history(conversation_id: str):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT role, content, created_at
                   FROM messages
                   WHERE conversation_id = $1
                   ORDER BY created_at ASC""",
                uuid.UUID(conversation_id),
            )
        return [Message(role=r["role"], content=r["content"], created_at=str(r["created_at"])) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
