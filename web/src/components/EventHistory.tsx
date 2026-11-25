import { formatTimeId, formatTransition, formatWasteType } from "@/lib/fstLabels";
import type { BinEvent } from "@/lib/types";

interface EventHistoryProps {
  events: BinEvent[];
}

export function EventHistory({ events }: EventHistoryProps) {
  return (
    <section
      aria-labelledby="history-heading"
      className="rounded-lg border border-[#DED8CC] bg-white p-5 sm:p-6"
    >
      <div className="flex items-baseline justify-between gap-2">
        <h2
          id="history-heading"
          className="text-base font-semibold text-[#1E2620]"
        >
          Riwayat 20 Kejadian Terakhir
        </h2>
        <span className="text-xs text-[#4A544C]">
          Pembaruan otomatis realtime
        </span>
      </div>

      {events.length === 0 ? (
        <p className="mt-4 rounded-md border border-dashed border-[#DED8CC] bg-[#FAF8F4] px-4 py-6 text-center text-sm text-[#4A544C]">
          Belum ada riwayat kejadian. Masukkan sampah atau kirim perintah simulasi dari ESP32.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <caption className="visually-hidden">
              Daftar 20 kejadian transisi FST tempat sampah pintar terbaru
            </caption>
            <thead>
              <tr className="border-b border-[#DED8CC] text-xs font-medium text-[#4A544C]">
                <th scope="col" className="py-2.5 pr-4">
                  Waktu
                </th>
                <th scope="col" className="py-2.5 pr-4">
                  Transisi FST
                </th>
                <th scope="col" className="py-2.5 pr-4">
                  Jenis Sampah
                </th>
                <th scope="col" className="py-2.5 text-right">
                  Kapasitas (Org / Anorg)
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EFEBE2]">
              {events.map((ev) => (
                <tr key={ev.id}>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-xs text-[#4A544C]">
                    {formatTimeId(ev.created_at)}
                  </td>
                  <td className="py-2.5 pr-4 font-mono text-xs text-[#1E2620]">
                    {formatTransition(ev)}
                  </td>
                  <td className="whitespace-nowrap py-2.5 pr-4 text-xs font-medium text-[#1E2620]">
                    {formatWasteType(ev.waste_type)}
                  </td>
                  <td className="whitespace-nowrap py-2.5 text-right text-xs tabular-nums text-[#4A544C]">
                    {Number(ev.organic_fill_pct).toFixed(0)}% /{" "}
                    {Number(ev.inorganic_fill_pct).toFixed(0)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
