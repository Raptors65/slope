import Link from "next/link";

export default function RunNotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-24">
      <h1
        className="text-3xl font-semibold"
        style={{ fontFamily: "var(--font-fraunces), serif" }}
      >
        Run not found
      </h1>
      <p className="mt-3 text-[var(--muted)]">
        That id is not in the local runs store.
      </p>
      <Link
        href="/runs"
        className="mt-8 rounded-lg border border-[var(--surface-border)] px-5 py-2.5 text-sm text-[var(--accent)] transition hover:border-[var(--accent)]/50"
      >
        Back to runs
      </Link>
    </div>
  );
}
