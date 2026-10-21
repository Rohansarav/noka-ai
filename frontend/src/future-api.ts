import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useProfile, type Match } from './profile-api';
export type Scenario = 'acceleration' | 'governed' | 'collaboration';
export type FutureMatch = Match & { planning_index: number; context_emphasis?:number; scenario_emphasis: number; scenario_reason: string; priority_skills: string[] };
export type Task = Match['gaps'][number] & { note: string; status: 'planned' | 'in_progress' | 'completed'; effort_hours: number; start_week: number; end_week: number; objective: string; activity: string; project: string; why: string; scenario_priority: boolean; estimate_method: string };
export type Future = { analysis_context?:import('./profile-api').OnboardingDraft;  worlds: Record<Scenario, {pathway: Task[]; future_self: string | null}>;  profile_id: string; profile_revision: string; scenario: Scenario; role_id: string | null; weekly_hours: number; version: string; scenarios: Record<Scenario, { name: string; assumption: string; skills: string[] }>; matches: FutureMatch[]; pathway: Task[]; future_self: string | null; comparisons: Record<Scenario, FutureMatch[]>; method: string; conversation: { question: string; execution_id: string; scenario: string; created_at: string }[] };
export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, { method, credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json', ...(method !== 'GET' ? { 'X-Noka-CSRF': '1' } : {}) }, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error(response.status === 404 ? 'Create and confirm your profile to begin.' : 'This change could not be saved. Please retry.');
  return response.json() as Promise<T>;
}
export function useFuture() {
  const profile = useProfile();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ['future', profile.data?.profile?.id, profile.data?.profile?.updated_at], queryFn: async () => {
    const data=await api<Future>('/profiles/current/future');
    if(!data.scenarios || !Array.isArray(data.matches) || !Array.isArray(data.pathway)) throw new Error('Future workspace response unavailable.');
    return data;
  }, enabled: !!profile.data?.profile?.confirmed, retry: false });
  const save = useMutation({ scope:{id:'future:'+profile.data?.profile?.id}, mutationFn: (body: { scenario?: Scenario; role_id?: string; weekly_hours?: number }) => api<Future>('/profiles/current/future', 'PUT', body), onMutate: async body => { const key=['future',profile.data?.profile?.id,profile.data?.profile?.updated_at]; await client.cancelQueries({queryKey:key}); const previous=client.getQueryData<Future>(key); if(previous && body.scenario && previous.worlds?.[body.scenario]) client.setQueryData(key,{...previous,scenario:body.scenario,matches:previous.comparisons[body.scenario],...previous.worlds[body.scenario]}); return {previous,key}; }, onError: (_error,_body,context) => { if(context?.previous) client.setQueryData(context.key,context.previous); }, onSuccess: data => { client.setQueryData(['future', data.profile_id, profile.data?.profile?.updated_at], data); void client.invalidateQueries({queryKey:['career-graph']}); } });
  const progress = useMutation({ scope:{id:'future:'+profile.data?.profile?.id}, mutationFn: (body: { skill_id: string; status?: Task['status']; note?: string }) => api<Future>('/profiles/current/pathway', 'PUT', body), onSuccess: data => client.setQueryData(['future', data.profile_id, profile.data?.profile?.updated_at], data) });
  return { ...query, save, progress, profileLoading:profile.isPending, profile: profile.data?.profile };
}
