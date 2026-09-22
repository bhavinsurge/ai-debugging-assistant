"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, InvestigationSummary } from "@/lib/api";

export default function InvestigationsPage() {
  const router = useRouter();
  const [items, setItems] = useState<InvestigationSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const me = await api.me();
      if (!me.success) {
        router.push("/login");
        return;
      }
      const list = await api.listInvestigations();
      if (!list.success) {
        setError(list.error?.message || "Failed to load");
        return;
      }
      setItems(list.data || []);
    })();
  }, [router]);

  return (
    <AppShell>
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold text-moss">Investigations</h1>
          <p className="mt-1 text-sm text-ink/60">
            Each report cites retrieved evidence — hypotheses never invent unseen signals.
          </p>
        </div>
        <Link
          href="/app/new"
          className="rounded-md bg-signal px-4 py-2 text-sm font-semibold text-white hover:bg-ink"
        >
          Start investigation
        </Link>
      </div>

      {error && <p className="mt-6 text-signal">{error}</p>}

      <ul className="mt-8 divide-y divide-line border border-line bg-paper/70">
        {items.length === 0 && (
          <li className="px-4 py-10 text-center text-sm text-ink/50">
            No investigations yet. Start one to collect evidence and form a hypothesis.
          </li>
        )}
        {items.map((item) => (
          <li key={item.id}>
            <Link
              href={`/app/investigations/${item.id}`}
              className="flex flex-wrap items-center justify-between gap-3 px-4 py-4 transition hover:bg-mist/70"
            >
              <div>
                <div className="font-medium text-ink">{item.title}</div>
                <div className="mt-0.5 max-w-2xl truncate text-sm text-ink/55">{item.symptom}</div>
              </div>
              <div className="flex items-center gap-3 font-mono text-xs text-ink/50">
                <span>{item.service || "—"}</span>
                <span className="rounded bg-mist px-2 py-0.5 uppercase">{item.status}</span>
                {item.confidence != null && (
                  <span className="text-moss">{Math.round(item.confidence * 100)}%</span>
                )}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </AppShell>
  );
}
