"""
Unit test untuk memastikan pemetaan kelas (waste_mapping.py) dan
majority voting window (yolo_detector.py) bekerja benar tanpa butuh webcam/GPU.
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from waste_mapping import map_label_to_bin_class, to_serial_command
from yolo_detector import FramePrediction, aggregate_window_votes


class TestVisionLogic(unittest.TestCase):
    def test_mapping_kaggle_and_common_labels(self) -> None:
        self.assertEqual(map_label_to_bin_class("O"), "organic")
        self.assertEqual(map_label_to_bin_class("Organic"), "organic")
        self.assertEqual(map_label_to_bin_class("sisa makanan"), "organic")
        self.assertEqual(map_label_to_bin_class("R"), "inorganic")
        self.assertEqual(map_label_to_bin_class("plastic-bottle"), "inorganic")
        self.assertEqual(map_label_to_bin_class("objek_asing_xyz"), "unknown")

    def test_serial_commands(self) -> None:
        self.assertEqual(to_serial_command("organic"), "CLS:organic")
        self.assertEqual(to_serial_command("inorganic"), "CLS:inorganic")
        self.assertEqual(to_serial_command("unknown"), "CLS:unknown")

    def test_majority_vote_passes_organic(self) -> None:
        frames = [
            FramePrediction("organic", "O", 0.85),
            FramePrediction("organic", "O", 0.78),
            FramePrediction("organic", "O", 0.82),
            FramePrediction("inorganic", "R", 0.65),
        ]
        res = aggregate_window_votes(frames, min_confidence=0.60, min_majority_ratio=0.60)
        self.assertEqual(res.final_class, "organic")
        self.assertAlmostEqual(res.vote_ratio, 0.75)

    def test_low_confidence_returns_unknown(self) -> None:
        frames = [
            FramePrediction("inorganic", "R", 0.45),
            FramePrediction("inorganic", "R", 0.50),
            FramePrediction("inorganic", "R", 0.48),
        ]
        res = aggregate_window_votes(frames, min_confidence=0.60, min_majority_ratio=0.60)
        self.assertEqual(res.final_class, "unknown")

    def test_split_vote_below_majority_returns_unknown(self) -> None:
        frames = [
            FramePrediction("organic", "O", 0.90),
            FramePrediction("inorganic", "R", 0.90),
            FramePrediction("unknown", "none", 0.10),
        ]
        res = aggregate_window_votes(frames, min_confidence=0.60, min_majority_ratio=0.60)
        self.assertEqual(res.final_class, "unknown")


if __name__ == "__main__":
    unittest.main()
