#ifndef FST_TABLE_H
#define FST_TABLE_H

#include <Arduino.h>

// ============================================================================
// DEFINISI FORMAL FINITE STATE TRANSDUCER (MESIN MEALY)
// Harus identik dengan fst/fst_definition.json
// M = (Q, Sigma, Delta, delta, lambda, q0)
// ============================================================================

enum State {
  STATE_Q0 = 0,  // Siaga
  STATE_Q1,      // Tutup Terbuka
  STATE_Q2,      // Memilah
  STATE_QF       // Penuh (terkunci sampai dikosongkan)
};

enum Input {
  INPUT_NONE = 0,
  INPUT_F,        // f: salah satu keranjang penuh (< 5 cm)
  INPUT_N,        // n: kapasitas aman (>= 5 cm)
  INPUT_P,        // p: pengguna terdeteksi (< 30 cm)
  INPUT_P_PRIME,  // p': tidak ada pengguna
  INPUT_W,        // w: perintah Force Open dari dashboard
  INPUT_O,        // o: objek organik dari YOLO
  INPUT_A,        // a: objek anorganik dari YOLO
  INPUT_DELAY,    // delay: timer tutup terbuka habis
  INPUT_U         // u: [EKSTENSI] klasifikasi gagal / tidak yakin / timeout
};

// Pointer fungsi aksi output Mesin Mealy
typedef void (*OutputHandler)(State fromState, Input inp, State toState);

// Struktur satu baris pada Tabel Transisi Mealy
struct Transition {
  State currentState;
  Input input;
  OutputHandler outputFn;
  const char* outputLabel;  // Nama output untuk log serial & database
  State nextState;
};

inline const char* stateToStr(State s) {
  switch (s) {
    case STATE_Q0: return "q0";
    case STATE_Q1: return "q1";
    case STATE_Q2: return "q2";
    case STATE_QF: return "qF";
    default: return "q0";
  }
}

inline const char* inputToStr(Input inp) {
  switch (inp) {
    case INPUT_F: return "f";
    case INPUT_N: return "n";
    case INPUT_P: return "p";
    case INPUT_P_PRIME: return "p'";
    case INPUT_W: return "w";
    case INPUT_O: return "o";
    case INPUT_A: return "a";
    case INPUT_DELAY: return "delay";
    case INPUT_U: return "u";
    default: return "none";
  }
}

#endif
