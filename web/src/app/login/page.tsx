import type { Metadata } from "next";
import { LoginForm } from "@/components/LoginForm";

export const metadata: Metadata = {
  title: "Masuk Admin | Tempat Sampah Pintar FST",
};

export default function LoginPage() {
  return (
    <main
      id="konten-utama"
      className="flex min-h-screen items-center justify-center px-4 py-10"
    >
      <LoginForm />
    </main>
  );
}
