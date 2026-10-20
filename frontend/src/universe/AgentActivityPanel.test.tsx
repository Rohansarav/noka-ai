import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
  it('requires a selected role and submits its real context',async()=>{
    const callback=vi.fn(); const view=render(<AgentActivityPanel graph={graph} role={null} onEffects={callback}/>);
    expect(screen.getByRole('button',{name:'Explore selected role'})).toBeDisabled();
    view.rerender(<AgentActivityPanel graph={graph} role={role} onEffects={callback}/>);
    fireEvent.click(screen.getByRole('button',{name:'Explore selected role'}));
    await screen.findByText(/Matchmaker: queued/);
    expect(requests[0].body).toEqual({agent:'matchmaker',question:expect.any(String),role_id:role.entity_id});
    expect(screen.getByRole('status')).toHaveAttribute('aria-live','polite');
    expect(screen.getByText(/recorded events/)).toBeVisible();
  });
  it('progresses from saved events to completion and valid graph highlighting',async()=>{
    const callback=vi.fn();render(<AgentActivityPanel graph={graph} role={role} onEffects={callback}/>);
    fireEvent.click(screen.getByRole('button',{name:'Explore selected role'})); await screen.findByText(/Matchmaker: queued/);
    status={...queued,status:'running',events:[...queued.events,{sequence:2,agent:'matchmaker',type:'tool_completed',status:'running',at:'now',message:'Read-only tool completed.',payload:{tool:'get_ranked_matches'}}]};
    listeners.activity(); await screen.findByText('get_ranked_matches');
    status={...status,status:'completed',result}; listeners.done();
    await screen.findByRole('heading',{name:'Exploration of '+role.label});
    await waitFor(()=>expect(callback).toHaveBeenCalledWith(result.effects));
    expect(screen.getByText(/heuristic skill fit/)).toBeVisible();
  });
  it('shows honest provider failure without applying UI effects',async()=>{
    status={...queued,status:'failed',error_code:'ai_unavailable'};const callback=vi.fn();
    render(<AgentActivityPanel graph={graph} role={role} onEffects={callback}/>);
    fireEvent.click(screen.getByRole('button',{name:'Explore selected role'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('ai_unavailable');expect(callback).not.toHaveBeenCalled();
  });
  it('cancels a queued execution',async()=>{
    render(<AgentActivityPanel graph={graph} role={role} onEffects={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Explore selected role'}));
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
    fireEvent.click(screen.getByRole('button',{name:'Explore selected role'})); await screen.findByText(/Matchmaker: queued/);
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
