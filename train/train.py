"""
YOLOv8 Buzdolabı Ürün Tespiti Eğitim Scripti
=============================================

Bu script, sentetik olarak üretilmiş buzdolabı görüntüleri üzerinde
YOLOv8 modelini eğitmek için kullanılır.

Kullanım:
    python train/train.py --data path/to/data.yaml --epochs 100 --model yolov8s
    python train/train.py --resume  # Son checkpoint'tan devam et
"""

import os
import argparse
from pathlib import Path
from datetime import datetime

# Ultralytics YOLO import
from ultralytics import YOLO

# Proje kök dizini
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "annotations" / "yolo" / "data.yaml"
RUNS_DIR = PROJECT_ROOT / "train" / "runs"


def parse_args():
    """Komut satırı argümanlarını parse et."""
    parser = argparse.ArgumentParser(
        description="YOLOv8 Buzdolabı Ürün Tespiti Eğitimi"
    )

    # Veri ve model ayarları
    parser.add_argument(
        "--data",
        type=str,
        default=str(DEFAULT_DATA_PATH),
        help="data.yaml dosyasının yolu"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8s.pt",
        choices=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        help="Kullanılacak YOLOv8 model boyutu (n=nano, s=small, m=medium, l=large, x=xlarge)"
    )

    # Eğitim hiperparametreleri
    parser.add_argument("--epochs", type=int, default=100, help="Eğitim epoch sayısı")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Görüntü boyutu")
    parser.add_argument("--lr0", type=float, default=0.01, help="Başlangıç learning rate")
    parser.add_argument("--lrf", type=float, default=0.01, help="Final learning rate (lr0 * lrf)")

    # Data augmentation
    parser.add_argument("--augment", action="store_true", default=True, help="Data augmentation aktif")
    parser.add_argument("--mosaic", type=float, default=1.0, help="Mosaic augmentation olasılığı")
    parser.add_argument("--mixup", type=float, default=0.1, help="Mixup augmentation olasılığı")
    parser.add_argument("--hsv_h", type=float, default=0.015, help="HSV-Hue augmentation")
    parser.add_argument("--hsv_s", type=float, default=0.7, help="HSV-Saturation augmentation")
    parser.add_argument("--hsv_v", type=float, default=0.4, help="HSV-Value augmentation")

    # Diğer ayarlar
    parser.add_argument("--device", type=str, default="", help="Eğitim cihazı (cuda, mps, cpu)")
    parser.add_argument("--workers", type=int, default=8, help="DataLoader worker sayısı")
    parser.add_argument("--patience", type=int, default=50, help="Early stopping patience")
    parser.add_argument("--save_period", type=int, default=10, help="Kaç epoch'ta bir checkpoint kaydet")
    parser.add_argument("--resume", action="store_true", help="Son checkpoint'tan devam et")
    parser.add_argument("--pretrained", action="store_true", default=True, help="Pretrained weights kullan")
    parser.add_argument("--freeze", type=int, default=0, help="İlk N layer'ı dondur (transfer learning)")
    parser.add_argument("--name", type=str, default="", help="Eğitim run ismi")
    parser.add_argument("--exist_ok", action="store_true", help="Mevcut run klasörünü kullan")

    return parser.parse_args()


def get_device():
    """En uygun eğitim cihazını belirle."""
    import torch

    if torch.cuda.is_available():
        device = "cuda"
        print(f"✓ CUDA cihazı bulundu: {torch.cuda.get_device_name(0)}")
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    elif torch.backends.mps.is_available():
        device = "mps"
        print("✓ Apple Silicon MPS cihazı bulundu")
    else:
        device = "cpu"
        print("⚠ GPU bulunamadı, CPU kullanılacak")

    return device


def validate_data_path(data_path: str) -> Path:
    """Veri yolunu doğrula."""
    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(f"data.yaml bulunamadı: {path}")

    # data.yaml içeriğini kontrol et
    import yaml
    with open(path) as f:
        data_config = yaml.safe_load(f)

    required_keys = ["train", "val", "nc", "names"]
    for key in required_keys:
        if key not in data_config:
            raise ValueError(f"data.yaml'da '{key}' anahtarı eksik")

    print(f"✓ Veri seti yüklendi:")
    print(f"  Sınıf sayısı: {data_config['nc']}")
    print(f"  Sınıflar: {', '.join(data_config['names'][:5])}...")

    return path


def create_run_name(args) -> str:
    """Eğitim run ismi oluştur."""
    if args.name:
        return args.name

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = args.model.replace(".pt", "")
    return f"fridge_{model_name}_{timestamp}"


def train(args):
    """Ana eğitim fonksiyonu."""
    print("\n" + "="*60)
    print("🧊 BUZDOLABI ÜRÜN TESPİTİ - YOLOv8 EĞİTİMİ")
    print("="*60 + "\n")

    # Cihaz seçimi
    device = args.device if args.device else get_device()

    # Veri yolunu doğrula
    data_path = validate_data_path(args.data)

    # Run ismi
    run_name = create_run_name(args)

    # Runs dizinini oluştur
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n📋 Eğitim Konfigürasyonu:")
    print(f"  Model: {args.model}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch Size: {args.batch}")
    print(f"  Image Size: {args.imgsz}")
    print(f"  Learning Rate: {args.lr0} → {args.lr0 * args.lrf}")
    print(f"  Device: {device}")
    print(f"  Run Name: {run_name}")
    print(f"  Output: {RUNS_DIR / 'detect' / run_name}")

    # YOLO modelini yükle
    print(f"\n🔄 Model yükleniyor: {args.model}")

    if args.resume:
        # Son checkpoint'tan devam et
        last_run = sorted(RUNS_DIR.glob("detect/fridge_*/weights/last.pt"))
        if not last_run:
            raise FileNotFoundError("Devam edilecek checkpoint bulunamadı!")
        model = YOLO(str(last_run[-1]))
        print(f"✓ Checkpoint yüklendi: {last_run[-1]}")
    else:
        model = YOLO(args.model)
        print(f"✓ Pretrained model yüklendi")

    # Eğitimi başlat
    print(f"\n🚀 Eğitim başlatılıyor...\n")

    results = model.train(
        # Temel ayarlar
        data=str(data_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=device,

        # Learning rate
        lr0=args.lr0,
        lrf=args.lrf,

        # Data augmentation
        augment=args.augment,
        mosaic=args.mosaic,
        mixup=args.mixup,
        hsv_h=args.hsv_h,
        hsv_s=args.hsv_s,
        hsv_v=args.hsv_v,

        # Optimizasyon
        optimizer="SGD",
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,

        # Kaydetme ayarları
        project=str(RUNS_DIR / "detect"),
        name=run_name,
        exist_ok=args.exist_ok,
        save=True,
        save_period=args.save_period,

        # Early stopping
        patience=args.patience,

        # Diğer
        workers=args.workers,
        pretrained=args.pretrained,
        freeze=args.freeze,
        verbose=True,
        seed=42,

        # Validation
        val=True,
        plots=True,

        # Cache için
        cache=True,
    )

    print("\n" + "="*60)
    print("✅ EĞİTİM TAMAMLANDI!")
    print("="*60)

    # Sonuçları göster
    best_model_path = RUNS_DIR / "detect" / run_name / "weights" / "best.pt"
    print(f"\n📊 Sonuçlar:")
    print(f"  En iyi model: {best_model_path}")

    if hasattr(results, 'results_dict'):
        metrics = results.results_dict
        print(f"\n📈 Final Metrikler:")
        print(f"  mAP@50: {metrics.get('metrics/mAP50(B)', 'N/A'):.4f}")
        print(f"  mAP@50-95: {metrics.get('metrics/mAP50-95(B)', 'N/A'):.4f}")
        print(f"  Precision: {metrics.get('metrics/precision(B)', 'N/A'):.4f}")
        print(f"  Recall: {metrics.get('metrics/recall(B)', 'N/A'):.4f}")

    return results


def validate_model(model_path: str, data_path: str):
    """Eğitilmiş modeli doğrula."""
    print(f"\n🔍 Model doğrulanıyor: {model_path}")

    model = YOLO(model_path)
    results = model.val(data=data_path, split="test")

    print(f"\n📊 Test Seti Sonuçları:")
    print(f"  mAP@50: {results.box.map50:.4f}")
    print(f"  mAP@50-95: {results.box.map:.4f}")
    print(f"  Precision: {results.box.mp:.4f}")
    print(f"  Recall: {results.box.mr:.4f}")

    return results


def export_model(model_path: str, format: str = "onnx"):
    """Modeli farklı formatlara export et."""
    print(f"\n📦 Model export ediliyor: {format}")

    model = YOLO(model_path)
    model.export(format=format)

    print(f"✓ Export tamamlandı")


if __name__ == "__main__":
    args = parse_args()

    try:
        results = train(args)

        # Eğitim sonrası test seti validasyonu
        if not args.resume:
            best_model = RUNS_DIR / "detect" / create_run_name(args) / "weights" / "best.pt"
            if best_model.exists():
                validate_model(str(best_model), args.data)

    except KeyboardInterrupt:
        print("\n\n⚠️ Eğitim kullanıcı tarafından durduruldu!")
        print("Devam etmek için: python train/train.py --resume")
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        raise
