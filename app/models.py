from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: Optional[int] = None


class StoreEvent(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_staff: bool = False
    metadata: Optional[EventMetadata] = None

    model_config = {
        "extra": "forbid",
    }


class IngestError(BaseModel):
    event_id: Optional[str] = None
    error: str


class IngestRequest(BaseModel):
    events: List[StoreEvent]

    model_config = {
        "extra": "forbid",
    }


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    duplicate: int
    errors: List[IngestError]


class ZoneDwell(BaseModel):
    zone_id: str
    avg_dwell_seconds: float


class MetricsResponse(BaseModel):
    unique_visitors: int
    conversion_rate: float
    queue_depth: int
    abandonment_rate: float
    avg_dwell_per_zone: List[ZoneDwell]


class FunnelStage(BaseModel):
    stage: str
    count: int
    drop_off_pct: float


class FunnelResponse(BaseModel):
    stages: List[FunnelStage]


class HeatmapZone(BaseModel):
    zone_id: str
    avg_dwell_seconds: float
    normalised_score: float


class HeatmapResponse(BaseModel):
    zones: List[HeatmapZone]
    data_confidence: str


class Anomaly(BaseModel):
    anomaly_type: str
    severity: str
    description: str
    detected_at: datetime
    details: Optional[Dict[str, str]] = None


class AnomalyResponse(BaseModel):
    anomalies: List[Anomaly]


class StoreHealth(BaseModel):
    store_id: str
    event_count: int
    transaction_count: int
    last_event_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str
    checked_at: datetime
    stores: List[StoreHealth]
