# Setup Supabase (Tahap B)

## 1. Membuat Proyek & Menjalankan SQL
1. Buat proyek baru di [Supabase](https://supabase.com/).
2. Buka **SQL Editor** dan jalankan secara berurutan:
   1. `01_schema.sql`
   2. `02_rls_and_realtime.sql`
   3. `03_seed.sql`
3. Buka **Authentication -> Users -> Add user -> Create new user**, buat akun admin (email + password) yang akan dipakai login di halaman `/login` dashboard Next.js. (Matikan opsi "Confirm email" atau centang "Auto Confirm User" agar langsung bisa dipakai login).
4. Buka **Project Settings -> API**, salin:
   - **Project URL** (`NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_URL`)
   - **anon public key** (`NEXT_PUBLIC_SUPABASE_ANON_KEY` / `SUPABASE_ANON_KEY`)
   > **PERINGATAN KEAMANAN**: Jangan pernah menyalin `service_role` key ke kode ESP32 maupun file `.env.local` Next.js di sisi browser!

---

## 2. Perbandingan Keamanan ESP32 <-> Supabase

Untuk komunikasi antara ESP32 dan database, ada dua pendekatan yang bisa dipilih:

### Opsi A (Default Proyek Ini): RLS Terbatas + `anon` Key langsung ke REST API
- **Cara kerja**: ESP32 memanggil REST endpoint `/rest/v1/bin_status`, `/rest/v1/bin_events`, dan `/rest/v1/bin_commands` memakai `anon` key.
- **Kelebihan**:
  - Paling sederhana untuk mahasiswa: tidak perlu deploy Deno CLI atau Edge Function.
  - Tetap aman untuk **baca data dashboard**, karena `SELECT` pada `bin_status` dan `bin_events` **hanya diizinkan untuk `authenticated`** (admin yang sudah login). Pengunjung tanpa login tidak bisa melihat isi dashboard maupun riwayat tempat sampah.
- **Kekurangan (Jujur)**:
  - `anon` key bersifat publik (atau tertanam di flash ESP32). Jika seseorang membongkar `anon` key dan tahu struktur tabel, secara teori ia bisa mengirim request `INSERT` palsu ke `bin_events` atau `UPDATE` ke `bin_status` dari luar perangkat.

### Opsi B (Untuk Produksi / Nilai Plus): Edge Function + `x-device-key`
- **Cara kerja**: Gunakan contoh file `optional_edge_function/device-sync/index.ts`. ESP32 hanya memanggil Edge Function tersebut sambil menyertakan header rahasia `x-device-key` (disimpan di `secrets.h`), sementara `SUPABASE_SERVICE_ROLE_KEY` hanya tersimpan aman di server Edge Function Supabase. Tabel `bin_status` dan `bin_events` tidak perlu memberi izin tulis apa pun ke `anon`.
- **Kelebihan**: Tidak ada akses tulis publik dari internet tanpa `x-device-key` yang valid.
- **Kekurangan**: Perlu setup Supabase CLI untuk deploy Edge Function dan mengganti endpoint HTTP di firmware ESP32.
