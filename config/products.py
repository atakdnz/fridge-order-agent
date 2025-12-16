"""
Test products for fridge order automation.
Replace with actual detection results in production.
"""

TEST_PRODUCTS = [
    {"name": "Süt", "quantity": 1, "category": "dairy"},
    {"name": "Yumurta", "quantity": 1, "category": "dairy"},
    {"name": "Ekmek", "quantity": 1, "category": "bakery"},
    {"name": "Su", "quantity": 2, "category": "beverages"},
]


def get_test_products() -> list[dict]:
    """Return the list of test products."""
    return TEST_PRODUCTS
