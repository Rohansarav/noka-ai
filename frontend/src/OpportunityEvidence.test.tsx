import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CareerOpportunity, OpportunityExplorer, ClaimEvidence } from './OpportunityEvidence';
const result={items:[],total:0,counts:{emerging:0,growing:0},covered_roles:0,catalogue_roles:910,sources:[],method:'Only reviewed evidence publishes labels.'};
function setup(node:React.ReactNode){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{node}</QueryClientProvider>);}
afterEach(()=>vi.unstubAllGlobals());
it('searches synthetic careers inside Atlas and keeps their assumptions explicit',async()=>{
 const fetcher=vi.fn(async(input:unknown)=>({ok:true,json:async()=>String(input).includes('review=synthetic')?{...result,total:1,covered_roles:1,items:[{synthetic:true,dimensions:{demand:'growing',change:'emerging',availability:'reported_shortage'},role_id:'synthetic:0',title:'Forward Deployed Engineer',category:'emerging',market:'Global illustrative context',tasks:'Evaluate client deployments.',skills:['AI evaluation'],assumption:'Illustrative classification, not an observed forecast.',baselines:[{statement:'Public task-change context',source:{publisher:'Baseline publisher',title:'Baseline report',url:'https://example.org/report',publication_date:'2025-01-01'}}]}]}:result}));
 vi.stubGlobal('fetch',fetcher); setup(<OpportunityExplorer/>);
 await screen.findByText(/0 careers with evidence/);
 expect(screen.getByLabelText('Evidence status').querySelectorAll('option')).toHaveLength(2);
 fireEvent.change(screen.getByLabelText('Evidence status'),{target:{value:'synthetic'}});
 await screen.findByRole('heading',{name:'Forward Deployed Engineer'});
 expect(screen.getByText(/not an observed forecast/)).toBeInTheDocument();
 expect(screen.getByRole('link',{name:/Baseline report/})).toHaveAttribute('href','https://example.org/report');
 fireEvent.change(screen.getByLabelText('Find a career'),{target:{value:'Forward'}});
 await waitFor(()=>expect(fetcher.mock.calls.some(c=>String(c[0]).includes('search=Forward')&&String(c[0]).includes('review=synthetic'))).toBe(true));
 expect(fetcher.mock.calls.every(c=>!String(c[0]).includes('work-changes'))).toBe(true);
});
it('explains empty categories and sends separate geography and review filters',async()=>{
 const fetcher=vi.fn(async(_input:unknown)=>({ok:true,json:async()=>result}));vi.stubGlobal('fetch',fetcher);
 setup(<OpportunityExplorer/>);
 await screen.findByText(/0 careers with evidence/);
 fireEvent.click(screen.getByRole('button',{name:/emerging 0/i}));
 await screen.findByText('No emerging evidence in this view.');
 expect(screen.getByText(/No current claim has both/)).toBeInTheDocument();
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
 await screen.findByText('Insufficient reviewed evidence');
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

it('keeps internal approval context out of evidence cards while preserving sources and status',()=>{
 const review={status:'approved',reviewer:'Rohan',reviewed_at:'2026-10-22',reason:'Project owner explicitly instructed: Just approve all the data.'};
 render(<ClaimEvidence claim={{id:'claim-fixture',category:'reported_shortage',dimension:'availability',market:'MY',basis:'shortage_list',observation_period:'2024/2025',horizon:null,statement:'The source reports an occupation shortage.',locator:'Page 10',valid_until:'2027-01-01',state:'published',current:true,review,
 mapping:{id:'mapping-fixture',occupation_code:'123',occupation_title:'Example occupation',taxonomy:'Fixture taxonomy',family:'Example',relationship:'equivalent',rationale:'Responsibilities match this occupation.',limitations:'Occupation scope applies.',review},
 source:{id:'source-fixture',title:'Original publication',publisher:'Example publisher',url:'https://example.com/source',publication_date:'2025-01-01',retrieved_at:'2026-10-22',version:'1',coverage:'MY',access:'public',refresh:'annual',reuse:'attributed',limitation:'Scope applies.'}}}/>);
 fireEvent.click(screen.getByText('View evidence'));
 expect(screen.getByText('Malaysia · Reviewed evidence')).toBeInTheDocument();
 expect(screen.getByRole('link',{name:/Original publication/})).toHaveAttribute('href','https://example.com/source');
 expect(screen.getByText(/Mapping ID: mapping-fixture/)).toBeInTheDocument();
 expect(screen.queryByText(/Rohan|Project owner explicitly instructed|Claim review:|Mapping review:|Mapping: approved/)).not.toBeInTheDocument();
});
