import hashlib
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.services.agentic_service import AgenticService


app = FastAPI(
    title="ShopAssist AI",
    description=(
        "Production-oriented AI customer support assistant "
        "with RAG, intent routing, and bounded agentic support"
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
    )


class RateLimiter:
    def __init__(
        self,
        limit: int = 20,
        window_seconds: int = 60,
    ):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
        self.lock = Lock()

    def allow(self, client_id: str) -> bool:
        now = time.time()

        with self.lock:
            queue = self.requests[client_id]

            while (
                queue
                and now - queue[0] > self.window_seconds
            ):
                queue.popleft()

            if len(queue) >= self.limit:
                return False

            queue.append(now)

            return True


rate_limiter = RateLimiter(
    limit=20,
    window_seconds=60,
)

# W16 agentic service does not eagerly import the RAG stack.
agentic_service = AgenticService()

_cache = {}
_cache_lock = Lock()

CACHE_TTL = 300


def cache_key(message: str) -> str:
    return hashlib.sha256(
        message.strip().lower().encode("utf-8")
    ).hexdigest()


def get_cached(message: str):
    key = cache_key(message)

    with _cache_lock:
        item = _cache.get(key)

        if not item:
            return None

        timestamp, value = item

        if time.time() - timestamp > CACHE_TTL:
            del _cache[key]
            return None

        return value


def set_cached(
    message: str,
    value: dict,
):
    key = cache_key(message)

    with _cache_lock:
        _cache[key] = (
            time.time(),
            value,
        )


def get_chat_service():
    """
    Lazily import the W15 ChatService.

    The W15 service imports sentence-transformers and PyTorch.
    Keeping this import inside the function allows the FastAPI
    application and W16 agent to start even when the local
    PyTorch DLL is blocked by Windows Application Control.
    """
    from backend.services.chat_service import ChatService

    return ChatService()


@app.get("/")
def root():
    return {
        "message": "ShopAssist AI is running",
        "version": "3.0.0",
        "features": [
            "Gemini LLM",
            "Intent Routing",
            "RAG",
            "Vector Search",
            "Tool Calling",
            "Caching",
            "Rate Limiting",
            "Bounded Agentic Loop",
            "Adaptive Tool Selection",
            "Evidence Compaction",
        ],
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "shopassist-ai",
    }


@app.get("/ready")
def readiness():
    return {
        "status": "ready",
        "service": "shopassist-ai",
    }


# ============================================================
# W15 ENDPOINT
# ============================================================

@app.post("/chat")
def chat(
    request: ChatRequest,
    http_request: Request,
):
    """
    Original W15 endpoint.

    ChatService is imported lazily because its RAG dependency
    stack currently triggers the Windows PyTorch DLL policy error.
    """

    client_id = (
        http_request.client.host
        if http_request.client
        else "unknown"
    )

    if not rate_limiter.allow(client_id):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": (
                    "Too many requests. "
                    "Please retry shortly."
                ),
            },
        )

    cached = get_cached(request.message)

    if cached is not None:
        cached = dict(cached)
        cached["cached"] = True
        return cached

    try:
        chat_service = get_chat_service()

        response = chat_service.process(
            request.message
        )

        response["cached"] = False

        set_cached(
            request.message,
            response,
        )

        return response

    except Exception as exc:
        error_name = type(exc).__name__
        error_text = str(exc).lower()

        if (
            "ratelimit" in error_name.lower()
            or "quota" in error_text
            or "429" in error_text
        ):
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "provider_rate_limited",
                    "message": (
                        "The AI provider is temporarily "
                        "rate-limited. Please retry after "
                        "the quota resets."
                    ),
                },
            )

        print(
            f"Chat request failed: "
            f"{type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "chat_generation_failed",
                "message": (
                    "The AI service could not "
                    "complete this request."
                ),
            },
        )


# ============================================================
# W16 AGENTIC ENDPOINT
# ============================================================

@app.post("/agent/chat")
def agent_chat(
    request: ChatRequest,
    http_request: Request,
):
    """
    W16 bounded agentic endpoint.

    The model dynamically chooses the next action based on
    the evidence gathered during previous iterations.
    """

    client_id = (
        http_request.client.host
        if http_request.client
        else "unknown"
    )

    if not rate_limiter.allow(client_id):
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "message": (
                    "Too many requests. "
                    "Please retry shortly."
                ),
            },
        )

    try:
        response = agentic_service.process(
            request.message
        )

        response["agentic"] = True

        return response

    except Exception as exc:
        error_name = type(exc).__name__
        error_text = str(exc).lower()

        if (
            "ratelimit" in error_name.lower()
            or "quota" in error_text
            or "429" in error_text
        ):
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "provider_rate_limited",
                    "message": (
                        "The AI provider is temporarily "
                        "rate-limited. Please retry after "
                        "the quota resets."
                    ),
                },
            )

        print(
            f"Agent request failed: "
            f"{type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "agent_generation_failed",
                "message": (
                    "The agent could not safely "
                    "complete this request."
                ),
            },
        )
