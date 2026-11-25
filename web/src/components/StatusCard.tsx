import { STATE_META, formatTimeId, formatTransition, formatWasteType } from "@/lib/fstLabels";
import type { BinEvent, BinStatus } from "@/lib/types";

interface StatusCardProps {
  status: BinStatus;
  latestEvent: BinEvent | null;
}

export function StatusCard({ status, latestEvent }: StatusCardProps) {
  const meta = STATE_META[status.current_state];

  return (
    <section
      aria-labelledby="status-heading"
      className="rounded-lg border border-[#DED8CC] bg-white p-5 sm:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2
            id="status-heading"
            className="text-sm font-medium text-[#4A544C]"
          >
            Status Sistem Saat Ini (FST Mealy)
          </h2>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <span
              className={`inline-flex items-center rounded-md border px-3 py-1 text-base font-semibold ${meta.badgeClass}`}
            >
              {status.current_state} — {meta.label}
            </span>
            {status.is_full && (
              <span className="inline-flex items-center rounded-md border border-[#DFB2AC] bg-[#F9EAE7] px-2.5 py-1 text-xs font-semibold text-[#8A3228]">
                Indikator Penuh Aktif
              </span>
            )}
          </div>
          <p className="mt-2 text-sm text-[#4A544C]">{meta.description}</p>
        </div>

        <div className="text-left sm:text-right">
          <p className="text-xs font-medium text-[#4A544C]">
            Pemilahan Terakhir
          </p>
          <p className="mt-0.5 text-sm font-semibold text-[#1E2620]">
            {formatWasteType(status.last_waste_type)}
          </p>
          <p className="mt-1 text-xs text-[#4A544C]">
            Diperbarui: {formatTimeId(status.updated_at)}
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-[#E7E2D8] bg-[#FAF8F4] px-3.5 py-2.5">
        <p className="text-xs font-medium text-[#4A544C]">
          Transisi FST Terakhir
        </p>
        <p className="mt-0.5 font-mono text-sm text-[#1E2620] break-words">
          {latestEvent
            ? formatTransition(latestEvent)
            : "Belum ada transisi FST tercatat."}
        </p>
      </div>
    </section>
  );
}
