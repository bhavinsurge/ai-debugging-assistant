"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { api, InvestigationReport } from "@/lib/api";

export default function InvestigationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const me = await api.me();
      if (!me.success) {
        router.push("/login");
        return;
      }
      const res = await api.getInvestigation(params.id);
      if (!res.success || !res.data) {
        setError(res.error?.message || "Not found");
        return;
      }
      setReport(res.data);
    })();
  }, [params.id, router]);

  const evidenceMap = useMemo(() => {
    const map = new Map<string, InvestigationReport["evidence"][number]>();
    report?.evidence.forEach((e) => map.set(e.id, e));
    return map;
  }, [report]);

  if (error) {
    return (
      <AppShell>
        <p className="text-signal">{error}</p>
      </AppShell>
    );
  }

  if (!report) {
    return (
      <AppShell>
        <p className="text-ink/50">Loading report…</p>
      </AppShell>
    );
  }

  const hyp = report.primary_hypothesis;

  return (
    <AppShell>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-signal">
            Investigation report
          </p>
          <h1 className="mt-1 font-display text-3xl font-semibold text-moss">{report.title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-ink/65">{report.symptom}</p>
        </div>
        <div className="font-mono text-xs text-ink/50">
          <div>provider: {report.llm_provider}</div>
          <div>status: {report.status}</div>
          <div>
            service: {report.service || "—"} · {report.environment}
          </div>
        </div>
      </div>

      {report.warnings.length > 0 && (
        <div className="mt-6 border border-signal/30 bg-signal/5 px-4 py-3 text-sm text-ink/80">
          {report.warnings.map((w) => (
            <div key={w}>{w}</div>
          ))}
        </div>
      )}

      <section className="mt-8 border border-line bg-paper/80 p-5">
        <h2 className="font-display text-xl font-semibold text-moss">Primary hypothesis</h2>
        {hyp ? (
          <>
            <p className="mt-3 text-base leading-relaxed text-ink">{hyp.statement}</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <ConfidenceBar value={hyp.confidence} />
              <span className="font-mono text-xs text-ink/50">
                {Math.round(hyp.confidence * 100)}% confidence
              </span>
            </div>
            <p className="mt-3 text-sm text-ink/60">{hyp.rationale}</p>
            <div className="mt-4">
              <p className="font-mono text-[11px] uppercase tracking-wider text-ink/45">
                Cited evidence
              </p>
              <ul className="mt-2 space-y-2">
                {hyp.evidence_ids.map((id) => {
                  const ev = evidenceMap.get(id);
                  return (
                    <li key={id} className="border-l-2 border-moss/40 pl-3 text-sm">
                      <span className="font-mono text-xs text-moss">{id}</span>
                      <div className="text-ink/75">{ev?.summary || "Evidence item"}</div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </>
        ) : (
          <p className="mt-3 text-sm text-ink/50">No hypothesis produced.</p>
        )}
      </section>

      <section className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="border border-line bg-paper/80 p-5">
          <h2 className="font-display text-lg font-semibold text-moss">Recommended investigation</h2>
          <ol className="mt-4 space-y-3">
            {report.recommended_investigation.map((step) => (
              <li key={step.order} className="text-sm">
                <div className="font-medium text-ink">
                  {step.order}. {step.action}
                </div>
                <div className="text-ink/55">{step.reason}</div>
                {step.related_evidence_ids.length > 0 && (
                  <div className="mt-1 font-mono text-[11px] text-moss/80">
                    {step.related_evidence_ids.join(", ")}
                  </div>
                )}
              </li>
            ))}
          </ol>
        </div>

        <div className="border border-line bg-paper/80 p-5">
          <h2 className="font-display text-lg font-semibold text-moss">Tools invoked</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {report.tools_invoked.map((t) => (
              <span key={t} className="rounded bg-mist px-2 py-1 font-mono text-xs text-moss">
                {t}()
              </span>
            ))}
          </div>
          {report.alternate_hypotheses.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-ink/70">Alternates</h3>
              <ul className="mt-2 space-y-2 text-sm text-ink/65">
                {report.alternate_hypotheses.map((a) => (
                  <li key={a.statement}>
                    {a.statement}{" "}
                    <span className="font-mono text-xs">({Math.round(a.confidence * 100)}%)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </section>

      <section className="mt-6 border border-line bg-paper/80 p-5">
        <h2 className="font-display text-lg font-semibold text-moss">
          Evidence trail ({report.evidence.length})
        </h2>
        <ul className="mt-4 max-h-[420px] space-y-3 overflow-auto">
          {report.evidence.map((e) => (
            <li key={e.id} className="border-b border-line/70 pb-3 text-sm last:border-0">
              <div className="flex flex-wrap gap-2 font-mono text-[11px] text-ink/45">
                <span className="text-moss">{e.id}</span>
                <span>{e.tool}</span>
                <span>{e.source}</span>
                {e.relevance != null && <span>rel {e.relevance.toFixed(2)}</span>}
              </div>
              <p className="mt-1 text-ink/80">{e.summary}</p>
            </li>
          ))}
        </ul>
      </section>
    </AppShell>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="h-2 w-40 overflow-hidden rounded-full bg-mist">
      <div className="h-full rounded-full bg-moss transition-all duration-700" style={{ width: `${pct}%` }} />
    </div>
  );
}
