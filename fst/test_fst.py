"""
Suite unit test untuk memverifikasi seluruh aturan Finite State Transducer (Mesin Mealy).
Jalankan: python3 -m unittest discover -s fst -p "test_*.py" -v
"""

import unittest
from pathlib import Path
import sys

# Pastikan direktori fst/ berada di sys.path saat dijalankan dari root proyek
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fst_simulator import MealyFST


class TestMealyFST(unittest.TestCase):
    def setUp(self) -> None:
        self.fst = MealyFST()

    def test_01_jalur_normal_organik(self) -> None:
        """q0 -p-> q1 -delay-> q2 -o-> q0"""
        results = self.fst.run_sequence(["p", "delay", "o"])
        self.assertEqual([r.to_state for r in results], ["q1", "q2", "q0"])
        self.assertEqual(results[0].outputs, ("s_Buka",))
        self.assertEqual(results[1].outputs, ("s_Tutup",))
        self.assertEqual(results[2].outputs, ("m_Kiri", "c_Sync"))
        self.assertEqual(results[2].waste_type, "organic")

    def test_02_jalur_normal_anorganik(self) -> None:
        """q0 -p-> q1 -delay-> q2 -a-> q0"""
        results = self.fst.run_sequence(["p", "delay", "a"])
        self.assertEqual([r.to_state for r in results], ["q1", "q2", "q0"])
        self.assertEqual(results[0].outputs, ("s_Buka",))
        self.assertEqual(results[1].outputs, ("s_Tutup",))
        self.assertEqual(results[2].outputs, ("m_Kanan", "c_Sync"))
        self.assertEqual(results[2].waste_type, "inorganic")

    def test_03_force_open_dashboard(self) -> None:
        """q0 -w-> q1 -delay-> q2 -o-> q0"""
        results = self.fst.run_sequence(["w", "delay", "o"])
        self.assertEqual([r.to_state for r in results], ["q1", "q2", "q0"])
        self.assertEqual(results[0].outputs, ("s_Buka",))
        self.assertEqual(results[1].outputs, ("s_Tutup",))
        self.assertEqual(results[2].outputs, ("m_Kiri", "c_Sync"))

    def test_04_keranjang_penuh_kunci_dan_pulih(self) -> None:
        """q0 -f-> qF, p dan w diabaikan di qF, qF -n-> q0"""
        r_full = self.fst.step("f")
        self.assertEqual(r_full.to_state, "qF")
        self.assertEqual(r_full.outputs, ("L_Merah", "c_Sync"))

        # Selama di qF, tutup tidak boleh terbuka meskipun ada p atau w
        r_p = self.fst.step("p")
        self.assertFalse(r_p.valid_transition)
        self.assertEqual(r_p.to_state, "qF")
        self.assertEqual(r_p.outputs, ())

        r_w = self.fst.step("w")
        self.assertFalse(r_w.valid_transition)
        self.assertEqual(r_w.to_state, "qF")
        self.assertEqual(r_w.outputs, ())

        # Saat kapasitas aman kembali (n), lampu mati dan kembali ke q0
        r_safe = self.fst.step("n")
        self.assertTrue(r_safe.valid_transition)
        self.assertEqual(r_safe.to_state, "q0")
        self.assertEqual(r_safe.outputs, ("Off_LED", "c_Sync"))

    def test_05_klasifikasi_gagal_ekstensi_u(self) -> None:
        """q2 -u-> q0 mencatat gagal klasifikasi & buang residu m_Kanan"""
        results = self.fst.run_sequence(["p", "delay", "u"])
        last = results[-1]
        self.assertEqual(last.to_state, "q0")
        self.assertEqual(last.outputs, ("c_Sync", "m_Kanan"))
        self.assertEqual(last.waste_type, "unknown")
        self.assertIn("gagal klasifikasi", last.note.lower())

    def test_06_prioritas_f_atas_p_dan_w_di_q0(self) -> None:
        """Ketika f dan p (atau w) muncul bersamaan di q0, hasilnya wajib qF"""
        res_fp = self.fst.step_simultaneous(["p", "f"])
        self.assertEqual(res_fp.input_symbol, "f")
        self.assertEqual(res_fp.to_state, "qF")
        self.assertEqual(res_fp.outputs, ("L_Merah", "c_Sync"))

        self.fst.reset()
        res_fw = self.fst.step_simultaneous(["w", "f"])
        self.assertEqual(res_fw.input_symbol, "f")
        self.assertEqual(res_fw.to_state, "qF")

    def test_07_input_tidak_valid_diabaikan_tanpa_crash(self) -> None:
        """Input yang tidak berlaku pada state tertentu diabaikan dengan aman"""
        for invalid_inp in ["o", "a", "u", "delay", "n", "p'", "tidak_dikenal"]:
            res = self.fst.step(invalid_inp)
            self.assertFalse(res.valid_transition)
            self.assertEqual(res.to_state, "q0")
            self.assertEqual(res.outputs, ())


if __name__ == "__main__":
    unittest.main()
