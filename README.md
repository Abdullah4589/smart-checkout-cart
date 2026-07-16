# SmartCart — AI Checkout MVP

A camera-based self-checkout proof of concept, built as a pitch prototype for
Pakistani superstore chains (in the mould of **Imtiaz Super Market**, **Chase
Up**, and **Al-Fatah**). A webcam identifies products as customers place them
in view, looks up prices from the store catalog, tallies quantities, applies
GST, and produces an itemized bill — no barcode scanning required.

> **Demo branding:** the store name/branch shown in the app ("Al-Noor
> SuperMart") is a placeholder — swap it via env vars (see Config) for any
> client's actual name at demo time.

## Why this matters for a Pakistani superstore

- **Checkout queues are the #1 in-store friction point** at busy branches
  (weekend rush, Ramadan/Eid peak hours). Self-checkout lanes reduce staffing
  pressure on those peaks without a full POS overhaul.
- **Camera-based item recognition needs no barcode/RFID retrofit** — it layers
  on top of an existing catalog and price list, which lowers pilot cost
  versus RFID-tagging inventory.
- **Local payment rails are first-class**: Cash, Card, JazzCash, and EasyPaisa
  are all selectable at checkout, matching how Pakistani customers actually
  pay.
- **GST-compliant receipts** (17% standard rate, configurable) with invoice
  numbering — a real requirement for FBR-registered retailers, not just a
  demo nicety.

## Status
- ✅ **Phase 1 — Foundation** (catalog + UI shell)
- ✅ **Phase 2 — Detection** (YOLOv8 + live overlay)
- ✅ **Phase 3 — Matching + billing** (label→SKU, debounced cart, itemized bill)
- ✅ **Phase 4 — Polish** (multi-item scan, manual override UI, error/loading states)
- ✅ **Phase 5 — Retail readiness** (PKR pricing, GST, local payment methods,
  branded receipts/invoices, white-label store config)

## Multi-product scanning
Multiple products can be scanned at once — lay several items in view (or hold a
few up together) and each detected instance is counted, **including several of
the same product**. A higher count must persist for `COUNT_CONFIRM_POLLS`
(default 2) consecutive detection polls before it's added, so momentary
detection flicker can't inflate quantities. Counts never decrement mid-episode;
a product must leave view for `REDETECT_COOLDOWN_SECONDS` before it re-counts.

## Billing & payments
- Every cart shows **Subtotal → GST → Grand Total**, matching a standard
  Pakistani retail receipt breakdown.
- Checkout prompts for a **payment method** (Cash / Card / JazzCash /
  EasyPaisa) before finalizing the sale.
- The receipt carries a store name, branch, invoice number, date/time, item
  lines, GST, total, and payment method — laid out like a till slip.

## API
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | status + model load state |
| GET  | `/api/store` | store name/branch/currency/GST rate/payment methods |
| GET  | `/api/products` | full catalog |
| POST | `/api/detect` | frame → detections + updated cart (form: `frame`, `session`, `conf`) |
| GET  | `/api/cart?session=` | current cart summary (subtotal, GST, grand total) |
| POST | `/api/cart/reset?session=` | clear cart (new customer) |
| POST | `/api/cart/set-qty?session=` | body `{sku, qty}` — manual qty override |
| POST | `/api/cart/remove?session=&sku=` | remove a line item |
| POST | `/api/cart/checkout?session=&payment_method=` | finalize the sale, return an invoice receipt, clear the lane |

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

## Config (env vars)
| Var | Default | Purpose |
|-----|---------|---------|
| `STORE_NAME` | `Al-Noor SuperMart` | Store name shown in header + receipts (white-label per client) |
| `STORE_BRANCH` | `Clifton Block 5, Karachi` | Branch/address line on receipts |
| `STORE_NTN` | `1234567-8` | Tax registration number for receipts |
| `CURRENCY_SYMBOL` | `Rs. ` | Currency prefix used everywhere |
| `GST_RATE` | `0.17` | Sales tax rate applied to subtotal (0 disables it) |
| `CONFIDENCE_THRESHOLD` | `0.50` | Min detection confidence |
| `REDETECT_COOLDOWN_SECONDS` | `3.0` | Absence before an item re-counts |
| `COUNT_CONFIRM_POLLS` | `2` | Polls a higher count must persist before crediting |
| `MODEL_WEIGHTS` | `yolov8n.pt` | YOLO weights |

## Demo tips
- Click **Complete Sale**, choose a payment method (Cash/Card/JazzCash/
  EasyPaisa), and the receipt shows the full invoice — a good moment to point
  out GST compliance and invoice numbering to the client.
- The **Debug view** checkbox toggles raw detection confidence % on the
  overlay boxes — leave it off for a clean client-facing view, switch it on if
  you need to explain *why* something matched or didn't.
- If the camera, model, or backend hits an error mid-demo, a banner appears
  at the top of the page explaining what happened instead of failing silently.
- The catalog (see `backend/catalog_data.py`) is intentionally limited to
  pretrained YOLOv8/COCO classes that read as plausible checkout items
  (produce, bakery, deli, beverages), given Pakistani names and PKR pricing —
  steer the live demo toward those so an audience member testing an unrelated
  object doesn't see it billed as groceries.
- Before a client meeting, set `STORE_NAME`/`STORE_BRANCH` to their actual
  branding so the receipt and header read as *their* store, not a generic demo.

## Known limitations (by design for MVP)
- Heavily overlapping/stacked *identical* items may be under-counted (the
  detector can't separate them). Distinct items side by side count fine.
- No reliable discrimination between near-identical SKUs (e.g. flavors/brands
  of the same packaged good) — the catalog uses generic COCO object classes,
  not the client's actual packaging.
- No payment gateway integration — JazzCash/EasyPaisa/Card selection is
  recorded on the receipt but not processed; a pilot would wire these to real
  merchant APIs.
- No multi-camera / multi-lane support or staff authentication yet.
- Cart/session state and invoice numbering are in-memory and reset on server
  restart — fine for a demo lane, not for production.

## Roadmap (post-pilot)
1. **Fine-tune the detector** on the client's actual SKU photos (own-brand
   packaging, produce varieties) instead of generic COCO classes — this is
   the biggest accuracy lever for a real rollout.
2. **Persist carts/invoices** to a database and add daily sales reporting.
3. **Real payment gateway integration** (JazzCash/EasyPaisa merchant APIs,
   card terminal).
4. **Weight-sensor or loss-prevention cross-check** at the lane exit, since
   pure vision-based counting can be gamed by a determined customer.
5. **Multi-lane deployment** with a central admin dashboard (per-branch sales,
   catalog sync, staff overrides).

## Layout
```
backend/    FastAPI app, SQLite, catalog seed
frontend/   index.html, style.css, app.js
```
