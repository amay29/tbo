#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>

#include "config.h"
#include "fst_table.h"

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #include "secrets.example.h"
  #warning "secrets.h tidak ditemukan, memakai nilai placeholder dari secrets.example.h"
#endif

// ============================================================================
// OBJEK PERANGKAT KERAS & VARIABEL GLOBAL
// ============================================================================

Servo servoLid;   // Servo 1: tutup utama
Servo servoSort;  // Servo 2: papan pengarah

State currentState = STATE_Q0;

// Pengukuran sensor ultrasonik terbaru
float organicDistCm = BIN_HEIGHT_CM;
float inorganicDistCm = BIN_HEIGHT_CM;
float userDistCm = 100.0f;
float organicFillPct = 0.0f;
float inorganicFillPct = 0.0f;
const char* lastWasteType = nullptr;  // "organic", "inorganic", "unknown", atau nullptr

// Timer non-blocking berbasis millis()
unsigned long lastSensorPollMs = 0;
unsigned long q1StartMs = 0;
unsigned long q2StartMs = 0;
unsigned long lastSupabasePollMs = 0;
unsigned long lastWifiAttemptMs = 0;

// Antrean input dari serial dan web command
Input pendingSerialInput = INPUT_NONE;
bool pendingWebForceOpen = false;
String serialLineBuffer = "";

// State internal untuk jeda non-blocking servo 2 (lepas sampah 1,5 detik -> netral -> q0)
enum SortPhase {
  SORT_IDLE = 0,
  SORT_WAIT_DROP,
  SORT_WAIT_SETTLE
};

SortPhase sortPhase = SORT_IDLE;
unsigned long sortPhaseStartMs = 0;
State pendingPostSortState = STATE_Q0;
State pendingFromState = STATE_Q2;
Input pendingSortInput = INPUT_NONE;
const char* pendingSortOutputLabel = "";
const char* pendingSortWasteType = nullptr;
bool pendingSyncAlreadyDone = false;

// ============================================================================
// DEKLARASI FUNGSI
// ============================================================================
void emitState(State s);
void logTransition(State from, Input inp, const char* outputLabel, State to);
void syncToSupabase(State from, Input inp, const char* outputLabel, State to, const char* wasteType);
bool isAnyBinFull();
bool areBothBinsSafe();

// ============================================================================
// FUNGSI OUTPUT MESIN MEALY (DELTA)
// ============================================================================

void out_L_Merah_c_Sync(State from, Input inp, State to) {
  digitalWrite(PIN_LED_FULL, HIGH);
  syncToSupabase(from, inp, "L_Merah, c_Sync", to, lastWasteType);
}

void out_Off_LED_c_Sync(State from, Input inp, State to) {
  digitalWrite(PIN_LED_FULL, LOW);
  syncToSupabase(from, inp, "Off_LED, c_Sync", to, lastWasteType);
}

void out_s_Buka(State from, Input inp, State to) {
  (void)from;
  (void)inp;
  (void)to;
  servoLid.write(SERVO_LID_OPEN_DEG);
  q1StartMs = millis();
}

void out_s_Tutup(State from, Input inp, State to) {
  (void)from;
  (void)inp;
  (void)to;
  servoLid.write(SERVO_LID_CLOSE_DEG);
  q2StartMs = millis();
}

void out_m_Kiri_c_Sync(State from, Input inp, State to) {
  // Gerakkan papan pengarah ke wadah organik (kiri), tahan 1,5 detik non-blocking
  servoSort.write(SERVO_SORT_ORGANIC_DEG);
  lastWasteType = "organic";
  sortPhase = SORT_WAIT_DROP;
  sortPhaseStartMs = millis();
  pendingFromState = from;
  pendingSortInput = inp;
  pendingSortOutputLabel = "m_Kiri, c_Sync";
  pendingPostSortState = to;
  pendingSortWasteType = "organic";
  pendingSyncAlreadyDone = false;
}

void out_m_Kanan_c_Sync(State from, Input inp, State to) {
  // Gerakkan papan pengarah ke wadah anorganik (kanan), tahan 1,5 detik non-blocking
  servoSort.write(SERVO_SORT_INORGANIC_DEG);
  lastWasteType = "inorganic";
  sortPhase = SORT_WAIT_DROP;
  sortPhaseStartMs = millis();
  pendingFromState = from;
  pendingSortInput = inp;
  pendingSortOutputLabel = "m_Kanan, c_Sync";
  pendingPostSortState = to;
  pendingSortWasteType = "inorganic";
  pendingSyncAlreadyDone = false;
}

void out_u_Residu_c_Sync(State from, Input inp, State to) {
  // Ekstensi input u:
  // 1) Servo 2 tetap di posisi netral terlebih dahulu sambil c_Sync mencatat "gagal klasifikasi"
  servoSort.write(SERVO_SORT_NEUTRAL_DEG);
  lastWasteType = "unknown";
  syncToSupabase(from, inp, "c_Sync (gagal klasifikasi), m_Kanan", to, "unknown");

  // 2) Anggap residu ke wadah anorganik (m_Kanan), tahan 1,5 detik lalu kembali ke netral
  servoSort.write(SERVO_SORT_INORGANIC_DEG);
  sortPhase = SORT_WAIT_DROP;
  sortPhaseStartMs = millis();
  pendingFromState = from;
  pendingSortInput = inp;
  pendingSortOutputLabel = "c_Sync (gagal klasifikasi), m_Kanan";
  pendingPostSortState = to;
  pendingSortWasteType = "unknown";
  pendingSyncAlreadyDone = true;
}

// ============================================================================
// TABEL TRANSISI MEALY (IDENTIK DENGAN fst/fst_definition.json)
// ============================================================================
const Transition TRANSITION_TABLE[] = {
  { STATE_Q0, INPUT_F,     out_L_Merah_c_Sync,   "L_Merah, c_Sync",                   STATE_QF },
  { STATE_Q0, INPUT_P,     out_s_Buka,           "s_Buka",                            STATE_Q1 },
  { STATE_Q0, INPUT_W,     out_s_Buka,           "s_Buka",                            STATE_Q1 },
  { STATE_Q1, INPUT_DELAY, out_s_Tutup,          "s_Tutup",                           STATE_Q2 },
  { STATE_Q2, INPUT_O,     out_m_Kiri_c_Sync,    "m_Kiri, c_Sync",                    STATE_Q0 },
  { STATE_Q2, INPUT_A,     out_m_Kanan_c_Sync,   "m_Kanan, c_Sync",                   STATE_Q0 },
  { STATE_Q2, INPUT_U,     out_u_Residu_c_Sync,  "c_Sync (gagal klasifikasi), m_Kanan", STATE_Q0 },
  { STATE_QF, INPUT_N,     out_Off_LED_c_Sync,   "Off_LED, c_Sync",                   STATE_Q0 }
};

constexpr size_t TRANSITION_COUNT = sizeof(TRANSITION_TABLE) / sizeof(TRANSITION_TABLE[0]);

// ============================================================================
// PEMBACAAN SENSOR ULTRASONIK (MEDIAN 5 SAMPEL)
// ============================================================================

float readSingleUltrasonicCm(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, ULTRASONIC_TIMEOUT_US);
  if (duration == 0) {
    return -1.0f;  // Timeout / tidak ada pantulan
  }
  return (duration * 0.0343f) / 2.0f;
}

float readUltrasonicMedianCm(int trigPin, int echoPin) {
  float samples[ULTRASONIC_SAMPLES];
  int validCount = 0;

  for (int i = 0; i < ULTRASONIC_SAMPLES; i++) {
    float d = readSingleUltrasonicCm(trigPin, echoPin);
    if (d > 0.5f && d < 400.0f) {
      samples[validCount++] = d;
    }
    delay(10);  // Jeda pendek antar ping agar tidak saling memantul
  }

  if (validCount == 0) {
    // Jika sensor timeout semua, kembalikan tinggi keranjang agar tidak salah memicu penuh
    return BIN_HEIGHT_CM;
  }

  // Urutkan sampel valid (insertion sort sederhana) untuk mengambil median
  for (int i = 1; i < validCount; i++) {
    float key = samples[i];
    int j = i - 1;
    while (j >= 0 && samples[j] > key) {
      samples[j + 1] = samples[j];
      j--;
    }
    samples[j + 1] = key;
  }

  return samples[validCount / 2];
}

float computeFillPercent(float distanceCm) {
  float pct = ((BIN_HEIGHT_CM - distanceCm) / BIN_HEIGHT_CM) * 100.0f;
  if (pct < 0.0f) return 0.0f;
  if (pct > 100.0f) return 100.0f;
  return pct;
}

void pollPhysicalSensors() {
  if (SIMULATION_MODE) {
    return;
  }
  unsigned long now = millis();
  if (now - lastSensorPollMs < SENSOR_POLL_INTERVAL_MS) {
    return;
  }
  lastSensorPollMs = now;

  userDistCm = readUltrasonicMedianCm(PIN_US_USER_TRIG, PIN_US_USER_ECHO);
  organicDistCm = readUltrasonicMedianCm(PIN_US_ORG_TRIG, PIN_US_ORG_ECHO);
  inorganicDistCm = readUltrasonicMedianCm(PIN_US_INORG_TRIG, PIN_US_INORG_ECHO);

  organicFillPct = computeFillPercent(organicDistCm);
  inorganicFillPct = computeFillPercent(inorganicDistCm);
}

bool isAnyBinFull() {
  return (organicDistCm < FULL_THRESHOLD_CM) || (inorganicDistCm < FULL_THRESHOLD_CM);
}

bool areBothBinsSafe() {
  return (organicDistCm >= FULL_THRESHOLD_CM) && (inorganicDistCm >= FULL_THRESHOLD_CM);
}

// ============================================================================
// KOMUNIKASI SERIAL (PROTOKOL 115200 BAUD + SIMULATION_MODE)
// ============================================================================

void emitState(State s) {
  Serial.print("STATE:");
  Serial.println(stateToStr(s));
}

void logTransition(State from, Input inp, const char* outputLabel, State to) {
  Serial.print("[");
  Serial.print(stateToStr(from));
  Serial.print("] --");
  Serial.print(inputToStr(inp));
  Serial.print(" / ");
  Serial.print(outputLabel);
  Serial.print("--> [");
  Serial.print(stateToStr(to));
  Serial.println("]");
}

void handleSerialLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  // Perintah klasifikasi dari laptop/YOLO
  if (line == "CLS:organic") {
    pendingSerialInput = INPUT_O;
    return;
  }
  if (line == "CLS:inorganic") {
    pendingSerialInput = INPUT_A;
    return;
  }
  if (line == "CLS:unknown") {
    pendingSerialInput = INPUT_U;
    return;
  }

  // Perintah simulasi tanpa sensor fisik
  if (line.startsWith("SIM:")) {
    if (!SIMULATION_MODE) {
      Serial.println("# Abaikan perintah SIM:... karena SIMULATION_MODE = false di config.h");
      return;
    }
    String simCmd = line.substring(4);
    simCmd.trim();
    if (simCmd == "f+p" || simCmd == "f,p" || simCmd == "p+f") {
      // Simulasi f dan p muncul bersamaan: f selalu menang sesuai aturan prioritas q0
      organicDistCm = 2.0f;
      organicFillPct = computeFillPercent(organicDistCm);
      userDistCm = 15.0f;
      pendingSerialInput = INPUT_F;
    } else if (simCmd == "p") {
      userDistCm = 15.0f;
      pendingSerialInput = INPUT_P;
    } else if (simCmd == "p'") {
      userDistCm = 100.0f;
      pendingSerialInput = INPUT_P_PRIME;
    } else if (simCmd == "w") {
      pendingSerialInput = INPUT_W;
    } else if (simCmd == "f") {
      organicDistCm = 2.0f;
      organicFillPct = computeFillPercent(organicDistCm);
      pendingSerialInput = INPUT_F;
    } else if (simCmd == "n") {
      organicDistCm = 35.0f;
      inorganicDistCm = 35.0f;
      organicFillPct = computeFillPercent(organicDistCm);
      inorganicFillPct = computeFillPercent(inorganicDistCm);
      pendingSerialInput = INPUT_N;
    } else if (simCmd == "delay") {
      pendingSerialInput = INPUT_DELAY;
    } else if (simCmd == "o") {
      pendingSerialInput = INPUT_O;
    } else if (simCmd == "a") {
      pendingSerialInput = INPUT_A;
    } else if (simCmd == "u") {
      pendingSerialInput = INPUT_U;
    } else {
      Serial.print("# Perintah simulasi tidak dikenal: ");
      Serial.println(line);
    }
  }
}

void pollSerialCommands() {
  while (Serial.available() > 0) {
    char ch = static_cast<char>(Serial.read());
    if (ch == '\r') continue;
    if (ch == '\n') {
      handleSerialLine(serialLineBuffer);
      serialLineBuffer = "";
    } else if (serialLineBuffer.length() < 120) {
      serialLineBuffer += ch;
    }
  }
}

// ============================================================================
// WIFI & SUPABASE REST API
// ============================================================================

bool hasValidSupabaseConfig() {
  return String(SUPABASE_URL).indexOf("ganti-dengan") == -1 &&
         String(SUPABASE_ANON_KEY).indexOf("ganti-dengan") == -1 &&
         String(WIFI_SSID) != "NAMA_WIFI_ANDA";
}

void ensureWifiConnected() {
  if (!hasValidSupabaseConfig()) return;
  if (WiFi.status() == WL_CONNECTED) return;

  unsigned long now = millis();
  if (now - lastWifiAttemptMs < WIFI_RECONNECT_INTERVAL_MS) return;
  lastWifiAttemptMs = now;

  Serial.println("# Mencoba menyambung ulang WiFi...");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void syncToSupabase(State from, Input inp, const char* outputLabel, State to, const char* wasteType) {
  if (!hasValidSupabaseConfig() || WiFi.status() != WL_CONNECTED) {
    Serial.println("# c_Sync dilewati (WiFi/Supabase belum terhubung, FST tetap jalan lokal).");
    return;
  }

  WiFiClientSecure client;
  // Catatan mahasiswa: setInsecure() dipakai agar mudah di praktikum tanpa mengurus sertifikat CA.
  // Untuk produksi, pasang root CA Supabase menggunakan client.setCACert(...).
  client.setInsecure();

  HTTPClient http;
  String baseUrl = String(SUPABASE_URL);

  // 1. PATCH status terkini pada baris tunggal id=1 di bin_status
  {
    String url = baseUrl + "/rest/v1/bin_status?id=eq.1";
    if (http.begin(client, url)) {
      http.addHeader("apikey", SUPABASE_ANON_KEY);
      http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
      http.addHeader("Content-Type", "application/json");
      http.addHeader("Prefer", "return=minimal");

      JsonDocument doc;
      doc["current_state"] = stateToStr(to);
      doc["organic_fill_pct"] = roundf(organicFillPct * 100.0f) / 100.0f;
      doc["inorganic_fill_pct"] = roundf(inorganicFillPct * 100.0f) / 100.0f;
      doc["is_full"] = (to == STATE_QF);
      if (wasteType != nullptr) {
        doc["last_waste_type"] = wasteType;
      }

      String payload;
      serializeJson(doc, payload);
      int code = http.PATCH(payload);
      if (code < 200 || code >= 300) {
        Serial.print("# Peringatan PATCH bin_status HTTP ");
        Serial.println(code);
      }
      http.end();
    }
  }

  // 2. POST riwayat transisi ke bin_events (created_at diisi otomatis oleh server)
  {
    String url = baseUrl + "/rest/v1/bin_events";
    if (http.begin(client, url)) {
      http.addHeader("apikey", SUPABASE_ANON_KEY);
      http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
      http.addHeader("Content-Type", "application/json");
      http.addHeader("Prefer", "return=minimal");

      JsonDocument doc;
      doc["from_state"] = stateToStr(from);
      doc["input"] = inputToStr(inp);
      doc["output"] = outputLabel;
      doc["to_state"] = stateToStr(to);
      if (wasteType != nullptr) {
        doc["waste_type"] = wasteType;
      } else {
        doc["waste_type"] = nullptr;
      }
      doc["organic_fill_pct"] = roundf(organicFillPct * 100.0f) / 100.0f;
      doc["inorganic_fill_pct"] = roundf(inorganicFillPct * 100.0f) / 100.0f;

      String payload;
      serializeJson(doc, payload);
      int code = http.POST(payload);
      if (code < 200 || code >= 300) {
        Serial.print("# Peringatan POST bin_events HTTP ");
        Serial.println(code);
      }
      http.end();
    }
  }
}

void markCommandProcessed(long commandId) {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;
  String url = String(SUPABASE_URL) + "/rest/v1/bin_commands?id=eq." + String(commandId);

  if (http.begin(client, url)) {
    http.addHeader("apikey", SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("Prefer", "return=minimal");
    http.PATCH("{\"processed\":true}");
    http.end();
  }
}

void pollSupabaseCommands() {
  if (!hasValidSupabaseConfig() || WiFi.status() != WL_CONNECTED) return;

  unsigned long now = millis();
  if (now - lastSupabasePollMs < SUPABASE_POLL_INTERVAL_MS) return;
  lastSupabasePollMs = now;

  WiFiClientSecure client;
  client.setInsecure();
  HTTPClient http;
  String url = String(SUPABASE_URL) +
               "/rest/v1/bin_commands?select=id,command&processed=eq.false&order=created_at.asc&limit=1";

  if (http.begin(client, url)) {
    http.addHeader("apikey", SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);

    int code = http.GET();
    if (code == 200) {
      String body = http.getString();
      JsonDocument doc;
      if (!deserializeJson(doc, body) && doc.is<JsonArray>() && doc.size() > 0) {
        long cmdId = doc[0]["id"] | -1;
        const char* cmd = doc[0]["command"] | "";
        if (cmdId > 0 && strcmp(cmd, "force_open") == 0) {
          pendingWebForceOpen = true;
          markCommandProcessed(cmdId);
        }
      }
    }
    http.end();
  }
}

// ============================================================================
// KONTROL INTI FST: readInput(), step(), dan SEKUENS NON-BLOCKING SERVO 2
// ============================================================================

void updateSortSequence() {
  if (sortPhase == SORT_IDLE) return;

  unsigned long elapsed = millis() - sortPhaseStartMs;
  if (sortPhase == SORT_WAIT_DROP && elapsed >= DROP_HOLD_DURATION_MS) {
    // Setelah jeda lepas-sampah 1,5 detik, kembalikan papan pengarah ke netral (90 derajat)
    servoSort.write(SERVO_SORT_NEUTRAL_DEG);
    sortPhase = SORT_WAIT_SETTLE;
    sortPhaseStartMs = millis();
  } else if (sortPhase == SORT_WAIT_SETTLE && elapsed >= SERVO_SETTLE_MS) {
    // Papan pengarah sudah kembali netral -> barulah resmi masuk kembali ke q0
    sortPhase = SORT_IDLE;
    if (!pendingSyncAlreadyDone) {
      syncToSupabase(
        pendingFromState,
        pendingSortInput,
        pendingSortOutputLabel,
        pendingPostSortState,
        pendingSortWasteType
      );
    }
    currentState = pendingPostSortState;
    logTransition(pendingFromState, pendingSortInput, pendingSortOutputLabel, currentState);
    emitState(currentState);
  }
}

Input readInput() {
  // Jangan baca input baru saat servo 2 sedang menyelesaikan jeda lepas sampah -> netral
  if (sortPhase != SORT_IDLE) {
    return INPUT_NONE;
  }

  // Ambil satu input serial yang masuk jika ada
  Input serialInp = pendingSerialInput;
  pendingSerialInput = INPUT_NONE;

  // Cek perintah Force Open dari Web Dashboard
  bool webW = pendingWebForceOpen;
  pendingWebForceOpen = false;

  switch (currentState) {
    case STATE_Q0: {
      // Aturan prioritas di q0: cek f lebih dulu; abaikan p dan w jika penuh
      if (SIMULATION_MODE) {
        if (serialInp == INPUT_F) return INPUT_F;
        if (webW || serialInp == INPUT_W) return INPUT_W;
        if (serialInp == INPUT_P) return INPUT_P;
        if (serialInp != INPUT_NONE) return serialInp;  // Teruskan input lain agar teruji di step()
        return INPUT_NONE;
      } else {
        if (isAnyBinFull()) return INPUT_F;
        if (webW || serialInp == INPUT_W) return INPUT_W;
        if (userDistCm < USER_DETECT_CM || serialInp == INPUT_P) return INPUT_P;
        if (serialInp != INPUT_NONE) return serialInp;
        return INPUT_P_PRIME;
      }
    }

    case STATE_Q1: {
      if (serialInp == INPUT_DELAY) return INPUT_DELAY;
      if (millis() - q1StartMs >= LID_OPEN_DURATION_MS) return INPUT_DELAY;
      if (serialInp != INPUT_NONE) return serialInp;
      return INPUT_NONE;
    }

    case STATE_Q2: {
      if (serialInp == INPUT_O || serialInp == INPUT_A || serialInp == INPUT_U) {
        return serialInp;
      }
      // Jika laptop tidak menjawab dalam 6 detik setelah STATE:q2 -> input ekstensi u
      if (millis() - q2StartMs >= CLASSIFY_TIMEOUT_MS) {
        return INPUT_U;
      }
      if (serialInp != INPUT_NONE) return serialInp;
      return INPUT_NONE;
    }

    case STATE_QF: {
      // Di qF, tutup terkunci (input p dan w diabaikan), hanya cek kapasitas aman (n)
      if (SIMULATION_MODE) {
        if (serialInp == INPUT_N) return INPUT_N;
        if (webW) return INPUT_W;  // Akan diabaikan secara resmi di step()
        if (serialInp != INPUT_NONE) return serialInp;
        return INPUT_NONE;
      } else {
        if (areBothBinsSafe()) return INPUT_N;
        if (webW) return INPUT_W;  // Akan diabaikan oleh tabel transisi
        if (serialInp != INPUT_NONE) return serialInp;
        return INPUT_NONE;
      }
    }
  }

  return INPUT_NONE;
}

void step(Input inp) {
  if (inp == INPUT_NONE || inp == INPUT_P_PRIME) {
    return;
  }

  for (size_t i = 0; i < TRANSITION_COUNT; i++) {
    const Transition& t = TRANSITION_TABLE[i];
    if (t.currentState == currentState && t.input == inp) {
      State prevState = currentState;
      t.outputFn(prevState, inp, t.nextState);

      // Untuk q2 -> q0, transisi resmi ke q0 diselesaikan setelah servo 2 kembali netral
      if (sortPhase == SORT_IDLE) {
        currentState = t.nextState;
        logTransition(prevState, inp, t.outputLabel, currentState);
        emitState(currentState);
      }
      return;
    }
  }

  // Input tidak valid untuk state saat ini -> abaikan tanpa crash
  Serial.print("[");
  Serial.print(stateToStr(currentState));
  Serial.print("] --");
  Serial.print(inputToStr(inp));
  Serial.println(" / (diabaikan)--> [" + String(stateToStr(currentState)) + "]");
}

// ============================================================================
// SETUP & LOOP UTAMA
// ============================================================================

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(200);

  pinMode(PIN_US_USER_TRIG, OUTPUT);
  pinMode(PIN_US_USER_ECHO, INPUT);
  pinMode(PIN_US_ORG_TRIG, OUTPUT);
  pinMode(PIN_US_ORG_ECHO, INPUT);
  pinMode(PIN_US_INORG_TRIG, OUTPUT);
  pinMode(PIN_US_INORG_ECHO, INPUT);
  pinMode(PIN_LED_FULL, OUTPUT);
  digitalWrite(PIN_LED_FULL, LOW);

  servoLid.setPeriodHertz(50);
  servoSort.setPeriodHertz(50);
  servoLid.attach(PIN_SERVO_LID, 500, 2400);
  servoSort.attach(PIN_SERVO_SORT, 500, 2400);

  // Posisi awal aman: tutup tertutup, papan pengarah netral
  servoLid.write(SERVO_LID_CLOSE_DEG);
  servoSort.write(SERVO_SORT_NEUTRAL_DEG);

  if (hasValidSupabaseConfig()) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.println("# Menghubungkan WiFi untuk Supabase...");
  } else {
    Serial.println("# secrets.h belum dikonfigurasi -> berjalan dalam mode lokal tanpa Supabase.");
  }

  Serial.print("# Smart Bin FST siap. SIMULATION_MODE = ");
  Serial.println(SIMULATION_MODE ? "true" : "false");
  emitState(currentState);
}

void loop() {
  ensureWifiConnected();
  pollSerialCommands();
  pollPhysicalSensors();
  pollSupabaseCommands();
  updateSortSequence();

  Input inp = readInput();
  if (inp != INPUT_NONE) {
    step(inp);
  }
}
