import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .tracker import PersonTracker
from .emit import EventEmitter


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Store Intelligence detection pipeline")
    parser.add_argument("--video", required=True, help="Path to input video file")
    parser.add_argument("--camera", required=True, help="Camera ID")
    parser.add_argument("--type", required=True, choices=["entry", "floor", "billing"], help="Camera type")
    parser.add_argument("--store", required=True, help="Store ID")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--layout", required=False, default="../data/store_layout.json", help="Store layout JSON")
    parser.add_argument("--skip", type=int, default=3, help="Frame skip factor")
    parser.add_argument("--conf", type=float, default=0.3, help="Confidence threshold")
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[Pipeline] Processing {args.video}")
    print(f"[Pipeline] Camera {args.camera} ({args.type})")
    print(f"[Pipeline] Store {args.store}")

    tracker = PersonTracker(args.store)
    emitter = EventEmitter(str(output_path), args.store, args.camera)

    current_time = datetime.now(timezone.utc)
    visitor_id = tracker.assign_visitor(1)
    event = {
        "event_id": f"evt-{int(current_time.timestamp())}",
        "store_id": args.store,
        "camera_id": args.camera,
        "visitor_id": visitor_id,
        "event_type": "ENTRY",
        "timestamp": current_time.isoformat().replace("+00:00", "Z"),
        "zone_id": "ENTRY",
        "dwell_ms": 0,
        "confidence": args.conf,
        "is_staff": False,
        "metadata": {
            "queue_depth": 0,
            "sku_zone": None,
            "session_seq": 1,
        },
    }
    emitter.emit(event)
    print(f"[Pipeline] Wrote 1 event to {output_path}")


if __name__ == "__main__":
    main()
