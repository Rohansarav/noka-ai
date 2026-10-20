import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import App from './App';

// Derived from attributed, real source subsets. The manifest records upstream
// checksums and transformations; no market observations are invented.
const fixture = JSON.parse(readFileSync(resolve('data/fixtures/api.json'), 'utf8'));
function visit(path: string) {
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>);
}
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async input => {
    const url = String(input);
    const data = url === '/api/health' ? {status:'ok',service:'noka-api'} : url === '/api/datasets/summary' ? fixture.summary : url === '/api/roles' ? fixture.roles : url.startsWith('/api/roles/') ? fixture.role : url === '/api/sdgs' ? fixture.sdgs : url.startsWith('/api/demand/history?') ? fixture.history : {};
    return {ok:true,json:async()=>data} as Response;
  }));
});
afterEach(() => { vi.mocked(fetch).mockReset(); });

describe('public evidence journey', () => {
  it('shows coverage, dates, attribution and storage limitations', async () => {
    visit('/datasets');
    expect(await screen.findByText('141')).toBeInTheDocument();
    expect(screen.getByText(/1 Feb 2020/)).toBeInTheDocument();
    expect(screen.getByText(/3 Feb 2020/)).toBeInTheDocument();
    expect(screen.getByText(/Local SQLite evidence store/)).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'Indeed US sector total-posting index'})).toHaveAttribute('href','https://github.com/hiring-lab/job_postings_tracker');
    expect(screen.getByText(/No Malaysian historical series is included/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'View historical rows'}));
    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(screen.getByText('2 Feb 2020')).toBeInTheDocument();
  });
  it('lists real occupations and canonical skill importance without match percentages', async () => {
    visit('/roles');
    expect(await screen.findByRole('heading',{name:'Software Developers'})).toBeInTheDocument();
    fireEvent.change(screen.getByRole('textbox',{name:'Search roles or sectors'}),{target:{value:'Software Developers'}});
    fireEvent.click(screen.getByRole('button',{name:'View skills & evidence'}));
    expect(await screen.findByText('Critical Thinking')).toBeInTheDocument();
    expect(screen.getByText(/Never an individual statistical forecast/)).toBeInTheDocument();
    expect(screen.getByText('Public role catalogue')).toBeInTheDocument();
  });
  it('retries history after a transient request failure', async () => {
    let attempts = 0;
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      if (String(input).startsWith('/api/demand/history?') && attempts++ === 0) return {ok:false} as Response;
      return original(input, init);
    });
    visit('/datasets');
    const button = await screen.findByRole('button',{name:'View historical rows'});
    fireEvent.click(button);
    expect(await screen.findByText('Sector history is unavailable. Please try again.')).toBeInTheDocument();
    fireEvent.click(button);
    expect(await screen.findByRole('table')).toBeInTheDocument();
  });
  it('displays all 17 goals, official target descriptions and reviewed links', async () => {
    visit('/sdgs');
    expect(await screen.findByText('17 official goals')).toBeInTheDocument();
    const goals = screen.getAllByRole('heading',{level:2}).filter(heading=>heading.textContent?.startsWith('Goal '));
    expect(goals).toHaveLength(17);
    const education = screen.getByRole('heading',{name:'Goal 4'}).closest('section')!;
    fireEvent.click(within(education).getByText('Explore targets & relevance'));
    expect(within(education).getByText(/substantially increase the number of youth and adults/)).toBeInTheDocument();
    expect(within(education).getAllByText('human reviewed').length).toBeGreaterThan(0);
    expect(screen.getByRole('link',{name:'United Nations source'})).toHaveAttribute('href','https://sdgs.un.org/goals');
  });
  it('marks market history as historical and keeps live AI feeds disconnected', async () => {
    visit('/');
    expect(await screen.findByText('US market history imported')).toBeInTheDocument();
    expect(screen.getByText(/Live AI feeds are not connected/)).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'View data & provenance'})).toHaveAttribute('href','/datasets');
  });
  it('preserves last-successful counts and shows a failed latest attempt', async () => {
    vi.mocked(fetch).mockImplementation(async input => ({ok:true,json:async()=>String(input)==='/api/health'?{status:'ok',service:'noka-api'}:{...fixture.summary,last_attempt:{...fixture.summary.last_attempt,status:'failed'}}}) as Response);
    visit('/datasets');
    expect(await screen.findByText('141')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Last-successful data remains available');
  });
});
