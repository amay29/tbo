"""
Program utama runtime Computer Vision (tahap D):
Menghubungkan modul webcam (camera_handler.py), model YOLO (yolo_detector.py),
dan komunikasi serial ESP32 (serial_bridge.py).

Aturan kendali FST:
- ESP32 adalah pengendali penuh FST.
- Laptop HANYA mengirim CLS:organic / CLS:inorganic / CLS:unknown setelah menerima STATE:q2.
- Selama menerima STATE:q2, sistem mengumpulkan prediksi frame selama ~1,5 detik lalu
  melakukan majority voting. Di luar q2, sistem tidak mengirim hasil klasifikasi.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
from dotenv import load_dotenv

from camera_handler import PreviewOverlayInfo, WebcamStream
from serial_bridge import Esp32SerialBridge, MockSerialBridge
from waste_mapping import to_serial_command
from yolo_detector import FramePrediction, WasteYoloClassifier, aggregate_window_votes


def log_msg(message: str) -> None:
    """Mencetak log ke console lengkap dengan timestamp presisi."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {message}", flush=True)


def run_test_image(image_path: Path, detector: WasteYoloClassifier, no_gui: bool) -> None:
    """Menguji satu file gambar tanpa membutuhkan webcam maupun ESP32."""
    if not image_path.exists():
        raise FileNotFoundError(f"Gambar uji tidak ditemukan: {image_path}")

    frame = cv2.imread(str(image_path))
    if frame is None:
        raise RuntimeError(f"Gagal membaca gambar: {image_path}")

    pred = detector.predict_frame(frame)
    serial_cmd = to_serial_command(pred.mapped_class)

    log_msg(
        f"Hasil test-image '{image_path.name}': "
        f"raw='{pred.raw_label}', kelas='{pred.mapped_class}', "
        f"confidence={pred.confidence:.3f}, perintah_serial='{serial_cmd}'"
    )

    if not no_gui:
        cam = WebcamStream()
        annotated = cam.draw_overlay(
            frame,
            PreviewOverlayInfo(
                esp_state="TEST_IMAGE",
                mapped_class=pred.mapped_class,
                raw_label=pred.raw_label,
                confidence=pred.confidence,
                bbox_xyxy=pred.bbox_xyxy,
                status_note=f"Akan kirim: {serial_cmd}",
            ),
        )
        cv2.imshow("Uji Gambar YOLO - Tekan tombol apa saja untuk tutup", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="YOLO + Webcam Serial Bridge untuk Tempat Sampah Pintar FST"
    )
    parser.add_argument(
        "--test-image",
        type=Path,
        default=None,
        help="Uji inferensi pada satu gambar tanpa webcam & ESP32",
    )
    parser.add_argument(
        "--mock-serial",
        action="store_true",
        help="Jalankan webcam + YOLO tanpa ESP32 (cetak perintah serial ke console)",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Jangan tampilkan jendela preview OpenCV (berguna pada mode --test-image)",
    )
    args = parser.parse_args()

    model_path = os.getenv("MODEL_PATH", "runs/classify/smart_bin_cls/weights/best.pt")
    yolo_task = os.getenv("YOLO_TASK", "classify")
    camera_index = int(os.getenv("WEBCAM_INDEX", "0"))
    cam_width = int(os.getenv("CAMERA_WIDTH", "640"))
    cam_height = int(os.getenv("CAMERA_HEIGHT", "480"))
    serial_port = os.getenv("SERIAL_PORT", "AUTO")
    serial_baud = int(os.getenv("SERIAL_BAUD", "115200"))
    conf_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
    majority_ratio = float(os.getenv("MAJORITY_RATIO", "0.60"))
    window_sec = float(os.getenv("CLASSIFY_WINDOW_SEC", "1.5"))

    try:
        detector = WasteYoloClassifier(model_path=model_path, task=yolo_task)
        log_msg(f"Model YOLO dimuat: {model_path} (task={yolo_task})")
    except Exception as exc:
        log_msg(f"[ERROR MODEL] {exc}")
        sys.exit(1)

    if args.test_image is not None:
        try:
            run_test_image(args.test_image, detector, no_gui=args.no_gui)
        except Exception as exc:
            log_msg(f"[ERROR TEST-IMAGE] {exc}")
            sys.exit(1)
        return

    # Buka webcam USB
    cam = WebcamStream(camera_index=camera_index, width=cam_width, height=cam_height)
    try:
        cam.open()
        log_msg(f"Webcam terbuka pada index {camera_index} ({cam_width}x{cam_height})")
    except Exception as exc:
        log_msg(f"[ERROR WEBCAM] {exc}")
        sys.exit(1)

    # Siapkan serial bridge (asli atau mock)
    bridge = (
        MockSerialBridge()
        if args.mock_serial
        else Esp32SerialBridge(port=serial_port, baudrate=serial_baud)
    )
    if bridge.connect():
        log_msg(f"Serial terhubung pada port {bridge.active_port} @ {serial_baud} baud")
    else:
        log_msg(
            "Port serial ESP32 belum terdeteksi; program tetap berjalan dan akan mencoba auto-reconnect."
        )

    esp_state = "q0"
    collecting_window = False
    window_start = 0.0
    window_samples: list[FramePrediction] = []

    try:
        while True:
            # 1. Pastikan koneksi serial tetap hidup (auto-reconnect jika putus)
            if not bridge.ensure_connected():
                serial_note = "Serial putus (mencoba sambung ulang...)"
            else:
                serial_note = f"Serial: {bridge.active_port}"

            # 2. Baca pesan state/log terbaru dari ESP32
            for line in bridge.read_lines():
                log_msg(f"[ESP32 -> Laptop] {line}")
                if line.startswith("STATE:"):
                    esp_state = line.split(":", 1)[1].strip()
                    if esp_state == "q2" and not collecting_window:
                        collecting_window = True
                        window_start = time.monotonic()
                        window_samples = []
                        log_msg(
                            f"ESP32 masuk q2 -> memulai window klasifikasi selama {window_sec:.1f} detik..."
                        )
                    elif esp_state != "q2" and collecting_window:
                        # Jika ESP32 keluar dari q2 lebih awal (misal timeout), hentikan window
                        collecting_window = False
                        window_samples = []

            # 3. Ambil frame webcam & jalankan inferensi untuk tampilan/window
            try:
                frame = cam.read_frame()
            except Exception as exc:
                log_msg(f"[ERROR WEBCAM] {exc}")
                time.sleep(0.5)
                continue

            pred = detector.predict_frame(frame)

            # 4. Jika sedang berada di window STATE:q2, kumpulkan voting dan kirim hasilnya sekali
            status_note = serial_note
            if collecting_window:
                window_samples.append(pred)
                elapsed = time.monotonic() - window_start
                status_note = f"Mengklasifikasi q2 ({elapsed:.1f}/{window_sec:.1f}s)"

                if elapsed >= window_sec:
                    vote = aggregate_window_votes(
                        window_samples,
                        min_confidence=conf_threshold,
                        min_majority_ratio=majority_ratio,
                    )
                    cmd = to_serial_command(vote.final_class)
                    log_msg(
                        f"Hasil voting ({vote.total_frames} frame): kelas='{vote.final_class}', "
                        f"mayoritas={vote.vote_ratio:.0%}, avg_conf={vote.avg_confidence:.2f}, "
                        f"alasan='{vote.reason}' -> kirim '{cmd}'"
                    )
                    if bridge.send_command(cmd):
                        log_msg(f"[Laptop -> ESP32] Terkirim: {cmd}")
                    else:
                        log_msg(f"[PERINGATAN] Gagal kirim '{cmd}' karena serial terputus.")

                    collecting_window = False
                    window_samples = []
                    # Tunggu konfirmasi state baru dari ESP32
                    esp_state = "menunggu_q0"

            # 5. Gambar preview OpenCV
            annotated = cam.draw_overlay(
                frame,
                PreviewOverlayInfo(
                    esp_state=esp_state,
                    mapped_class=pred.mapped_class,
                    raw_label=pred.raw_label,
                    confidence=pred.confidence,
                    bbox_xyxy=pred.bbox_xyxy,
                    status_note=status_note,
                ),
            )
            key = cam.show_frame("Pemilah Sampah Pintar - YOLO Preview", annotated)

            if key == ord("q"):
                log_msg("Dihentikan oleh pengguna.")
                break
            elif key == ord("t") and isinstance(bridge, MockSerialBridge):
                bridge.trigger_mock_q2()
    finally:
        cam.release()
        bridge.close()


if __name__ == "__main__":
    main()
