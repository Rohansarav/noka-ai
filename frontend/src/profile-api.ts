import { useQuery } from '@tanstack/react-query';

export type Level = 'learning' | 'working' | 'strong';
export type CustomSkill = {name:string;level:Level;years:number|null};
export type SoftwareItem = {skill_id:string;name:string;source_id:string;in_demand:boolean};
export type TechnicalAlignment = {status:'source_available'|'no_source_associations';associated_count:number;matched_count:number;matched:SoftwareItem[];explore:SoftwareItem[];note:string};
export type CareerAspiration = {title:string; role_ids:string[]; status:'confirmed'|'unmapped'};
export type ProfileSkill = { skill_id: string; level: Level; years: number | null };
export type OnboardingDraft = { step: number; status: 'student'|'employed'|'self_employed'|'seeking'|'other'; current_field: string; experience_years: number; country: string; market: string; goal: string; custom_skills?:CustomSkill[]; projects?:string; constraints?:string; aspirations?:CareerAspiration[]; interests: string[]; weekly_hours: number; skills: ProfileSkill[]; completed?: boolean };
export type Profile = { id: string; country: string; interests: string[]; is_demo: boolean; confirmed: boolean; updated_at: string; skills: ProfileSkill[]; onboarding?: OnboardingDraft | null };
export type Candidate = { mention: string; mentions?: string[]; years: number | null; evidence_excerpt: string; confidence: 'low' | 'medium' | 'high'; mapping: string; options: string[] };
export type Extraction = { candidates: Candidate[]; mode: 'local' | 'openai' | 'manual_fallback'; message: string; truncated: boolean; warnings?: string[]; duplicates_merged?: number; schema_version?: 'skill-review-v2' };
export type Match = { is_explored?:boolean; discovery_reasons?:string[]; discovery_relevance?:number; limited_requirements?:boolean; assessment?:import('./ReadinessEvidence').Assessment|null; technical?:TechnicalAlignment; readiness_status?:'self_reported'|'not_assessed'; is_target?:boolean; context_alignment?:number; context_reasons?:string[]; selection_reason?:string;  role_id: string; title: string; score: number; coverage: number; transferable_coverage: number; interest_adjustment: number; explanation: string; source_ids: string[]; gaps: { skill_id: string; name: string; importance: number; gap: number; critical: boolean }[] };
export type Matches = { status: 'ready' | 'insufficient_profile_information'; matches: Match[]; methodology: string; geography_note: string };

// The opaque HttpOnly cookie stays with the browser. No resume or token enters localStorage.
export async function profileRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const multipart = body instanceof FormData;
  const response = await fetch(`/api/profiles${path}`, { method, credentials: 'same-origin', cache: 'no-store',
    headers: { ...(method !== 'GET' ? { 'X-Noka-CSRF': '1' } : {}), ...(!multipart && body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? multipart ? body : JSON.stringify(body) : undefined, signal: AbortSignal.timeout(path.endsWith('/analysis')?60000:40000) }).catch((error:Error)=>{throw new Error(error.name==='TimeoutError'||error.name==='AbortError'?'This is taking longer than expected. Your input is still here. Retry, or switch off AI analysis to use local suggestions.':'Could not reach Noka. Your input is still here; check your connection and retry.');});
  if (!response.ok) {
    const detail=await response.json().catch(()=>null);
    const message=typeof detail?.error?.message==='string'&&detail.error.message.length<400?detail.error.message:null;
    throw new Error(message ?? (response.status === 413 ? 'File exceeds the 5 MB limit.' : response.status === 422 ? 'Check your fields and use a readable PDF or DOCX, or enter your experience manually.' : response.status === 404 ? 'Your private session has expired. Start a new profile.' : 'Profile service unavailable. Your changes are still on this page; retry when ready.'));
  }
  return response.status === 204 ? undefined as T : await response.json() as T;
}
export function useProfile() {
  const query = useQuery({ queryKey: ['private-profile'], queryFn: () => profileRequest<{ profile: Profile | null }>('/current'), retry: false });
  return { ...query, journeyPath: query.data?.profile?.confirmed ? '/universe' : '/profile/intake' };
}
