"""
Skrip persiapan dataset untuk training YOLO11 (mode klasifikasi default maupun deteksi).
Memetakan nama kelas dataset (misal Kaggle 'O'/'R' atau folder custom) menjadi
2 kelas akhir FST: 'organic' dan 'inorganic' berdasarkan waste_mapping.py.
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

import yaml

from waste_mapping import map_label_to_bin_class

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def collect_images_by_class(source_dir: Path) -> dict[str, list[Path]]:
    """Menelusuri subdirektori dan memetakan folder kelas mentah -> organic / inorganic."""
    grouped: dict[str, list[Path]] = {"organic": [], "inorganic": []}
    if not source_dir.exists():
        return grouped

    skipped_folders: set[str] = set()
    for path in source_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        # Cek nama folder induk langsung (misal 'O', 'R', 'Organic', 'plastic')
        raw_class = path.parent.name
        mapped = map_label_to_bin_class(raw_class)
        if mapped in grouped:
            grouped[mapped].append(path)
        else:
            skipped_folders.add(raw_class)

    if skipped_folders:
        print(
            f"[INFO] Folder berikut belum ada di waste_mapping.py dan dilewati: "
            f"{sorted(skipped_folders)}"
        )
    return grouped


def copy_split_classification(
    grouped: dict[str, list[Path]],
    output_dir: Path,
    val_ratio: float,
    seed: int,
    prefix: str,
) -> dict[str, dict[str, int]]:
    """Menyalin gambar ke struktur klasifikasi Ultralytics: train/<kelas> & val/<kelas>."""
    rng = random.Random(seed)
    stats: dict[str, dict[str, int]] = {}

    for cls_name, files in grouped.items():
        shuffled = list(files)
        rng.shuffle(shuffled)
        val_count = int(len(shuffled) * val_ratio) if len(shuffled) > 1 else 0
        val_files = shuffled[:val_count]
        train_files = shuffled[val_count:]

        for split_name, split_files in (("train", train_files), ("val", val_files)):
            target_dir = output_dir / split_name / cls_name
            target_dir.mkdir(parents=True, exist_ok=True)
            for idx, src in enumerate(split_files):
                dst_name = f"{prefix}_{idx:05d}_{src.name}"
                shutil.copy2(src, target_dir / dst_name)

        stats[cls_name] = {"train": len(train_files), "val": len(val_files)}

    return stats


def remap_detection_dataset(source_yaml: Path, output_dir: Path) -> None:
    """
    Memetakan ulang dataset deteksi objek YOLO (format Roboflow / TACO export)
    ke 2 kelas akhir: 0 = organic, 1 = inorganic.
    """
    if not source_yaml.exists():
        raise FileNotFoundError(f"data.yaml sumber tidak ditemukan: {source_yaml}")

    with source_yaml.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    raw_names = cfg.get("names", {})
    if isinstance(raw_names, list):
        id_to_raw = {i: name for i, name in enumerate(raw_names)}
    elif isinstance(raw_names, dict):
        id_to_raw = {int(k): str(v) for k, v in raw_names.items()}
    else:
        raise ValueError("Format 'names' di data.yaml tidak dikenali.")

    id_remap: dict[int, int] = {}
    for old_id, raw_name in id_to_raw.items():
        mapped = map_label_to_bin_class(raw_name)
        if mapped == "organic":
            id_remap[old_id] = 0
        elif mapped == "inorganic":
            id_remap[old_id] = 1
        else:
            print(f"[PERINGATAN] Kelas '{raw_name}' (id={old_id}) belum dipetakan -> diabaikan.")

    base_dir = Path(cfg.get("path", source_yaml.parent))
    if not base_dir.is_absolute():
        base_dir = (source_yaml.parent / base_dir).resolve()

    for split in ("train", "val"):
        rel_img_dir = cfg.get(split)
        if not rel_img_dir:
            continue
        src_img_dir = (base_dir / rel_img_dir).resolve()
        src_lbl_dir = Path(str(src_img_dir).replace("images", "labels"))

        dst_img_dir = output_dir / "images" / split
        dst_lbl_dir = output_dir / "labels" / split
        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        if not src_img_dir.exists():
            continue

        for img_path in src_img_dir.iterdir():
            if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            lbl_path = src_lbl_dir / f"{img_path.stem}.txt"
            new_lines: list[str] = []
            if lbl_path.exists():
                for line in lbl_path.read_text(encoding="utf-8").splitlines():
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    old_cls = int(parts[0])
                    if old_cls in id_remap:
                        parts[0] = str(id_remap[old_cls])
                        new_lines.append(" ".join(parts))

            if new_lines:
                shutil.copy2(img_path, dst_img_dir / img_path.name)
                (dst_lbl_dir / f"{img_path.stem}.txt").write_text(
                    "\n".join(new_lines) + "\n", encoding="utf-8"
                )

    print(f"[SELESAI] Dataset deteksi 2-kelas tersimpan di: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Siapkan dataset organik/anorganik untuk training YOLO11"
    )
    parser.add_argument(
        "--kaggle-dir",
        type=Path,
        default=None,
        help="Folder dataset Kaggle Waste Classification (berisi TRAIN/O, TRAIN/R, TEST/O, TEST/R)",
    )
    parser.add_argument(
        "--webcam-dir",
        type=Path,
        default=Path("datasets/webcam_raw"),
        help="Folder foto hasil capture_images.py (berisi subfolder organic/ dan inorganic/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("datasets/waste_cls"),
        help="Folder output dataset klasifikasi siap latih",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Proporsi data validasi (default 0.2 = 20%%)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed pembagian train/val",
    )
    parser.add_argument(
        "--detect-yaml",
        type=Path,
        default=None,
        help="Opsional: path data.yaml dari Roboflow/TACO jika ingin menyiapkan dataset deteksi",
    )
    args = parser.parse_args()

    if args.detect_yaml is not None:
        remap_detection_dataset(args.detect_yaml, Path("datasets/waste_det"))
        return

    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)

    total_written = False

    if args.kaggle_dir is not None:
        if not args.kaggle_dir.exists():
            raise FileNotFoundError(f"Folder Kaggle tidak ditemukan: {args.kaggle_dir}")
        grouped_kaggle = collect_images_by_class(args.kaggle_dir)
        stats_k = copy_split_classification(
            grouped_kaggle, args.output_dir, args.val_ratio, args.seed, prefix="kaggle"
        )
        print(f"[KAGGLE] Distribusi tersalin: {stats_k}")
        total_written = True

    if args.webcam_dir is not None and args.webcam_dir.exists():
        grouped_cam = collect_images_by_class(args.webcam_dir)
        if grouped_cam["organic"] or grouped_cam["inorganic"]:
            stats_c = copy_split_classification(
                grouped_cam, args.output_dir, args.val_ratio, args.seed, prefix="webcam"
            )
            print(f"[WEBCAM] Distribusi tersalin: {stats_c}")
            total_written = True

    if not total_written:
        print(
            "Tidak ada gambar yang diproses.\n"
            "Contoh pemakaian:\n"
            "  python3 prepare_dataset.py --kaggle-dir ~/Downloads/DATASET --webcam-dir datasets/webcam_raw"
        )
    else:
        print(f"[SELESAI] Dataset klasifikasi siap di: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
