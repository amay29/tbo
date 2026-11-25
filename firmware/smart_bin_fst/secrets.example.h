#ifndef SECRETS_EXAMPLE_H
#define SECRETS_EXAMPLE_H

// ============================================================================
// SALIN FILE INI MENJADI "secrets.h" DI FOLDER YANG SAMA (smart_bin_fst/)
// Jangan pernah commit secrets.h ke Git dan JANGAN taruh service_role key!
// ============================================================================

#define WIFI_SSID "NAMA_WIFI_ANDA"
#define WIFI_PASSWORD "PASSWORD_WIFI_ANDA"

// Contoh: "https://abcdefghijklmno.supabase.co" (tanpa garis miring di akhir)
#define SUPABASE_URL "https://ganti-dengan-project-id.supabase.co"

// Gunakan anon public key (BUKAN service_role key)
#define SUPABASE_ANON_KEY "ganti-dengan-anon-public-key-anda"

#endif
