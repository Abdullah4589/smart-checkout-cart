"""Seed data for the demo product catalog.

Prices are illustrative PKR shelf prices (Lahore/Karachi superstore range as of
2026), for pitching to a Pakistani retail client (Imtiaz Super Market, Chase
Up, Al-Fatah-style store). Swap in the client's real POS price list before a
production pilot. Products are intentionally visually distinct (see MVP
notes): fine-grained discrimination between near-identical SKUs (e.g. flavors
or brands of the same item) is a known limitation, out of scope for the MVP.

`detection_label` is a free-text term shown to the open-vocabulary YOLO-World
detector (see detector.py) — it is NOT restricted to a fixed class list
anymore. Adding a new product row with a short, visually-descriptive term
("bag of potato chips", "milk carton") makes it detectable immediately, with
no retraining. Prefer plain, unambiguous English nouns/phrases — that's what
the detector was trained to ground — even though the display `name` can be
in Urdu/Roman Urdu for the receipt.

A production rollout would still benefit from fine-tuning on the client's
exact packaged SKUs for higher accuracy (own-brand milk, snack packets,
etc.), but it is no longer required just to go beyond COCO's 80 classes —
see README "Roadmap".
"""

# (sku, name, price, category, detection_label, image_path)
SEED_PRODUCTS = [
    ("SKU-1001", "Seb (Apple)",         80,   "Produce",   "apple",                 None),
    ("SKU-1002", "Kela (Banana)",       30,   "Produce",   "banana",                None),
    ("SKU-1003", "Malta (Orange)",      60,   "Produce",   "orange",                None),
    ("SKU-1004", "Broccoli",            120,  "Produce",   "broccoli",              None),
    ("SKU-1005", "Gajar (Carrot)",      40,   "Produce",   "carrot",                None),
    ("SKU-1016", "Aam (Mango)",         70,   "Produce",   "mango",                 None),
    ("SKU-1006", "Mineral Water 1.5L",  80,   "Beverages", "plastic water bottle",  None),
    ("SKU-1007", "Coffee Cup (Cafe)",   250,  "Beverages", "paper coffee cup",      None),
    ("SKU-1008", "Chicken Sandwich",    280,  "Deli",      "sandwich",              None),
    ("SKU-1009", "Pizza Slice",         320,  "Deli",      "pizza slice",           None),
    ("SKU-1010", "Donut",               90,   "Bakery",    "donut",                 None),
    ("SKU-1011", "Cake Slice",          250,  "Bakery",    "cake slice",            None),
    ("SKU-1012", "Lays Chips Packet",   100,  "Snacks",    "bag of potato chips",   None),
    ("SKU-1013", "Milk Pack 1L",        190,  "Dairy",     "milk carton",           None),
    ("SKU-1014", "Biscuit Pack",        60,   "Bakery",    "biscuit packet",        None),
    ("SKU-1015", "Instant Noodles",     45,   "Snacks",    "instant noodles packet", None),
]
