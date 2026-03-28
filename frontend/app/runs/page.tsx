import Link from "next/link";
import { fetchRunSummaries } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  let runs: Awaited<ReturnType<typeof fetchRunSummaries>> = [];
  let err: string | null = null;
  try {
    runs = await fetchRunSummaries();
  } catch (e) {
    err = e instanceof Error ? e.message : "Could not load runs.";
  }

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 px-5 py-12 sm:px-8">
      <header className="mb-12 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link
            href="/"
            className="font-mono text-xs text-[var(--muted)] transition hover:text-[var(--accent)]"
          >
            Back to Slope
          </Link>
          <h1
            className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl"
            style={{ fontFamily: "var(--font-fraunces), serif" }}
          >
            Runs
          </h1>
          <p className="mt-2 max-w-lg text-[var(--muted)]">
            Newest pipeline runs. Open a card for the full map.
          </p>
        </div>
      </header>

      {err ? (
        <div
          className="rounded-xl border border-amber-500/30 bg-[var(--warning-bg)] px-5 py-4 text-amber-100"
          role="alert"
        >
          <p className="font-medium">API unreachable</p>
          <p className="mt-1 text-sm text-amber-200/90">{err}</p>
          <p className="mt-3 font-mono text-xs text-amber-200/70">
            Set NEXT_PUBLIC_API_BASE_URL to your FastAPI URL (example
            http://127.0.0.1:8000) and start the backend.
          </p>
        </div>
      ) : runs.length === 0 ? (
        <p className="text-[var(--muted)]">
          No runs yet. Assign an issue with the webhook connected.
        </p>
      ) : (
        <ul className="flex flex-col gap-4">
          {runs.map((r, i) => (
            <li
              key={r.id}
              className="animate-enter group"
              style={{ animationDelay: `${0.08 + i * 0.07}s` }}
            >
              <Link
                href={`/runs/${r.id}`}
                className="block rounded-xl border border-[var(--surface-border)] bg-[var(--surface)]/85 p-5 transition hover:border-[var(--accent)]/35 hover:shadow-[0_0_40px_-12px_rgba(196,242,49,0.25)] sm:p-6"
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-xs text-[var(--muted)]">
                      {r.created_at.replace("T", " ").replace("Z", " UTC")}
                    </p>
                    <p className="mt-2 truncate text-lg font-medium text-[var(--text)] group-hover:text-[var(--accent)]">
                      {r.issue_title || "(no title)"}
                    </p>
                    <p className="mt-1 font-mono text-sm text-[var(--muted)]">
                      {r.owner}/{r.repo}#{r.issue_number}
                    </p>
                  </div>
                  <span
                    className={
                      r.map_ready
                        ? "shrink-0 self-start rounded-full border border-[var(--accent)]/40 bg-[var(--accent-dim)] px-3 py-1 text-xs font-medium text-[var(--accent)]"
                        : "shrink-0 self-start rounded-full border border-[var(--surface-border)] px-3 py-1 text-xs text-[var(--muted)]"
                    }
                  >
                    {r.map_ready ? "Map ready" : "Partial"}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
