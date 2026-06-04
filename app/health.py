from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import EventRecord, POSTransaction
from .models import HealthResponse, StoreHealth


def get_health(store_id: Optional[str], db: Session) -> HealthResponse:
    store_ids: List[str] = []
    if store_id:
        store_ids = [store_id]
    else:
        rows = db.query(EventRecord.store_id).distinct().all()
        store_ids = [row[0] for row in rows if row[0]]

    stores: List[StoreHealth] = []
    for sid in store_ids:
        event_count = db.query(func.count(EventRecord.id)).filter(EventRecord.store_id == sid).scalar() or 0
        transaction_count = db.query(func.count(POSTransaction.id)).filter(POSTransaction.store_id == sid).scalar() or 0
        last_event = db.query(EventRecord.timestamp).filter(EventRecord.store_id == sid).order_by(EventRecord.timestamp.desc()).first()
        stores.append(
            StoreHealth(
                store_id=sid,
                event_count=event_count,
                transaction_count=transaction_count,
                last_event_at=last_event[0] if last_event else None,
            )
        )

    status = "ok" if stores else "degraded"
    return HealthResponse(
        status=status,
        checked_at=datetime.utcnow(),
        stores=stores,
    )
