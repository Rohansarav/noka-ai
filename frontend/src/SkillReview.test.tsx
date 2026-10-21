import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import SkillReview from './SkillReview';
import type { Candidate, CustomSkill, ProfileSkill } from './profile-api';
const core=[{id:'broad:p',canonical_name:'Programming',aliases:[],category:'essential',source_id:'onet'}];
const software=[{id:'tech:p',canonical_name:'Python',aliases:['python programming'],category:'software',source_id:'software',source_url:'https://www.onetcenter.org/dictionary/31.0/csv/software_skills.html',source_version:'31.0'},{id:'tech:sql',canonical_name:'Structured query language SQL',aliases:['sql'],category:'software',source_id:'software'}];
let fail:boolean;
let requests:string[];
beforeEach(()=>{fail=false;requests=[];vi.stubGlobal('fetch',vi.fn(async(path:string)=>{requests.push(String(path));const url=new URL(String(path),'http://testserver');const q=(url.searchParams.get('q')??'').toLowerCase();const ids=url.searchParams.get('ids')?.split(',');const type=url.searchParams.get('category');const skills=[...core,...software].filter(s=>(!ids||ids.includes(s.id))&&(!q||[s.canonical_name,...s.aliases].some(n=>n.toLowerCase().includes(q)))&&(type==='core'?s.category!=='software':type==='software'?s.category==='software':true));return {ok:!fail,json:async()=>({skills,catalogue_total:3,matched_total:skills.length,counts:{core:1,software:2},offset:0,limit:20,method:'Published associations, not importance ratings.'})};}));});
afterEach(()=>vi.unstubAllGlobals());
function Harness({candidates=[]}:{candidates?:Candidate[]}){const [selected,setSelected]=useState<ProfileSkill[]>([]),[custom,setCustom]=useState<CustomSkill[]>([]);return <><SkillReview skills={core} candidates={candidates} selected={selected} onChange={setSelected} custom={custom} onCustomChange={setCustom}/><output aria-label="Stored selections">{JSON.stringify({selected,custom})}</output></>;}
function visit(candidates:Candidate[]=[]){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Harness candidates={candidates}/></QueryClientProvider>);}

it('searches aliases, shows catalogue totals and keeps software separate from broad skill credit',async()=>{
  visit();await screen.findByRole('button',{name:'Choose Python'});
  expect(screen.getByText(/Catalogue: 3 skills/)).toHaveTextContent('1 broad · 2 software and tools');
  fireEvent.change(screen.getByRole('searchbox'),{target:{value:'SQL'}});
  fireEvent.click(await screen.findByRole('button',{name:'Choose Structured query language SQL'}));
  const selected=screen.getByRole('region',{name:'Your confirmed skills'});
  await waitFor(()=>expect(within(selected).getByText('Structured query language SQL')).toBeInTheDocument());
  expect(screen.getByLabelText('Stored selections')).toHaveTextContent('"skill_id":"tech:sql"');
  expect(screen.getByLabelText('Stored selections')).not.toHaveTextContent('"skill_id":"broad:p"');
  expect(screen.getByText('Specific software · technical alignment only')).toBeInTheDocument();
});

it('loads extracted software labels by bounded IDs before presenting an addable suggestion',async()=>{
  visit([{mention:'Python',years:null,evidence_excerpt:'Used Python',confidence:'high',mapping:'exact',options:['tech:p']}]);
  fireEvent.click(await screen.findByRole('button',{name:'Add Python'}));
  expect(await screen.findByRole('button',{name:'Remove Python'})).toBeInTheDocument();
  expect(requests.some(path=>path.includes('ids=tech%3Ap'))).toBe(true);
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});

it('keeps unknown custom skills explicitly unmapped and preserves selections during catalogue failure',async()=>{
  visit();fireEvent.click(await screen.findByRole('button',{name:'Choose Python'}));
  fireEvent.change(screen.getByRole('searchbox'),{target:{value:'A custom laboratory workflow'}});
  fireEvent.click(await screen.findByRole('button',{name:'Keep “A custom laboratory workflow” as an unmapped custom skill'}));
  expect(screen.getByLabelText('Stored selections')).toHaveTextContent('"name":"A custom laboratory workflow"');
  fail=true;
  fireEvent.change(screen.getByRole('searchbox'),{target:{value:'New query'}});
  await screen.findByText(/Full catalogue search is unavailable/);
  expect(screen.getByLabelText('Stored selections')).toHaveTextContent('"skill_id":"tech:p"');
  expect(screen.getByText(/Custom · unmapped/)).toBeInTheDocument();
});
