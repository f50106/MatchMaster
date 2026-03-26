"""MatchMaster — AI Recruitment Screening Tool."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import calibration as calibration_api
from app.api.v1 import config as config_api
from app.api.v1 import evaluation as eval_api
from app.api.v1 import jd as jd_api
from app.api.v1 import stats as stats_api
from app.config import settings
from app.infrastructure.cache.redis_cache import redis_cache

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MatchMaster (env=%s)", settings.app_env)
    await redis_cache.connect()
    yield
    # Shutdown
    await redis_cache.disconnect()
    logger.info("MatchMaster shutdown complete")


app = FastAPI(
    title="MatchMaster",
    description="AI Recruitment Screening Tool — Hybrid Scoring Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(jd_api.router, prefix="/api/v1")
app.include_router(eval_api.router, prefix="/api/v1")
app.include_router(config_api.router, prefix="/api/v1")
app.include_router(stats_api.router, prefix="/api/v1")
app.include_router(calibration_api.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
