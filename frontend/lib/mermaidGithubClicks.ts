import {
  defaultGitBranch,
  githubBlobUrl,
  looksLikeRepoPath,
} from "./githubUrls";

function stripLabelQuotes(label: string): string {
  const t = label.trim();
  if (
    (t.startsWith('"') && t.endsWith('"')) ||
    (t.startsWith("'") && t.endsWith("'"))
  ) {
    return t.slice(1, -1);
  }
  return t;
}

/**
 * Append `click id href "url" _blank` lines so Mermaid opens blob URLs (securityLevel: loose + bindFunctions).
 * No tooltip string — Mermaid's body-level hover tooltip has poor contrast on dark pages.
 */
export function appendGithubClickDirectives(
  source: string,
  owner: string,
  repo: string,
  branch: string | null | undefined,
): string {
  const br = defaultGitBranch(branch);
  const clicks: string[] = [];
  const seen = new Set<string>();

  const maybeAdd = (nodeId: string, rawLabel: string) => {
    const label = stripLabelQuotes(rawLabel);
    if (!looksLikeRepoPath(label)) return;
    if (seen.has(nodeId)) return;
    seen.add(nodeId);
    const url = githubBlobUrl(owner, repo, br, label);
    if (!url) return;
    const escUrl = url.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    clicks.push(`click ${nodeId} href "${escUrl}" _blank`);
  };

  const reBracket = /(\b[A-Za-z][A-Za-z0-9_]*)\[([^\]]+)\]/g;
  let m: RegExpExecArray | null;
  while ((m = reBracket.exec(source)) !== null) {
    maybeAdd(m[1], m[2]);
  }

  const reStadium = /(\b[A-Za-z][A-Za-z0-9_]*)\(([^)]+)\)/g;
  while ((m = reStadium.exec(source)) !== null) {
    const inner = m[2].trim();
    if (
      inner === "" ||
      inner === "()" ||
      /^call\s/i.test(inner) ||
      /^href\s/i.test(inner)
    ) {
      continue;
    }
    maybeAdd(m[1], inner);
  }

  if (clicks.length === 0) return source;
  return `${source.trim()}\n${clicks.join("\n")}\n`;
}
