"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabaseClient";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const configured = isSupabaseConfigured();

  useEffect(() => {
    if (!configured) return;
    const supabase = getSupabaseClient();
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        router.replace("/");
      }
    });
  }, [configured, router]);

  function validateEmail(value: string): string {
    if (!value.trim()) return "Email wajib diisi.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) {
      return "Masukkan format email yang benar.";
    }
    return "";
  }

  function validatePassword(value: string): string {
    if (!value) return "Kata sandi wajib diisi.";
    return "";
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitError("");

    const nextEmailErr = validateEmail(email);
    const nextPassErr = validatePassword(password);
    setEmailError(nextEmailErr);
    setPasswordError(nextPassErr);

    if (nextEmailErr) {
      document.getElementById("email")?.focus();
      return;
    }
    if (nextPassErr) {
      document.getElementById("password")?.focus();
      return;
    }

    if (!configured) {
      setSubmitError(
        "Konfigurasi Supabase belum diatur. Lengkapi file .env.local terlebih dahulu."
      );
      return;
    }

    setIsLoading(true);
    try {
      const supabase = getSupabaseClient();
      const { error } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (error) {
        setSubmitError("Email atau kata sandi tidak cocok. Silakan periksa kembali.");
        return;
      }

      router.replace("/");
    } catch {
      setSubmitError("Gagal terhubung ke layanan autentikasi Supabase.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-md rounded-lg border border-[#DED8CC] bg-white p-6 sm:p-8">
      <h1 id="login-title" className="text-xl font-semibold text-[#1E2620]">
        Masuk Admin Tempat Sampah Pintar
      </h1>
      <p className="mt-1.5 text-sm text-[#4A544C]">
        Gunakan akun admin Supabase untuk memantau status pemilahan dan mengendalikan tutup.
      </p>

      {!configured && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-[#DFB2AC] bg-[#F9EAE7] p-3 text-sm text-[#8A3228]"
        >
          Variabel <code className="font-mono">NEXT_PUBLIC_SUPABASE_URL</code> dan{" "}
          <code className="font-mono">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> belum diatur pada{" "}
          <code className="font-mono">.env.local</code>.
        </div>
      )}

      {submitError && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-[#DFB2AC] bg-[#F9EAE7] p-3 text-sm text-[#8A3228]"
        >
          {submitError}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        noValidate
        aria-labelledby="login-title"
        className="mt-6 space-y-5"
      >
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-[#1E2620]"
          >
            Email Admin <span aria-hidden="true">*</span>
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            autoCorrect="off"
            autoCapitalize="none"
            spellCheck={false}
            enterKeyHint="next"
            required
            value={email}
            aria-invalid={emailError ? "true" : "false"}
            aria-describedby={emailError ? "email-error" : undefined}
            onChange={(e) => {
              const val = e.target.value;
              setEmail(val);
              if (emailError) setEmailError(validateEmail(val));
            }}
            onBlur={(e) => {
              if (e.target.value.trim().length > 0) {
                setEmailError(validateEmail(e.target.value));
              }
            }}
            className="field-input mt-1.5 block min-h-12 w-full rounded-md border border-[#746E62] bg-white px-3.5 py-2.5 text-base text-[#1E2620] transition-colors duration-150"
          />
          {emailError && (
            <p id="email-error" className="mt-1.5 text-sm text-[#8A3228]">
              {emailError}
            </p>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between gap-2">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-[#1E2620]"
            >
              Kata Sandi <span aria-hidden="true">*</span>
            </label>
            <button
              type="button"
              aria-pressed={showPassword}
              onClick={() => setShowPassword((prev) => !prev)}
              className="rounded px-2 py-1 text-xs font-medium text-[#4A544C] hover:bg-[#F3EFE6] hover:text-[#1E2620]"
            >
              {showPassword ? "Sembunyikan" : "Tampilkan"}
            </button>
          </div>
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            enterKeyHint="done"
            required
            value={password}
            aria-invalid={passwordError ? "true" : "false"}
            aria-describedby={passwordError ? "password-error" : undefined}
            onChange={(e) => {
              const val = e.target.value;
              setPassword(val);
              if (passwordError) setPasswordError(validatePassword(val));
            }}
            onBlur={(e) => {
              if (e.target.value.length > 0) {
                setPasswordError(validatePassword(e.target.value));
              }
            }}
            className="field-input mt-1.5 block min-h-12 w-full rounded-md border border-[#746E62] bg-white px-3.5 py-2.5 text-base text-[#1E2620] transition-colors duration-150"
          />
          {passwordError && (
            <p id="password-error" className="mt-1.5 text-sm text-[#8A3228]">
              {passwordError}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="min-h-12 w-full cursor-pointer rounded-md bg-[#4A6B4D] px-4 py-2.5 text-base font-medium text-white transition-colors duration-150 hover:bg-[#3D5940] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? "Memeriksa akun..." : "Masuk ke Dashboard"}
        </button>
      </form>
    </div>
  );
}
