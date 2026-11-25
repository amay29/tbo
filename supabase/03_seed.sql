-- ============================================================================
-- TAHAP B.3: DATA AWAL (SEED)
-- Jalankan setelah 01_schema.sql dan 02_rls_and_realtime.sql.
-- ============================================================================

INSERT INTO public.bin_status (
  id,
  current_state,
  organic_fill_pct,
  inorganic_fill_pct,
  is_full,
  last_waste_type
)
VALUES (
  1,
  'q0',
  0.00,
  0.00,
  false,
  NULL
)
ON CONFLICT (id) DO NOTHING;
