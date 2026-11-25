# Panduan Wiring, Catu Daya, Kalibrasi, dan Troubleshooting (Tahap E)

## 1. Tabel Pin Default ESP32 (`firmware/smart_bin_fst/config.h`)

| Komponen | Pin Komponen | Pin ESP32 (GPIO) | Keterangan |
|---|---|---|---|
| Ultrasonik 1 (Pengguna) | `TRIG` | `GPIO 13` | Output trigger |
| Ultrasonik 1 (Pengguna) | `ECHO` | `GPIO 12` | Input echo (pakai pembagi tegangan 5V -> 3.3V) |
| Ultrasonik 2 (Organik) | `TRIG` | `GPIO 14` | Output trigger |
| Ultrasonik 2 (Organik) | `ECHO` | `GPIO 27` | Input echo (pakai pembagi tegangan 5V -> 3.3V) |
| Ultrasonik 3 (Anorganik) | `TRIG` | `GPIO 26` | Output trigger |
| Ultrasonik 3 (Anorganik) | `ECHO` | `GPIO 25` | Input echo (pakai pembagi tegangan 5V -> 3.3V) |
| Servo 1 (Tutup Utama) | `Signal (Oranye/Kuning)` | `GPIO 18` | PWM 50 Hz (`0°` tutup, `90°` buka) |
| Servo 2 (Papan Pengarah) | `Signal (Oranye/Kuning)` | `GPIO 19` | PWM 50 Hz (`90°` netral, `30°` kiri, `150°` kanan) |
| LED Merah (Indikator Penuh) | `Anoda (+)` | `GPIO 2` | Seri resistor `220 Ohm` ke `GND` |

> Catatan: Semua pin dapat diubah di `firmware/smart_bin_fst/config.h`. Catatan khusus `GPIO 12` pada beberapa board ESP32 tidak boleh ditarik HIGH saat boot; pada HC-SR04 normal kondisi idle `ECHO` adalah LOW sehingga aman, namun jika ingin ekstra aman saat upload/boot, Anda dapat memindahkan `PIN_US_USER_ECHO` ke `GPIO 34` atau `GPIO 35` (input-only).

---

## 2. Diagram Wiring (Teks/Tabel) & Catatan Catu Daya (PENTING)

```text
[Adaptor 5V >= 2A] ──(+5V)──> Rel +5V Servo 1, Servo 2, dan VCC HC-SR04 (1, 2, 3)
                   └──(GND)───> Rel GND bersama (WAJIB tersambung ke GND ESP32!)

[Laptop / PC] <════(Kabel USB Data)════> [ESP32]
  (Webcam USB terpasang di Laptop, BUKAN di ESP32)

Pembagi Tegangan untuk setiap pin ECHO HC-SR04 (karena output HC-SR04 5V, GPIO ESP32 3.3V):
  ECHO HC-SR04 ──[Resistor 1 kOhm]──┬──> GPIO ECHO ESP32
                                    └──[Resistor 2 kOhm]──> GND
```

**Catatan Daya Wajib Diperhatikan Mahasiswa:**
1. **Jangan catu Servo 1 dan Servo 2 dari pin `VIN`/`3V3` ESP32!** Saat dua servo bergerak bersamaan atau tertahan beban tutup/sampah, lonjakan arusnya dapat melebihi `1 A`, menyebabkan ESP32 *brownout* (restart terus-menerus) atau gagal kirim WiFi.
2. **Gunakan adaptor/PSU eksternal `5V` minimal `2A`** (atau modul buck converter `LM2596` disetel ke `5.0V`) khusus untuk jalur VCC Servo.
3. **Common Ground (GND Bersama) wajib terhubung**: kutub negatif (`-`) adaptor 5V eksternal HARUS dihubungkan ke pin `GND` ESP32 agar sinyal PWM servo memiliki referensi tegangan yang sama.

---

## 3. Panduan Kalibrasi

### A. Sensor Ultrasonik & Tinggi Keranjang (`H`)
- Ukur tinggi efektif bagian dalam keranjang dari permukaan bawah sampai jarak aman di bawah sensor tutup, lalu isi `BIN_HEIGHT_CM` di `config.h` (default `40.0f` cm).
- Rumus keterisian:
  $$L = \frac{H - d}{H} \times 100\%$$
  Contoh dengan `H = 40 cm`:
  - Kosong (`d = 40 cm`) -> $L = 0\%$
  - Terisi separuh (`d = 20 cm`) -> $L = 50\%$
  - Batas penuh (`d < 5 cm`) -> $L > 87,5\%$ dan memicu input `f`.

### B. Sudut Servo 1 & Servo 2
1. Lepas lengan (horn) plastik servo terlebih dahulu, nyalakan ESP32 agar masuk posisi awal (`Servo 1 = 0°`, `Servo 2 = 90°`), lalu pasang lengan servo tepat pada posisi menutup / tengah.
2. Uji bertahap dengan mengubah `SERVO_LID_OPEN_DEG` (`90`), `SERVO_SORT_ORGANIC_DEG` (`30`), dan `SERVO_SORT_INORGANIC_DEG` (`150`) di `config.h` agar papan tidak membentur dinding tempat sampah.
3. Sesuaikan `DROP_HOLD_DURATION_MS` (`1500` ms) jika sampah basah butuh waktu sedikit lebih lama untuk meluncur dari papan pengarah.

### C. Ambang Confidence & Window YOLO (`vision/.env`)
- `CONFIDENCE_THRESHOLD=0.60`: nilai awal yang seimbang. Naikkan ke `0.70` jika sering salah tebak pada objek meragukan (lebih sering masuk residu `u`); turunkan ke `0.50` jika pencahayaan redup membuat skor turun.
- `MAJORITY_RATIO=0.60`: minimal 60% frame selama `CLASSIFY_WINDOW_SEC=1.5` detik harus sepakat sebelum mengirim `CLS:organic` atau `CLS:inorganic`.
- Pastikan `CLASSIFY_WINDOW_SEC` (`1.5` detik) jauh lebih singkat dari `CLASSIFY_TIMEOUT_MS` di ESP32 (`6000` ms) agar jawaban laptop selalu tiba sebelum timeout `u`.

---

## 4. Troubleshooting Umum

| Masalah | Penyebab Umum | Solusi |
|---|---|---|
| Port serial tidak muncul / Permission denied | Driver CH340/CP2102 belum terpasang atau port sedang dipakai Serial Monitor | Tutup Serial Monitor Arduino IDE sebelum menjalankan `vision/main.py` (hanya 1 program boleh buka port serial). Di Linux jalankan `sudo usermod -aG dialout $USER`. |
| `Webcam pada index 0 tidak ditemukan` | Webcam internal laptop vs webcam USB berbeda index | Coba ubah `WEBCAM_INDEX=1` atau `2` di `vision/.env`. Pastikan izin kamera OS (macOS/Windows) aktif untuk terminal. |
| ESP32 selalu memicu `qF` padahal kosong | Kabel ECHO/TRIG terbalik atau sensor belum terpasang | Uji dulu dengan `SIMULATION_MODE = true` di `config.h`. Periksa sambungan pembagi tegangan ECHO dan VCC 5V sensor. |
| WiFi putus atau HTTP gagal ke Supabase | SSID/password salah, WiFi 5 GHz (ESP32 hanya mendukung **2.4 GHz**), atau URL ada `/` di akhir | Gunakan hotspot/router **2.4 GHz**. Pastikan `SUPABASE_URL` di `secrets.h` tidak berakhiran `/`. |
| Dashboard kosong / error RLS di browser | Belum login atau policy RLS / seed belum dijalankan | Pastikan sudah menjalankan `01_schema.sql`, `02_rls_and_realtime.sql`, dan `03_seed.sql`, lalu login menggunakan akun di `/login`. |
| Error `401/403` saat ESP32 POST ke Supabase | Memakai `service_role` salah tempat atau header `Prefer: return=minimal` hilang | Pastikan `secrets.h` memakai `anon` key dan `02_rls_and_realtime.sql` sudah dijalankan. |
