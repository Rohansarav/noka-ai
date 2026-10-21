import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render as rtlRender, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
function render(ui:Parameters<typeof rtlRender>[0]){return rtlRender(ui,{wrapper:MemoryRouter});}
import AgentActivityPanel from './AgentActivityPanel';
import UniverseLoading from './UniverseLoading';
import { validEffects, type AgentResult, type Execution } from './agent-api';
import type { CareerGraphData } from './universe-types';

// Attributed, anonymized actual graph from Phase 3.5A; provider output below is mocked.
const graph: CareerGraphData = JSON.parse(readFileSync(resolve('docs/qa/phase3_5a/career-graph-example.json'),'utf8'));
const role = graph.nodes.find(n=>n.type==='role')!;
const skill = graph.nodes.find(n=>n.type==='owned_skill')!;
const result: AgentResult = {sections:[{kind:'fit',data:{title:role.label,score:role.score,explanation:role.explanation}}], effects:{focus_role:role.id,highlight_skills:[skill.id],open_evidence:null}, profile_revision:graph.profile_revision!,notice:'Server-assembled heuristic evidence; not a forecast.'};
const queued: Execution = {id:'opaque-test',status:'queued',error_code:null,tool_count:0,token_usage:0,result:null,events:[{sequence:1,agent:'matchmaker',type:'queued',status:'queued',at:'now',message:'Request accepted.',payload:{}}]};
let status: Execution;
let requests: {path:string; body:unknown}[];
let listeners: Record<string,()=>void>;
beforeEach(()=>{
  status=structuredClone(queued); requests=[]; listeners={};
  vi.stubGlobal('EventSource',class {addEventListener(name:string,fn:()=>void){listeners[name]=fn;} close(){}});
  vi.stubGlobal('fetch',vi.fn(async(input,init)=>{requests.push({path:String(input),body:init?.body ? JSON.parse(init.body):null}); return {ok:true,json:async()=>String(input).endsWith('/cancel') ? {...status,status:'cancelled'} : status};}));
});
afterEach(()=>vi.unstubAllGlobals());

describe('authentic agent activity',()=>{
  it('accepts retrieved software/context highlights only when those nodes exist in the current graph',()=>{
    const expanded={...graph,nodes:[...graph.nodes,{...skill,id:'skill:software-example',type:'technology' as const},{...skill,id:'skill:impact-context',type:'context_skill' as const}]};
    const answer={...result,effects:{...result.effects,highlight_skills:['skill:software-example','skill:impact-context']}};
    expect(validEffects(answer,expanded)).toEqual(answer.effects);
    expect(validEffects(answer,graph)).toBeNull();
    expect(validEffects({...answer,effects:{...answer.effects,highlight_skills:['invented']}},expanded)).toBeNull();
  });
  it('switches a named world only for an explicit command without a model call',async()=>{
    const switchWorld=vi.fn().mockResolvedValue({});
    render(<AgentActivityPanel graph={graph} role={role} onEffects={vi.fn()} onScenarioRequest={switchWorld}/>);
    fireEvent.change(screen.getByLabelText('What would you like to understand?'),{target:{value:'Switch to Governed AI'}});
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'}));
    await screen.findByText('Your world is now Governed AI.');
    expect(switchWorld).toHaveBeenCalledWith('governed');
    expect(requests).toHaveLength(0);
  });

  it('offers contextual questions without making a provider request',()=>{
    render(<AgentActivityPanel graph={graph} role={role} onEffects={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Compare the three worlds'}));
    expect(screen.getByLabelText('What would you like to understand?')).toHaveValue('How does this role change across the three worlds?');
    expect(requests).toHaveLength(0);
  });
  it('requires a selected role and submits its real context',async()=>{
    const callback=vi.fn(); const view=render(<AgentActivityPanel graph={graph} role={null} onEffects={callback}/>);
    expect(screen.getByRole('button',{name:'Send question to Noka'})).toBeDisabled();
    view.rerender(<AgentActivityPanel graph={graph} role={role} onEffects={callback}/>);
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'}));
    await screen.findByText(/Noka is readying your question/);
    expect(requests[0].body).toEqual({agent:'matchmaker',question:expect.any(String),role_id:role.entity_id});
    expect(screen.getByRole('status')).toHaveAttribute('aria-live','polite');
    expect(screen.getByText(/recorded events/).closest('details')).not.toHaveAttribute('open');
  });
  it('progresses from saved events to completion and valid graph highlighting',async()=>{
    const callback=vi.fn();render(<AgentActivityPanel graph={graph} role={role} onEffects={callback}/>);
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'})); await screen.findByText(/Noka is readying your question/);
    status={...queued,status:'running',events:[...queued.events,{sequence:2,agent:'matchmaker',type:'tool_completed',status:'running',at:'now',message:'Read-only tool completed.',payload:{tool:'get_ranked_matches'}}]};
    await waitFor(()=>expect(listeners.activity).toBeTypeOf('function'));
    listeners.activity(); fireEvent.click(await screen.findByText(/Activity ·/)); await screen.findByText('get_ranked_matches');
    status={...status,status:'completed',result}; listeners.done();
    await screen.findByText('Here’s your next perspective.');
    await waitFor(()=>expect(callback).toHaveBeenCalledWith(result.effects));
    expect(screen.getByText(/documented coverage/)).toBeVisible();
  });
  it('shows honest provider failure without applying UI effects',async()=>{
    status={...queued,status:'failed',error_code:'ai_unavailable'};const callback=vi.fn();
    render(<AgentActivityPanel graph={graph} role={role} onEffects={callback}/>);
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('not configured');expect(callback).not.toHaveBeenCalled();
  });
  it('explains quota rejection and exposes only safe diagnostic details',async()=>{
    status={...queued,status:'failed',error_code:'provider_quota_exceeded',events:[{sequence:1,agent:'matchmaker',type:'failed',status:'failed',at:'now',message:'AI unavailable.',payload:{stage:'provider_request',http_status:429,provider_code:'insufficient_quota'}}]};
    render(<AgentActivityPanel graph={graph} role={role} onEffects={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('insufficient API quota');
    fireEvent.click(screen.getByText('Failure details'));
    expect(screen.getByText(/OpenAI HTTP 429/)).toBeVisible();
  });
  it('cancels a queued execution',async()=>{
    render(<AgentActivityPanel graph={graph} role={role} onEffects={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'}));
    fireEvent.click(await screen.findByRole('button',{name:'Cancel exploration'}));
    await screen.findByText('Exploration cancelled. Your profile is unchanged.');
    expect(requests.some(r=>r.path.endsWith('/cancel'))).toBe(true);
  });
  it('rejects unsupported IDs, stale results and invented effects',()=>{
    expect(validEffects(result,graph)).toEqual(result.effects);
    expect(validEffects({...result,effects:{...result.effects,focus_role:'role:fake'}},graph)).toBeNull();
    expect(validEffects({...result,effects:{...result.effects,highlight_skills:['skill:fake']}},graph)).toBeNull();
    expect(validEffects({...result,effects:{...result.effects,open_evidence:'fake-source'}},graph)).toBeNull();
    expect(validEffects({...result,profile_revision:'2000-01-01'},graph)).toBeNull();
    expect(validEffects({...result,effects:{...result.effects,command:'delete_profile'} as typeof result.effects},graph)).toBeNull();
  });
  it('polls when SSE is unavailable',async()=>{
    vi.stubGlobal('EventSource',undefined);
    render(<AgentActivityPanel graph={graph} role={role} onEffects={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'})); await screen.findByText(/Noka is readying your question/);
    status={...queued,status:'completed',result};
    await screen.findByRole('heading',{name:'Exploration of '+role.label},{timeout:3500});
    expect(requests.some(r=>r.path.endsWith('/opaque-test') && r.body===null)).toBe(true);
  });
  it('provides accessible unlabelled loading and expandable discovery without fake metrics',()=>{
    render(<UniverseLoading/>);
    expect(screen.getByRole('status',{name:'Loading your career connections'})).toBeVisible();
    fireEvent.click(screen.getByText('What will I discover?'));
    expect(screen.getByText(/Your confirmed skills, roles ranked/)).toBeVisible();
    expect(screen.queryByText(/researching|forecasting|agents working/i)).not.toBeInTheDocument();
  });
});
