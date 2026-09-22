"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@rootcause.local");
  const [password, setPassword] = useState("Password123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const res = await api.login(email, password);
    setLoading(false);
    if (!res.success) {
      setError(res.error?.message || "Login failed");
      return;
    }
    router.push("/app");
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md animate-rise">
        <Link href="/" className="font-display text-3xl font-semibold text-moss">
          RootCause
        </Link>
        <p className="mt-2 text-sm text-ink/60">Sign in to start an evidence-bound investigation.</p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4 border border-line bg-paper/80 p-6 shadow-sm">
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-ink/80">Email</span>
            <input
              className="w-full rounded-md border border-line bg-white px-3 py-2 outline-none ring-moss focus:ring-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium text-ink/80">Password</span>
            <input
              className="w-full rounded-md border border-line bg-white px-3 py-2 outline-none ring-moss focus:ring-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
            />
          </label>
          {error && <p className="text-sm text-signal">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-moss py-2.5 text-sm font-semibold text-paper hover:bg-ink disabled:opacity-60"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <p className="font-mono text-[11px] text-ink/45">
            Demo: admin@rootcause.local / Password123!
          </p>
        </form>
      </div>
    </div>
  );
}
