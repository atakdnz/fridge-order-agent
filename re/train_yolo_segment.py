"""
YOLOv8m-seg Model Training Script
Refrigerator ingredient segmentation
"""

import os
from ultralytics import YOLO

# Configuration
DATASET_PATH = "/content/drive/MyDrive/refrigerator_yolo_dataset"
DATA_YAML = os.path.join(DATASET_PATH, "dataset.yaml")

BASE_MODEL = "yolov8m-seg.pt"
EPOCHS = 150
IMG_SIZE = 640
BATCH_SIZE = 16
PATIENCE = 30
WORKERS = 4

FREEZE_LAYERS = 10
WARMUP_EPOCHS = 5

PROJECT_NAME = "refrigerator_segmentation"
RUN_NAME = "train_yolov8m_segment"


def check_dataset():
    print("=" * 60)
    print("DATASET CHECK")
    print("=" * 60)

    if not os.path.exists(DATA_YAML):
        print(f"data.yaml not found: {DATA_YAML}")
        return False

    print("data.yaml found")

    for split in ["train", "val"]:
        img_dir = os.path.join(DATASET_PATH, "images", split)
        lbl_dir = os.path.join(DATASET_PATH, "labels", split)

        if not os.path.exists(img_dir):
            print(f"Missing: {img_dir}")
            return False
        if not os.path.exists(lbl_dir):
            print(f"Missing: {lbl_dir}")
            return False

        img_count = len([f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        lbl_count = len([f for f in os.listdir(lbl_dir) if f.endswith('.txt')])

        print(f"{split}: {img_count} images, {lbl_count} labels")

    print("=" * 60)
    return True


def train():
    print("=" * 60)
    print("YOLO SEGMENT TRAINING")
    print("=" * 60)
    print(f"Model: {BASE_MODEL}")
    print(f"Dataset: {DATASET_PATH}")
    print(f"Epochs: {EPOCHS} | Batch: {BATCH_SIZE} | ImgSize: {IMG_SIZE}")
    print("=" * 60)

    if not check_dataset():
        print("\nDataset check failed!")
        return None

    checkpoint_path = f"{PROJECT_NAME}/{RUN_NAME}/weights/last.pt"
    if os.path.exists(checkpoint_path):
        print(f"\nResuming from: {checkpoint_path}")
        model = YOLO(checkpoint_path)
    else:
        print(f"\nLoading base model: {BASE_MODEL}")
        model = YOLO(BASE_MODEL)

    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        patience=PATIENCE,
        workers=WORKERS,
        project=PROJECT_NAME,
        name=RUN_NAME,
        exist_ok=True,

        # Transfer learning
        freeze=FREEZE_LAYERS,

        # Augmentation
        hsv_h=0.02,
        hsv_s=0.8,
        hsv_v=0.5,
        degrees=15,
        translate=0.15,
        scale=0.6,
        shear=8,
        perspective=0.001,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.15,
        copy_paste=0.1,
        erasing=0.1,

        # Optimizer
        optimizer='AdamW',
        lr0=0.001,
        lrf=0.01,
        warmup_epochs=WARMUP_EPOCHS,

        # Other
        amp=True,
        cache='ram',
        verbose=True,
        plots=True,
        save_period=10,
    )

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Best model: {PROJECT_NAME}/{RUN_NAME}/weights/best.pt")

    return results


def validate(model_path=None):
    if model_path is None:
        model_path = f"{PROJECT_NAME}/{RUN_NAME}/weights/best.pt"

    print(f"\nValidating: {model_path}")
    model = YOLO(model_path)
    return model.val(data=DATA_YAML)


def predict_sample(model_path=None, image_path=None):
    if model_path is None:
        model_path = f"{PROJECT_NAME}/{RUN_NAME}/weights/best.pt"

    model = YOLO(model_path)

    if image_path is None:
        val_dir = os.path.join(DATASET_PATH, "images", "val")
        images = [f for f in os.listdir(val_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
        if images:
            image_path = os.path.join(val_dir, images[0])

    if image_path and os.path.exists(image_path):
        return model.predict(source=image_path, save=True, project=PROJECT_NAME, name="predictions")
    return None


def export_model(model_path=None, format="onnx"):
    if model_path is None:
        model_path = f"{PROJECT_NAME}/{RUN_NAME}/weights/best.pt"

    model = YOLO(model_path)
    model.export(format=format)


if __name__ == "__main__":
    train()
