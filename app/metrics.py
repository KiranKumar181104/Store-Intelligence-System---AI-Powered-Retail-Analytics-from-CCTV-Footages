from typing import List, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import EventRecord, POSTransaction
from .models import (
    FunnelResponse,
    FunnelStage,
    HeatmapResponse,
    HeatmapZone,
    MetricsResponse,
    ZoneDwell,
)


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_metrics(store_id: str, db: Session) -> MetricsResponse:
    events = db.query(EventRecord).filter(EventRecord.store_id == store_id).all()
    unique_visitors = len({e.visitor_id for e in events if not e.is_staff})

    purchases = db.query(func.count(POSTransaction.id)).filter(POSTransaction.store_id == store_id).scalar() or 0
    conversion_rate = _safe_divide(purchases, unique_visitors)

    queue_depth = len({
        e.visitor_id
        for e in events
        if e.zone_id == "BILLING" and not e.is_staff
    })

    abandonment_visitors = {
        e.visitor_id
        for e in events
        if e.event_type.upper() == "EXIT" and e.zone_id != "BILLING" and not e.is_staff
    }
    abandonment_rate = _safe_divide(len(abandonment_visitors), unique_visitors)

    zone_stats: Dict[str, Dict[str, float]] = {}
    for event in events:
        if not event.zone_id or event.is_staff:
            continue
        stats = zone_stats.setdefault(event.zone_id, {"count": 0, "dwell": 0.0})
        stats["count"] += 1
        stats["dwell"] += float(event.dwell_ms or 0)

    avg_dwell_per_zone = [
        ZoneDwell(
            zone_id=zone_id,
            avg_dwell_seconds=_safe_divide(stats["dwell"], stats["count"]) / 1000.0,
        )
        for zone_id, stats in sorted(zone_stats.items())
    ]

    return MetricsResponse(
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate,
        avg_dwell_per_zone=avg_dwell_per_zone,
    )


def compute_funnel(store_id: str, db: Session) -> FunnelResponse:
    events = db.query(EventRecord).filter(EventRecord.store_id == store_id).all()

    entry_visitors = {
        e.visitor_id
        for e in events
        if e.event_type.upper() in ("ENTRY", "REENTRY") and not e.is_staff
    }
    browse_visitors = {
        e.visitor_id
        for e in events
        if e.zone_id and e.zone_id not in ("ENTRY", "BILLING") and not e.is_staff
    }
    billing_visitors = {
        e.visitor_id
        for e in events
        if e.zone_id == "BILLING" and not e.is_staff
    }

    purchase_count = len(billing_visitors)

    stages = [
        FunnelStage(stage="Entry", count=len(entry_visitors), drop_off_pct=0.0),
        FunnelStage(
            stage="Browse",
            count=len(browse_visitors),
            drop_off_pct=_safe_divide(len(entry_visitors) - len(browse_visitors), max(len(entry_visitors), 1)) * 100.0,
        ),
        FunnelStage(
            stage="Billing",
            count=len(billing_visitors),
            drop_off_pct=_safe_divide(len(browse_visitors) - len(billing_visitors), max(len(browse_visitors), 1)) * 100.0,
        ),
        FunnelStage(
            stage="Purchase",
            count=purchase_count,
            drop_off_pct=_safe_divide(len(billing_visitors) - purchase_count, max(len(billing_visitors), 1)) * 100.0,
        ),
    ]

    return FunnelResponse(stages=stages)


def compute_heatmap(store_id: str, db: Session) -> HeatmapResponse:
    events = db.query(EventRecord).filter(EventRecord.store_id == store_id).all()

    zone_stats: Dict[str, Dict[str, float]] = {}
    for event in events:
        if not event.zone_id or event.is_staff:
            continue
        stats = zone_stats.setdefault(event.zone_id, {"count": 0, "dwell": 0.0})
        stats["count"] += 1
        stats["dwell"] += float(event.dwell_ms or 0)

    zone_models = []
    if zone_stats:
        max_avg = max((stats["dwell"] / stats["count"]) for stats in zone_stats.values())
    else:
        max_avg = 0.0

    for zone_id, stats in sorted(zone_stats.items()):
        avg_seconds = _safe_divide(stats["dwell"], stats["count"]) / 1000.0
        normalised_score = _safe_divide(avg_seconds, max_avg / 1000.0) * 100.0 if max_avg else 0.0
        zone_models.append(
            HeatmapZone(
                zone_id=zone_id,
                avg_dwell_seconds=avg_seconds,
                normalised_score=min(max(normalised_score, 0.0), 100.0),
            )
        )

    confidence = "HIGH" if len(events) >= 20 else "LOW"
    return HeatmapResponse(zones=zone_models, data_confidence=confidence)
