import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../App';
import type { CareerGraphData, CareerNode } from './universe-types';
import type { UniverseFilter } from './universe-types';
import { filterGraph } from './universe-layout';

// JSDOM cannot measure a pan/zoom canvas. This page-level adapter exercises the
// selection contract; the real React Flow renderer is checked in live browser QA.
vi.mock('./CareerGraph', () => ({ default: ({ graph, filter, onSelect, highlighted }: { highlighted?: string[]; graph: CareerGraphData; filter: UniverseFilter; onSelect: (id: string) => void }) => <div role="region" aria-label="Interactive career connections">{filterGraph(graph, filter).nodes.map(n => <button key={n.id} data-agent-highlighted={highlighted?.includes(n.id) ? "true" : "false"} onClick={() => onSelect(n.id)}>Select canvas node {n.label}</button>)}</div> }));

// Occupational labels/IDs and target text come from the attributed real-row fixture.
// Scores/profile levels below are unit-test inputs, not asserted market observations.
const evidence = JSON.parse(readFileSync(resolve('data/fixtures/api.json'), 'utf8'));
const role = evidence.role;
const programming = role.skills.find((s: { skill: { canonical_name: string } }) => s.skill.canonical_name === 'Programming').skill;
const reading = role.skills.find((s: { skill: { canonical_name: string } }) => s.skill.canonical_name === 'Reading Comprehension').skill;
const instructing = role.skills.find((s: { skill: { canonical_name: string } }) => s.skill.canonical_name === 'Instructing').skill;
const goal = evidence.sdgs.goals.find((g: { id: number }) => g.id === 4);
const target = goal.targets.find((t: { id: string }) => t.id === '4.4');
function node(id: string, type: CareerNode['type'], label: string, extra: Partial<CareerNode> = {}): CareerNode {
  return { id, type, label, entity_id: id.split(':').slice(1).join(':'), description: '', source_ids: [], review_status: null, level: null, years: null, skill_count: null, country: null, is_demo: true, score: null, coverage: null, explanation: null, goal_id: null, ...extra };
}
const profile = node('profile:test-profile', 'profile', 'Demo profile', { skill_count: 3, country: 'MY' });
const prog = node(`skill:${programming.id}`, 'owned_skill', programming.canonical_name, { level: 'working' });
const missing = node(`skill:${reading.id}`, 'required_skill', reading.canonical_name);
const instruction = node(`skill:${instructing.id}`, 'owned_skill', instructing.canonical_name, { level: 'strong' });
const career = node(`role:${role.id}`, 'role', role.title, { score: 42, coverage: 42, explanation: 'Unit-test fit explanation.', country: 'US', review_status: 'human_reviewed' });
const sdg = node('sdg:4', 'sdg', 'Goal 4', { goal_id: 4, description: goal.title });
const sdgTarget = node('sdg_target:4.4', 'sdg_target', 'Target 4.4', { goal_id: 4, description: target.description });
function edge(type: CareerGraphData['edges'][number]['type'], source: string, destination: string, extra = {}) {
  return { id: `${type}:${source}:${destination}`, type, source, target: destination, source_ids: [], importance: null, gap: null, critical: false, review_status: null, rationale: null, supporting_id: null, ...extra };
}
const original: CareerGraphData = { status: 'ready', profile_revision: '2026-10-20T00:00:00Z', generated_at: '2026-10-20T00:00:00Z', nodes: [profile, prog, missing, instruction, career, sdg, sdgTarget], edges: [edge('has_skill',profile.id,prog.id), edge('has_skill',profile.id,instruction.id), edge('requires_skill',career.id,prog.id,{ importance:4,gap:.35 }), edge('missing_skill',career.id,prog.id,{ importance:4,gap:.35 }), edge('requires_skill',career.id,missing.id,{ importance:3.5,gap:1 }), edge('missing_skill',career.id,missing.id,{ importance:3.5,gap:1 }), edge('contributes_to_target',instruction.id,sdgTarget.id,{ rationale:'Reviewed teaching relevance.',review_status:'human_reviewed' }), edge('target_belongs_to_goal',sdgTarget.id,sdg.id)], sources: [], methodology: 'Unit-test methodology: weighted skill coverage, not a forecast.', limitations: ['Unit test data.'] };
let graph: CareerGraphData;
let hasProfile: boolean;
let profileConfirmed: boolean;
let failed: boolean;
function visit(path='/universe') { render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>); }
beforeEach(() => {
  graph = structuredClone(original); hasProfile = true; profileConfirmed = true; failed = false;
  vi.stubGlobal('fetch',vi.fn(async input => {
    const path = String(input);
    const data = path.endsWith('/career-graph') ? graph : path === '/api/profiles/current' ? { profile: hasProfile ? { id:'test-profile', confirmed:profileConfirmed, skills:[],updated_at:'now' } : null } : path === '/api/health' ? { status:'ok',service:'noka-api' } : path === '/api/datasets/summary' ? evidence.summary : {};
    return {ok: !(failed && path.endsWith('/career-graph')),status:failed?503:200,json:async()=>data} as Response;
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe('Career Universe page', () => {
  it('keeps a low-readiness target explicit and separates it from discovered directions',async()=>{
    const targetNode=graph.nodes.find(n=>n.type==='role')!;
    targetNode.is_target=true;targetNode.score=5;targetNode.coverage=5;
    const match={role_id:targetNode.entity_id,title:targetNode.label,is_target:true,score:5,coverage:5,planning_index:7,context_emphasis:1,scenario_emphasis:1,priority_skills:[],gaps:[],scenario_reason:'Planning assumption'};
    const future={profile_id:'test-profile',scenario:'collaboration',role_id:targetNode.entity_id,matches:[match],pathway:[],conversation:[],scenarios:{collaboration:{name:'Human-AI Collaboration',assumption:'Planning assumption',skills:[]}},comparisons:{collaboration:[match]},worlds:{},analysis_context:{goal:'Explore an ambitious career',aspirations:[{title:'My unmapped specialty',role_ids:[],status:'unmapped'}]}};
    const previous=vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((input,init)=>String(input).endsWith('/future')?Promise.resolve({ok:true,status:200,json:async()=>future} as Response):previous(input,init));
    visit('/');
    const directions=await screen.findByRole('region',{name:'Career directions'});
    expect(within(directions).getByRole('heading',{name:'Your targets'})).toBeInTheDocument();
    expect(within(directions).getByText('5/100 readiness')).toBeInTheDocument();
    expect(within(directions).getByText('Your confirmed target · interest adds no points')).toBeInTheDocument();
    expect(within(directions).getByText('My unmapped specialty')).toBeInTheDocument();
    expect(within(directions).getByRole('heading',{name:'Other directions to explore'})).toBeInTheDocument();
    fireEvent.click(within(directions).getByRole('button',{name:new RegExp(targetNode.label)}));
    await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([path,init])=>String(path).endsWith('/future')&&init?.method==='PUT'&&JSON.parse(String(init.body)).role_id===targetNode.entity_id)).toBe(true));
  });
  it('adds primary navigation and routes a confirmed homepage journey to Universe', async () => {
    visit('/');
    expect(screen.getByRole('link',{name:'My Future'})).toHaveAttribute('href','/');
    await screen.findByRole('region',{name:'Interactive career connections'});
    expect(screen.queryByRole('link',{name:'Build My Future'})).not.toBeInTheDocument();
  });
  it('keeps the homepage intake journey for no confirmed profile', async () => {
    hasProfile = false; visit('/');
    expect(await screen.findByRole('heading',{name:'Let’s find your direction.'})).toBeInTheDocument();
    expect(screen.queryByRole('region',{name:'Interactive career connections'})).not.toBeInTheDocument();
  });
  it('switches the companion tabs with arrow keys and restores expansion focus',async()=>{
    visit(); await screen.findByRole('region',{name:'Interactive career connections'});
    const ask=screen.getByRole('tab',{name:'Ask Noka'}); ask.focus();
    fireEvent.keyDown(ask,{key:'ArrowRight'});
    expect(screen.getByRole('tab',{name:'Connection'})).toHaveFocus();
    expect(screen.getByRole('tab',{name:'Connection'})).toHaveAttribute('aria-selected','true');
    const expand=screen.getByRole('button',{name:'Expand Universe'});fireEvent.click(expand);
    const dialog=screen.getByRole('dialog',{name:'Expanded Career Universe'});expect(dialog).toHaveFocus();
    fireEvent.keyDown(dialog,{key:'Escape'});expect(expand).toHaveFocus();
  });
  it('shows the backend graph loading state', async () => {
    vi.mocked(fetch).mockImplementation(input => String(input).endsWith('/career-graph') ? new Promise(()=>{}) : Promise.resolve({ok:true,json:async()=>({status:'ok',service:'noka-api',profile:{id:'test',confirmed:true}})} as Response));
    visit(); expect(await screen.findByRole('status',{name:'Loading your career connections'})).toBeInTheDocument();
  });
  it('keeps draft profiles on the intake journey', async () => {
    profileConfirmed = false; visit('/');
    expect(await screen.findByRole('heading',{name:'Let’s find your direction.'})).toBeInTheDocument();
    expect(screen.queryByRole('region',{name:'Interactive career connections'})).not.toBeInTheDocument();
  });
  it('selects a canvas role and opens its real relationships and methodology', async () => {
    visit();
    fireEvent.click(await screen.findByRole('button',{name:`Select canvas node ${role.title}`}));
    const panel = screen.getByRole('complementary',{name:'Selected connection details'});
    expect(within(panel).getByRole('heading',{name:role.title})).toBeInTheDocument();
    expect(within(panel).getByText('Partial · 35% proficiency gap')).toBeInTheDocument();
    expect(within(panel).getByText('Not recorded · 100% proficiency gap')).toBeInTheDocument();
    expect(within(panel).getByText('Skill-fit methodology')).toBeInTheDocument();
    expect(within(panel).getByRole('link',{name:'Full Role Matches'})).toHaveAttribute('href','/matches');
  });
  it('filters presentation without writes or changing skill ownership', async () => {
    visit(); await screen.findByRole('button',{name:`Select canvas node ${role.title}`});
    fireEvent.click(screen.getByRole('button',{name:'My existing skills'}));
    const canvas = screen.getByRole('region',{name:'Interactive career connections'});
    expect(within(canvas).queryByText(`Select canvas node ${reading.canonical_name}`)).not.toBeInTheDocument();
    expect(within(canvas).getByText(`Select canvas node ${programming.canonical_name}`)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'SDG connections'}));
    expect(within(canvas).getByText('Select canvas node Target 4.4')).toBeInTheDocument();
    expect(vi.mocked(fetch).mock.calls.every(([,init])=>!init?.method || init.method==='GET')).toBe(true);
  });
  it('provides an independently selectable accessible list and reviewed SDG rationale', async () => {
    visit(); fireEvent.click(await screen.findByText('Explore connections as a list')); await screen.findByRole('heading',{name:'Explore without the canvas.'});
    const list = screen.getByRole('region',{name:'Explore without the canvas.'});
    const choose = within(list).getByRole('button',{name:/sdg target Target 4.4/});
    choose.focus(); expect(choose).toHaveFocus(); fireEvent.click(choose);
    const panel = screen.getByRole('complementary',{name:'Selected connection details'});
    expect(within(panel).getByRole('heading',{name:'Target 4.4'})).toBeInTheDocument();
    expect(within(panel).getByText('Reviewed teaching relevance.')).toBeInTheDocument();
    expect(within(list).getByRole('link',{name:'Read details for Target 4.4'})).toHaveAttribute('href','#universe-details');
  });
  it('does not invent careers for an insufficient profile', async () => {
    graph = {...graph,status:'insufficient_profile_information',nodes:[profile,prog],edges:[edge('has_skill',profile.id,prog.id)]};
    visit(); expect(await screen.findByText(/Confirm at least three skills/)).toBeInTheDocument();
    expect(screen.queryByRole('group',{name:'Choose a career direction'})).not.toBeInTheDocument();
  });
  it('offers onboarding when no private profile exists', async () => {
    graph = {...graph,status:'no_profile',nodes:[],edges:[],profile_revision:null}; visit();
    expect(await screen.findByRole('link',{name:'Build my skill profile'})).toHaveAttribute('href','/profile/intake');
    expect(screen.queryByRole('region',{name:'Interactive career connections'})).not.toBeInTheDocument();
  });
  it('explains absent reviewed SDG connections without inventing links', async () => {
    graph = {...graph,nodes:graph.nodes.filter(n=>!n.type.startsWith('sdg')),edges:graph.edges.filter(e=>e.type!=='contributes_to_target' && e.type!=='target_belongs_to_goal')};
    visit(); await screen.findByRole('button',{name:`Select canvas node ${role.title}`});
    fireEvent.click(screen.getByRole('button',{name:'SDG connections'}));
    expect(screen.getByText(/No reviewed SDG connections exist/)).toBeInTheDocument();
  });
  it('reports errors and retries without substitute connections', async () => {
    failed = true; visit();
    expect(await screen.findByText(/No substitute connections/)).toBeInTheDocument();
    failed = false; fireEvent.click(screen.getByRole('button',{name:'Retry Universe'}));
    expect(await screen.findByRole('button',{name:`Select canvas node ${role.title}`})).toBeInTheDocument();
  });
});


it('passes validated Matchmaker highlights to the existing canvas and clears them on selection', async () => {
  const ordinaryFetch = globalThis.fetch;
  vi.stubGlobal('fetch', vi.fn(async (input, init) => {
    if (String(input) === '/api/agent-executions') return {ok:true,json:async()=>({id:'test-execution',status:'completed',error_code:null,tool_count:1,token_usage:1,events:[],result:{sections:[],notice:'Unit-test server result.',profile_revision:graph.profile_revision,effects:{focus_role:career.id,highlight_skills:[prog.id],open_evidence:null}}})} as Response;
    return ordinaryFetch(input, init);
  }));
  visit();
  fireEvent.click(await screen.findByRole('button',{name:'Select canvas node '+career.label}));
  fireEvent.click(screen.getByRole('tab',{name:'Ask Noka'}));
  fireEvent.click(screen.getByRole('button',{name:'Send question to Noka'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Select canvas node '+prog.label})).toHaveAttribute('data-agent-highlighted','true'));
  fireEvent.click(screen.getByRole('button',{name:'Select canvas node '+prog.label}));
  expect(screen.getByRole('button',{name:'Select canvas node '+prog.label})).toHaveAttribute('data-agent-highlighted','false');
});
