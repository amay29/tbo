"""
Skrip pengumpulan dataset foto langsung dari webcam USB di atas papan pengarah.
Disarankan mengumpulkan 150-300 foto per kelas pada kondisi pencahayaan nyata.

Kontrol keyboard pada jendela webcam:
  - Tekan 'o' : simpan frame sebagai sampah ORGANIK
  - Tekan 'a' : simpan frame sebagai sampah ANORGANIK
  - Tekan 'q' : keluar
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import cv2
from dotenv import load_dotenv

from camera_handler import WebcamStream


def count_images(folder: Path) -> int:
    if not folder.exists():
        return 0
    return sum(1 for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".png", ".jpeg"})


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ambil foto dataset dari webcam untuk tiap kelas")
    parser.add_argument(
        "--camera",
        type=int,
        default=int(os.getenv("WEBCAM_INDEX", "0")),
        help="Index kamera USB (default dari WEBCAM_INDEX di .env atau 0)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("datasets/webcam_raw"),
        help="Folder penyimpanan foto mentah per kelas",
    )
    args = parser.parse_args()

    org_dir = args.output_dir / "organic"
    inorg_dir = args.output_dir / "inorganic"
    org_dir.mkdir(parents=True, exist_ok=True)
    inorg_dir.mkdir(parents=True, exist_ok=True)

    org_count = count_images(org_dir)
    inorg_count = count_images(inorg_dir)

    cam = WebcamStream(
        camera_index=args.camera,
        width=int(os.getenv("CAMERA_WIDTH", "640")),
        height=int(os.getenv("CAMERA_HEIGHT", "480")),
    )
    cam.open()
    print("Webcam terbuka. Tekan 'o' (organik), 'a' (anorganik), atau 'q' (keluar).")

    try:
        while True:
            frame = cam.read_frame()
            preview = frame.copy()
            h, w = preview.shape[:2]

            # Gambar kotak area papan pengarah sebagai panduan penempatan objek
            cv2.rectangle(
                preview,
                (int(w * 0.18), int(h * 0.15)),
                (int(w * 0.82), int(h * 0.85)),
                (77, 140, 74),
                2,
            )
            cv2.rectangle(preview, (0, 0), (w, 56), (34, 42, 36), -1)
            cv2.putText(
                preview,
                f"Organik: {org_count}  |  Anorganik: {inorg_count}  (Target: 150-300/kelas)",
                (12, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (250, 248, 244),
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                preview,
                "Tombol: [o] Simpan Organik   [a] Simpan Anorganik   [q] Keluar",
                (12, 46),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (215, 210, 198),
                1,
                cv2.LINE_AA,
            )

            key = cam.show_frame("Capture Dataset Tempat Sampah Pintar", preview)
            ts = int(time.time() * 1000)

            if key == ord("o"):
                out_path = org_dir / f"org_{ts}.jpg"
                cv2.imwrite(str(out_path), frame)
                org_count += 1
                print(f"[SIMPAN] Organik -> {out_path} (total: {org_count})")
            elif key == ord("a"):
                out_path = inorg_dir / f"inorg_{ts}.jpg"
                cv2.imwrite(str(out_path), frame)
                inorg_count += 1
                print(f"[SIMPAN] Anorganik -> {out_path} (total: {inorg_count})")
            elif key == ord("q"):
                break
    finally:
        cam.release()


if __name__ == "__main__":
    main()
