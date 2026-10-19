import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';

vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
function visit(path: string) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={[path]}><App/></MemoryRouter></QueryClientProvider>); }
describe('Noka navigation', () => {
  it('offers the complete phase-zero navigation', () => { visit('/'); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Tomorrow’s work.'); expect(screen.getByRole('navigation').querySelectorAll('a')).toHaveLength(8); });
  it.each([['/profile', 'Your next chapter starts with you.'], ['/forecast', 'Look ahead, with perspective.'], ['/signals', 'See what’s shaping work.'], ['/matches', 'Find where your strengths fit.'], ['/roadmap', 'Small steps. New possibilities.'], ['/sdgs', 'Build skills with a bigger purpose.'], ['/model-lab', 'Understand the evidence behind it.']])('opens %s with an honest empty state', (path, title) => { visit(path); expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(title); expect(screen.getByText('Not connected yet')).toBeInTheDocument(); });
  it('handles missing routes', () => { visit('/missing'); expect(screen.getByText('This path doesn’t exist yet.')).toBeInTheDocument(); });
  it('shows API failure honestly', async () => { visit('/'); expect(await screen.findByRole('alert')).toHaveTextContent('API unavailable'); });
});
