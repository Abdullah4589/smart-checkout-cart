"""In-memory cart / session state with double-count protection.

Keyed by session id (one checkout lane = one session for the MVP). State is
intentionally in-memory: it should reset on restart, and a single lane doesn't
need persistence.

Multi-item counting + debounce model:
    Multiple products can be scanned at once — every instance YOLO detects in a
    frame is counted, including several of the *same* product side by side.

    Per product label we track how many instances have been "credited" to the
    cart during the current presence episode. A frame showing N instances credits
    (N - already_credited) new units. The count only ever grows within an episode
    (we never decrement on a low-flicker frame). A new higher count must persist
    for COUNT_CONFIRM_POLLS consecutive polls before it's credited, so a single
    spurious detection can't inflate the quantity.

    Once a label hasn't been seen for REDETECT_COOLDOWN_SECONDS the episode ends;
    the next detection starts a fresh episode and credits again. This handles both
    "lay all groceries down at once" and "hold each item up in turn" without
    re-adding forever.

Remaining limitation (consistent with the MVP's out-of-scope list): heavily
overlapping / stacked identical items may be under-counted because the detector
can't separate them — reliable stacked-object counting is out of scope.
"""

from __future__ import annotations

import threading
import time

import config
import database

_sessions: dict[str, dict] = {}
_lock = threading.Lock()
_invoice_seq = 1000  # in-memory; resets on restart (fine for a single-lane MVP)


def _new_session() -> dict:
    return {
        "items": {},      # sku -> {sku, name, unit_price, qty}
        # detection_label -> {last_seen, credited, cand, cand_hits}
        "presence": {},
    }


def _get(session_id: str) -> dict:
    sess = _sessions.get(session_id)
    if sess is None:
        sess = _new_session()
        _sessions[session_id] = sess
    return sess


def process_detections(session_id: str, detections: list[dict]) -> dict:
    """Update the cart from a frame's detections. Counts every instance of each
    product (multiple items at once), debounced per COUNT_CONFIRM_POLLS and the
    re-detect cooldown. Annotates each detection with its matched catalog product
    and how many units it added this frame."""
    now = time.time()
    cooldown = config.REDETECT_COOLDOWN_SECONDS
    confirm = max(1, config.COUNT_CONFIRM_POLLS)

    with _lock:
        sess = _get(session_id)
        presence = sess["presence"]
        items = sess["items"]

        # Count instances of each label in this frame.
        counts: dict[str, int] = {}
        for det in detections:
            counts[det["label"]] = counts.get(det["label"], 0) + 1

        annotated: list[dict] = [
            {
                **det,
                "sku": (p := database.get_product_by_label(det["label"]))
                and p["sku"],
                "product_name": p["name"] if p else None,
                "matched": p is not None,
                "added": 0,  # units this label added this frame (set below)
            }
            for det in detections
        ]

        added_per_label: dict[str, int] = {}
        for label, n in counts.items():
            entry = presence.get(label)
            fresh = entry is None or (now - entry["last_seen"]) > cooldown
            if fresh:
                entry = {"last_seen": now, "credited": 0, "cand": 0, "cand_hits": 0}
            entry["last_seen"] = now

            if n > entry["credited"]:
                # A higher count must persist for `confirm` polls before crediting.
                if n == entry["cand"]:
                    entry["cand_hits"] += 1
                else:
                    entry["cand"], entry["cand_hits"] = n, 1

                if entry["cand_hits"] >= confirm:
                    product = database.get_product_by_label(label)
                    if product is not None:  # unknown objects are shown, not billed
                        add = n - entry["credited"]
                        _add_units(items, product, add)
                        added_per_label[label] = add
                    entry["credited"] = n
                    entry["cand"], entry["cand_hits"] = 0, 0
            else:
                # stable or fewer instances (flicker) — hold count, clear candidate
                entry["cand"], entry["cand_hits"] = 0, 0

            presence[label] = entry

        # Record added units on the first matched detection of each label.
        for a in annotated:
            label = a["label"]
            if a["matched"] and added_per_label.get(label):
                a["added"] = added_per_label.pop(label)

        return {"cart": _summary(items), "detections": annotated}


def _add_units(items: dict[str, dict], product: dict, count: int) -> None:
    sku = product["sku"]
    if sku in items:
        items[sku]["qty"] += count
    else:
        items[sku] = {
            "sku": sku,
            "name": product["name"],
            "unit_price": product["price"],
            "qty": count,
        }


def _summary(items: dict[str, dict]) -> dict:
    lines = []
    subtotal = 0.0
    for it in items.values():
        line_total = round(it["unit_price"] * it["qty"], 2)
        subtotal += line_total
        lines.append({**it, "line_total": line_total})
    lines.sort(key=lambda x: x["name"])
    subtotal = round(subtotal, 2)
    gst = round(subtotal * config.GST_RATE, 2)
    return {
        "items": lines,
        "subtotal": subtotal,
        "gst_rate": config.GST_RATE,
        "gst_amount": gst,
        "grand_total": round(subtotal + gst, 2),
    }


def get_cart(session_id: str) -> dict:
    with _lock:
        return _summary(_get(session_id)["items"])


def reset(session_id: str) -> dict:
    with _lock:
        _sessions[session_id] = _new_session()
        return _summary(_sessions[session_id]["items"])


def checkout(session_id: str, payment_method: str = "Cash") -> dict:
    """Finalize the sale: snapshot the cart as a receipt, then clear the lane
    for the next customer (same as reset, but returns what was sold)."""
    global _invoice_seq
    with _lock:
        receipt = _summary(_get(session_id)["items"])
        receipt["completed_at"] = time.time()
        receipt["payment_method"] = payment_method
        receipt["invoice_no"] = f"INV-{_invoice_seq}"
        _invoice_seq += 1
        _sessions[session_id] = _new_session()
        return receipt


def set_qty(session_id: str, sku: str, qty: int) -> dict:
    """Manual override (Phase 4): set an item's quantity; qty<=0 removes it."""
    with _lock:
        items = _get(session_id)["items"]
        if qty <= 0:
            items.pop(sku, None)
        elif sku in items:
            items[sku]["qty"] = qty
        else:
            product = database.get_product_by_sku(sku)
            if product:
                items[sku] = {
                    "sku": sku,
                    "name": product["name"],
                    "unit_price": product["price"],
                    "qty": qty,
                }
        return _summary(items)


def remove_item(session_id: str, sku: str) -> dict:
    with _lock:
        _get(session_id)["items"].pop(sku, None)
        return _summary(_get(session_id)["items"])
