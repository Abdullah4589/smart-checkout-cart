"""YOLO-World open-vocabulary object detection wrapper.

Loads a pretrained YOLO-World model lazily (on first use) so the server can
start even before weights are downloaded, and so import stays cheap.

Unlike a plain YOLOv8/COCO model — which can only ever emit its 80 fixed
training classes — YOLO-World detects an arbitrary text vocabulary supplied
at inference time via `set_classes()`. That vocabulary is simply the current
catalog's `detection_label` terms (see database.list_detection_terms()), so
the product list is no longer hardcoded to COCO classes: adding a new
product row (name + price + a short descriptive term) makes it detectable
immediately, with no retraining and no code change.

Detections are returned as plain dicts with pixel-space boxes relative to
the received frame.
"""

from __future__ import annotations

import io
import threading

import config
import database

_model = None
_model_lock = threading.Lock()
_load_error: str | None = None
_loaded_classes: list[str] = []


def load_model():
    """Load the YOLO-World model once (thread-safe), then sync its
    vocabulary to the current catalog. Returns the model or None."""
    global _model, _load_error
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from ultralytics import YOLOWorld  # imported lazily (heavy)

                    _model = YOLOWorld(config.MODEL_WEIGHTS)
                    _load_error = None
                except Exception as exc:  # noqa: BLE001 - surface any load failure
                    _load_error = str(exc)
                    _model = None
    if _model is not None:
        _refresh_classes()
    return _model


def _refresh_classes() -> None:
    """Point the model's open vocabulary at the current catalog's detection
    terms. Cheap to call on every request — skipped unless the catalog's
    terms actually changed since the last call."""
    global _loaded_classes
    terms = database.list_detection_terms()
    if terms and terms != _loaded_classes:
        _model.set_classes(terms)
        _loaded_classes = terms


def model_status() -> dict:
    return {
        "loaded": _model is not None,
        "weights": config.MODEL_WEIGHTS,
        "error": _load_error,
        "vocabulary": _loaded_classes,
    }


def detect(image_bytes: bytes, conf: float | None = None) -> list[dict]:
    """Run detection on raw image bytes.

    Returns a list of detections:
        {label, confidence, box: [x1, y1, x2, y2]}  (pixel coords)
    """
    model = load_model()
    if model is None:
        return []

    threshold = config.CONFIDENCE_THRESHOLD if conf is None else conf

    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    results = model.predict(img, conf=threshold, verbose=False)

    detections: list[dict] = []
    for result in results:
        names = result.names
        for box in result.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
            detections.append(
                {
                    "label": names[cls_id],
                    "confidence": round(confidence, 3),
                    "box": [round(x1), round(y1), round(x2), round(y2)],
                }
            )
    return detections
