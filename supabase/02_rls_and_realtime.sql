-- ============================================================================
-- TAHAP B.2: ROW LEVEL SECURITY (RLS) & REALTIME SUBSCRIPTION
-- Jalankan setelah 01_schema.sql di Supabase SQL Editor.
-- ============================================================================

-- Aktifkan RLS di semua tabel
ALTER TABLE public.bin_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bin_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bin_commands ENABLE ROW LEVEL SECURITY;

-- Hapus policy lama bila dijalankan ulang (agar idempoten)
DROP POLICY IF EXISTS "Admin dapat membaca status" ON public.bin_status;
DROP POLICY IF EXISTS "ESP32 anon dapat update status id=1" ON public.bin_status;

DROP POLICY IF EXISTS "Admin dapat membaca riwayat kejadian" ON public.bin_events;
DROP POLICY IF EXISTS "ESP32 anon dapat mencatat riwayat kejadian" ON public.bin_events;

DROP POLICY IF EXISTS "Admin dapat membaca perintah" ON public.bin_commands;
DROP POLICY IF EXISTS "Admin dapat mengirim perintah force_open" ON public.bin_commands;
DROP POLICY IF EXISTS "ESP32 anon dapat membaca perintah tertunda" ON public.bin_commands;
DROP POLICY IF EXISTS "ESP32 anon dapat menandai perintah selesai" ON public.bin_commands;

-- ----------------------------------------------------------------------------
-- Kebijakan untuk Admin Dashboard (role: authenticated / login Supabase Auth)
-- ----------------------------------------------------------------------------
CREATE POLICY "Admin dapat membaca status"
ON public.bin_status
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Admin dapat membaca riwayat kejadian"
ON public.bin_events
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Admin dapat membaca perintah"
ON public.bin_commands
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Admin dapat mengirim perintah force_open"
ON public.bin_commands
FOR INSERT
TO authenticated
WITH CHECK (command = 'force_open' AND processed = false);

-- ----------------------------------------------------------------------------
-- Kebijakan terbatas untuk ESP32 (role: anon)
-- Catatan: ESP32 memakai header Prefer: return=minimal saat PATCH/POST sehingga
-- anon tidak perlu izin SELECT pada bin_status maupun bin_events.
-- ----------------------------------------------------------------------------
CREATE POLICY "ESP32 anon dapat update status id=1"
ON public.bin_status
FOR UPDATE
TO anon
USING (id = 1)
WITH CHECK (id = 1);

CREATE POLICY "ESP32 anon dapat mencatat riwayat kejadian"
ON public.bin_events
FOR INSERT
TO anon
WITH CHECK (true);

CREATE POLICY "ESP32 anon dapat membaca perintah tertunda"
ON public.bin_commands
FOR SELECT
TO anon
USING (processed = false);

CREATE POLICY "ESP32 anon dapat menandai perintah selesai"
ON public.bin_commands
FOR UPDATE
TO anon
USING (processed = false)
WITH CHECK (processed = true);

-- ----------------------------------------------------------------------------
-- Aktifkan Supabase Realtime untuk bin_status, bin_events, dan bin_commands
-- ----------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'bin_status'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.bin_status;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'bin_events'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.bin_events;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime' AND schemaname = 'public' AND tablename = 'bin_commands'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE public.bin_commands;
  END IF;
END
$$;
