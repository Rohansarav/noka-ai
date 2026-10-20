import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
function visit(path: string) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>); }
afterEach(() => { vi.useRealTimers(); vi.mocked(fetch).mockReset().mockRejectedValue(new Error('offline')); });
describe('Noka navigation', () => {
  it('offers the complete module navigation and the branded hero', () => { visit('/'); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Noka.Navigate tomorrow’swork, today.'); expect(screen.getByRole('navigation').querySelectorAll('a')).toHaveLength(8); expect(screen.getByRole('link', { name: 'Build My Future' })).toHaveAttribute('href', '/profile/intake'); });
  it.each([['/profile', 'Your next chapter starts with you.'], ['/forecast', 'Look ahead, with perspective.'], ['/roadmap', 'Small steps. New possibilities.'], ['/model-lab', 'Understand the evidence behind it.']])('opens %s with an honest empty state', (path, title) => { visit(path); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(title); expect(screen.getByText('Not connected yet')).toBeInTheDocument(); });
  it('handles missing routes', () => { visit('/missing'); expect(screen.getByText('This path doesn’t exist yet.')).toBeInTheDocument(); });
  it('shows API failure honestly', async () => { visit('/'); expect(await screen.findByRole('alert')).toHaveTextContent('API unavailable'); });
  it('does not equate API connectivity with source ingestion', async () => {
    vi.mocked(fetch).mockImplementation(async path => ({ ok: true, json: async () => String(path) === '/api/health' ? { status: 'ok', service: 'noka-api' } : { sources: [], counts: { job_demand_observations: 0 }, last_successful_imports: [], end_date: null } }) as Response);
    visit('/');
    expect(await screen.findByText('API connected')).toBeInTheDocument();
    expect(screen.getByText('No data yet')).toBeInTheDocument();
    expect(screen.getByText('Never')).toBeInTheDocument();
    expect(screen.queryByText(/\d+ job postings/)).not.toBeInTheDocument();
  });
  it('offers the three named steps', () => {
    visit('/');
    for (const name of ['How Noka works', 'Scout', 'Oracle', 'Guide']) expect(screen.getByRole('heading', { name })).toBeInTheDocument();
  });
  it.each(['/profile', '/roadmap'])('offers honest intake from %s', path => {
    visit(path);
    expect(screen.getByRole('heading', { name: 'No profile yet' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Explore profile intake' })).toHaveAttribute('href', '/profile/intake');
  });
  it('opens intake from the hero without collecting or claiming to save a profile', () => {
    visit('/');
    fireEvent.click(screen.getByRole('link', { name: 'Build My Future' }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Start with what makes you, you.');
    expect(screen.getByText('Nothing has been uploaded or saved.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Resume upload coming soon' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Manual entry coming soon' })).toBeDisabled();
    expect(screen.getByRole('main')).toHaveFocus();
    expect(document.title).toBe('Noka — Profile intake');
  });
  it('supports Escape and route selection in the mobile navigation disclosure', () => {
    visit('/');
    const toggle = screen.getByRole('button', { name: 'Open navigation' });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(toggle).toHaveFocus();
    fireEvent.click(toggle);
    fireEvent.click(within(screen.getByRole('navigation')).getByRole('link', { name: 'Forecast' }));
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('main')).toHaveFocus();
  });
  it('provides labelled sample states and progress in the gallery', () => {
    visit('/design-preview');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('A little calm. A lot of clarity.');
    expect(screen.getByRole('progressbar', { name: 'Example progress 40%' })).toHaveAttribute('value', '40');
    expect(screen.getByRole('status', { name: 'Example loading state' })).toBeInTheDocument();
    expect(screen.getByText(/All values below are visual examples/)).toBeInTheDocument();
  });
  it('closes mobile navigation when selecting the current page', () => {
    visit('/');
    const toggle = screen.getByRole('button', { name: 'Open navigation' });
    fireEvent.click(toggle);
    fireEvent.click(within(screen.getByRole('navigation')).getByRole('link', { name: 'Overview' }));
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByRole('main')).toHaveFocus();
  });
  it('announces and dismisses a sample toast without claiming a save', () => {
    visit('/design-preview');
    const region = screen.getByRole('region', { name: 'Notifications' });
    expect(region).toHaveAttribute('aria-live', 'polite');
    fireEvent.click(screen.getByRole('button', { name: 'Show sample notification' }));
    expect(within(region).getByText('This is a design-system example. Nothing was saved.')).toBeInTheDocument();
    fireEvent.click(within(region).getByRole('button', { name: 'Dismiss Preview notification' }));
    expect(within(region).queryByText('Preview notification')).not.toBeInTheDocument();
  });
  it('pauses toast dismissal while focused and dismisses after leaving', () => {
    vi.useFakeTimers();
    visit('/design-preview');
    fireEvent.click(screen.getByRole('button', { name: 'Show sample notification' }));
    const dismiss = screen.getByRole('button', { name: 'Dismiss Preview notification' });
    fireEvent.focus(dismiss);
    act(() => { vi.advanceTimersByTime(10000); });
    expect(dismiss).toBeInTheDocument();
    fireEvent.blur(dismiss);
    act(() => { vi.advanceTimersByTime(8000); });
    expect(screen.queryByRole('button', { name: 'Dismiss Preview notification' })).not.toBeInTheDocument();
  });
});
