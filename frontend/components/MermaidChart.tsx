"use client";

import { useEffect, useRef, useState } from "react";
import { normalizeMermaidSource } from "@/lib/mermaidNormalize";

type Props = {
  chart: string;
};

export function MermaidChart({ chart }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const text = normalizeMermaidSource(chart);
    if (!text) return;

    let cancelled = false;
    const el = hostRef.current;
    if (!el) return;

    (async () => {
      setError(null);
      el.innerHTML = "";
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "loose",
          fontFamily: "var(--font-mono), ui-monospace, monospace",
          themeVariables: {
            primaryColor: "#101816",
            primaryTextColor: "#f2efe9",
            primaryBorderColor: "#1e2a26",
            lineColor: "#c4f231",
            secondaryColor: "#1a2420",
            tertiaryColor: "#0c0d10",
            mainBkg: "#101816",
            nodeBorder: "#c4f231",
            clusterBkg: "#0f1513",
            titleColor: "#f2efe9",
            edgeLabelBackground: "#101816",
          },
        });
        const id = `g${Math.random().toString(36).slice(2, 11)}`;
        const { svg } = await mermaid.render(id, text);
        if (!cancelled && hostRef.current) {
          hostRef.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [chart]);

  if (!normalizeMermaidSource(chart)) {
    return (
      <p className="text-[var(--muted)] text-sm font-sans">
        No diagram for this run.
      </p>
    );
  }

  if (error) {
    return (
      <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200 font-mono">
        {error}
      </p>
    );
  }

  return (
    <div
      ref={hostRef}
      className="mermaid-host flex min-h-[200px] justify-center overflow-x-auto [&_svg]:max-w-full"
    />
  );
}
