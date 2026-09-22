import Link from "next/link";

export default function HomePage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="absolute inset-0 grid-noise opacity-70" />
      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-6 py-16">
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.22em] text-signal animate-rise">
          Local RAG · tool-calling · evidence-first
        </p>
        <h1 className="font-display text-5xl font-semibold leading-[1.05] tracking-tight text-moss sm:text-7xl animate-rise [animation-delay:80ms]">
          RootCause
        </h1>
        <p className="mt-5 max-w-xl text-lg text-ink/70 animate-rise [animation-delay:140ms]">
          An AI debugging assistant that retrieves logs, metrics, deploys, dependencies,
          incidents, and runbooks — then forms root-cause hypotheses only from cited evidence.
        </p>
        <div className="mt-8 flex flex-wrap gap-3 animate-rise [animation-delay:200ms]">
          <Link
            href="/login"
            className="rounded-md bg-moss px-5 py-2.5 text-sm font-semibold text-paper shadow-sm transition hover:bg-ink"
          >
            Open console
          </Link>
          <a
            href="http://localhost:8009/docs"
            className="rounded-md border border-line bg-paper/70 px-5 py-2.5 text-sm font-medium text-moss hover:border-moss"
          >
            API docs
          </a>
        </div>
      </div>
    </div>
  );
}
