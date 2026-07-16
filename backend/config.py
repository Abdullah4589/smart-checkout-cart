"""Runtime configuration. Values can be overridden with environment variables
so they're easy to tune during testing (e.g. the detection threshold)."""

import os

# Minimum detection confidence to accept a detection. Tune during testing.
CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.50"))

# How long (seconds) the same product must be absent before a re-detection
# counts as a new physical item. Used by the cart debounce logic (Phase 3).
REDETECT_COOLDOWN_SECONDS: float = float(os.getenv("REDETECT_COOLDOWN_SECONDS", "3.0"))

# How many consecutive detection polls a given instance-count must persist
# before it's credited to the cart. Guards multi-item counting against
# single-frame detection flicker / false spikes. 1 = credit immediately.
COUNT_CONFIRM_POLLS: int = int(os.getenv("COUNT_CONFIRM_POLLS", "2"))

# YOLO model weights (Phase 2). 'yolov8n.pt' is the smallest (~6 MB).
MODEL_WEIGHTS: str = os.getenv("MODEL_WEIGHTS", "yolov8n.pt")
