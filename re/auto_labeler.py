"""
Auto Labeler for Refrigerator Ingredient Dataset
Uses YOLOv8m-seg for high-quality segmentation labeling

Pipeline:
1. YOLOv8m-seg → Object detection + Instance segmentation
2. Export → YOLO format labels (detect or segment)

For Google Colab - requires GPU (T4 or better)
"""

import os
import glob
import torch
import numpy as np
import cv2
from PIL import Image
from tqdm.auto import tqdm
from ultralytics import YOLO

# ============================================================================
# CONFIGURATION
# ============================================================================

# Our 23 ingredient classes
INGREDIENT_CLASSES = [
    "milk",             # 0
    "eggs",             # 1
    "cheese",           # 2
    "yogurt",           # 3
    "butter",           # 4
    "waterbottle",      # 5
    "soda",             # 6
    "juice",            # 7
    "tomato",           # 8
    "cucumber",         # 9
    "pepper",           # 10
    "apple",            # 11
    "orange",           # 12
    "lemon",            # 13
    "salami",           # 14
    "sausage",          # 15
    "chicken",          # 16
    "fish",             # 17
    "cake",             # 18
    "chocolate",        # 19
    "lettuce",          # 20
    "carrot",           # 21
    "banana",           # 22
]

# Paths
DATASET_PATH = "/content/drive/MyDrive/refrigerator_yolo_dataset"

# Model configuration - YOLOv8m-seg
MODEL_NAME = "yolov8m-seg.pt"

# Detection settings
CONFIDENCE = 0.25
IOU_THRESHOLD = 0.45
MAX_DET = 100

# Output format
OUTPUT_FORMAT = "segment"  # "detect" for bbox, "segment" for polygon masks
SIMPLIFY_POLYGON = True
MAX_POLYGON_POINTS = 50

# ============================================================================
# MODEL LOADING
# ============================================================================

def load_yolo_model(model_path=None):
    """Load YOLOv8m-seg model"""
    print("\n🚀 Loading YOLOv8m-seg model...")
    
    if model_path and os.path.exists(model_path):
        model = YOLO(model_path)
        print(f"✅ Loaded custom model: {model_path}")
    else:
        model = YOLO(MODEL_NAME)
        print(f"✅ Loaded pretrained model: {MODEL_NAME}")
    
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("   Running on CPU")
    
    return model


# ============================================================================
# DETECTION AND SEGMENTATION
# ============================================================================

def predict_image(model, image_path):
    """Run YOLOv8m-seg prediction on a single image"""
    results = model.predict(
        source=image_path,
        conf=CONFIDENCE,
        iou=IOU_THRESHOLD,
        max_det=MAX_DET,
        verbose=False,
        save=False,
    )
    return results[0] if results else None


def mask_to_polygon(mask, img_width, img_height):
    """Convert binary mask to normalized polygon points"""
    mask_uint8 = (mask * 255).astype(np.uint8)
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
    
    largest_contour = max(contours, key=cv2.contourArea)
    
    if SIMPLIFY_POLYGON:
        epsilon = 0.002 * cv2.arcLength(largest_contour, True)
        largest_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    if len(largest_contour) > MAX_POLYGON_POINTS:
        indices = np.linspace(0, len(largest_contour) - 1, MAX_POLYGON_POINTS, dtype=int)
        largest_contour = largest_contour[indices]
    
    points = largest_contour.reshape(-1, 2)
    normalized = []
    for x, y in points:
        nx = max(0.0, min(1.0, float(x) / img_width))
        ny = max(0.0, min(1.0, float(y) / img_height))
        normalized.extend([nx, ny])
    
    return normalized


def bbox_to_yolo(bbox, img_width, img_height):
    """Convert [x1, y1, x2, y2] to YOLO format [x_center, y_center, width, height]"""
    x1, y1, x2, y2 = bbox
    x_center = (x1 + x2) / 2 / img_width
    y_center = (y1 + y2) / 2 / img_height
    width = (x2 - x1) / img_width
    height = (y2 - y1) / img_height
    
    return (
        max(0, min(1, x_center)),
        max(0, min(1, y_center)),
        max(0, min(1, width)),
        max(0, min(1, height))
    )


# ============================================================================
# LABELING FUNCTIONS
# ============================================================================

def get_images_to_label(dataset_path: str, overwrite=False):
    """Get all images that need labeling"""
    images = []
    
    for split in ["train", "val", "test"]:
        img_dir = os.path.join(dataset_path, "images", split)
        if not os.path.exists(img_dir):
            continue
            
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            for img_path in glob.glob(os.path.join(img_dir, ext)):
                label_path = img_path.replace("/images/", "/labels/")
                label_path = label_path.rsplit(".", 1)[0] + ".txt"
                
                has_label = os.path.exists(label_path) and os.path.getsize(label_path) > 0
                
                if overwrite or not has_label:
                    images.append({
                        "image_path": img_path,
                        "label_path": label_path,
                        "split": split
                    })
    
    return images


def label_dataset(model_path=None, overwrite=False):
    """Label all images using YOLOv8m-seg"""
    print("="*60)
    print("🏷️  AUTO LABELER - YOLOv8m-seg")
    print("="*60)
    print(f"Model: {model_path or MODEL_NAME}")
    print(f"Output format: {OUTPUT_FORMAT}")
    print(f"Classes: {len(INGREDIENT_CLASSES)}")
    print("="*60)
    
    # Get images to label
    images = get_images_to_label(DATASET_PATH, overwrite)
    
    if not images:
        print("✅ All images already labeled!")
        return
    
    print(f"\n📊 Images to label: {len(images)}")
    
    # Load model
    model = load_yolo_model(model_path)
    
    # Process images
    print(f"\n🚀 Starting labeling...")
    
    stats = {
        "labeled": 0,
        "no_detections": 0,
        "errors": 0,
        "class_counts": {cls: 0 for cls in INGREDIENT_CLASSES}
    }
    
    for img_info in tqdm(images, desc="Labeling images"):
        img_path = img_info["image_path"]
        label_path = img_info["label_path"]
        
        try:
            image = Image.open(img_path)
            img_width, img_height = image.size
            
            result = predict_image(model, img_path)
            
            if result is None or result.boxes is None or len(result.boxes) == 0:
                stats["no_detections"] += 1
                os.makedirs(os.path.dirname(label_path), exist_ok=True)
                with open(label_path, 'w') as f:
                    pass
                continue
            
            yolo_labels = []
            
            for i, box in enumerate(result.boxes):
                class_id = int(box.cls[0])
                bbox = box.xyxy[0].cpu().numpy()
                
                if class_id >= len(INGREDIENT_CLASSES):
                    continue
                
                if OUTPUT_FORMAT == "segment" and result.masks is not None:
                    mask = result.masks.data[i].cpu().numpy()
                    polygon = mask_to_polygon(mask, img_width, img_height)
                    
                    if polygon and len(polygon) >= 6:
                        poly_str = " ".join([f"{p:.6f}" for p in polygon])
                        yolo_labels.append(f"{class_id} {poly_str}")
                    else:
                        x_c, y_c, w, h = bbox_to_yolo(bbox, img_width, img_height)
                        if w > 0 and h > 0:
                            yolo_labels.append(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")
                else:
                    x_c, y_c, w, h = bbox_to_yolo(bbox, img_width, img_height)
                    if w > 0 and h > 0:
                        yolo_labels.append(f"{class_id} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")
                
                stats["class_counts"][INGREDIENT_CLASSES[class_id]] += 1
            
            os.makedirs(os.path.dirname(label_path), exist_ok=True)
            with open(label_path, 'w') as f:
                f.write("\n".join(yolo_labels))
            
            stats["labeled"] += 1
            
        except Exception as e:
            print(f"\n❌ Error processing {img_path}: {e}")
            stats["errors"] += 1
            continue
    
    # Summary
    print("\n" + "="*60)
    print("✅ LABELING COMPLETE!")
    print("="*60)
    print(f"Images labeled: {stats['labeled']}")
    print(f"No detections: {stats['no_detections']}")
    print(f"Errors: {stats['errors']}")
    
    print("\n📊 Class Distribution:")
    for cls, count in sorted(stats["class_counts"].items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"   {cls}: {count}")
    
    print(f"\n📁 Labels saved to: {DATASET_PATH}/labels/")


def create_dataset_yaml():
    """Create dataset.yaml for YOLO training"""
    yaml_content = f"""# Refrigerator Ingredients Dataset
# Auto-labeled with YOLOv8m-seg

path: {DATASET_PATH}
train: images/train
val: images/val
test: images/test

# Classes
names:
"""
    for i, cls in enumerate(INGREDIENT_CLASSES):
        yaml_content += f"  {i}: {cls}\n"
    
    yaml_path = os.path.join(DATASET_PATH, "dataset.yaml")
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    
    print(f"✅ Created {yaml_path}")
    return yaml_path


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLOv8m-seg Auto Labeler")
    parser.add_argument("--model", type=str, default=None,
                       help="Path to custom model")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing labels")
    
    args = parser.parse_args()
    
    print("="*60)
    print("🍅 YOLOv8m-seg AUTO LABELER")
    print("="*60)
    
    label_dataset(model_path=args.model, overwrite=args.overwrite)
    create_dataset_yaml()
    
    print("\n🎉 Done!")
    print("📌 Next: Run train_yolo_segment.py for training")


if __name__ == "__main__":
    main()
