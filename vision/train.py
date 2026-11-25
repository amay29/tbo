"""
Skrip training YOLO11 untuk klasifikasi sampah organik vs anorganik.
Default memakai yolo11n-cls (klasifikasi satu objek di atas papan pengarah)
karena dataset publik seperti Kaggle Waste Classification berlabel per gambar
tanpa bounding box. Tetap mendukung --task detect untuk yolo11n + data.yaml.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Latih model YOLO11 untuk pemilahan sampah")
    parser.add_argument(
        "--task",
        choices=("classify", "detect"),
        default="classify",
        help="Pendekatan model: 'classify' (default, yolo11n-cls) atau 'detect' (yolo11n)",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Path folder dataset (classify) atau file data.yaml (detect)",
    )
    parser.add_argument("--epochs", type=int, default=60, help="Jumlah epoch (disarankan 50-100)")
    parser.add_argument("--imgsz", type=int, default=640, help="Ukuran gambar input (default 640)")
    parser.add_argument("--batch", type=int, default=16, help="Ukuran batch")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Perangkat training: 'cpu', '0' (CUDA GPU), atau 'mps' (Apple Silicon)",
    )
    args = parser.parse_args()

    if args.task == "classify":
        data_arg = args.data or "datasets/waste_cls"
        if not Path(data_arg).exists():
            raise FileNotFoundError(
                f"Folder dataset '{data_arg}' belum ada. Jalankan prepare_dataset.py terlebih dahulu."
            )
        model_weights = "yolo11n-cls.pt"
        run_name = "smart_bin_cls"
    else:
        data_arg = args.data or "data.yaml"
        if not Path(data_arg).exists():
            raise FileNotFoundError(f"File '{data_arg}' tidak ditemukan.")
        model_weights = "yolo11n.pt"
        run_name = "smart_bin_det"

    print(f"Memulai training {model_weights} | data={data_arg} | epochs={args.epochs} | imgsz={args.imgsz}")
    model = YOLO(model_weights)
    results = model.train(
        data=data_arg,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project="runs/" + args.task,
        name=run_name,
        exist_ok=True,
    )

    print("\nTraining selesai.")
    print(f"Folder hasil & grafik: {results.save_dir}")
    print(
        "Cara membaca hasil:\n"
        "- Mode classify: periksa metrik top1 accuracy (target >= 0.85) dan confusion_matrix.png.\n"
        "- Mode detect  : periksa mAP50 dan mAP50-95 pada results.csv/png serta confusion_matrix.png.\n"
        "- Salin path weights/best.pt ke MODEL_PATH di file vision/.env."
    )


if __name__ == "__main__":
    main()
