"""Seed data for the demo product catalog.

Placeholder products only — swap in real products, prices, and images later.
Products are intentionally visually distinct (see MVP notes): fine-grained
discrimination between near-identical SKUs is a known limitation, out of scope.

`detection_label` maps a detector's output class name to this SKU, and must be
a real pretrained YOLOv8/COCO class name (the model only ever emits those 80
labels) — otherwise the product could never be detected. The catalog is
deliberately limited to COCO classes that read as plausible checkout items
(produce, bakery, deli, beverages); classes like "scissors" or "bowl" are
dropped even though YOLO recognizes them, since a client testing the demo with
a stray office object shouldn't see it get rung up as groceries.
"""

# (sku, name, price, category, detection_label, image_path)
SEED_PRODUCTS = [
    ("SKU-1001", "Red Apple",     0.79,  "Produce",   "apple",    None),
    ("SKU-1002", "Banana",        0.35,  "Produce",   "banana",   None),
    ("SKU-1003", "Orange",        0.89,  "Produce",   "orange",   None),
    ("SKU-1004", "Broccoli",      1.49,  "Produce",   "broccoli", None),
    ("SKU-1005", "Carrot",        0.59,  "Produce",   "carrot",   None),
    ("SKU-1006", "Water Bottle",  1.19,  "Beverages", "bottle",   None),
    ("SKU-1007", "Coffee Cup",    3.25,  "Beverages", "cup",      None),
    ("SKU-1008", "Sandwich",      3.79,  "Deli",      "sandwich", None),
    ("SKU-1009", "Pizza Slice",   4.50,  "Deli",      "pizza",    None),
    ("SKU-1010", "Donut",         1.25,  "Bakery",    "donut",    None),
    ("SKU-1011", "Cake Slice",    3.99,  "Bakery",    "cake",     None),
]
