from datetime import datetime
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import EventRecord, POSTransaction
from .models import Anomaly, AnomalyResponse


def run_anomaly_detection(store_id: str, db: Session) -> AnomalyResponse:
    events = db.query(EventRecord).filter(EventRecord.store_id == store_id).all()
    if not events:
        return AnomalyResponse(anomalies=[])

    anomaly_list: List[Anomaly] = []
    billing_events = [e for e in events if e.zone_id == "BILLING" and not e.is_staff]
    unique_visitors = {e.visitor_id for e in events if not e.is_staff}

    if len(billing_events) > 20:
        anomaly_list.append(
            Anomaly(
                anomaly_type="high_queue_depth",
                severity="warning",
                description="Billing queue depth is higher than expected.",
                detected_at=datetime.utcnow(),
                details={"billing_events": str(len(billing_events))},
            )
        )

    dwell_times = [e.dwell_ms for e in events if e.dwell_ms and not e.is_staff]
    if dwell_times:
        avg_dwell = sum(dwell_times) / len(dwell_times) / 1000.0
        if avg_dwell < 20.0:
            anomaly_list.append(
                Anomaly(
                    anomaly_type="low_dwell_time",
                    severity="info",
                    description="Average dwell time across zones is low.",
                    detected_at=datetime.utcnow(),
                    details={"avg_dwell_seconds": f"{avg_dwell:.1f}"},
                )
            )

    purchase_count = db.query(func.count(POSTransaction.id)).filter(POSTransaction.store_id == store_id).scalar() or 0
    if unique_visitors and purchase_count / len(unique_visitors) < 0.05:
        anomaly_list.append(
            Anomaly(
                anomaly_type="low_conversion",
                severity="warning",
                description="Store conversion rate is below expected level.",
                detected_at=datetime.utcnow(),
                details={
                    "unique_visitors": str(len(unique_visitors)),
                    "purchases": str(purchase_count),
                },
            )
        )

    return AnomalyResponse(anomalies=anomaly_list)
