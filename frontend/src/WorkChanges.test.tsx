import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import WorkChanges from './WorkChanges';
import { Dimensions, type Opportunity } from './OpportunityEvidence';

const row:Opportunity={role_id:'developer',title:'Developer',market:'MY',dimensions:{demand:{labels:['growing'],status:'supported',market:'Global'},change:{labels:[],status:'insufficient_evidence',market:null,reason:'Evidence awaiting human review'},availability:{labels:['reported_shortage'],status:'supported',market:'MY'}},evidence:[],mappings:[],published_count:0,pending_count:0,limitation:''};
afterEach(()=>vi.unstubAllGlobals());

const eligible:Opportunity={...row,dimensions:{...row.dimensions,change:{labels:['transforming'],status:'supported',market:'Global'}},evidence:[{id:'claim',current:true,dimension:'change',category:'transforming',market:'Global',observation_period:'2025',source:{title:'Task study',url:'https://example.com/study'}} as Opportunity['evidence'][number]]};

it.each(['insufficient_evidence','stale','pending_review'])('hides interpretation for %s even with cached or unrelated evidence',status=>{
 const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);
 render(<QueryClientProvider client={new QueryClient()}><WorkChanges row={{...eligible,dimensions:{...eligible.dimensions,change:{labels:[],status,market:null}}}}/></QueryClientProvider>);
 expect(screen.queryByText('How work could change')).not.toBeInTheDocument();
 expect(fetcher).not.toHaveBeenCalled();
});

it.each(['availability','demand'])('does not use %s evidence to enable explanation',dimension=>{
 render(<QueryClientProvider client={new QueryClient()}><WorkChanges row={{...eligible,evidence:eligible.evidence.map(c=>({...c,dimension}))}}/></QueryClientProvider>);
 expect(screen.queryByText('How work could change')).not.toBeInTheDocument();
});

it('uses distinct signal colours with explicit unknown evidence and reason',()=>{
 render(<Dimensions row={row}/>);
 expect(screen.getByText('growing')).toHaveClass('signal-growing');
 expect(screen.getByText('reported shortage')).toHaveClass('signal-reported_shortage');
 expect(screen.getByText('Insufficient reviewed evidence')).toHaveClass('signal-insufficient_evidence');
 expect(screen.getByText('Evidence awaiting human review')).toBeVisible();
 expect(screen.queryByText('declining')).not.toBeInTheDocument();
});

it('generates only on request, replaces unsupported suggestions with sources and resets for a new market',async()=>{
 const fetcher=vi.fn(async()=>({ok:true,json:async()=>({status:'suggestion',label:'transforming',explanation:'',source_ids:[],notice:'LLM suggestion, needs reviewed evidence'})}));vi.stubGlobal('fetch',fetcher);
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 const view=render(<QueryClientProvider client={client}><WorkChanges row={eligible}/></QueryClientProvider>);
 expect(fetcher).not.toHaveBeenCalled();
 fireEvent.click(screen.getByText('How work could change'));
 fireEvent.click(screen.getByRole('button',{name:'Explain these work changes'}));
 expect(await screen.findByText('An explanation could not be generated from the available sources.')).toBeVisible();
 expect(screen.getByRole('link',{name:/Task study/})).toBeVisible();
 expect(screen.queryByText(/tentative label|Possibly transforming/)).not.toBeInTheDocument();
 expect(fetcher).toHaveBeenCalledTimes(1);
 view.rerender(<QueryClientProvider client={client}><WorkChanges row={{...eligible,market:'SG'}}/></QueryClientProvider>);
 expect(screen.queryByText('Possibly transforming')).not.toBeInTheDocument();
 expect(fetcher).toHaveBeenCalledTimes(1);
});

it('keeps a failed interpretation retryable without inventing a label',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline')));
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><WorkChanges row={eligible}/></QueryClientProvider>);
 fireEvent.click(screen.getByText('How work could change'));
 fireEvent.click(screen.getByRole('button',{name:'Explain these work changes'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Interpretation unavailable');
 expect(screen.getByRole('button',{name:'Explain these work changes'})).toBeEnabled();
 expect(screen.queryByText('Possibly transforming')).not.toBeInTheDocument();
});
