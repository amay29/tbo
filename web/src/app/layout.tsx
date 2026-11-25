import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dashboard Pemantauan | Tempat Sampah Pintar FST",
  description:
    "Pemantauan realtime Finite State Transducer (Mealy) dan kapasitas tempat sampah pintar pemilah otomatis.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="min-h-screen antialiased">
        <a
          href="#konten-utama"
          className="visually-hidden fixed top-3 left-3 z-50 rounded-md bg-[#1E2620] px-4 py-2 text-sm font-medium text-white"
        >
          Lewati ke konten utama
        </a>
        {children}
      </body>
    </html>
  );
}
