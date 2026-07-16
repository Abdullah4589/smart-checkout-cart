"""Seed data for the demo product catalog.

Prices are illustrative PKR shelf prices (Lahore/Karachi superstore range as of
2026), for pitching to a Pakistani retail client (Imtiaz Super Market, Chase
Up, Al-Fatah-style store). Swap in the client's real POS price list before a
production pilot. Products are intentionally visually distinct (see MVP
notes): fine-grained discrimination between near-identical SKUs (e.g. flavors
or brands of the same item) is a known limitation, out of scope for the MVP.

`detection_label` maps a detector's output class name to this SKU, and must be
a real pretrained YOLOv8/COCO class name (the model only ever emits those 80
labels) — otherwise the product could never be detected. The catalog is
deliberately limited to COCO classes that read as plausible checkout items
(produce, bakery, deli, beverages); classes like "scissors" or "bowl" are
dropped even though YOLO recognizes them, since a client testing the demo with
a stray office object shouldn't see it get rung up as groceries.

A production rollout would fine-tune the detector on the client's actual
packaged SKUs (own-brand milk, snack packets, etc.) rather than relying on
generic COCO classes — see README "Roadmap".
"""

# (sku, name, price, category, detection_label, image_path)
SEED_PRODUCTS = [
    ("SKU-1001", "Seb (Apple)",         80,   "Produce",   "apple",    None),
    ("SKU-1002", "Kela (Banana)",       30,   "Produce",   "banana",   None),
    ("SKU-1003", "Malta (Orange)",      60,   "Produce",   "orange",   None),
    ("SKU-1004", "Broccoli",            120,  "Produce",   "broccoli", None),
    ("SKU-1005", "Gajar (Carrot)",      40,   "Produce",   "carrot",   None),
    ("SKU-1006", "Mineral Water 1.5L",  80,   "Beverages", "bottle",   None),
    ("SKU-1007", "Coffee Cup (Cafe)",   250,  "Beverages", "cup",      None),
    ("SKU-1008", "Chicken Sandwich",    280,  "Deli",      "sandwich", None),
    ("SKU-1009", "Pizza Slice",         320,  "Deli",      "pizza",    None),
    ("SKU-1010", "Donut",               90,   "Bakery",    "donut",    None),
    ("SKU-1011", "Cake Slice",          250,  "Bakery",    "cake",     None),
]
