import Link from "next/link";
import { notFound } from "next/navigation";
import { MarkdownBody } from "@/components/MarkdownBody";
import { MermaidChart } from "@/components/MermaidChart";
import { fetchRunById } from "@/lib/api";
import type { OnboardingMapPayload } from "@/lib/types";

export const dynamic = "force-dynamic";

function safeMap(raw: unknown): OnboardingMapPayload | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const files = Array.isArray(o.files_to_read) ? o.files_to_read : [];
  const warnings = Array.isArray(o.warnings) ? o.warnings : [];
  const mermaid = typeof o.mermaid === "string" ? o.mermaid : "";
  return {
    files_to_read: files.map((f) => {
      const x = f as Record<string, unknown>;
      return {
        path: String(x.path ?? ""),
        summary: String(x.summary ?? ""),
      };
    }),
    warnings: warnings.map((w) => String(w)),
    mermaid,
  };
}

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const run = await fetchRunById(id);
  if (!run) notFound();

  const map = run.onboarding_map
    ? safeMap(run.onboarding_map)
    : safeMap(null);
  const analysis = run.ticket_analysis || {};
  const featureArea = String(analysis.feature_area ?? "");
  const taskType = String(analysis.task_type ?? "");
  const risk = String(analysis.risk_surface ?? "");

  return (
    <div className="mx-auto w-full max-w-6xl flex-1 px-5 py-10 sm:px-8">
      <Link
        href="/runs"
        className="font-mono text-xs text-[var(--muted)] transition hover:text-[var(--accent)]"
      >
        ← All runs
      </Link>

      <header className="mt-6 border-b border-[var(--surface-border)] pb-10">
        <p className="font-mono text-xs text-[var(--muted)]">
          {run.created_at.replace("T", " ").replace("Z", " UTC")}
        </p>
        <h1
          className="mt-3 max-w-4xl text-3xl font-semibold leading-tight tracking-tight sm:text-4xl"
          style={{ fontFamily: "var(--font-fraunces), serif" }}
        >
          {run.issue_title || "Issue"}
        </h1>
        <p className="mt-2 font-mono text-sm text-[var(--muted)]">
          {run.owner}/{run.repo}#{run.issue_number}
          {run.default_branch ? ` · ${run.default_branch}` : ""}
        </p>
        {(featureArea || taskType) && (
          <div className="mt-5 flex flex-wrap gap-2">
            {featureArea ? (
              <span className="rounded-md border border-[var(--surface-border)] bg-[var(--bg-elevated)] px-3 py-1 text-xs text-[var(--text)]">
                {featureArea}
              </span>
            ) : null}
            {taskType ? (
              <span className="rounded-md border border-[var(--accent)]/25 bg-[var(--accent-dim)] px-3 py-1 text-xs font-medium text-[var(--accent)]">
                {taskType}
              </span>
            ) : null}
          </div>
        )}
      </header>

      {run.image_urls.length > 0 && (
        <section className="mt-10">
          <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
            Issue images
          </h2>
          <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
            {run.image_urls.map((url) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 overflow-hidden rounded-lg border border-[var(--surface-border)] ring-[var(--accent)]/0 transition hover:ring-2 hover:ring-[var(--accent)]/40"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={url}
                  alt=""
                  className="h-36 w-auto max-w-[min(100vw,320px)] object-cover"
                  loading="lazy"
                />
              </a>
            ))}
          </div>
        </section>
      )}

      {run.issue_body ? (
        <section className="mt-10">
          <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
            Description
          </h2>
          <div className="mt-4 rounded-xl border border-[var(--surface-border)] bg-[var(--surface)]/50 p-5">
            <MarkdownBody text={run.issue_body} />
          </div>
        </section>
      ) : null}

      {risk ? (
        <section className="mt-10">
          <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
            Risk surface
          </h2>
          <p className="mt-3 max-w-3xl text-[var(--text)]/90">{risk}</p>
        </section>
      ) : null}

      <div className="mt-12 grid gap-8 lg:grid-cols-2 lg:gap-10">
        <section>
          <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
            Files to read
          </h2>
          {map && map.files_to_read.length > 0 ? (
            <ol className="mt-4 space-y-4">
              {map.files_to_read.map((f, idx) => (
                <li
                  key={`${f.path}-${idx}`}
                  className="rounded-lg border border-[var(--surface-border)] bg-[var(--surface)]/40 p-4"
                >
                  <span className="font-mono text-sm text-[var(--accent)]">
                    {idx + 1}.
                  </span>{" "}
                  <span className="font-mono text-sm text-[var(--text)]">
                    {f.path}
                  </span>
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">
                    {f.summary}
                  </p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-4 text-sm text-[var(--muted)]">No file list.</p>
          )}
        </section>

        <section>
          <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
            Warnings
          </h2>
          {map && map.warnings.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {map.warnings.map((w, i) => (
                <li
                  key={i}
                  className="rounded-lg border border-[var(--warning)]/25 bg-[var(--warning-bg)] px-4 py-3 text-sm text-amber-100/95"
                >
                  {w}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-[var(--muted)]">No warnings.</p>
          )}
        </section>
      </div>

      {run.memory_snippets.length > 0 && (
        <section className="mt-12">
          <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
            Team memory
          </h2>
          <ul className="mt-4 space-y-3">
            {run.memory_snippets.map((s, i) => (
              <li
                key={i}
                className="rounded-lg border border-[var(--surface-border)] bg-[var(--bg-elevated)]/80 px-4 py-3 text-sm text-[var(--muted)]"
              >
                {s}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-14">
        <h2 className="font-mono text-xs tracking-widest text-[var(--muted)] uppercase">
          Dependency map
        </h2>
        <div className="mt-4 rounded-2xl border border-[var(--accent)]/20 bg-[radial-gradient(ellipse_at_50%_0%,var(--accent-dim),transparent_55%)] p-6 sm:p-8">
          <MermaidChart chart={map?.mermaid ?? ""} />
        </div>
      </section>
    </div>
  );
}
