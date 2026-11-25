# Tempat Sampah Pintar Berbasis Finite State Transducer (FST Mealy) — Tahap 2

Implementasi **Tahap 2** proyek mata kuliah **Teori Bahasa dan Automata** dengan arsitektur:
`Webcam USB -> Python + YOLO11 (Laptop) -> USB Serial (115200 baud) -> ESP32 (FST Mealy) -> WiFi HTTP -> Supabase <-> Web Dashboard Next.js (Realtime)`

## Struktur Proyek

```text
pbo_project/
├── fst/                          # Tahap A: Sumber kebenaran FST & simulator Python
│   ├── fst_definition.json
│   ├── fst_simulator.py
│   └── test_fst.py
├── supabase/                     # Tahap B: Skema SQL, RLS, Realtime, Seed
│   ├── 01_schema.sql
│   ├── 02_rls_and_realtime.sql
│   ├── 03_seed.sql
│   ├── README.md
│   └── optional_edge_function/device-sync/index.ts
├── web/                          # Tahap B: Web Dashboard Next.js + Tailwind CSS
│   ├── .env.local.example
│   └── src/
├── firmware/                     # Tahap C: Firmware ESP32 (PlatformIO & Arduino IDE)
│   ├── platformio.ini
│   └── smart_bin_fst/
│       ├── config.h
│       ├── fst_table.h
│       ├── secrets.example.h
│       └── smart_bin_fst.ino
├── vision/                       # Tahap D: Modul terpisah Webcam, YOLO11, & Serial
│   ├── .env.example
│   ├── requirements.txt
│   ├── waste_mapping.py
│   ├── camera_handler.py
│   ├── yolo_detector.py
│   ├── serial_bridge.py
│   ├── prepare_dataset.py
│   ├── capture_images.py
│   ├── data.yaml
│   ├── train.py
│   ├── main.py
│   └── test_vision.py
└── docs/                         # Tahap E & Bahan Revisi Laporan
    ├── wiring_and_calibration.md
    ├── end_to_end_verification.md
    └── report_updates.md
```

## Urutan Menjalankan & Verifikasi Cepat

1. **Tahap A (Simulator & Unit Test FST)**:
   ```bash
   python3 -m unittest discover -s fst -p "test_*.py" -v
   python3 fst/fst_simulator.py --run-tests
   ```
2. **Tahap B (Supabase & Next.js Dashboard)**:
   - Jalankan `supabase/01_schema.sql`, `02_rls_and_realtime.sql`, `03_seed.sql` di Supabase SQL Editor.
   - Buat akun admin di **Supabase Authentication -> Users**.
   - Salin `web/.env.local.example` -> `web/.env.local`, isi URL & anon key, lalu jalankan:
     ```bash
     cd web
     npm install
     npm run dev
     ```
3. **Tahap C (Firmware ESP32)**:
   - Salin `firmware/smart_bin_fst/secrets.example.h` -> `secrets.h` dan isi WiFi + Supabase.
   - Buka `firmware/smart_bin_fst/smart_bin_fst.ino` di Arduino IDE (instal library `ESP32Servo` & `ArduinoJson`) atau buka folder `firmware/` di PlatformIO.
   - Untuk uji tanpa sensor fisik, ubah `SIMULATION_MODE` ke `true` di `config.h` dan kirim `SIM:p`, `SIM:delay`, `SIM:o`, dll. lewat Serial Monitor (`115200 baud`).
4. **Tahap D (YOLO + Webcam + Serial)**:
   ```bash
   cd vision
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   python3 -m unittest test_vision.py -v
   ```
   Lalu ikuti `docs/end_to_end_verification.md` untuk capture dataset (`capture_images.py`), training (`train.py`), dan runtime (`python3 main.py`).
