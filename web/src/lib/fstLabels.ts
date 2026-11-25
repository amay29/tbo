import type { BinEvent, FstState, WasteType } from "./types";

export const STATE_META: Record<
  FstState,
  { label: string; description: string; badgeClass: string }
> = {
  q0: {
    label: "Siaga",
    description: "Siap menerima sampah atau perintah dari dashboard.",
    badgeClass:
      "bg-[#EBF1EB] text-[#2F4A32] border-[#B6C7B7]",
  },
  q1: {
    label: "Tutup Terbuka",
    description: "Tutup utama sedang terbuka agar pengguna memasukkan sampah.",
    badgeClass:
      "bg-[#EBF0F3] text-[#324653] border-[#B8C7D1]",
  },
  q2: {
    label: "Memilah",
    description: "Kamera sedang mengenali jenis sampah organik atau anorganik.",
    badgeClass:
      "bg-[#F5EFE3] text-[#66441A] border-[#D9C6A3]",
  },
  qF: {
    label: "Penuh",
    description: "Salah satu atau kedua keranjang penuh. Tutup terkunci sampai dikosongkan.",
    badgeClass:
      "bg-[#F9EAE7] text-[#8A3228] border-[#DFB2AC]",
  },
};

export function formatWasteType(wasteType: WasteType | null): string {
  if (wasteType === "organic") return "Organik";
  if (wasteType === "inorganic") return "Anorganik";
  if (wasteType === "unknown") return "Gagal klasifikasi (residu)";
  return "-";
}

export function formatTransition(event: Pick<BinEvent, "from_state" | "input" | "output" | "to_state">): string {
  return `${event.from_state} --${event.input} / ${event.output}--> ${event.to_state}`;
}

export function formatTimeId(isoString: string): string {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}
