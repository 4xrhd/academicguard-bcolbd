"""
main.py — FastAPI application entry point.
Registers all routers, middleware, CORS, and startup events.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.api import auth, batches, results, reports, admin, annotations, training, marking
from app.core.middleware import AuditLogMiddleware
from app.db.session import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialise DB tables (Alembic handles migrations in production)
    await init_db()
    
    # Recovery: Re-queue pending/processing batches and training runs
    from app.engine.pdf_processor import resume_pending_batches
    from app.engine.auto_trainer import resume_pending_training
    from app.engine.ai_detector import _load_gpt2, _load_ai_classifier
    import asyncio

    async def _safe_resume(coro, name: str):
        try:
            await coro
        except Exception as exc:
            print(f"[WARN] {name} failed during startup recovery: {exc!r}")

    async def _preload_models():
        try:
            from app.engine.text_similarity import preload_models
            await asyncio.to_thread(_load_gpt2)
            await asyncio.to_thread(_load_ai_classifier)
            await asyncio.to_thread(preload_models)
        except Exception as exc:
            print(f"[WARN] Model preloading failed: {exc!r}")

    asyncio.create_task(_safe_resume(resume_pending_batches(), "resume_pending_batches"))
    asyncio.create_task(_safe_resume(resume_pending_training(), "resume_pending_training"))
    asyncio.create_task(_preload_models())
    
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:8080", "http://127.0.0.1:8080", "http://0.0.0.0:8080"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Audit Log Middleware ───────────────────────────────────────────────────────
app.add_middleware(AuditLogMiddleware)

# ── Security Headers Middleware ────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ── Routers ───────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(auth.router,    prefix=f"{API_PREFIX}/auth",    tags=["Authentication"])
app.include_router(batches.router, prefix=f"{API_PREFIX}/batches", tags=["Batches"])
app.include_router(results.router, prefix=f"{API_PREFIX}",         tags=["Results"])
app.include_router(reports.router,      prefix=f"{API_PREFIX}",              tags=["Reports"])
app.include_router(admin.router,        prefix=f"{API_PREFIX}/admin",          tags=["Admin"])
app.include_router(annotations.router,  prefix=f"{API_PREFIX}",              tags=["Annotations"])
app.include_router(training.router,     prefix=f"{API_PREFIX}",              tags=["Training"])
app.include_router(marking.router,      prefix=f"{API_PREFIX}",              tags=["Marking Configurations"])


# Static Files (FR-CORE-01)
# Mount frontend directories for static serving
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_path):
    for static_dir in ["pages", "js", "css", "images", "assets"]:
        dir_path = os.path.join(frontend_path, static_dir)
        if os.path.exists(dir_path):
            app.mount(f"/{static_dir}", StaticFiles(directory=dir_path), name=static_dir)


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status":"ok", "version": settings.APP_VERSION}


from fastapi.responses import FileResponse

@app.get("/")
async def read_index():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Frontend index not found"}
