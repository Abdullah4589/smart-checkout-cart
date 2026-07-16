"""Smart Checkout MVP — FastAPI backend.

Serves the frontend and exposes the API. Phase 1 covers the catalog and the
UI shell; detection (Phase 2) and cart/billing (Phase 3) endpoints are added
incrementally.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import cart
import config
import database
import detector

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db(seed=True)
    yield


app = FastAPI(title="Smart Checkout MVP", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "confidence_threshold": config.CONFIDENCE_THRESHOLD,
        "model": detector.model_status(),
    }


@app.get("/api/store")
def store_info() -> dict:
    return {
        "name": config.STORE_NAME,
        "branch": config.STORE_BRANCH,
        "ntn": config.STORE_NTN,
        "currency_symbol": config.CURRENCY_SYMBOL,
        "gst_rate": config.GST_RATE,
        "payment_methods": config.PAYMENT_METHODS,
    }


@app.get("/api/products")
def get_products() -> dict:
    products = database.list_products()
    return {"count": len(products), "products": products}


@app.post("/api/detect")
async def detect(
    frame: UploadFile = File(...),
    session: str = Form("default"),
    conf: float | None = Form(None),
) -> dict:
    """Receive a camera frame: detect, match to catalog, update the cart.

    Returns detections annotated with matched SKU/product + `added` flag, plus
    the current cart summary (items with line totals and grand total).
    """
    image_bytes = await frame.read()
    detections = detector.detect(image_bytes, conf=conf)
    result = cart.process_detections(session, detections)
    status = detector.model_status()
    return {
        "model_loaded": status["loaded"],
        "model_error": status["error"],
        "detections": result["detections"],
        "cart": result["cart"],
    }


# --- Cart management ---

class QtyUpdate(BaseModel):
    sku: str
    qty: int


@app.get("/api/cart")
def get_cart(session: str = "default") -> dict:
    return cart.get_cart(session)


@app.post("/api/cart/reset")
def reset_cart(session: str = "default") -> dict:
    return cart.reset(session)


@app.post("/api/cart/checkout")
def checkout_cart(session: str = "default", payment_method: str = "Cash") -> dict:
    """Finalize the sale and return a receipt; clears the lane for the next customer."""
    if payment_method not in config.PAYMENT_METHODS:
        payment_method = "Cash"
    return cart.checkout(session, payment_method)


@app.post("/api/cart/set-qty")
def set_qty(update: QtyUpdate, session: str = "default") -> dict:
    return cart.set_qty(session, update.sku, update.qty)


@app.post("/api/cart/remove")
def remove_item(sku: str, session: str = "default") -> dict:
    return cart.remove_item(session, sku)


# --- Frontend (served last so /api/* takes precedence) ---

@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")
