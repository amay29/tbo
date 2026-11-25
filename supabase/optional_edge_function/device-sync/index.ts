// ============================================================================
// OPSIONAL (UNTUK PRODUKSI): Supabase Edge Function `device-sync`
// Memberikan keamanan ekstra dibanding pemakaian anon key langsung di ESP32,
// karena ESP32 mengirim `x-device-key` rahasia dan hanya Edge Function yang
// memegang SUPABASE_SERVICE_ROLE_KEY di server Supabase.
// ============================================================================

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const DEVICE_API_KEY = Deno.env.get("DEVICE_API_KEY") ?? "";
const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { status: 200 });
  }

  const clientKey = req.headers.get("x-device-key") ?? "";
  if (!DEVICE_API_KEY || clientKey !== DEVICE_API_KEY) {
    return Response.json({ error: "Unauthorized device" }, { status: 401 });
  }

  const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

  try {
    if (req.method === "POST") {
      // Sinkronisasi status + catat event dari ESP32
      const body = await req.json();
      const {
        current_state,
        organic_fill_pct,
        inorganic_fill_pct,
        is_full,
        last_waste_type,
        event,
      } = body;

      const { error: statusError } = await supabase
        .from("bin_status")
        .update({
          current_state,
          organic_fill_pct,
          inorganic_fill_pct,
          is_full,
          last_waste_type,
        })
        .eq("id", 1);

      if (statusError) throw statusError;

      if (event) {
        const { error: eventError } = await supabase.from("bin_events").insert({
          from_state: event.from_state,
          input: event.input,
          output: event.output,
          to_state: event.to_state,
          waste_type: event.waste_type ?? null,
          organic_fill_pct,
          inorganic_fill_pct,
        });
        if (eventError) throw eventError;
      }

      return Response.json({ ok: true });
    }

    if (req.method === "GET") {
      // Polling perintah force_open tertunda
      const { data, error } = await supabase
        .from("bin_commands")
        .select("id, command, created_at")
        .eq("processed", false)
        .order("created_at", { ascending: true })
        .limit(1);

      if (error) throw error;
      return Response.json({ commands: data ?? [] });
    }

    if (req.method === "PATCH") {
      // Tandai perintah sudah dieksekusi oleh ESP32
      const { id } = await req.json();
      const { error } = await supabase
        .from("bin_commands")
        .update({ processed: true, processed_at: new Date().toISOString() })
        .eq("id", id)
        .eq("processed", false);

      if (error) throw error;
      return Response.json({ ok: true });
    }

    return Response.json({ error: "Method not allowed" }, { status: 405 });
  } catch (err) {
    return Response.json({ error: String(err) }, { status: 500 });
  }
});
