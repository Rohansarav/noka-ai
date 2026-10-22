import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CareerOpportunity, OpportunityExplorer } from './OpportunityEvidence';
const result={items:[],total:0,counts:{emerging:0,growing:0},covered_roles:0,catalogue_roles:910,sources:[],method:'Only reviewed evidence publishes labels.'};
function setup(node:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{node}</QueryClientProvider>);}
afterEach(()=>vi.unstubAllGlobals());
it('explains empty categories and sends separate geography and review filters',async()=>{
 const fetcher=vi.fn(async(_input:unknown)=>({ok:true,json:async()=>result}));vi.stubGlobal('fetch',fetcher);
 setup(<OpportunityExplorer/>);
 await screen.findByText(/0 careers with evidence/);
 fireEvent.click(screen.getByRole('button',{name:/emerging 0/i}));
 await screen.findByText('No emerging evidence in this view.');
 expect(screen.getByText(/new title or a search result alone/)).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Evidence status'),{target:{value:'published'}});
 await screen.findByText(/No current claim has both/);
 expect(fetcher.mock.calls.some(c=>String(c[0]).includes('review=published'))).toBe(true);
 fireEvent.change(screen.getByLabelText('Market'),{target:{value:'Global'}});
 await waitFor(()=>expect(fetcher.mock.calls.some(c=>String(c[0]).includes('market=Global'))).toBe(true));
});
it('changes the evidence query when the saved market changes without displaying invented scores',async()=>{
 const fetcher=vi.fn(async(_input:unknown)=>({ok:true,json:async()=>({role_id:'15-1252.00',title:'Software Developers',dimensions:{demand:{labels:[],status:'insufficient_evidence',market:null}},evidence:[],mappings:[],published_count:0,pending_count:0,limitation:'No hiring probability.'})}));vi.stubGlobal('fetch',fetcher);
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 const view=render(<QueryClientProvider client={client}><CareerOpportunity roleId="15-1252.00" market="MY"/></QueryClientProvider>);
 await screen.findByText('Not established');
 expect(screen.getByText(/does not mean the career is declining/)).toBeInTheDocument();
 view.rerender(<QueryClientProvider client={client}><CareerOpportunity roleId="15-1252.00" market="SG"/></QueryClientProvider>);
 await waitFor(()=>expect(fetcher.mock.calls.some(c=>String(c[0]).includes('market=SG'))).toBe(true));
});
it('handles unavailable and malformed responses with retry',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(_input:unknown)=>({ok:true,json:async()=>({})})));
 setup(<OpportunityExplorer/>);
 expect(await screen.findByRole('alert')).toHaveTextContent('Evidence could not be loaded');
 expect(screen.getByRole('button',{name:'Retry'})).toBeEnabled();
});
