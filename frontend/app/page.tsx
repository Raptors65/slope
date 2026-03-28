import Link from "next/link";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-24">
      <div
        className="animate-enter max-w-2xl text-center"
        style={{ animationDelay: "0.05s" }}
      >
        <p className="font-mono text-xs tracking-[0.25em] text-[var(--muted)] uppercase">
          GitHub-native onboarding
        </p>
        <h1
          className="mt-4 text-5xl leading-[1.05] font-semibold tracking-tight text-[var(--text)] sm:text-6xl"
          style={{ fontFamily: "var(--font-fraunces), serif" }}
        >
          Trace the path
          <span className="text-[var(--accent)]">.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-md text-lg leading-relaxed text-[var(--muted)]">
          Assigned issues become maps: files, warnings, and live graphs for
          your next engineer.
        </p>
        <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/runs"
            className="rounded-lg bg-[var(--accent)] px-8 py-3.5 text-sm font-semibold tracking-wide text-[var(--bg)] shadow-[0_0_32px_-4px_rgba(196,242,49,0.45)] transition hover:brightness-110"
          >
            View runs
          </Link>
        </div>
      </div>
    </div>
  );
}
