"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { STATE_META } from "@/lib/fstLabels";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabaseClient";
import type { BinCommand, BinEvent, BinStatus } from "@/lib/types";
import { CapacityBar } from "./CapacityBar";
import { EventHistory } from "./EventHistory";
import { StatusCard } from "./StatusCard";

function startOfLocalDayIso(): string {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return now.toISOString();
}

export function DashboardClient() {
  const router = useRouter();
  const configured = isSupabaseConfigured();

  const [authChecked, setAuthChecked] = useState(false);
  const [userEmail, setUserEmail] = useState<string>("");
  const [status, setStatus] = useState<BinStatus | null>(null);
  const [events, setEvents] = useState<BinEvent[]>([]);
  const [todayOrganic, setTodayOrganic] = useState(0);
  const [todayInorganic, setTodayInorganic] = useState(0);
  const [hasPendingCommand, setHasPendingCommand] = useState(false);

  const [isLoadingData, setIsLoadingData] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [isSubmittingCommand, setIsSubmittingCommand] = useState(false);
  const [liveAnnouncement, setLiveAnnouncement] = useState("");

  const loadDashboardData = useCallback(async () => {
    if (!configured) {
      setErrorMessage(
        "Konfigurasi Supabase belum diatur. Salin .env.local.example menjadi .env.local dan isi kredensial Anda."
      );
      setIsLoadingData(false);
      return;
    }

    setErrorMessage("");
    try {
      const supabase = getSupabaseClient();
      const todayIso = startOfLocalDayIso();

      const [statusRes, eventsRes, todayRes, pendingCmdRes] = await Promise.all([
        supabase.from("bin_status").select("*").eq("id", 1).maybeSingle(),
        supabase
          .from("bin_events")
          .select("*")
          .order("created_at", { ascending: false })
          .limit(20),
        supabase
          .from("bin_events")
          .select("waste_type")
          .gte("created_at", todayIso)
          .in("waste_type", ["organic", "inorganic"]),
        supabase
          .from("bin_commands")
          .select("id")
          .eq("processed", false)
          .limit(1),
      ]);

      if (statusRes.error) throw statusRes.error;
      if (eventsRes.error) throw eventsRes.error;
      if (todayRes.error) throw todayRes.error;
      if (pendingCmdRes.error) throw pendingCmdRes.error;

      setStatus(statusRes.data as BinStatus | null);
      setEvents((eventsRes.data as BinEvent[]) ?? []);

      const todayRows = (todayRes.data ?? []) as Array<{ waste_type: string }>;
      setTodayOrganic(todayRows.filter((r) => r.waste_type === "organic").length);
      setTodayInorganic(todayRows.filter((r) => r.waste_type === "inorganic").length);
      setHasPendingCommand((pendingCmdRes.data ?? []).length > 0);
    } catch {
      setErrorMessage(
        "Gagal memuat data dari Supabase. Periksa koneksi internet dan kebijakan RLS."
      );
    } finally {
      setIsLoadingData(false);
    }
  }, [configured]);

  useEffect(() => {
    if (!configured) {
      setAuthChecked(true);
      setIsLoadingData(false);
      setErrorMessage(
        "Variabel NEXT_PUBLIC_SUPABASE_URL dan NEXT_PUBLIC_SUPABASE_ANON_KEY belum diatur."
      );
      return;
    }

    const supabase = getSupabaseClient();
    let isMounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!isMounted) return;
      if (!data.session) {
        router.replace("/login");
        return;
      }
      setUserEmail(data.session.user.email ?? "Admin");
      setAuthChecked(true);
      void loadDashboardData();
    });

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!session) {
          router.replace("/login");
        }
      }
    );

    return () => {
      isMounted = false;
      authListener.subscription.unsubscribe();
    };
  }, [configured, loadDashboardData, router]);

  useEffect(() => {
    if (!configured || !authChecked) return;

    const supabase = getSupabaseClient();
    const channel = supabase
      .channel("smart-bin-realtime")
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "bin_status",
          filter: "id=eq.1",
        },
        (payload) => {
          const next = payload.new as BinStatus;
          setStatus(next);
          setLiveAnnouncement(
            `Status sistem berubah menjadi ${next.current_state} (${STATE_META[next.current_state].label}).`
          );
        }
      )
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "bin_events",
        },
        (payload) => {
          const newEvent = payload.new as BinEvent;
          setEvents((prev) => [newEvent, ...prev].slice(0, 20));
          if (newEvent.waste_type === "organic") {
            setTodayOrganic((c) => c + 1);
          } else if (newEvent.waste_type === "inorganic") {
            setTodayInorganic((c) => c + 1);
          }
        }
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "bin_commands",
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            const cmd = payload.new as BinCommand;
            if (!cmd.processed) setHasPendingCommand(true);
          } else if (payload.eventType === "UPDATE") {
            const cmd = payload.new as BinCommand;
            if (cmd.processed) {
              setHasPendingCommand(false);
              setActionMessage("Perintah buka tutup sudah diproses oleh ESP32.");
            }
          }
        }
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [authChecked, configured]);

  async function handleForceOpen() {
    if (!status) return;
    const isLockedFull = status.current_state === "qF" || status.is_full;
    const isBusy = status.current_state !== "q0";

    if (isLockedFull || isBusy || hasPendingCommand || isSubmittingCommand) {
      return;
    }

    setIsSubmittingCommand(true);
    setActionMessage("");
    setErrorMessage("");

    try {
      const supabase = getSupabaseClient();
      const { error } = await supabase.from("bin_commands").insert({
        command: "force_open",
        processed: false,
      });

      if (error) throw error;

      setHasPendingCommand(true);
      setActionMessage("Perintah Buka Tutup dikirim. Menunggu ESP32 membaca perintah...");
    } catch {
      setErrorMessage("Gagal mengirim perintah Buka Tutup ke Supabase.");
    } finally {
      setIsSubmittingCommand(false);
    }
  }

  async function handleSignOut() {
    if (!configured) return;
    const supabase = getSupabaseClient();
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (!authChecked || isLoadingData) {
    return (
      <main id="konten-utama" className="mx-auto max-w-[960px] px-4 py-10">
        <div className="rounded-lg border border-[#DED8CC] bg-white p-6">
          <h1 className="text-xl font-semibold text-[#1E2620]">
            Dashboard Tempat Sampah Pintar
          </h1>
          <p className="mt-2 text-sm text-[#4A544C]">
            Memuat data pemantauan dari Supabase...
          </p>
        </div>
      </main>
    );
  }

  const isLockedFull = status ? status.current_state === "qF" || status.is_full : false;
  const isNotIdle = status ? status.current_state !== "q0" : false;
  const isButtonDisabled =
    !status || isLockedFull || isNotIdle || hasPendingCommand || isSubmittingCommand;

  let forceOpenHint =
    "Membuka tutup utama secara jarak jauh (input w -> transisi q0 ke q1).";
  if (!status) {
    forceOpenHint = "Data status belum tersedia di database.";
  } else if (isLockedFull) {
    forceOpenHint =
      "Tombol dinonaktifkan: tempat sampah penuh (state qF). Tutup terkunci sampai keranjang dikosongkan.";
  } else if (hasPendingCommand) {
    forceOpenHint =
      "Tombol dinonaktifkan: perintah Buka Tutup sebelumnya belum selesai diproses ESP32.";
  } else if (isNotIdle) {
    forceOpenHint = `Tombol dinonaktifkan sementara: sistem sedang berada di state ${status.current_state} (${STATE_META[status.current_state].label}).`;
  }

  return (
    <>
      <header className="border-b border-[#DED8CC] bg-white">
        <div className="mx-auto flex max-w-[960px] flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div>
            <h1 className="text-lg font-semibold text-[#1E2620]">
              Tempat Sampah Pintar FST
            </h1>
            <p className="text-xs text-[#4A544C]">
              Pemantauan Pemilahan Otomatis Organik &amp; Anorganik
            </p>
          </div>

          <div className="flex items-center gap-3">
            {userEmail && (
              <span className="text-xs text-[#4A544C]">{userEmail}</span>
            )}
            <button
              type="button"
              onClick={handleSignOut}
              className="min-h-10 cursor-pointer rounded-md border border-[#746E62] bg-white px-3 py-1.5 text-xs font-medium text-[#1E2620] transition-colors duration-150 hover:bg-[#F3EFE6]"
            >
              Keluar
            </button>
          </div>
        </div>
      </header>

      <main
        id="konten-utama"
        className="mx-auto max-w-[960px] space-y-5 px-4 py-6"
      >
        <div aria-live="polite" className="visually-hidden">
          {liveAnnouncement}
        </div>

        {errorMessage && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#DFB2AC] bg-[#F9EAE7] p-4 text-sm text-[#8A3228]"
          >
            <span>{errorMessage}</span>
            <button
              type="button"
              onClick={() => {
                setIsLoadingData(true);
                void loadDashboardData();
              }}
              className="min-h-9 cursor-pointer rounded border border-[#8A3228] bg-white px-3 py-1 text-xs font-medium text-[#8A3228] hover:bg-[#FDF5F3]"
            >
              Coba Lagi
            </button>
          </div>
        )}

        {!status ? (
          <section className="rounded-lg border border-[#DED8CC] bg-white p-6">
            <h2 className="text-base font-semibold text-[#1E2620]">
              Status Tempat Sampah Belum Tersedia
            </h2>
            <p className="mt-1.5 text-sm text-[#4A544C]">
              Baris awal <code className="font-mono">bin_status (id = 1)</code> belum ditemukan.
              Pastikan Anda sudah menjalankan file <code className="font-mono">03_seed.sql</code>{" "}
              di SQL Editor Supabase.
            </p>
          </section>
        ) : (
          <>
            <StatusCard status={status} latestEvent={events[0] ?? null} />

            <section
              aria-labelledby="capacity-heading"
              className="grid gap-4 sm:grid-cols-2"
            >
              <h2 id="capacity-heading" className="visually-hidden">
                Keterisian Keranjang
              </h2>
              <CapacityBar
                id="progress-organik"
                label="Kapasitas Keranjang Organik"
                percentage={status.organic_fill_pct}
                variant="organic"
              />
              <CapacityBar
                id="progress-anorganik"
                label="Kapasitas Keranjang Anorganik"
                percentage={status.inorganic_fill_pct}
                variant="inorganic"
              />
            </section>

            <section
              aria-labelledby="summary-control-heading"
              className="grid gap-4 sm:grid-cols-2"
            >
              <h2 id="summary-control-heading" className="visually-hidden">
                Ringkasan Harian dan Kontrol Tutup
              </h2>

              <div className="rounded-lg border border-[#DED8CC] bg-white p-5">
                <h3 className="text-sm font-medium text-[#4A544C]">
                  Ringkasan Hari Ini
                </h3>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div className="rounded-md border border-[#E7E2D8] bg-[#FAF8F4] p-3">
                    <p className="text-xs text-[#4A544C]">Organik</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums text-[#2F4A32]">
                      {todayOrganic}
                    </p>
                  </div>
                  <div className="rounded-md border border-[#E7E2D8] bg-[#FAF8F4] p-3">
                    <p className="text-xs text-[#4A544C]">Anorganik</p>
                    <p className="mt-1 text-2xl font-semibold tabular-nums text-[#324653]">
                      {todayInorganic}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex flex-col justify-between rounded-lg border border-[#DED8CC] bg-white p-5">
                <div>
                  <h3 className="text-sm font-medium text-[#4A544C]">
                    Kontrol Jarak Jauh
                  </h3>
                  <p id="force-open-hint" className="mt-1.5 text-sm text-[#1E2620]">
                    {forceOpenHint}
                  </p>
                </div>

                <div className="mt-4">
                  <button
                    type="button"
                    aria-disabled={isButtonDisabled}
                    aria-describedby="force-open-hint"
                    onClick={handleForceOpen}
                    className={`min-h-12 w-full rounded-md px-4 py-2.5 text-base font-medium transition-colors duration-150 ${
                      isButtonDisabled
                        ? "cursor-not-allowed border border-[#CFC8B9] bg-[#EFECE5] text-[#5B635C]"
                        : "cursor-pointer bg-[#4A6B4D] text-white hover:bg-[#3D5940]"
                    }`}
                  >
                    {isSubmittingCommand ? "Mengirim perintah..." : "Buka Tutup"}
                  </button>
                  {actionMessage && (
                    <p role="status" className="mt-2 text-xs text-[#2F4A32]">
                      {actionMessage}
                    </p>
                  )}
                </div>
              </div>
            </section>

            <EventHistory events={events} />
          </>
        )}
      </main>
    </>
  );
}
