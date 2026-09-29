"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";

const links = [
  { href: "/app", label: "Investigations" },
  { href: "/app/new", label: "New" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    await api.logout();
    router.push("/login");
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-line/80 bg-paper/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <Link href="/app" className="group flex items-baseline gap-2">
            <span className="font-display text-2xl font-semibold tracking-tight text-moss transition group-hover:text-signal">
              RootCause
            </span>
            <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink/45">
              evidence-bound
            </span>
          </Link>
          <nav className="flex items-center gap-1">
            {links.map((l) => {
              const active = pathname === l.href;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-md px-3 py-1.5 text-sm transition ${
                    active ? "bg-moss text-paper" : "text-ink/70 hover:bg-mist hover:text-ink"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
            <button
              onClick={logout}
              className="ml-2 rounded-md px-3 py-1.5 text-sm text-ink/55 hover:bg-mist hover:text-ink"
            >
              Sign out
            </button>
          </nav>
        </div>
        <div className="h-0.5 origin-left bg-signal/80 animate-pulse-bar" />
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8 animate-rise">{children}</main>
    </div>
  );
}
