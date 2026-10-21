import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { PathwayPage, WorldDial } from './FuturePages';
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
});
