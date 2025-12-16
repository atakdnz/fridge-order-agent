# SiparisAgent 🛒

Automated fridge order agent that adds products to **Getir.com** basket.

## Quick Start

```bash
# Setup
cd SiparisAgent
source venv/bin/activate

# Login to Getir (one-time)
python main.py login

# Add test products to cart
python main.py order
```

## Commands

| Command | Description |
|---------|-------------|
| `python main.py login` | Login to Getir (saves session) |
| `python main.py order` | Add missing products to cart |
| `python main.py cart` | Show cart info |
| `python main.py test` | Dry run - show test products |

## Test Products

- Süt (Milk) x1
- Yumurta (Eggs) x1
- Ekmek (Bread) x1
- Su (Water) x2

## Project Structure

```
SiparisAgent/
├── main.py              # CLI entry point
├── browser/
│   └── getir_client.py  # Playwright automation
├── config/
│   ├── products.py      # Test product list
│   └── settings.py      # App configuration
└── detection/
    └── detector.py      # Detection stub (future ML)
```

## Future: Object Detection

Replace `detection/detector.py` with actual fridge detection model:

```python
def get_missing_products() -> list[dict]:
    # Load model, capture image, run inference
    # Return list of missing items
    pass
```
