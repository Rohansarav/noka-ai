import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export type StartingPoint = 'unassessed'|'learn'|'practice'|'demonstrate';
export type Requirement = {id:string;source_id:string;title:string;quote:string;priority:'required'|'preferred'|'unspecified'};
export type Milestone = {id:string;title:string;objective:string;requirement_ids:string[];steps:string[];deliverable:string;acceptance_criteria:string[];learn:string;effort_hours:number;note:string;status:'planned'|'in_progress'|'completed'};
export type ResearchRun = {
  update_history?: {id:string;mode:string;status:string;reviewed_at:string;draft?:{reason:string;addition:Milestone|null}}[];
  evolution?: {id:string;mode:'evidence'|'simulation';status:string;message:string;reviewed_at?:string;sources:{id:string;title:string;statement:string;url:string|null;market:string;scope:string;period:string}[];draft?:{reason:string;implications:{task:string;effect:string;explanation:string;conditions:string;source_ids:string[]}[];addition:Milestone|null}}|null;
  id:string;role_id:string;target:string;market:string;created_at:string;
  status:'queued'|'searching'|'extracting'|'analyzing'|'review'|'planning'|'ready'|'failed';
  events:{stage:string;message:string;at:string}[];
  sources:{id:string;title:string;url:string|null;origin:'web'|'manual';retrieved_at:string;location:string;availability:string;reason:string}[];
  requirements:Requirement[];
  review:{reviewed_at:string;reviewed_by:string;items:{requirement_id:string;starting_point:StartingPoint}[]}|null;
  project:{title:string;problem:string;audience:string;why_you:string;scope:string;assumptions:string[];milestones:Milestone[];accepted_at:string|null;accepted_by:string|null}|null;
  error:string|null;
};
export const running = (run?:ResearchRun) => !!run && (['queued','searching','extracting','analyzing','planning'].includes(run.status)||run.evolution?.status==='analyzing');

async function request<T>(path:string, method='GET', body?:unknown):Promise<T> {
  const response=await fetch(`/api/pathway-research${path}`,{method,credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json',...(method!=='GET'?{'X-Noka-CSRF':'1'}:{})},
    body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw new Error(response.status===429?'Research limit reached or another run is active. Wait for it to finish before retrying.':response.status===409?'This research state has changed. Reload your saved research and try again.':response.status===422?'Check the description, selected requirements or evidence note and try again.':'Could not reach your saved research. Your draft is still here; please retry.');
  return response.json();
}

export function usePathwayResearch(profileId:string,roleId:string) {
  const client=useQueryClient(), key=['pathway-research',profileId,roleId];
  const query=useQuery({queryKey:key,queryFn:async()=>{
    const value=await request<{runs:ResearchRun[]}>(`?role_id=${encodeURIComponent(roleId)}`);
    if(!Array.isArray(value.runs))throw new Error('Saved research response unavailable.');
    return value;
  },refetchInterval:q=>q.state.data?.runs.some(running)?1200:false,retry:false});
  const action=useMutation({mutationFn:({path,body,method}:{path:string;body?:unknown;method?:string})=>request<ResearchRun>(path,method??'POST',body),onSuccess:run=>{
    client.setQueryData<{runs:ResearchRun[]}>(key,previous=>({runs:[run,...(previous?.runs??[]).filter(r=>r.id!==run.id)].sort((a,b)=>b.created_at.localeCompare(a.created_at))}));
    void client.invalidateQueries({queryKey:key});
  }});
  return {...query,action};
}
