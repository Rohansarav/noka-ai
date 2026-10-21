import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import type { Extraction, Profile } from './profile-api';

const skills = ['Programming', 'Writing', 'Critical Thinking', 'Speaking'].map((canonical_name, i) => ({ id: String(i), canonical_name, category: 'transferable', aliases: [], source_id: 'onet' }));
let saved: Profile | null;
let requests: { path: string; init?: RequestInit }[];
let extraction:Extraction;
let failAnalysis:boolean;
function visit(path: string) { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>); }
beforeEach(() => {
  saved = null; requests = [];failAnalysis=false;
  extraction={candidates:[{mention:'Python',years:null,evidence_excerpt:'Python',confidence:'medium',mapping:'alias',options:['0','0']},{mention:'Programming',years:null,evidence_excerpt:'Programming',confidence:'medium',mapping:'exact',options:['0']},{mention:'communication',years:null,evidence_excerpt:'communication',confidence:'low',mapping:'ambiguous',options:['1','3']}],mode:'openai',message:'AI suggestions need your review.',truncated:false};
  vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
    const path = String(input); requests.push({ path, init });
    let data: unknown = {};
    if (path === '/api/profiles/current') data = { profile: saved };
    else if (path === '/api/skills') data = { skills };
    else if (path === '/api/roles') data = { roles: [] };
    else if (path === '/api/health') data = { status: 'ok', service: 'noka-api' };
    else if (path === '/api/profiles') { saved = { id: 'private-id', country: 'MY', interests: [], is_demo: JSON.parse(String(init?.body)).is_demo ?? false, confirmed: false, updated_at: 'now', skills: [] }; data = saved; }
    else if (path.endsWith('/onboarding')) { saved = { ...saved!, onboarding: JSON.parse(init?.body as string) }; data=saved; }
    else if (path.endsWith('/future')) data={profile_id:saved?.id,weekly_hours:18,scenario:'collaboration',matches:[],pathway:[],conversation:[],scenarios:{collaboration:{name:'Human-AI Collaboration',assumption:'Fixture planning assumption',skills:[]}},comparisons:{collaboration:[]},worlds:{}};
    else if (path.endsWith('/skills')) { saved = { ...saved!, ...JSON.parse(init?.body as string), confirmed: true }; data = saved; }
    else if (path.endsWith('/analysis')) {if(failAnalysis)return {ok:false,status:503,json:async()=>({error:{message:'Analysis temporarily unavailable. Your experience is still here.'}})} as Response;data=extraction;}
    else if (path.endsWith('/matches')) data = { status: 'insufficient_profile_information', matches: [], methodology: 'Heuristic, not a probability.', geography_note: 'US catalogue.' };
    return { ok: true, status: 200, json: async () => data } as Response;
  }));
});
afterEach(() => vi.unstubAllGlobals());
const experience='I used Python programming to build tools, wrote reports and used critical thinking.';
async function manual(){
  visit('/profile/intake');
  await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse my experience'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Enter manually'}));
  fireEvent.change(screen.getByLabelText('Current role or field of study'),{target:{value:'Computer science'}});
  fireEvent.change(screen.getByRole('textbox',{name:'Your experience'}),{target:{value:experience}});
}
async function analyse(){fireEvent.click(screen.getByRole('button',{name:'Analyse my experience'}));await screen.findByRole('heading',{name:'Your Skills'});}

describe('private profile journey', () => {
  it('preserves the workspace pace and reviews saved skills without compulsory re-analysis',async()=>{
    saved={id:'legacy',country:'MY',interests:[],is_demo:false,confirmed:true,updated_at:'now',skills:skills.slice(0,3).map(s=>({skill_id:s.id,level:'working',years:null}))};
    visit('/profile/intake');
    await waitFor(()=>expect(screen.getByRole('button',{name:'Review my skills'})).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Current role or field of study'),{target:{value:'Test existing career'}});
    fireEvent.click(screen.getByRole('button',{name:'Review my skills'}));
    await screen.findByRole('heading',{name:'Your Skills'});
    fireEvent.click(screen.getByRole('button',{name:'Find my direction'}));
    await screen.findByRole('heading',{name:'Your Direction'});
    expect(screen.getByRole('slider')).toHaveValue('18');
    expect(saved?.confirmed).toBe(true);
    expect(requests.some(r=>r.path.endsWith('/analysis'))).toBe(false);
    expect(requests.some(r=>r.path.endsWith('/future')&&r.init?.method==='PUT')).toBe(false);
  });
  it('keeps the provider-independent demo labelled while using the manual input path',async()=>{
    visit('/profile/intake');
    await screen.findByRole('button',{name:'Try a labelled demo'});
    fireEvent.click(screen.getByRole('button',{name:'Try a labelled demo'}));
    expect(screen.getByText('Demo profile · illustrative experience')).toBeInTheDocument();
    await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse my experience'})).toBeEnabled());
    await analyse();
    expect(saved?.is_demo).toBe(true);
    const body=requests.find(r=>r.path.endsWith('/analysis'))?.init?.body as FormData;
    expect(body.get('use_ai')).toBe('false');expect(body.get('file')).toBeNull();
  });
  it('routes a new visitor to onboarding with exactly two input choices', async()=>{
    visit('/');
    await screen.findByRole('heading',{name:'Let’s find your direction.'});
    expect(within(screen.getByRole('group',{name:'Experience input method'})).getAllByRole('button')).toHaveLength(2);
    expect(screen.queryByRole('button',{name:'Paste experience'})).not.toBeInTheDocument();
    expect(screen.queryByRole('region',{name:'Choose your future world'})).not.toBeInTheDocument();
  });
  it('resumes a private skills draft with a searchable catalogue',async()=>{
    saved={id:'draft',country:'MY',interests:[],is_demo:false,confirmed:false,updated_at:'now',skills:[],onboarding:{step:1,status:'student',current_field:'Demo study',experience_years:0,country:'MY',market:'MY',goal:'',interests:[],weekly_hours:6,skills:[{skill_id:'0',level:'working',years:null}]}};
    visit('/');
    await screen.findByRole('heading',{name:'Your Skills'});
    expect(within(screen.getByRole('region',{name:'Your confirmed skills'})).getByText('Programming')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Find my direction'})).toBeDisabled();
    expect(screen.getByRole('searchbox')).toBeInTheDocument();
  });
  it('sends manual experience through analysis and saves only standard canonical reviewed skills', async () => {
    await manual();await analyse();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Add Programming'}));
    fireEvent.click(screen.getByRole('button',{name:'Add Writing'}));
    fireEvent.click(screen.getByRole('button',{name:'Choose Critical Thinking'}));
    fireEvent.click(within(screen.getByRole('group',{name:'Programming proficiency'})).getByRole('button',{name:'Strong'}));
    fireEvent.change(screen.getByRole('spinbutton',{name:'Programming years'}),{target:{value:'2'}});
    fireEvent.click(screen.getByRole('button', { name: 'Find my direction' }));
    await screen.findByLabelText('Preferred career market');
    fireEvent.change(screen.getByLabelText('Preferred career market'), { target: { value: 'SG' } });
    expect(saved?.confirmed).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Explore My Future' }));
    await waitFor(()=>expect(saved?.confirmed).toBe(true));
    expect(saved?.skills).toHaveLength(3);expect(saved?.country).toBe('SG');
    expect(saved?.skills.find(s=>s.skill_id==='0')).toEqual({skill_id:'0',level:'strong',years:2});
    const analysis=requests.find(r=>r.path.endsWith('/analysis'))!;
    expect((analysis.init?.body as FormData).get('text')).toBe(experience);
    expect((analysis.init?.body as FormData).get('file')).toBeNull();
    const mutation = requests.find(r => r.path.endsWith('/skills') && r.init?.method === 'PUT')!;
    expect(mutation.init?.headers).toMatchObject({ 'X-Noka-CSRF': '1' });
    expect(mutation.init?.credentials).toBe('same-origin');
    expect(String(mutation.init?.body)).not.toContain(experience);
    expect(String(mutation.init?.body)).not.toMatch(/evidence_excerpt/);
  });
  it('deduplicates OpenAI suggestions and allows adding without a per-skill dropdown',async()=>{
    await manual();await analyse();
    expect(screen.getAllByRole('button',{name:'Add Programming'})).toHaveLength(1);
    fireEvent.click(screen.getByRole('button',{name:'Add Programming'}));
    const confirmed=screen.getByRole('region',{name:'Your confirmed skills'});
    expect(within(confirmed).getByText('Programming')).toBeInTheDocument();
    expect(within(confirmed).getAllByRole('group',{name:'Programming proficiency'})).toHaveLength(1);
    expect(screen.queryByRole('button',{name:'Add Programming'})).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Remove Programming'}));
    expect(screen.getByRole('button',{name:'Add Programming'})).toBeEnabled();
  });
  it('lets the user choose a broad skill for an unmapped AI term instead of presenting a disabled add button',async()=>{
    extraction={...extraction,candidates:[{mention:'Custom tool',years:null,evidence_excerpt:'Used Custom tool',confidence:'low',mapping:'unmapped',options:[]}]};
    await manual();await analyse();
    expect(screen.getByText('A few terms need your help')).toBeInTheDocument();
    fireEvent.change(screen.getByRole('searchbox'),{target:{value:'Python'}});
    fireEvent.click(screen.getByRole('button',{name:'Choose Programming'}));
    expect(screen.getByRole('button',{name:'Remove Programming'})).toBeInTheDocument();
  });
  it('shows required manual-field errors and keeps invalid input away from analysis',async()=>{
    await manual();
    fireEvent.change(screen.getByRole('textbox',{name:'Your experience'}),{target:{value:'short'}});
    fireEvent.click(screen.getByRole('button',{name:'Analyse my experience'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('20 characters');
    expect(screen.getByRole('textbox',{name:'Your experience'})).toHaveFocus();
    expect(requests.some(r=>r.path.endsWith('/analysis'))).toBe(false);
  });
  it('preserves input on server failure and supports a successful retry',async()=>{
    await manual();failAnalysis=true;
    fireEvent.click(screen.getByRole('button',{name:'Analyse my experience'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Analysis temporarily unavailable');
    expect(screen.getByRole('textbox',{name:'Your experience'})).toHaveValue(experience);
    failAnalysis=false;await analyse();
    expect(screen.getByRole('button',{name:'Add Programming'})).toBeEnabled();
  });
  it('rejects oversized or unsupported files before upload',async()=>{
    visit('/profile/intake');
    await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse my experience'})).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Current role or field of study'),{target:{value:'Test role'}});
    const file=new File([new Uint8Array(5*1024*1024+1)],'demo.pdf',{type:'application/pdf'});
    fireEvent.change(screen.getByLabelText('Resume file'),{target:{files:[file]}});
    expect(screen.getByRole('alert')).toHaveTextContent('5 MB');
    fireEvent.click(screen.getByRole('button',{name:'Analyse my experience'}));
    expect(requests.some(r=>r.path.endsWith('/analysis'))).toBe(false);
    fireEvent.change(screen.getByLabelText('Resume file'),{target:{files:[new File(['bad'],'resume.exe')]}});
    expect(screen.getByRole('alert')).toHaveTextContent('Only PDF and DOCX');
  });
  it('uses the same analysis and confirmed-skill contract for an uploaded document',async()=>{
    visit('/profile/intake');
    await waitFor(()=>expect(screen.getByRole('button',{name:'Analyse my experience'})).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Current role or field of study'),{target:{value:'Test role'}});
    fireEvent.change(screen.getByLabelText('Resume file'),{target:{files:[new File(['fixture'],'demo.pdf',{type:'application/pdf'})]}});
    await analyse();
    const body=requests.find(r=>r.path.endsWith('/analysis'))?.init?.body as FormData;
    expect(body.get('file')).toBeInstanceOf(File);expect(body.get('text')).toBeNull();expect(body.get('use_ai')).toBe('true');
    fireEvent.click(screen.getByRole('button',{name:'Add Programming'}));
    expect(screen.getByRole('button',{name:'Remove Programming'})).toBeInTheDocument();
  });
});
