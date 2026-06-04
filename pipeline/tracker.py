class PersonTracker:
    def __init__(self, store_id: str):
        self.store_id = store_id
        self._next_id = 1

    def assign_visitor(self, track_id: int) -> str:
        return f"VIS_{track_id:06d}"

    def get_visitor_id(self, track_id: int) -> str:
        return f"VIS_{track_id:06d}"
