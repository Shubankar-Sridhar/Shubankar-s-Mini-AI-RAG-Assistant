import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, connection, health, sessions, upload
from app.config import get_settings
from app.core.cache import get_l2
from app.logging_config import setup_logging, get_logger, correlation_id

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", extra={"env": settings.app_env})
    from app.core.cache import get_l2
    from app.core.session_store import get_session_store
    await get_l2().connect()
    await get_session_store().connect()
    yield
    logger.info("application_shutdown")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id.set(cid)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


app.include_router(health.router)
app.include_router(connection.router)
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.get("/")
async def root():
    return {"app": settings.app_name, "status": "running"}