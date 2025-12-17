"""
Fridge detection module using YOLO model.
Detects products in fridge images and returns missing items for ordering.
"""

from pathlib import Path
from ultralytics import YOLO

# Default model path - can be overridden
DEFAULT_MODEL_PATH = "/Users/atakan/Desktop/Projeler/FridgeFrontend/models/best.pt"

# Mapping from model class names to Getir search terms (Turkish)
CLASS_TO_GETIR = {
    "milk": "Süt",
    "eggs": "Yumurta",
    "cheese": "Peynir",
    "yogurt": "Yoğurt",
    "butter": "Tereyağı",
    "water_bottle": "Su",
    "soda": "Gazlı İçecek",
    "juice": "Meyve Suyu",
    "tomato": "Domates",
    "cucumber": "Salatalık",
    "pepper": "Biber",
    "apple": "Elma",
    "orange": "Portakal",
    "lemon": "Limon",
    "salami": "Salam",
    "sausage": "Sosis",
    "chicken": "Tavuk",
    "fish": "Balık",
    "cake": "Pasta",
    "chocolate": "Çikolata",
    "lettuce": "Marul",
    "carrot": "Havuç",
    "banana": "Muz",
}

# Expected items in a well-stocked fridge (customize as needed)
EXPECTED_ITEMS = {
    "milk": 1,
    "eggs": 1,
    "water_bottle": 2,
    "cheese": 1,
}


class FridgeDetector:
    """Detects products in fridge images using YOLO."""
    
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        """Load the YOLO model."""
        print(f"🔍 Loading detection model...")
        self.model = YOLO(model_path)
        self.class_names = self.model.names
        print(f"   ✓ Model loaded ({len(self.class_names)} classes)")
    
    def detect(self, image_path: str, confidence: float = 0.5) -> dict[str, int]:
        """
        Detect products in an image.
        
        Args:
            image_path: Path to the fridge image
            confidence: Minimum confidence threshold
            
        Returns:
            Dict mapping class names to counts
        """
        print(f"📷 Analyzing image: {image_path}")
        
        results = self.model(image_path, conf=confidence, verbose=False)
        
        # Count detections per class
        counts = {}
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                class_name = self.class_names[class_id]
                counts[class_name] = counts.get(class_name, 0) + 1
        
        print(f"   ✓ Detected {sum(counts.values())} items: {counts}")
        return counts
    
    def get_missing_items(self, detected: dict[str, int], expected: dict[str, int] = None) -> list[dict]:
        """
        Compare detected items with expected and return missing items.
        
        Args:
            detected: Dict of detected class names and counts
            expected: Dict of expected class names and minimum counts
            
        Returns:
            List of missing products for ordering
        """
        if expected is None:
            expected = EXPECTED_ITEMS
        
        missing = []
        for item, min_count in expected.items():
            current = detected.get(item, 0)
            if current < min_count:
                needed = min_count - current
                getir_name = CLASS_TO_GETIR.get(item, item)
                missing.append({
                    "name": getir_name,
                    "quantity": needed,
                    "category": item,
                })
        
        return missing


# Global detector instance (lazy loaded)
_detector = None


def get_detector() -> FridgeDetector:
    """Get or create the global detector instance."""
    global _detector
    if _detector is None:
        _detector = FridgeDetector()
    return _detector


def detect_from_image(image_path: str) -> list[dict]:
    """
    Detect missing products from a fridge image.
    
    Args:
        image_path: Path to the fridge image
        
    Returns:
        List of missing products for ordering
    """
    detector = get_detector()
    detected = detector.detect(image_path)
    missing = detector.get_missing_items(detected)
    return missing


def get_missing_products(image_path: str = None) -> list[dict]:
    """
    Main entry point - detect missing products from fridge.
    
    If no image_path provided, uses test products for development.
    """
    if image_path:
        return detect_from_image(image_path)
    else:
        # Fallback to test products if no image provided
        print("📷 [No image provided - using test products]")
        from config.products import get_test_products
        return get_test_products()
