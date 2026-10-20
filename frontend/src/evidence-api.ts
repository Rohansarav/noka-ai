// Public contracts align with backend/app/schemas.py. No profile/resume data is sent.
export type Source = { id: string; dataset: string; title: string; canonical_url: string; file_url: string; publisher: string; publication_date: string | null; retrieved_at: string; version: string; sha256: string; license: string; license_url: string; geography: string; granularity: string; notes: string };
export type Role = { id: string; title: string; description: string; occupation_code: string; country: string; sector: string | null; evidence_status: 'sector_proxy_only' | 'not_covered'; crosswalk_rationale: string; curation_status: string; source_id: string; individual_statistically_forecastable: false };
export type Skill = { id: string; canonical_name: string; aliases: string[]; category: string; source_id: string };
export type SDGLink = { target_id: string; role_id: string | null; skill_id: string | null; entity_name: string; rationale: string; source_id: string; curation_status: string; reviewed_by: string | null; reviewed_at: string | null };
export type RoleDetail = Role & { source: Source; skills: { skill: Skill; required_importance: number; scale: 'O*NET IM 1–5'; source_id: string }[]; sdg_links: SDGLink[] };
export type Sector = { country: string; sector: string; observation_count: number; start_date: string; end_date: string };
export type Run = { dataset: string; started_at: string; completed_at: string; status: string; row_count: number; message: string };
export type Summary = { database: 'postgresql' | 'sqlite'; counts: Record<string, number>; countries: string[]; start_date: string | null; end_date: string | null; sectors: Sector[]; sources: Source[]; last_successful_imports: Run[]; last_attempt: Run | null; structural_directions: { subject: string; direction: string; rationale: string; horizon: string; source_id: string; curation_status: string }[]; limitations: string[] };
export type History = { country: 'US'; sector: string; granularity: string; variable: string; frequency: string; baseline: string; points: { date: string; indexed_value: number; adjusted_flag: boolean; source_id: string }[]; sources: Source[] };
export type Goal = { id: number; title: string; description: string; source_id: string; official_url: string; targets: { id: string; goal_id: number; description: string; source_id: string; links: SDGLink[] }[] };

// Validate each top-level response rather than accidentally treating SPA HTML as data.
export async function getEvidence<T>(path: string, key: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal: signal ?? AbortSignal.timeout(15000) });
  if (!response.ok) throw new Error('Evidence unavailable');
  const data: unknown = await response.json();
  if (!data || typeof data !== 'object' || !(key in data)) throw new Error('Unexpected evidence response');
  return data as T;
}

export const dateLabel = (value: string | null) => value ? new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(value)) : 'Not supplied';
export const timeLabel = (value: string | null) => value ? new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZoneName: undefined, timeZone: 'Asia/Kuala_Lumpur' }).format(new Date(value)) + ' MYT' : 'Never';
