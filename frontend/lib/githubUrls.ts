const EXT = /\.(js|cjs|mjs|ts|tsx|jsx|json|md|mdx|py|go|rs|java|kt|kts|swift|rb|php|cs|css|scss|html|vue|svelte|yml|yaml|toml|xml|gradle|properties|sh|bash|dockerfile|lock)$/i;

/** True if the label plausibly names a repo-relative file path (not prose). */
export function looksLikeRepoPath(label: string): boolean {
  const t = label.trim();
  if (!t || t.length > 512) return false;
  if (/^https?:\/\//i.test(t)) return false;
  if (/[\n\r]/.test(t)) return false;
  if (/^%%/.test(t)) return false;
  if (/[<>"|{}]/.test(t)) return false;
  if (/\s--\s/.test(t)) return false;
  if (t.includes(" ") && !t.includes("/")) return false;

  if (t.includes("/")) {
    if (t.startsWith("/")) return false;
    return true;
  }

  return EXT.test(t);
}

export function githubBlobUrl(
  owner: string,
  repo: string,
  branch: string,
  filePath: string,
): string {
  const p = filePath.trim().replace(/^\/+/, "");
  if (!p) return "";
  if (p.endsWith("/")) {
    const enc = p
      .replace(/\/+$/, "")
      .split("/")
      .map((s) => encodeURIComponent(s))
      .join("/");
    return `https://github.com/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/tree/${encodeURIComponent(branch)}/${enc}`;
  }
  const enc = p.split("/").map((s) => encodeURIComponent(s)).join("/");
  return `https://github.com/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/blob/${encodeURIComponent(branch)}/${enc}`;
}

export function defaultGitBranch(branch: string | null | undefined): string {
  const b = branch?.trim();
  return b || "main";
}
