/**
 * LLMs often emit `A[app.handle()]` — parentheses inside `[]` confuse Mermaid's
 * lexer (it expects `]` to close the node but hits `(` first). Wrap those labels
 * in double quotes: A["app.handle()"].
 */
export function normalizeMermaidSource(raw: string): string {
  let s = raw.trim();
  if (!s) return s;

  const fence = /^```(?:mermaid)?\s*\n?([\s\S]*?)\n?```$/im;
  const m = s.match(fence);
  if (m) s = m[1].trim();

  // Jump to first diagram keyword if the model added prose above
  const kw = s.search(
    /^(?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)\b/im,
  );
  if (kw > 0) s = s.slice(kw);

  // id[label] → id["label"] when label contains ( or ) and isn't already quoted
  s = s.replace(
    /(\b[A-Za-z][A-Za-z0-9_]*)\[([^\]]+)\]/g,
    (full, id: string, label: string) => {
      const t = label.trim();
      if (/^\s*"/.test(t)) return full;
      if (!/[()]/.test(t)) return full;
      const escaped = t.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      return `${id}["${escaped}"]`;
    },
  );

  // id{label} → id{"label"} for decision nodes when label contains parentheses
  s = s.replace(
    /(\b[A-Za-z][A-Za-z0-9_]*)\{([^}]+)\}/g,
    (full, id: string, label: string) => {
      const t = label.trim();
      if (/^\s*"/.test(t)) return full;
      if (!/[()]/.test(t)) return full;
      const escaped = t.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      return `${id}{"${escaped}"}`;
    },
  );

  return s;
}
