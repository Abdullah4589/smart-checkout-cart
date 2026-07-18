"""YOLOv8 object detection wrapper.

Loads a pretrained YOLOv8 model lazily (on first use) so the server can start
even before weights are downloaded, and so import stays cheap. Detections are
returned as plain dicts with pixel-space boxes relative to the received frame.

Uses the stock COCO-pretrained weights (80 fixed classes) rather than an
open-vocabulary model — YOLO-World + its CLIP text encoder needed too much
RAM for this deployment's resources and OOM-crashed the container. The
catalog is limited to COCO classes as a result (see catalog_data.py); a
production rollout would fine-tune on the client's real SKUs instead.
"""

from __future__ import annotations

import io
import threading

import config

_model = None
_model_lock = threading.Lock()
_load_error: str | None = None


def load_model():
    """Load the YOLO model once (thread-safe). Returns the model or None."""
    global _model, _load_error
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        try:
            from ultralytics import YOLO  # imported lazily (heavy)

            _model = YOLO(config.MODEL_WEIGHTS)
            _load_error = None
        except Exception as exc:  # noqa: BLE001 - surface any load failure
            _load_error = str(exc)
            _model = None
    return _model


def model_status() -> dict:
    return {
        "loaded": _model is not None,
        "weights": config.MODEL_WEIGHTS,
        "error": _load_error,
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
