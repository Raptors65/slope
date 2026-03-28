/** Mirrors backend OnboardingRunSummary / OnboardingRunRecord JSON. */

export type RunSummary = {
  id: string;
  created_at: string;
  owner: string;
  repo: string;
  issue_number: number;
  issue_title: string;
  map_ready: boolean;
};

export type MapFileEntry = {
  path: string;
  summary: string;
};

export type OnboardingMapPayload = {
  files_to_read: MapFileEntry[];
  warnings: string[];
  mermaid: string;
};

export type FullRun = {
  id: string;
  created_at: string;
  owner: string;
  repo: string;
  issue_number: number;
  issue_title: string;
  issue_body: string;
  default_branch: string | null;
  ticket_analysis: Record<string, unknown>;
  augment: Record<string, unknown> | null;
  onboarding_map: OnboardingMapPayload | null;
  memory_snippets: string[];
  image_urls: string[];
};
