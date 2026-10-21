import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { PathwayPage, WorldDial, ImpactPage, RadarPage } from './FuturePages';
import { useFuture } from './future-api';

const scenarios={acceleration:{name:'AI Acceleration',assumption:'Test assumption',skills:['Programming']},governed:{name:'Governed AI',assumption:'Test assumption',skills:['Monitoring']},collaboration:{name:'Human-AI Collaboration',assumption:'Test assumption',skills:['Active Listening']}};
const task={skill_id:'skill-1',name:'Programming',status:'completed',note:'Test note',effort_hours:24,start_week:1,end_week:0,objective:'Test objective',activity:'Test activity',project:'Test project',why:'Test explanation',scenario_priority:false,estimate_method:'Test estimate'};
let state: Record<string,unknown>;
let writes: {path:string;body:Record<string,unknown>}[];
let failSave=false;
beforeEach(()=>{
  writes=[];failSave=false;
  state={profile_id:'fixture-profile',profile_revision:'fixture-revision',scenario:'collaboration',role_id:'fixture-role',weekly_hours:6,version:'fixture',scenarios,matches:[{role_id:'fixture-role',title:'Fixture role'}],pathway:[task,{...task,skill_id:'skill-2',name:'Monitoring',status:'planned'}],future_self:'Collaboration fixture',conversation:[],comparisons:{acceleration:[],governed:[],collaboration:[]},worlds:{acceleration:{pathway:[task],future_self:'Acceleration fixture'},governed:{pathway:[task],future_self:'Governed fixture'},collaboration:{pathway:[task],future_self:'Collaboration fixture'}}};
  vi.stubGlobal('fetch',vi.fn(async (input,init)=>{
    const path=String(input);
    if(init?.method==='PUT'){
      const body=JSON.parse(String(init.body));writes.push({path,body});
      if(failSave)return {ok:false,status:503} as Response;
      state={...state,...body};
      return {ok:true,json:async()=>state} as Response;
    }
    return {ok:true,json:async()=>path==='/api/profiles/current'?{profile:{id:'fixture-profile',updated_at:'fixture-revision',confirmed:true}}:state} as Response;
  }));
});
afterEach(()=>vi.unstubAllGlobals());
function ReadContext(){const future=useFuture();return <output>{future.data?.scenario}</output>;}
function setup(children:React.ReactNode){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter>{children}</MemoryRouter></QueryClientProvider>);}
describe('Future workspace interactions',()=>{
  it.each(['/profile','/profile/intake','/signals','/sdgs','/model-lab'])('hides the dial on factual surface %s without scenario writes',path=>{
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={[path]}><WorldDial/></MemoryRouter></QueryClientProvider>);
    expect(screen.queryByRole('region',{name:'Choose your future world'})).not.toBeInTheDocument();
    expect(writes).toHaveLength(0);
  });
  it('shares the World Dial selection across query consumers',async()=>{
    setup(<><WorldDial/><ReadContext/></>);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Governed AI'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Governed AI'}));
    await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('governed'));
    expect(writes[0].body).toEqual({scenario:'governed'});
  });
  it('restores the previous world when persistence fails',async()=>{
    failSave=true;setup(<><WorldDial/><ReadContext/></>);
    await waitFor(()=>expect(screen.getByRole('button',{name:'AI Acceleration'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'AI Acceleration'}));
    await screen.findByRole('alert');
    expect(screen.getByRole('status')).toHaveTextContent('collaboration');
  });
  it('previews hours locally and saves only on explicit confirmation',async()=>{
    setup(<PathwayPage/>);
    await screen.findByText('Fixture role');
    fireEvent.change(screen.getByRole('slider'),{target:{value:'12'}});
    expect(screen.getByText('12 hours')).toBeInTheDocument();
    expect(writes).toHaveLength(0);
    expect(screen.getByDisplayValue('Completed')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Save commitment'}));
    await waitFor(()=>expect(writes[0].body).toEqual({weekly_hours:12}));
  });
  it('shows connected project handoffs and requires saved evidence before completion',async()=>{
    state={...state,pathway:[{...task,status:'planned',note:'',dependencies:[],handoff:'Define one career case study.',acceptance_criteria:['Check the work sample against success criteria.']}]};
    setup(<PathwayPage/>);
    expect(await screen.findByRole('heading',{name:'Your career portfolio'})).toBeVisible();
    expect(screen.getByText('Define one career case study.')).toBeVisible();
    expect(screen.getByText('Check the work sample against success criteria.')).toBeVisible();
    expect(screen.getByRole('option',{name:'Completed'})).toBeDisabled();
    expect(screen.getByText(/at least 20 characters/)).toBeVisible();
  });
  it('explains which world effects are planning assumptions',async()=>{
    state={...state,matches:[{role_id:'fixture-role',title:'Fixture role',priority_skills:['Active Listening']}]};
    setup(<WorldDial/>);
    expect(await screen.findByText(/Saved planning lens/)).toBeVisible();
    expect(screen.getByRole('heading',{name:'Fixture role'})).toBeVisible();
    expect(screen.getByText('Active Listening')).toBeVisible();
    expect(screen.getByRole('link',{name:'Explore your pathway'})).toHaveAttribute('href','/roadmap');
    fireEvent.click(screen.getByText('What changes with this lens?'));
    expect(screen.getByText(/Profile coverage, published requirements and reviewed SDG evidence stay fixed/)).toBeVisible();
    fireEvent.click(screen.getByRole('button',{name:'Human-AI Collaboration'}));
    expect(writes).toHaveLength(0);
  });
});


describe('focused evidence exploration',()=>{
  it('reveals the selected real target without promoting a pending proposal',async()=>{
    const ordinary=globalThis.fetch;
    vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
      const path=String(input);
      const payload=path==='/api/roles'?{roles:[{id:'fixture-role',title:'Fixture role'}]}:path.startsWith('/api/impact/')?{role:'Fixture role',limitation:'Fixture relevance only',relationships:[{id:'a',skill:'Instructing',responsibility:null,target_id:'4.4',goal_id:4,target:'Fixture education target',explanation:'Fixture reviewed relevance',status:'Curated SDG relationship',url:'https://sdgs.un.org/goals/goal4',relationship_type:'skill_target'},{id:'b',skill:null,responsibility:'Fixture role responsibility',target_id:'3.8',goal_id:3,target:'Fixture health target',explanation:'Fixture proposal',status:'Pending review',url:'https://sdgs.un.org/goals/goal3',relationship_type:'role_target'}]}:null;
      return payload?{ok:true,json:async()=>payload} as Response:ordinary(input,init);
    }));
    setup(<ImpactPage/>);
    await screen.findByRole('heading',{name:'Target 4.4'});
    fireEvent.click(screen.getByRole('button',{name:'Role responsibility to target 3.8'}));
    expect(screen.getByRole('heading',{name:'Target 3.8'})).toBeInTheDocument();
    expect(screen.getByText('Pending review')).toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Target 4.4'})).not.toBeInTheDocument();
    expect(writes).toHaveLength(0);
  });
  it('filters research and reveals source details without substituting a publication date',async()=>{
    const ordinary=globalThis.fetch;
    const finding={url:'https://example.org/evidence',publication_date:null,retrieved_at:'2026-10-20',source_statement:'Fixture source excerpt',inspection:'Fixture inspection',review_status:'pending',role_ids:[],skill_ids:[],interpretation:'Fixture interpretation'};
    vi.stubGlobal('fetch',vi.fn(async(input,init)=>String(input)==='/api/intelligence'?{ok:true,json:async()=>({outlooks:[],runs:[],method:'Fixture method',findings:[{...finding,id:'global',title:'Global fixture story',market:'Global'},{...finding,id:'my',title:'Malaysia fixture story',market:'MY'}]})} as Response:ordinary(input,init)));
    setup(<RadarPage/>);
    await screen.findByRole('heading',{name:'Global fixture story'});
    fireEvent.click(screen.getByRole('button',{name:'Malaysia'}));
    expect(screen.getByRole('heading',{name:'Malaysia fixture story'})).toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Global fixture story'})).not.toBeInTheDocument();
    expect(screen.getByText('Published date not verified')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Source excerpt & mapping status'));
    expect(screen.getByText('Fixture source excerpt')).toBeVisible();
    expect(writes).toHaveLength(0);
  });
});
