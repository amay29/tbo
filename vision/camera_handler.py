"""
Modul khusus penanganan webcam USB dan tampilan preview OpenCV.
Terpisah dari logika inferensi YOLO dan komunikasi serial agar kode rapi.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class PreviewOverlayInfo:
    """Data tampilan yang digambar di atas jendela preview OpenCV."""

    esp_state: str
    mapped_class: str
    raw_label: str
    confidence: float
    bbox_xyxy: Optional[Tuple[int, int, int, int]] = None
    status_note: str = "Menunggu STATE:q2"


class WebcamStream:
    """Pembungkus VideoCapture OpenCV dengan resolusi tetap dan error handling jelas."""

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None

    def open(self) -> None:
        """Membuka perangkat webcam USB dan menyetel resolusi 640x480."""
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            raise RuntimeError(
                f"Webcam pada index {self.camera_index} tidak ditemukan atau sedang dipakai aplikasi lain. "
                "Periksa koneksi USB atau ubah WEBCAM_INDEX di .env."
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def read_frame(self) -> np.ndarray:
        """Membaca satu frame BGR dari webcam; melempar error jika kamera terputus."""
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError("Webcam belum dibuka.")

        ok, frame = self.cap.read()
        if not ok or frame is None:
            raise RuntimeError(
                "Gagal membaca frame dari webcam. Pastikan kabel USB webcam tidak longgar."
            )
        return frame

    def draw_overlay(self, frame: np.ndarray, info: PreviewOverlayInfo) -> np.ndarray:
        """Menggambar kotak deteksi/ROI, label kelas, confidence, dan state ESP32."""
        canvas = frame.copy()
        h, w = canvas.shape[:2]

        # Warna kotak BGR sesuai hasil klasifikasi
        if info.mapped_class == "organic":
            color = (77, 140, 74)      # Hijau sage tenang
        elif info.mapped_class == "inorganic":
            color = (140, 108, 76)     # Biru-abu hangat
        else:
            color = (70, 82, 169)      # Merah bata lembut

        if info.bbox_xyxy is not None:
            x1, y1, x2, y2 = info.bbox_xyxy
        else:
            # Mode klasifikasi: gambar kotak ROI area papan pengarah di tengah frame
            x1, y1 = int(w * 0.18), int(h * 0.15)
            x2, y2 = int(w * 0.82), int(h * 0.85)

        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)

        label_text = f"{info.mapped_class.upper()} ({info.confidence:.2f})"
        if info.raw_label and info.raw_label.lower() != info.mapped_class.lower():
            label_text = f"{info.mapped_class.upper()} [{info.raw_label}] ({info.confidence:.2f})"

        cv2.rectangle(canvas, (x1, max(0, y1 - 28)), (min(w, x1 + 360), y1), color, -1)
        cv2.putText(
            canvas,
            label_text,
            (x1 + 6, max(18, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Panel informasi state ESP32 di sudut kiri atas
        cv2.rectangle(canvas, (0, 0), (w, 56), (34, 42, 36), -1)
        cv2.putText(
            canvas,
            f"ESP32 State: {info.esp_state}  |  {info.status_note}",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (250, 248, 244),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            "Tekan 'q' keluar | (Mode mock-serial: tekan 't' untuk simulasi STATE:q2)",
            (12, 46),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.44,
            (215, 210, 198),
            1,
            cv2.LINE_AA,
        )

        return canvas

    def show_frame(self, window_name: str, frame: np.ndarray) -> int:
        """Menampilkan frame ke jendela OpenCV dan mengembalikan kode tombol tekan."""
        cv2.imshow(window_name, frame)
        return cv2.waitKey(1) & 0xFF

    def release(self) -> None:
        """Menutup webcam dan seluruh jendela OpenCV dengan aman."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
