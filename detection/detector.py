"""
Fridge detection stub.
Replace this with actual object detection model integration.
"""

from config.products import get_test_products


def get_missing_products() -> list[dict]:
    """
    Detect missing products in the fridge.
    
    TODO: Integrate with actual object detection model
    - Load trained model
    - Capture fridge image
    - Run inference
    - Compare with expected inventory
    - Return list of missing items
    
    For now, returns test products for development.
    """
    print("📷 [STUB] Detecting missing products...")
    print("   (Using test products - replace with actual detection)")
    
    # Return test products as "missing" items
    return get_test_products()


def detect_from_image(image_path: str) -> list[dict]:
    """
    Detect products from a fridge image.
    
    Args:
        image_path: Path to the fridge image
        
    Returns:
        List of detected products with quantities
        
    TODO: Implement actual detection
    """
    print(f"📷 [STUB] Would analyze image: {image_path}")
    return get_test_products()
