# Smart Checkout MVP

Camera-based supermarket checkout proof of concept. A webcam identifies
products from a small fixed catalog, looks up prices, counts quantities, and
builds an itemized bill.

## Status
- ✅ **Phase 1 — Foundation** (catalog + UI shell)
- ✅ **Phase 2 — Detection** (YOLOv8 + live overlay)
- ✅ **Phase 3 — Matching + billing** (label→SKU, debounced cart, itemized bill)
- ✅ **Phase 4 — Polish** (multi-item scan, manual override UI, error/loading states)

## Multi-product scanning
Multiple products can be scanned at once — lay several items in view (or hold a
few up together) and each detected instance is counted, **including several of
the same product**. A higher count must persist for `COUNT_CONFIRM_POLLS`
(default 2) consecutive detection polls before it's added, so momentary
detection flicker can't inflate quantities. Counts never decrement mid-episode;
a product must leave view for `REDETECT_COOLDOWN_SECONDS` before it re-counts.

## API
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | status + model load state |
| GET  | `/api/products` | full catalog |
| POST | `/api/detect` | frame → detections + updated cart (form: `frame`, `session`, `conf`) |
| GET  | `/api/cart?session=` | current cart summary |
| POST | `/api/cart/reset?session=` | clear cart (new customer) |
| POST | `/api/cart/set-qty?session=` | body `{sku, qty}` — manual qty override |
| POST | `/api/cart/remove?session=&sku=` | remove a line item |
| POST | `/api/cart/checkout?session=` | finalize the sale, return a receipt, clear the lane |

## Stack
- **Backend:** Python + FastAPI, SQLite catalog (`backend/checkout.db`, auto-created & seeded).
- **Frontend:** plain HTML/CSS/JS served by FastAPI (single origin, no CORS).

## Run

**Local development** (auto-reloads on code changes):
```powershell
python -m pip install -r requirements.txt
cd backend
python -m uvicorn main:app --reload --port 8000
```

**Client demo / production-style run** (no reload, bound for LAN access):
```powershell
python -m pip install -r requirements.txt
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```
Use the `--host 0.0.0.0` form if you're demoing from a laptop and want other
devices on the same network to reach it (e.g. `http://<your-ip>:8000`); note
that browsers only grant camera access over `localhost` or HTTPS, so a demo
viewed from another device will need a proper TLS setup — for a single-machine
demo, plain `http://localhost:8000` is simplest and needs no extra setup.

Open the app and click **Start Camera** (grant the browser camera permission
when prompted).

## Config (env vars, for tuning during testing)
| Var | Default | Purpose |
|-----|---------|---------|
| `CONFIDENCE_THRESHOLD` | `0.50` | Min detection confidence |
| `REDETECT_COOLDOWN_SECONDS` | `3.0` | Absence before an item re-counts |
| `COUNT_CONFIRM_POLLS` | `2` | Polls a higher count must persist before crediting |
| `MODEL_WEIGHTS` | `yolov8n.pt` | YOLO weights |

## Demo tips
- Click **Complete Sale** to finalize the cart into a receipt and reset the
  lane for the next customer (an alternative to **New Customer**, which just
  clears without showing a receipt).
- The **Debug view** checkbox toggles raw detection confidence % on the
  overlay boxes — leave it off for a clean client-facing view, switch it on if
  you need to explain *why* something matched or didn't.
- If the camera, model, or backend hits an error mid-demo, a banner appears
  at the top of the page explaining what happened instead of failing silently.
- The catalog (see `backend/catalog_data.py`) is intentionally limited to
  pretrained YOLOv8/COCO classes that read as plausible checkout items
  (produce, bakery, deli, beverages) — steer the live demo toward those so an
  audience member testing an unrelated object doesn't see it billed as
  groceries.

## Known limitations (by design for MVP)
- Heavily overlapping/stacked *identical* items may be under-counted (the
  detector can't separate them). Distinct items side by side count fine.
- No reliable discrimination between near-identical SKUs (e.g. flavors).
- No payment/POS integration, multi-camera, or auth.
- Catalog uses pretrained COCO classes as stand-ins; fine-tuning on real
  product photos is future work.

## Layout
```
backend/    FastAPI app, SQLite, catalog seed
frontend/   index.html, style.css, app.js
```
