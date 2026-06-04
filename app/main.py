import csv
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from .database import SessionLocal, POSTransaction, create_tables, get_db
from .models import (
    AnomalyResponse,
    FunnelResponse,
    HealthResponse,
    HeatmapResponse,
    IngestRequest,
    IngestResponse,
    MetricsResponse,
)
from .anomalies import run_anomaly_detection
from .health import get_health
from .ingestion import ingest_events
from .metrics import compute_funnel, compute_heatmap, compute_metrics

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger("store_intelligence")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Store Intelligence API")
    create_tables()
    load_pos_data()
    logger.info("Startup complete")
    yield
    logger.info("Shutting down")


def load_pos_data():
    pos_path = os.environ.get("POS_DATA_PATH", "./data/pos_transactions.csv")
    if not Path(pos_path).exists():
        logger.warning(f"POS data not found at {pos_path} — skipping")
        return

    db = SessionLocal()
    try:
        count = 0
        with open(pos_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts_str = row["timestamp"].replace("Z", "+00:00")
                ts = datetime.fromisoformat(ts_str).replace(tzinfo=None)
                existing = db.query(POSTransaction).filter_by(
                    transaction_id=row["transaction_id"]
                ).first()
                if not existing:
                    db.add(POSTransaction(
                        transaction_id=row["transaction_id"],
                        store_id=row["store_id"],
                        timestamp=ts,
                        basket_value=float(row["basket_value_inr"]),
                    ))
                    count += 1
        db.commit()
        logger.info(f"Loaded {count} POS transactions")
    except Exception as e:
        logger.error(f"Failed to load POS data: {e}")
    finally:
        db.close()


app = FastAPI(
    title="Store Intelligence API",
    description="Purplle Tech Challenge 2026 — Retail analytics from CCTV",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    start = time.time()
    store_id = request.path_params.get("store_id", "-")

    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(json.dumps({
            "trace_id": trace_id,
            "store_id": store_id,
            "endpoint": str(request.url.path),
            "latency_ms": round((time.time() - start) * 1000, 1),
            "status_code": 500,
            "error": str(e),
        }))
        raise

    latency = round((time.time() - start) * 1000, 1)
    logger.info(json.dumps({
        "trace_id": trace_id,
        "store_id": store_id,
        "endpoint": str(request.url.path),
        "method": request.method,
        "latency_ms": latency,
        "status_code": response.status_code,
    }))
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "error": "service_unavailable",
            "message": "An internal error occurred. Please try again.",
            "trace_id": str(uuid.uuid4())[:8],
        },
    )


@app.post("/events/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest, db: Session = Depends(get_db)):
    if len(payload.events) > 500:
        raise HTTPException(
            status_code=422,
            detail=f"Batch size {len(payload.events)} exceeds limit of 500",
        )

    logger.info(f"[Ingest] Received batch of {len(payload.events)} events")
    result = ingest_events([event.model_dump(mode="json") for event in payload.events], db)
    logger.info(json.dumps({
        "endpoint": "/events/ingest",
        "event_count": len(payload.events),
        "accepted": result.accepted,
        "duplicate": result.duplicate,
        "rejected": result.rejected,
    }))
    return result


@app.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
def metrics(store_id: str, db: Session = Depends(get_db)):
    return compute_metrics(store_id, db)


@app.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
def funnel(store_id: str, db: Session = Depends(get_db)):
    return compute_funnel(store_id, db)


@app.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
def heatmap(store_id: str, db: Session = Depends(get_db)):
    return compute_heatmap(store_id, db)


@app.get("/stores/{store_id}/anomalies", response_model=AnomalyResponse)
def anomalies(store_id: str, db: Session = Depends(get_db)):
    return run_anomaly_detection(store_id, db)


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    return get_health(None, db)
