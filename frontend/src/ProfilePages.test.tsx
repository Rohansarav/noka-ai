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
    else if (path === '/api/profiles') { saved = { id: 'private-id', country: 'MY', interests: [], is_demo: false, confirmed: false, updated_at: 'now', skills: [] }; data = saved; }
    else if (path.endsWith('/skills')) { saved = { ...saved!, ...JSON.parse(init?.body as string), confirmed: true }; data = saved; }
    else if (path.endsWith('/resume')) data = { candidates: [{ mention: 'communication', years: null, evidence_excerpt: 'communication', confidence: 'low', mapping: 'ambiguous', options: ['1', '3'] }], mode: 'manual_fallback', message: 'AI extraction unavailable. Add skills manually.', truncated: false };
    else if (path.endsWith('/matches')) data = { status: 'insufficient_profile_information', matches: [], methodology: 'Heuristic, not a probability.', geography_note: 'US catalogue.' };
    return { ok: true, status: 200, json: async () => data } as Response;
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe('private profile journey', () => {
  it('completes manual intake with no resume or provider request', async () => {
    visit('/profile/intake');
    await waitFor(() => expect(screen.getByRole('button', { name: /Extract & review/ })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Manual only' }));
    fireEvent.click(screen.getByRole('button', { name: 'Choose my skills' }));
    await screen.findByText('Manual entry. Choose the skills you can demonstrate.');
    for (const id of ['0', '1', '2']) {
      fireEvent.change(screen.getByLabelText('Add a canonical skill'), { target: { value: id } });
      fireEvent.click(screen.getByRole('button', { name: 'Add skill' }));
    }
    fireEvent.click(screen.getByRole('button', { name: 'Continue with 3 reviewed skills' }));
    fireEvent.change(screen.getByLabelText('Preferred location'), { target: { value: 'SG' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review my profile' }));
    expect(saved?.confirmed).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Save profile & see matches' }));
    await screen.findByText('Insufficient profile information');
    expect(saved?.skills).toHaveLength(3);
    expect(saved?.country).toBe('SG');
    expect(requests.some(r => r.path.endsWith('/resume'))).toBe(false);
    const mutation = requests.find(r => r.path.endsWith('/skills') && r.init?.method === 'PUT')!;
    expect(mutation.init?.headers).toMatchObject({ 'X-Noka-CSRF': '1' });
    expect(mutation.init?.credentials).toBe('same-origin');
    expect(mutation.init?.body).not.toMatch(/resume|excerpt|name|text/);
  });
  it('requires choosing an ambiguous canonical skill after provider fallback', async () => {
    visit('/profile/intake');
    await waitFor(() => expect(screen.getByRole('button', { name: /Extract & review/ })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: 'Paste experience' }));
    fireEvent.change(screen.getByLabelText(/Your experience/), { target: { value: 'communication' } });
    fireEvent.click(screen.getByRole('button', { name: /Extract & review/ }));
    await screen.findByText('AI extraction unavailable. Add skills manually.');
    expect(screen.getByRole('button', { name: 'Confirm skill' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Canonical skill for communication'), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm skill' }));
    expect(screen.getByRole('button', { name: 'Continue with 1 reviewed skills' })).toBeEnabled();
    expect(saved?.skills).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: 'Remove Speaking' }));
    expect(screen.getByRole('button', { name: 'Continue with 0 reviewed skills' })).toBeDisabled();
  });
  it('rejects oversized CVs before upload', async () => {
    visit('/profile/intake');
    await waitFor(() => expect(screen.getByRole('button', { name: /Extract & review/ })).toBeEnabled());
    const file = new File([new Uint8Array(5 * 1024 * 1024 + 1)], 'demo.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Resume file'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /Extract & review/ }));
    expect(await screen.findByText(/Choose a PDF or DOCX up to 5 MB/)).toBeInTheDocument();
    expect(requests.some(r => r.path.endsWith('/resume'))).toBe(false);
  });
});
