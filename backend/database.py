"""SQLite persistence for the product catalog.

Cart/session state is kept in-memory (see cart.py) for the MVP — simpler to
reason about for a single checkout lane. The catalog is the only thing that
needs to survive restarts, so it lives here.
"""

import sqlite3
from pathlib import Path

from catalog_data import SEED_PRODUCTS

DB_PATH = Path(__file__).parent / "checkout.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(seed: bool = True) -> None:
    """Create the schema and (optionally) seed it if empty."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                sku             TEXT    UNIQUE NOT NULL,
                name            TEXT    NOT NULL,
                price           REAL    NOT NULL,
                category        TEXT    NOT NULL,
                detection_label TEXT,
                image_path      TEXT
            )
            """
        )
        conn.commit()

        if seed:
            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count == 0:
                conn.executemany(
                    """
                    INSERT INTO products
                        (sku, name, price, category, detection_label, image_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    SEED_PRODUCTS,
                )
                conn.commit()
    finally:
        conn.close()


def list_products() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY category, name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_product_by_label(label: str) -> dict | None:
    """Look up a catalog product by its detection label (case-insensitive)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE LOWER(detection_label) = LOWER(?)",
            (label,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_detection_terms() -> list[str]:
    """Distinct detection_label terms across the catalog, in catalog order.

    Feeds the open-vocabulary detector's class list (see detector.py) — the
    detector's vocabulary is just "whatever terms the catalog currently has",
    so adding a product row makes it detectable with no retraining."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT detection_label FROM products "
            "WHERE detection_label IS NOT NULL AND detection_label != '' "
            "ORDER BY id"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def get_product_by_sku(sku: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM products WHERE sku = ?", (sku,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
