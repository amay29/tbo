#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// KONFIGURASI PERANGKAT KERAS & PARAMETER FST ESP32
// Ubah nilai konstanta di bawah ini sesuai rangkaian dan ukuran keranjang Anda.
// ============================================================================

// Mode simulasi:
// true  = Uji FST lewat Serial Monitor / skrip Python tanpa sensor & servo nyata
// false = Gunakan sensor ultrasonik dan servo fisik (mode operasi normal)
#define SIMULATION_MODE false

// Serial & timing utama
constexpr unsigned long SERIAL_BAUD = 115200;
constexpr unsigned long SENSOR_POLL_INTERVAL_MS = 200;     // Interval baca ultrasonik
constexpr unsigned long LID_OPEN_DURATION_MS = 5000;       // Konstanta delay di q1 (default 5 detik)
constexpr unsigned long DROP_HOLD_DURATION_MS = 1500;      // Jeda lepas sampah di posisi miring (1,5 detik)
constexpr unsigned long SERVO_SETTLE_MS = 350;             // Jeda singkat kembali ke posisi netral
constexpr unsigned long CLASSIFY_TIMEOUT_MS = 6000;        // Timeout tunggu jawaban YOLO di q2 (6 detik -> u)
constexpr unsigned long SUPABASE_POLL_INTERVAL_MS = 2000;  // Polling perintah Force Open tiap 2 detik
constexpr unsigned long WIFI_RECONNECT_INTERVAL_MS = 10000;// Coba sambung ulang WiFi tiap 10 detik

// Pin Sensor Ultrasonik (HC-SR04)
// Catatan ESP32: GPIO 34, 35, 36, 39 adalah input-only, cocok untuk ECHO.
constexpr int PIN_US_USER_TRIG = 13;
constexpr int PIN_US_USER_ECHO = 12;

constexpr int PIN_US_ORG_TRIG = 14;
constexpr int PIN_US_ORG_ECHO = 27;

constexpr int PIN_US_INORG_TRIG = 26;
constexpr int PIN_US_INORG_ECHO = 25;

// Pin Aktuator & Indikator
constexpr int PIN_SERVO_LID = 18;   // Servo 1: tutup utama
constexpr int PIN_SERVO_SORT = 19;  // Servo 2: papan pengarah
constexpr int PIN_LED_FULL = 2;     // LED merah indikator penuh (bisa pakai LED eksternal + resistor 220 ohm)

// Parameter Kalibrasi Ultrasonik
constexpr float BIN_HEIGHT_CM = 40.0f;       // H: tinggi efektif keranjang (cm)
constexpr float FULL_THRESHOLD_CM = 5.0f;    // Jarak < 5 cm dianggap penuh (input f)
constexpr float USER_DETECT_CM = 30.0f;      // Jarak < 30 cm mendeteksi pengguna (input p)
constexpr int ULTRASONIC_SAMPLES = 5;        // Jumlah sampel untuk filter median (3-5 sampel)
constexpr unsigned long ULTRASONIC_TIMEOUT_US = 30000UL;

// Parameter Sudut Servo (derajat 0 - 180)
constexpr int SERVO_LID_CLOSE_DEG = 0;       // Tutup utama tertutup
constexpr int SERVO_LID_OPEN_DEG = 90;       // Tutup utama terbuka

constexpr int SERVO_SORT_NEUTRAL_DEG = 90;   // Papan pengarah netral/tengah
constexpr int SERVO_SORT_ORGANIC_DEG = 30;   // Miring ke kiri (wadah organik)
constexpr int SERVO_SORT_INORGANIC_DEG = 150;// Miring ke kanan (wadah anorganik)

#endif
