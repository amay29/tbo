"""
Modul khusus inferensi model Ultralytics YOLO11 (klasifikasi atau deteksi)
dan algoritma majority voting pada jendela waktu ~1,5 detik.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, Tuple

from waste_mapping import map_label_to_bin_class

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class FramePrediction:
    """Hasil prediksi YOLO pada satu frame gambar."""

    mapped_class: str  # "organic", "inorganic", atau "unknown"
    raw_label: str
    confidence: float
    bbox_xyxy: Optional[Tuple[int, int, int, int]] = None


@dataclass(frozen=True)
class WindowVoteResult:
    """Keputusan akhir hasil voting mayoritas selama window klasifikasi."""

    final_class: str  # "organic", "inorganic", atau "unknown"
    avg_confidence: float
    vote_ratio: float
    total_frames: int
    reason: str


def aggregate_window_votes(
    predictions: Iterable[FramePrediction],
    min_confidence: float = 0.60,
    min_majority_ratio: float = 0.60,
) -> WindowVoteResult:
    """
    Menentukan kelas akhir dari kumpulan prediksi frame selama ~1,5 detik.
    Aturan:
    - Minimal `min_majority_ratio` (default 60%) frame harus sepakat pada kelas yang sama
      ('organic' atau 'inorganic').
    - Rata-rata confidence kelas pemenang harus >= `min_confidence` (default 0.60).
    - Jika tidak terpenuhi atau tidak ada objek -> kembalikan 'unknown'.
    """
    samples = list(predictions)
    total = len(samples)
    if total == 0:
        return WindowVoteResult(
            final_class="unknown",
            avg_confidence=0.0,
            vote_ratio=0.0,
            total_frames=0,
            reason="tidak ada frame yang terbaca",
        )

    valid_votes = [s for s in samples if s.mapped_class in ("organic", "inorganic")]
    if not valid_votes:
        return WindowVoteResult(
            final_class="unknown",
            avg_confidence=0.0,
            vote_ratio=0.0,
            total_frames=total,
            reason="tidak ada objek organik/anorganik yang dikenali",
        )

    counts = Counter(s.mapped_class for s in valid_votes)
    winner, winner_count = counts.most_common(1)[0]
    vote_ratio = winner_count / total
    winner_confs = [s.confidence for s in valid_votes if s.mapped_class == winner]
    avg_conf = sum(winner_confs) / len(winner_confs)

    if vote_ratio < min_majority_ratio:
        return WindowVoteResult(
            final_class="unknown",
            avg_confidence=avg_conf,
            vote_ratio=vote_ratio,
            total_frames=total,
            reason=(
                f"mayoritas belum tercapai ({vote_ratio:.0%} < {min_majority_ratio:.0%})"
            ),
        )

    if avg_conf < min_confidence:
        return WindowVoteResult(
            final_class="unknown",
            avg_confidence=avg_conf,
            vote_ratio=vote_ratio,
            total_frames=total,
            reason=(
                f"confidence rata-rata rendah ({avg_conf:.2f} < {min_confidence:.2f})"
            ),
        )

    return WindowVoteResult(
        final_class=winner,
        avg_confidence=avg_conf,
        vote_ratio=vote_ratio,
        total_frames=total,
        reason="mayoritas dan confidence terpenuhi",
    )


class WasteYoloClassifier:
    """Pembungkus model YOLO11 untuk klasifikasi (yolo11n-cls) atau deteksi (yolo11n)."""

    def __init__(self, model_path: str | Path, task: str = "classify") -> None:
        self.model_path = Path(model_path)
        self.task = task.strip().lower()
        if self.task not in ("classify", "detect"):
            raise ValueError("YOLO_TASK harus 'classify' atau 'detect'.")

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"File model tidak ditemukan di '{self.model_path}'. "
                "Jalankan train.py terlebih dahulu atau perbaiki MODEL_PATH di .env."
            )

        # Import di dalam __init__ agar modul voting bisa diuji tanpa paket ultralytics terpasang
        from ultralytics import YOLO

        self.model = YOLO(str(self.model_path))

    def predict_frame(self, frame: np.ndarray) -> FramePrediction:
        """Menjalankan inferensi YOLO pada satu frame BGR dan memetakan ke kelas FST."""
        results = self.model.predict(source=frame, verbose=False)
        if not results:
            return FramePrediction(mapped_class="unknown", raw_label="none", confidence=0.0)

        result = results[0]

        if self.task == "classify":
            probs = getattr(result, "probs", None)
            if probs is None:
                return FramePrediction(
                    mapped_class="unknown", raw_label="no_probs", confidence=0.0
                )
            top_idx = int(probs.top1)
            conf = float(probs.top1conf)
            raw_name = str(self.model.names.get(top_idx, str(top_idx)))
            mapped = map_label_to_bin_class(raw_name)
            return FramePrediction(
                mapped_class=mapped,
                raw_label=raw_name,
                confidence=conf,
                bbox_xyxy=None,
            )

        # Mode deteksi objek (yolo11n)
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return FramePrediction(
                mapped_class="unknown", raw_label="no_object", confidence=0.0
            )

        xyxy_arr = boxes.xyxy.cpu().numpy()
        conf_arr = boxes.conf.cpu().numpy()
        cls_arr = boxes.cls.cpu().numpy()

        # Ambil deteksi dengan confidence tertinggi
        best_i = int(conf_arr.argmax())
        x1, y1, x2, y2 = (int(v) for v in xyxy_arr[best_i])
        conf = float(conf_arr[best_i])
        cls_id = int(cls_arr[best_i])
        raw_name = str(self.model.names.get(cls_id, str(cls_id)))
        mapped = map_label_to_bin_class(raw_name)

        return FramePrediction(
            mapped_class=mapped,
            raw_label=raw_name,
            confidence=conf,
            bbox_xyxy=(x1, y1, x2, y2),
        )
