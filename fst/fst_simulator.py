"""
Simulator Finite State Transducer (Mesin Mealy) - Sumber Kebenaran Python.
Memuat fst_definition.json dan memverifikasi seluruh transisi, prioritas,
serta penanganan input tidak valid tanpa membutuhkan perangkat keras.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

DEFAULT_DEFINITION_PATH = Path(__file__).with_name("fst_definition.json")


@dataclass(frozen=True)
class TransitionRule:
    """Representasi satu baris pada Tabel Transisi Mealy."""

    from_state: str
    input_symbol: str
    outputs: tuple[str, ...]
    to_state: str
    waste_type: Optional[str] = None
    note: str = ""


@dataclass(frozen=True)
class StepResult:
    """Hasil eksekusi satu langkah transisi FST."""

    from_state: str
    input_symbol: str
    outputs: tuple[str, ...]
    to_state: str
    valid_transition: bool
    waste_type: Optional[str] = None
    note: str = ""

    def format_arrow(self) -> str:
        """Format log standar: [q0] --p / s_Buka--> [q1]."""
        out_text = ", ".join(self.outputs) if self.outputs else "(diabaikan)"
        return f"[{self.from_state}] --{self.input_symbol} / {out_text}--> [{self.to_state}]"


class MealyFST:
    """Implementasi Finite State Transducer tipe Mesin Mealy berbasis tabel."""

    def __init__(self, definition_path: Path = DEFAULT_DEFINITION_PATH) -> None:
        with definition_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        self.definition = data
        self.initial_state: str = data["initial_state"]
        self.current_state: str = self.initial_state
        self.states: dict[str, dict] = data["states"]
        self.valid_inputs: set[str] = set(data["inputs"].keys())
        self.priority_rules: dict[str, list[str]] = data["priority_rules"]

        # Bangun tabel lookup (state, input) -> TransitionRule
        self.transition_table: dict[tuple[str, str], TransitionRule] = {}
        for item in data["transitions"]:
            rule = TransitionRule(
                from_state=item["from_state"],
                input_symbol=item["input"],
                outputs=tuple(item["outputs"]),
                to_state=item["to_state"],
                waste_type=item.get("waste_type"),
                note=item.get("note", ""),
            )
            self.transition_table[(rule.from_state, rule.input_symbol)] = rule

    def reset(self) -> None:
        """Mengembalikan mesin ke state awal q0."""
        self.current_state = self.initial_state

    def resolve_priority(self, simultaneous_inputs: Iterable[str]) -> Optional[str]:
        """
        Memilih satu input dengan prioritas tertinggi sesuai state saat ini.
        Contoh: di q0 jika ['f', 'p'] muncul bersamaan, 'f' menang.
        Di qF, input 'p' dan 'w' tidak masuk daftar prioritas sehingga diabaikan.
        """
        input_set = set(simultaneous_inputs)
        if not input_set:
            return None

        order = self.priority_rules.get(self.current_state, [])
        for candidate in order:
            if candidate in input_set:
                return candidate

        # Jika tidak ada dalam prioritas state saat ini, ambil elemen pertama yang dikenal
        for raw in simultaneous_inputs:
            if raw in self.valid_inputs:
                return raw
        return None

    def step(self, input_symbol: str) -> StepResult:
        """
        Memproses satu input pada state saat ini berdasarkan Tabel Mealy.
        Input yang tidak valid pada state tertentu diabaikan dengan aman tanpa crash.
        """
        from_state = self.current_state
        rule = self.transition_table.get((from_state, input_symbol))

        if rule is None:
            # Tidak ada transisi untuk (state, input) ini -> tetap di state sekarang
            reason = (
                "tidak ada pengguna (tetap siaga)"
                if input_symbol == "p'"
                else f"input '{input_symbol}' diabaikan pada state {from_state}"
            )
            return StepResult(
                from_state=from_state,
                input_symbol=input_symbol,
                outputs=(),
                to_state=from_state,
                valid_transition=False,
                waste_type=None,
                note=reason,
            )

        # Transisi sah: jalankan output Mealy lalu pindah ke state berikut
        self.current_state = rule.to_state
        return StepResult(
            from_state=from_state,
            input_symbol=input_symbol,
            outputs=rule.outputs,
            to_state=rule.to_state,
            valid_transition=True,
            waste_type=rule.waste_type,
            note=rule.note,
        )

    def step_simultaneous(self, inputs: Union[str, Iterable[str]]) -> StepResult:
        """Memproses satu input tunggal atau sekumpulan input simultan."""
        if isinstance(inputs, str):
            chosen = inputs
        else:
            chosen = self.resolve_priority(inputs)
            if chosen is None:
                return StepResult(
                    from_state=self.current_state,
                    input_symbol="none",
                    outputs=(),
                    to_state=self.current_state,
                    valid_transition=False,
                    note="tidak ada input aktif",
                )
        return self.step(chosen)

    def run_sequence(self, sequence: Iterable[Union[str, Iterable[str]]]) -> list[StepResult]:
        """Menjalankan serangkaian input berurutan dan mengembalikan daftar hasil."""
        return [self.step_simultaneous(item) for item in sequence]


def get_mandatory_scenarios() -> list[tuple[str, list[Union[str, list[str]]]]]:
    """Daftar 7 skenario pengujian wajib sesuai spesifikasi tugas."""
    return [
        ("1. Jalur Normal Organik", ["p", "delay", "o"]),
        ("2. Jalur Normal Anorganik", ["p", "delay", "a"]),
        ("3. Force Open dari Dashboard (w)", ["w", "delay", "o"]),
        ("4. Keranjang Penuh (qF mengabaikan p & w, pulih dg n)", ["f", "p", "w", "n"]),
        ("5. Klasifikasi Gagal / Tidak Yakin (u)", ["p", "delay", "u"]),
        ("6. Prioritas Simultan di q0 (f + p bersamaan)", [["f", "p"], "n"]),
        ("7. Input Tidak Valid di State Tertentu (o di q0, delay di q0)", ["o", "delay", "x"]),
    ]


def print_test_table() -> None:
    """Menjalankan semua skenario uji dan mencetak tabel input -> output -> state."""
    fst = MealyFST()
    print("=" * 92)
    print("HASIL VERIFIKASI FINITE STATE TRANSDUCER (MESIN MEALY)")
    print("=" * 92)

    for title, seq in get_mandatory_scenarios():
        fst.reset()
        print(f"\n>>> {title} (Mulai: {fst.current_state})")
        print(f"{'State Awal':<12} | {'Input':<14} | {'Output':<24} | {'State Akhir':<11} | {'Keterangan'}")
        print("-" * 92)
        for item in seq:
            raw_label = "+".join(item) if isinstance(item, list) else item
            res = fst.step_simultaneous(item)
            out_str = ", ".join(res.outputs) if res.outputs else "-"
            print(
                f"{res.from_state:<12} | {raw_label:<14} | {out_str:<24} | {res.to_state:<11} | {res.note}"
            )


def run_interactive() -> None:
    """Mode interaktif terminal untuk mencoba FST langkah demi langkah."""
    fst = MealyFST()
    print("Simulator Interaktif FST Mealy (ketik 'exit' untuk keluar, 'reset' untuk kembali ke q0)")
    print("Input valid: f, n, p, p', w, o, a, delay, u | Input simultan dipisah koma, mis: f,p")
    while True:
        try:
            raw = input(f"\n[{fst.current_state}] Masukkan input> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSelesai.")
            break

        if not raw:
            continue
        if raw.lower() == "exit":
            break
        if raw.lower() == "reset":
            fst.reset()
            print("State direset ke [q0].")
            continue

        parts = [part.strip() for part in raw.split(",") if part.strip()]
        res = fst.step_simultaneous(parts[0] if len(parts) == 1 else parts)
        print(f"Log Transisi : {res.format_arrow()}")
        if res.note:
            print(f"Catatan      : {res.note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulator FST Mealy Tempat Sampah Pintar")
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Jalankan 7 skenario pengujian wajib dan tampilkan tabel transisi",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Jalankan mode interaktif di terminal",
    )
    args = parser.parse_args()

    if args.interactive:
        run_interactive()
    else:
        print_test_table()


if __name__ == "__main__":
    main()
