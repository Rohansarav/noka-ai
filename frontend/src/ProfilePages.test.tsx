import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import type { Profile } from './profile-api';

const skills = ['Programming', 'Writing', 'Critical Thinking', 'Speaking'].map((canonical_name, i) => ({ id: String(i), canonical_name, category: 'transferable', aliases: [], source_id: 'onet' }));
let saved: Profile | null;
let requests: { path: string; init?: RequestInit }[];
function visit(path: string) { render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>); }
beforeEach(() => {
  saved = null; requests = [];
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
    else if (path.endsWith('/resume')) data = { candidates: [{ mention: 'communication', years: null, evidence_excerpt: 'communication', confidence: 'low', mapping: 'ambiguous', options: ['1', '3'] }], mode: 'manual_fallback', message: 'AI extraction unavailable. Add skills manually.', truncated: false };
    else if (path.endsWith('/matches')) data = { status: 'insufficient_profile_information', matches: [], methodology: 'Heuristic, not a probability.', geography_note: 'US catalogue.' };
    return { ok: true, status: 200, json: async () => data } as Response;
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe('private profile journey', () => {
  it('preserves the existing workspace pace when editing a legacy completed profile',async()=>{
    saved={id:'legacy',country:'MY',interests:[],is_demo:false,confirmed:true,updated_at:'now',skills:skills.slice(0,3).map(s=>({skill_id:s.id,level:'working',years:null}))};
    visit('/profile/intake');
    await waitFor(()=>expect(screen.getByRole('button',{name:'Choose my skills'})).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Current role or field of study'),{target:{value:'Test existing career'}});
    fireEvent.click(screen.getByRole('button',{name:'Choose my skills'}));
    await screen.findByRole('heading',{name:'Your Skills'});
    fireEvent.click(screen.getByRole('button',{name:'Find my direction'}));
    await screen.findByRole('heading',{name:'Your Direction'});
    expect(screen.getByRole('slider')).toHaveValue('18');
    expect(saved?.confirmed).toBe(true);
    expect(requests.some(r=>r.path.endsWith('/future')&&r.init?.method==='PUT')).toBe(false);
  });
  it('keeps the provider-independent demo clearly labelled',async()=>{
    visit('/profile/intake');
    await screen.findByRole('button',{name:'Try a labelled demo'});
    fireEvent.click(screen.getByRole('button',{name:'Try a labelled demo'}));
    expect(screen.getByText('Demo profile · illustrative experience')).toBeInTheDocument();
    await waitFor(()=>expect(screen.getByRole('button',{name:'Extract & review skills'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Extract & review skills'}));
    await screen.findByText('AI extraction unavailable. Add skills manually.');
    expect(saved?.is_demo).toBe(true);
    expect(String((requests.find(r=>r.path.endsWith('/resume'))?.init?.body as FormData).get('use_ai'))).toBe('false');
  });
  it('routes a new visitor to onboarding and hides the World Dial', async()=>{
    visit('/');
    await screen.findByRole('heading',{name:'Let’s find your direction.'});
    expect(screen.queryByRole('region',{name:'Choose your future world'})).not.toBeInTheDocument();
  });
  it('resumes a private structured draft at the saved skills stage',async()=>{
    saved={id:'draft',country:'MY',interests:[],is_demo:false,confirmed:false,updated_at:'now',skills:[],onboarding:{step:1,status:'student',current_field:'Demo study',experience_years:0,country:'MY',market:'MY',goal:'',interests:[],weekly_hours:6,skills:[{skill_id:'0',level:'working',years:null}]}};
    visit('/');
    await screen.findByRole('heading',{name:'Your Skills'});
    expect(screen.getByText('Programming')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Find my direction'})).toBeDisabled();
  });
  it('completes manual intake with no resume or provider request', async () => {
    visit('/profile/intake');
    await waitFor(() => expect(screen.getByRole('button', { name: /Extract & review/ })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Enter manually' }));
    fireEvent.change(screen.getByLabelText('Current role or field of study'), {target:{value:'Computer science'}});
    fireEvent.click(screen.getByRole('button', { name: 'Choose my skills' }));
    await screen.findByText('Manual entry. Choose the skills you can demonstrate.');
    for (const id of ['0', '1', '2']) {
      fireEvent.change(screen.getByLabelText('Add a canonical skill'), { target: { value: id } });
      fireEvent.click(screen.getByRole('button', { name: 'Add skill' }));
    }
    fireEvent.click(screen.getByRole('button', { name: 'Find my direction' }));
    await screen.findByLabelText('Preferred career market');
    fireEvent.change(screen.getByLabelText('Preferred career market'), { target: { value: 'SG' } });
    expect(saved?.confirmed).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Explore My Future' }));
    await waitFor(()=>expect(saved?.confirmed).toBe(true));
    expect(saved?.skills).toHaveLength(3);
    expect(saved?.country).toBe('SG');
    expect(requests.some(r => r.path.endsWith('/resume'))).toBe(false);
    const mutation = requests.find(r => r.path.endsWith('/skills') && r.init?.method === 'PUT')!;
    expect(mutation.init?.headers).toMatchObject({ 'X-Noka-CSRF': '1' });
    expect(mutation.init?.credentials).toBe('same-origin');
    expect(mutation.init?.body).not.toMatch(/resume|excerpt/);
  });
  it('requires choosing an ambiguous canonical skill after provider fallback', async () => {
    visit('/profile/intake');
    await waitFor(() => expect(screen.getByRole('button', { name: /Extract & review/ })).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Current role or field of study'), {target:{value:'Test role'}});
    fireEvent.click(screen.getByRole('button', { name: 'Paste experience' }));
    fireEvent.change(screen.getByLabelText(/Your experience/), { target: { value: 'communication' } });
    fireEvent.click(screen.getByRole('button', { name: /Extract & review/ }));
    await screen.findByText('AI extraction unavailable. Add skills manually.');
    expect(screen.getByRole('button', { name: 'Confirm skill' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Canonical skill for communication'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm skill' }));
    expect(screen.getByRole('button', { name: 'Find my direction' })).toBeDisabled();
    expect(saved?.skills).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: 'Remove Speaking' }));
    expect(screen.getByRole('button', { name: 'Find my direction' })).toBeDisabled();
  });
  it('rejects oversized CVs before upload', async () => {
    visit('/profile/intake');
    await waitFor(() => expect(screen.getByRole('button', { name: /Extract & review/ })).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Current role or field of study'), {target:{value:'Test role'}});
    const file = new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'demo.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Resume file'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Extract & review/ }));
    expect(await screen.findByText(/Choose a PDF or DOCX up to 5 MB/)).toBeInTheDocument();
    expect(requests.some(r => r.path.endsWith('/resume'))).toBe(false);
  });
});
