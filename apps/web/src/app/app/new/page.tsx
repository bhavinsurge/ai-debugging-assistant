"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

export default function NewInvestigationPage() {
  const router = useRouter();
  const [title, setTitle] = useState("Checkout 5xx spike");
  const [symptom, setSymptom] = useState(
    "checkout-api returning 500 errors on /checkout with NullPointerException in PaymentClient after recent deploy"
  );
  const [service, setService] = useState("checkout-api");
  const [environment, setEnvironment] = useState("production");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    const res = await api.createInvestigation({
      title,
      symptom,
      service: service || undefined,
      environment,
      time_window_minutes: 60,
    });
    setLoading(false);
    if (!res.success || !res.data) {
      setError(res.error?.message || "Investigation failed");
      return;
    }
    router.push(`/app/investigations/${res.data.investigation_id}`);
  }

  return (
    <AppShell>
      <h1 className="font-display text-3xl font-semibold text-moss">New investigation</h1>
      <p className="mt-1 text-sm text-ink/60">
        Describe the symptom. RootCause will call tools, retrieve evidence, then hypothesize.
      </p>

      <form onSubmit={onSubmit} className="mt-8 max-w-2xl space-y-4 border border-line bg-paper/80 p-6">
        <label className="block text-sm">
          <span className="mb-1 block font-medium">Title</span>
          <input
            className="w-full rounded-md border border-line px-3 py-2 outline-none ring-moss focus:ring-2"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            minLength={3}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium">Symptom</span>
          <textarea
            className="min-h-28 w-full rounded-md border border-line px-3 py-2 outline-none ring-moss focus:ring-2"
            value={symptom}
            onChange={(e) => setSymptom(e.target.value)}
            required
            minLength={10}
          />
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Service</span>
            <input
              className="w-full rounded-md border border-line px-3 py-2 outline-none ring-moss focus:ring-2"
              value={service}
              onChange={(e) => setService(e.target.value)}
              placeholder="checkout-api"
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Environment</span>
            <input
              className="w-full rounded-md border border-line px-3 py-2 outline-none ring-moss focus:ring-2"
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
            />
          </label>
        </div>
        {error && <p className="text-sm text-signal">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-moss px-5 py-2.5 text-sm font-semibold text-paper hover:bg-ink disabled:opacity-60"
        >
          {loading ? "Collecting evidence…" : "Run investigation"}
        </button>
      </form>
    </AppShell>
  );
}
