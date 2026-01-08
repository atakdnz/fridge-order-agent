# YOLOv8 Buzdolabı Eğitim Scripti

Bu klasör, buzdolabı ürün tespiti için YOLOv8 modelini eğitmek için gerekli dosyaları içerir.

## Kurulum

```bash
pip install ultralytics torch torchvision
```

## Kullanım

### Temel Eğitim

```bash
python train/train.py --data data/annotations/yolo/data.yaml --epochs 100
```

### Model Boyutu Seçimi

```bash
# Nano (en hızlı, düşük doğruluk)
python train/train.py --model yolov8n.pt --epochs 100

# Small (dengeli) - Önerilen
python train/train.py --model yolov8s.pt --epochs 100

# Medium (daha iyi doğruluk)
python train/train.py --model yolov8m.pt --epochs 100

# Large/XLarge (en iyi doğruluk, yavaş)
python train/train.py --model yolov8l.pt --epochs 100
```

### GPU/MPS Kullanımı

```bash
# CUDA (NVIDIA GPU)
python train/train.py --device cuda

# MPS (Apple Silicon)
python train/train.py --device mps

# CPU
python train/train.py --device cpu
```

### Checkpoint'tan Devam Etme

```bash
python train/train.py --resume
```

### Tüm Parametreler

```bash
python train/train.py --help
```

## Çıktılar

Eğitim sonrası `train/runs/detect/{run_name}/` klasöründe:
- `weights/best.pt` - En iyi model
- `weights/last.pt` - Son checkpoint
- `results.csv` - Epoch başına metrikler
- `confusion_matrix.png` - Confusion matrix
- `results.png` - Eğitim grafikleri
