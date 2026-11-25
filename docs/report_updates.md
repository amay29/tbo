# Perubahan yang Perlu Ditulis di Laporan (Tahap 2)

Dokumen ini merangkum pembaruan formal dari laporan Tahap 1 menuju implementasi Tahap 2 agar konsisten 100% dengan kode dan pengujian.

---

## 1. Revisi Himpunan Input ($\Sigma$)

Sensor material kapasitif pada Tahap 1 digantikan oleh klasifikasi visual webcam berbasis YOLO di laptop/PC, ditambah satu simbol ekstensi untuk penanganan kegagalan klasifikasi:

| Simbol | Arti Input | Sumber Input |
|---|---|---|
| $f$ | Salah satu atau kedua keranjang penuh ($d < 5\text{ cm}$) | Ultrasonik 2 / 3 (ESP32) |
| $n$ | Kapasitas kedua keranjang aman ($d \ge 5\text{ cm}$) | Ultrasonik 2 & 3 (ESP32) |
| $p$ | Pengguna terdeteksi ($d < 30\text{ cm}$) | Ultrasonik 1 (ESP32) |
| $p'$ | Tidak ada pengguna ($d \ge 30\text{ cm}$) | Ultrasonik 1 (ESP32) |
| $w$ | Perintah *Force Open* dari Web Dashboard | Supabase `bin_commands` |
| $o$ | Objek terklasifikasi **organik** (`CLS:organic`) | Laptop (YOLO + Webcam) via USB Serial |
| $a$ | Objek terklasifikasi **anorganik** (`CLS:inorganic`) | Laptop (YOLO + Webcam) via USB Serial |
| $delay$ | Timer tutup terbuka habis (default $5\text{ detik}$) | Timer `millis()` (ESP32) |
| $u$ *(Ekstensi)* | Klasifikasi gagal / confidence rendah / tidak ada objek / timeout $6\text{ detik}$ (`CLS:unknown`) | Laptop atau Timeout `q2` (ESP32) |

---

## 2. Revisi Himpunan Output ($\Delta$)

| Simbol | Aksi Output |
|---|---|
| `c_Sync` | HTTP POST/PATCH status dan riwayat kejadian ke Supabase REST API |
| `s_Buka` | Servo 1 tutup utama bergerak ke $90^\circ$ (buka) |
| `s_Tutup` | Servo 1 tutup utama bergerak ke $0^\circ$ (tutup) |
| `m_Kiri` | Servo 2 papan pengarah miring ke wadah organik, jeda $1{,}5\text{ detik}$, lalu kembali netral ($90^\circ$) |
| `m_Kanan` | Servo 2 papan pengarah miring ke wadah anorganik, jeda $1{,}5\text{ detik}$, lalu kembali netral ($90^\circ$) |
| `L_Merah` | LED merah indikator penuh menyala |
| `Off_LED` | LED merah indikator penuh mati |

---

## 3. Revisi Tabel Transisi dan Output Mealy ($\delta$ & $\lambda$)

| State Saat Ini | Input | Output ($\lambda$) | State Berikut ($\delta$) | Catatan |
|---|---|---|---|---|
| `q0` (Siaga) | `f` | `L_Merah`, `c_Sync` | `qF` | Prioritas utama: `p` dan `w` diabaikan bila `f` aktif |
| `q0` (Siaga) | `p` | `s_Buka` | `q1` | Tutup dibuka karena ada pengguna |
| `q0` (Siaga) | `w` | `s_Buka` | `q1` | Tutup dibuka oleh admin dashboard |
| `q1` (Tutup Terbuka) | `delay` | `s_Tutup` | `q2` | Menutup dan meminta klasifikasi visual |
| `q2` (Memilah) | `o` | `m_Kiri`, `c_Sync` | `q0` | Papan miring kiri lalu netral sebelum `q0` |
| `q2` (Memilah) | `a` | `m_Kanan`, `c_Sync` | `q0` | Papan miring kanan lalu netral sebelum `q0` |
| `q2` (Memilah) | `u` *(ekstensi)* | `c_Sync` ("gagal klasifikasi"), `m_Kanan` | `q0` | Servo 2 netral saat catat log gagal, lalu buang residu ke anorganik & kembali netral |
| `qF` (Penuh) | `n` | `Off_LED`, `c_Sync` | `q0` | Tutup terkunci atas `p` & `w` selama di `qF` |

---

## 4. Revisi Diagram State & Bab Metode

- **Diagram State**: Gunakan diagram Mermaid di `docs/end_to_end_verification.md` (menambahkan transisi berlabel `u / c_Sync (gagal klasifikasi), m_Kanan` dari `q2` ke `q0`).
- **Bab Metode (Perubahan Arsitektur Perangkat Keras & Lunak)**:
  1. **Subsistem Kendali (ESP32)**: Menjalankan FST Mealy berbasis tabel transisi deterministik, membaca 3 sensor ultrasonik dengan filter median 5 sampel untuk meredam noise, menghitung keterisian $L = \frac{H-d}{H}\times 100\%$, mengendalikan 2 servo secara non-blocking (`millis()`), dan menyinkronkan data ke Supabase lewat WiFi.
  2. **Subsistem Klasifikasi Visual (Laptop/PC + Webcam USB)**: Menggantikan sensor kapasitif. Webcam diarahkan ke papan pengarah. Saat ESP32 memasuki `q2` dan mengirim `STATE:q2`, program Python menjalankan inferensi model **Ultralytics YOLO11 (`yolo11n-cls`)** selama jendela waktu $1{,}5\text{ detik}$, menerapkan *majority voting* ($\ge 60\%$ frame sepakat dan rata-rata confidence $\ge 0{,}60$), lalu mengirim `CLS:organic`, `CLS:inorganic`, atau `CLS:unknown` kembali ke ESP32 melalui USB Serial (`115200 baud`).
  3. **Subsistem Pemantauan (Supabase & Web Dashboard Next.js)**: Menyimpan status terkini (`bin_status`), riwayat transisi (`bin_events`), dan antrean perintah (`bin_commands`) yang dilindungi Row Level Security (RLS) dan diperbarui ke browser admin secara real-time melalui Supabase Realtime.

---

## 5. Keterbatasan Sistem (Penting untuk Bab Pembahasan)

1. **Ketergantungan Pencahayaan dan Latar Belakang**: Akurasi klasifikasi YOLO sangat dipengaruhi intensitas cahaya di atas papan pengarah dan bayangan tutup tempat sampah; dibutuhkan pencahayaan yang cukup stabil agar confidence tidak turun di bawah ambang.
2. **Keterbatasan Dataset dan Generalisasi Objek**: Model bergantung pada variasi sampah di dataset latih (Kaggle *Waste Classification data* dan foto webcam lokal). Jenis kemasan atau limbah baru yang belum pernah dilatih berpotensi memicu kelas `unknown` (`u`).
3. **Objek Campuran atau Bertumpuk**: Pendekatan klasifikasi gambar tunggal (`yolo11n-cls`) mengasumsikan pengguna memasukkan satu objek pada satu waktu. Apabila sampah organik dan anorganik masuk bersamaan dan bertumpuk, model hanya memilih kelas yang paling dominan secara visual.
4. **Penanganan Residu pada Input `u`**: Saat klasifikasi gagal (`u`) atau terjadi timeout komunikasi serial selama $6\text{ detik}$, sistem mengambil langkah aman (*fail-safe*) dengan mengarahkan objek sebagai residu ke wadah anorganik (`m_Kanan`) agar papan pengarah tidak macet untuk pengguna berikutnya.
5. **Ketergantungan Jaringan WiFi**: Apabila koneksi WiFi terputus, logika FST lokal pada ESP32 tetap berjalan normal, namun sinkronisasi `c_Sync` dan perintah `Force Open` dari dashboard tertunda sampai WiFi tersambung kembali.

---

## 6. Daftar Pustaka Tambahan

1. Jocher, G., Qiu, J., & Chaurasia, A. (2023–2024). *Ultralytics YOLO11* [Perangkat Lunak Visi Komputer]. Tersedia di: https://github.com/ultralytics/ultralytics
2. Sekar, S. (`techsash`). *Waste Classification data (Organic and Recyclable Solid Waste Images)* [Dataset]. Kaggle. Tersedia di: https://www.kaggle.com/datasets/techsash/waste-classification-data
3. Proença, P. F., & Simões, P. (2020). *TACO: Trash Annotations in Context for Litter Detection*. arXiv preprint arXiv:2003.06975. (Referensi pembanding untuk pendekatan deteksi objek).
4. Supabase Inc. *Supabase Documentation: Row Level Security, Realtime, and REST API*. Tersedia di: https://supabase.com/docs
5. Vercel Inc. *Next.js App Router Documentation*. Tersedia di: https://nextjs.org/docs
