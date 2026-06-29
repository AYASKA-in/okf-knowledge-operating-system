from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import init_db
from app.api import ingest, knowledge, chat, export, admin, auth, search, edges


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Enterprise Knowledge Operating System (EKOS)",
    description="Open Knowledge Format (OKF) v0.1 – Deterministic Knowledge Infrastructure",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(knowledge.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(export.router)
app.include_router(admin.router)
app.include_router(edges.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "okf_spec": "v0.1"}


@app.get("/")
async def root():
    return {
        "service": "Enterprise Knowledge Operating System",
        "specification": "Open Knowledge Format (OKF) v0.1",
        "docs": "/docs",
    }
