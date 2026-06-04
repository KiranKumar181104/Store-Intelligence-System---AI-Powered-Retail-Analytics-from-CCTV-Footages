import logging
from typing import List

from sqlalchemy.orm import Session
from pydantic import ValidationError

from .database import EventRecord
from .models import EventMetadata, IngestError, IngestResponse, StoreEvent

logger = logging.getLogger("store_intelligence.ingestion")

VALID_EVENT_TYPES = {
    "ENTRY",
    "REENTRY",
    "EXIT",
    "BILLING",
    "FLOOR",
    "CHECKOUT",
}


def ingest_events(events: List[dict], db: Session) -> IngestResponse:
    accepted = 0
    duplicate = 0
    rejected = 0
    errors = []

    for payload in events:
        event_id = payload.get("event_id")
        try:
            store_event = StoreEvent.model_validate(payload)
            event_type = store_event.event_type.strip().upper()
            if event_type not in VALID_EVENT_TYPES:
                raise ValueError(f"unsupported event_type: {store_event.event_type}")
        except (ValidationError, ValueError) as exc:
            rejected += 1
            errors.append(IngestError(event_id=event_id, error=str(exc)))
            continue

        existing = db.query(EventRecord).filter_by(event_id=store_event.event_id).first()
        if existing:
            duplicate += 1
            continue

        record = EventRecord(
            event_id=store_event.event_id,
            store_id=store_event.store_id,
            camera_id=store_event.camera_id,
            visitor_id=store_event.visitor_id,
            event_type=store_event.event_type,
            timestamp=store_event.timestamp,
            zone_id=store_event.zone_id,
            dwell_ms=store_event.dwell_ms,
            confidence=store_event.confidence,
            is_staff=store_event.is_staff,
            metadata_json=store_event.metadata.model_dump() if store_event.metadata else {},
        )
        db.add(record)
        accepted += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to commit ingested events")
        rejected += accepted
        accepted = 0

    return IngestResponse(
        accepted=accepted,
        rejected=rejected,
        duplicate=duplicate,
        errors=errors,
    )
