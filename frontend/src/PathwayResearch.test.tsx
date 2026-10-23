import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PathwayResearch, { ResearchActivity } from './PathwayResearch';
import type { Future } from './future-api';
import type { ResearchRun } from './pathway-research-api';

const future={profile_id:'private-fixture',role_id:'role-fixture',weekly_hours:6,matches:[{role_id:'role-fixture',title:'AI Engineer'}]} as Future;
const base:ResearchRun={id:'run-fixture',role_id:'role-fixture',target:'AI Engineer',market:'Malaysia',created_at:'2026-10-23T08:00:00Z',status:'review',events:[],sources:[{id:'s1',title:'Fixture employer',url:'https://example.com/job',origin:'web',retrieved_at:'2026-10-23T08:00:00Z',location:'Malaysia',availability:'not_verified',reason:'Fixture job relevance.'}],requirements:[{id:'r1',source_id:'s1',title:'Design reliable systems',quote:'Design reliable systems and test failure modes.',priority:'required'}],review:null,project:null,error:null};
afterEach(()=>vi.unstubAllGlobals());
function setup(runs:ResearchRun[]=[]){
  const calls:{path:string;body:unknown}[]=[];
  vi.stubGlobal('fetch',vi.fn(async(input,init)=>{
    if(init?.method==='POST'||init?.method==='PUT'){
      calls.push({path:String(input),body:init.body?JSON.parse(init.body):null});
      return {ok:true,json:async()=>({...base,status:'planning',events:[{stage:'planning',message:'Designing your project.',at:base.created_at}]})};
    }
    return {ok:true,json:async()=>({runs})};
  }));
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}><PathwayResearch future={future}/></QueryClientProvider>);
  return calls;
}

it('loads saved research without automatically making provider requests',async()=>{
  const calls=setup();
  await waitFor(()=>expect(screen.getByRole('button',{name:'Research my target'})).toBeEnabled());
  expect(calls).toHaveLength(0);
  fireEvent.click(screen.getByRole('button',{name:'Research my target'}));
  await waitFor(()=>expect(calls[0].body).toEqual({role_id:'role-fixture'}));
});

it('requires a selected requirement and records the chosen starting point',async()=>{
  const calls=setup([base]);
  const confirm=await screen.findByRole('button',{name:'Confirm requirements & propose project'});
  fireEvent.click(screen.getByRole('checkbox',{name:'Design reliable systems'}));
  expect(confirm).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox',{name:'Design reliable systems'}));
  fireEvent.change(screen.getByRole('combobox',{name:'Starting point for Design reliable systems'}),{target:{value:'demonstrate'}});
  fireEvent.click(confirm);
  await waitFor(()=>expect(calls[0]).toEqual({path:'/api/pathway-research/run-fixture/review',body:{items:[{requirement_id:'r1',starting_point:'demonstrate'}]}}));
});

it('shows real server stages without a fabricated completion percentage',()=>{
  render(<ResearchActivity run={{...base,status:'extracting',events:[{stage:'extracting',message:'Found four pages. Reading descriptions.',at:base.created_at}]}}/>);
  expect(screen.getByRole('status')).toHaveTextContent('Found four pages. Reading descriptions.');
  expect(screen.getByText('Read sources').closest('li')).toHaveAttribute('aria-current','step');
  expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
});

it('keeps a manual description available when the request fails',async()=>{
  setup();
  await waitFor(()=>expect(screen.getByRole('button',{name:'Research my target'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Paste a description'}));
  const text='A fixture job description with responsibilities and requirements in Malaysia. '.repeat(3);
  fireEvent.change(screen.getByLabelText('Paste the full job description'),{target:{value:text}});
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,status:503})));
  fireEvent.click(screen.getByRole('button',{name:'Analyze this description'}));
  await screen.findByRole('alert');
  expect(screen.getByLabelText('Paste the full job description')).toHaveValue(text);
});

it('shows a saved project and gates completion on evidence',async()=>{
  setup([{...base,status:'ready',review:{reviewed_at:base.created_at,reviewed_by:'profile_owner',items:[{requirement_id:'r1',starting_point:'practice'}]},project:{title:'Fixture project',problem:'A fixture problem to validate.',audience:'Fixture audience',why_you:'Fixture prior experience.',scope:'One small fixture.',assumptions:['Validate access.'],accepted_at:base.created_at,accepted_by:'profile_owner',milestones:[{id:'m1',title:'Test a failure',objective:'Check a controlled failure.',requirement_ids:['r1'],steps:['Define failure.','Run check.'],deliverable:'A test report.',acceptance_criteria:['Record results.','Explain limits.'],learn:'Failure testing.',effort_hours:4,note:'',status:'planned'}]}}]);
  await screen.findByRole('heading',{name:'Fixture project'});
  expect(screen.getByRole('option',{name:'Completed'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Evidence and reflection'),{target:{value:'Tested the failure and recorded recovery behavior.'}});
  expect(screen.getByRole('option',{name:'Completed'})).toBeEnabled();
});
