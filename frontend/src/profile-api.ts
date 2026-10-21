import { useQuery } from '@tanstack/react-query';

export type Level = 'learning' | 'working' | 'strong';
export type ProfileSkill = { skill_id: string; level: Level; years: number | null };
export type OnboardingDraft = { step: number; status: 'student'|'employed'|'self_employed'|'seeking'|'other'; current_field: string; experience_years: number; country: string; market: string; goal: string; interests: string[]; weekly_hours: number; skills: ProfileSkill[]; completed?: boolean };
export type Profile = { id: string; country: string; interests: string[]; is_demo: boolean; confirmed: boolean; updated_at: string; skills: ProfileSkill[]; onboarding?: OnboardingDraft | null };
export type Candidate = { mention: string; years: number | null; evidence_excerpt: string; confidence: 'low' | 'medium' | 'high'; mapping: string; options: string[] };
export type Extraction = { candidates: Candidate[]; mode: 'local' | 'openai' | 'manual_fallback'; message: string; truncated: boolean };
export type Match = { role_id: string; title: string; score: number; coverage: number; transferable_coverage: number; interest_adjustment: number; explanation: string; source_ids: string[]; gaps: { skill_id: string; name: string; importance: number; gap: number; critical: boolean }[] };
export type Matches = { status: 'ready' | 'insufficient_profile_information'; matches: Match[]; methodology: string; geography_note: string };

// The opaque HttpOnly cookie stays with the browser. No resume or token enters localStorage.
export async function profileRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const multipart = body instanceof FormData;
  const response = await fetch(`/api/profiles${path}`, { method, credentials: 'same-origin', cache: 'no-store',
    headers: { ...(method !== 'GET' ? { 'X-Noka-CSRF': '1' } : {}), ...(!multipart && body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? multipart ? body : JSON.stringify(body) : undefined, signal: AbortSignal.timeout(40000) });
  if (!response.ok) throw new Error(response.status === 413 ? 'File exceeds the 5 MB limit.' : response.status === 422 ? 'Could not read this input. Use an unencrypted text PDF, DOCX, paste text, or add skills manually.' : response.status === 404 ? 'Your private session has expired. Start a new profile.' : 'Profile service unavailable. Your changes are still on this page; retry when ready.');
  return response.status === 204 ? undefined as T : await response.json() as T;
}
export function useProfile() {
  const query = useQuery({ queryKey: ['private-profile'], queryFn: () => profileRequest<{ profile: Profile | null }>('/current'), retry: false });
  return { ...query, journeyPath: query.data?.profile?.confirmed ? '/universe' : '/profile/intake' };
}
