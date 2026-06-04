import json
from pathlib import Path


class EventEmitter:
    def __init__(self, output_path: str, store_id: str, camera_id: str):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_id = store_id
        self.camera_id = camera_id

    def emit(self, event: dict) -> None:
        with open(self.output_path, "a", encoding="utf-8") as file:
            file.write(json.dumps(event) + "\n")


class EventType:
    ENTRY = "ENTRY"
    REENTRY = "REENTRY"
    BILLING = "BILLING"
    EXIT = "EXIT"
    FLOOR = "FLOOR"
