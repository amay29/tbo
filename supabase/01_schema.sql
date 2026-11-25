-- ============================================================================
-- TAHAP B.1: SKEMA DATABASE TEMPAT SAMPAH PINTAR (SUPABASE / POSTGRESQL)
-- Tempel dan jalankan di Supabase SQL Editor.
-- ============================================================================

-- 1. Tabel status terkini tempat sampah (dibatasi hanya 1 baris: id = 1)
CREATE TABLE IF NOT EXISTS public.bin_status (
  id integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  current_state text NOT NULL DEFAULT 'q0' CHECK (current_state IN ('q0', 'q1', 'q2', 'qF')),
  organic_fill_pct numeric(5, 2) NOT NULL DEFAULT 0 CHECK (organic_fill_pct >= 0 AND organic_fill_pct <= 100),
  inorganic_fill_pct numeric(5, 2) NOT NULL DEFAULT 0 CHECK (inorganic_fill_pct >= 0 AND inorganic_fill_pct <= 100),
  is_full boolean NOT NULL DEFAULT false,
  last_waste_type text NULL CHECK (last_waste_type IN ('organic', 'inorganic', 'unknown')),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Fungsi trigger untuk mengisi updated_at otomatis dari waktu server database
CREATE OR REPLACE FUNCTION public.set_bin_status_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bin_status_updated_at ON public.bin_status;
CREATE TRIGGER trg_bin_status_updated_at
BEFORE UPDATE ON public.bin_status
FOR EACH ROW
EXECUTE FUNCTION public.set_bin_status_updated_at();

-- 2. Tabel riwayat seluruh kejadian transisi FST
CREATE TABLE IF NOT EXISTS public.bin_events (
  id bigserial PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  from_state text NOT NULL CHECK (from_state IN ('q0', 'q1', 'q2', 'qF')),
  input text NOT NULL,
  output text NOT NULL,
  to_state text NOT NULL CHECK (to_state IN ('q0', 'q1', 'q2', 'qF')),
  waste_type text NULL CHECK (waste_type IN ('organic', 'inorganic', 'unknown')),
  organic_fill_pct numeric(5, 2) NOT NULL DEFAULT 0 CHECK (organic_fill_pct >= 0 AND organic_fill_pct <= 100),
  inorganic_fill_pct numeric(5, 2) NOT NULL DEFAULT 0 CHECK (inorganic_fill_pct >= 0 AND inorganic_fill_pct <= 100)
);

CREATE INDEX IF NOT EXISTS idx_bin_events_created_at ON public.bin_events (created_at DESC);

-- 3. Tabel antrean perintah dari Web Dashboard ke ESP32 (misal: 'force_open')
CREATE TABLE IF NOT EXISTS public.bin_commands (
  id bigserial PRIMARY KEY,
  created_at timestamptz NOT NULL DEFAULT now(),
  command text NOT NULL CHECK (command IN ('force_open')),
  processed boolean NOT NULL DEFAULT false,
  processed_at timestamptz NULL
);

CREATE INDEX IF NOT EXISTS idx_bin_commands_pending ON public.bin_commands (processed, created_at ASC);

CREATE OR REPLACE FUNCTION public.set_bin_commands_processed_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.processed = true AND OLD.processed = false AND NEW.processed_at IS NULL THEN
    NEW.processed_at = now();
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bin_commands_processed_at ON public.bin_commands;
CREATE TRIGGER trg_bin_commands_processed_at
BEFORE UPDATE ON public.bin_commands
FOR EACH ROW
EXECUTE FUNCTION public.set_bin_commands_processed_at();
