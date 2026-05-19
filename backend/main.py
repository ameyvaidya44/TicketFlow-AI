"""
backend/main.py — FastAPI application entry point.

Starts the TicketFlow AI backend:
- Registers all 7 routers
- Sets up MongoDB connections on startup
- Configures APScheduler for background tasks (SLA monitoring, root cause)
- Configures CORS for React frontend
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from core.config import settings
from core.database import db_manager as database_manager, create_indexes


# ─── Application lifespan ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("═══ TicketFlow AI Backend Starting ═══")

    # 1. Connect MongoDB
    await database_manager.connect()
    await create_indexes()
    logger.info("MongoDB connected and indexes created.")

    # 2. Display LLM Provider Configuration
    resolved = settings.resolved_llm_provider
    if resolved == "cerebras":
        logger.info(f"🤖 LLM provider: Cerebras (cloud)")
        logger.info(f"📦 Cerebras model: {settings.CEREBRAS_MODEL}")
    elif resolved == "ollama":
        logger.info(f"🤖 LLM provider: Ollama (local)")
        logger.info(f"📦 Ollama model: {settings.OLLAMA_MODEL}")
        logger.info(f"🔗 Ollama URL: {settings.OLLAMA_URL}")
    elif resolved == "qwen":
        logger.info(f"🤖 LLM provider: Qwen (cloud)")
        logger.info(f"📦 Qwen model: {settings.QWEN_MODEL}")
        logger.info(f"🔗 Qwen API: {settings.QWEN_API_BASE}")
    else:
        logger.warning(f"⚠️  Unknown LLM provider: {settings.LLM_PROVIDER}")

    # 3. Start APScheduler for background jobs
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = AsyncIOScheduler()

        # Root cause detection — every 5 minutes
        from services.root_cause_service import root_cause_service

        scheduler.add_job(
            root_cause_service.run_detection,
            trigger=IntervalTrigger(minutes=5),
            id="root_cause_detection",
            replace_existing=True,
        )

        # SLA warning check — every 2 minutes
        scheduler.add_job(
            check_sla_warnings,
            trigger=IntervalTrigger(minutes=2),
            id="sla_warning_check",
            replace_existing=True,
        )

        # Escalation chain timer check — every 5 minutes
        from services.escalation_service import escalation_service

        scheduler.add_job(
            escalation_service.check_escalations,
            trigger=IntervalTrigger(minutes=5),
            id="escalation_chain_check",
            replace_existing=True,
        )

        scheduler.start()
        app.state.scheduler = scheduler
        logger.info(
            "APScheduler started: root_cause(5min), sla_check(2min), escalation(5min)"
        )
    except ImportError:
        logger.warning("apscheduler not installed. Background jobs disabled.")

    logger.info("TicketFlow AI is ready!")

    yield  # --- Application running ---

    logger.info("Shutting down TicketFlow AI...")
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown(wait=False)
    await database_manager.disconnect()
    logger.info("MongoDB disconnected. Goodbye.")


async def check_sla_warnings():
    """
    Scheduled job: check all open tickets for SLA risk and notify agents.
    """
    from core.database import get_tickets_collection
    from services.sla_service import sla_service
    from services.notification_service import notification_service
    from datetime import datetime, timezone

    try:
        collection = get_tickets_collection()
        cursor = collection.find(
            {"status": "open"},
            {
                "ticket_id": 1,
                "ai_analysis.category": 1,
                "ai_analysis.priority": 1,
                "created_at": 1,
            },
        )
        tickets = await cursor.to_list(length=500)

        now = datetime.now(timezone.utc)
        for t in tickets:
            ai = t.get("ai_analysis") or {}
            category = ai.get("category", "Software")
            priority = ai.get("priority", "Medium")
            created_at = t.get("created_at")
            if not created_at:
                continue

            # MongoDB may return created_at as a string — parse it to datetime
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                except ValueError:
                    continue
            # Ensure timezone-aware
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            sla_info = sla_service.get_sla_info(category, priority, created_at)
            mins_left = sla_info["minutes_remaining"]

            # Warn when < 20% SLA time remaining
            sla_mins = sla_info["sla_minutes"]
            if 0 < mins_left < sla_mins * 0.20:
                await notification_service.notify_sla_warning(
                    ticket_id=t["ticket_id"],
                    minutes_left=mins_left,
                    category=category,
                    priority=priority,
                )
    except Exception as e:
        logger.error(f"SLA warning check failed: {e}")


# ─── FastAPI application ──────────────────────────────────────────────
app = FastAPI(
    title="TicketFlow AI",
    description="Intelligent Auto-Handling of Support Tickets with Confidence-Based HITL",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register all routers ─────────────────────────────────────────────
from routers.auth import router as auth_router
from routers.tickets import router as tickets_router
from routers.feedback import router as feedback_router
from routers.agents import router as agents_router
from routers.analytics import router as analytics_router
from routers.admin import router as admin_router
from routers.websocket import router as ws_router
from routers.security import router as security_router
from routers.queue import router as queue_router
from routers.simulation import router as simulation_router
from routers.images import router as images_router
from routers.journey import router as journey_router  # NEW: Journey tracking

app.include_router(auth_router)
app.include_router(tickets_router)
app.include_router(feedback_router)
app.include_router(agents_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(ws_router)
app.include_router(security_router)
app.include_router(queue_router)
app.include_router(simulation_router)
app.include_router(images_router)
app.include_router(journey_router)  # NEW: Journey tracking


# ─── Health endpoints ─────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "TicketFlow AI"}


@app.get("/health/llm")
async def llm_health_check():
    """Check LLM provider status and configuration."""
    from services.llm_provider_factory import llm_provider
    from services.ollama_provider import ollama_provider as ollama
    
    config = {
        "provider": settings.LLM_PROVIDER,
        "model": settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else settings.QWEN_MODEL,
        "url": settings.OLLAMA_URL if settings.LLM_PROVIDER == "ollama" else settings.QWEN_API_BASE,
    }
    
    # Test availability
    is_available = False
    error_message = None
    
    try:
        if settings.LLM_PROVIDER.lower() == "ollama":
            is_available = await ollama.is_available()
            if is_available:
                # Test generation
                test_response = await ollama.generate("Say 'OK'", temperature=0.1, max_tokens=10)
                is_available = bool(test_response)
                if not test_response:
                    error_message = "Ollama is reachable but generation failed"
        else:
            # For Qwen, just return config
            is_available = True
    except Exception as e:
        error_message = str(e)
    
    return {
        "status": "available" if is_available else "unavailable",
        "config": config,
        "error": error_message,
    }


@app.get("/")
async def root():
    return {
        "name": "TicketFlow AI",
        "version": "1.0.0",
        "docs": "/docs",
    }
