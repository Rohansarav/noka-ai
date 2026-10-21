import { useState } from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CareerDiscovery from './CareerDiscovery';
import type { CareerAspiration } from './profile-api';

let requests:string[],fail:boolean;
const dataRole={id:'15-2051.00',title:'Data Scientists',description:'Analyse data with statistical methods.',family:'15',source_id:'onet',match_reason:'Noka search hint; confirm this interpretation'};
beforeEach(()=>{requests=[];fail=false;vi.stubGlobal('fetch',vi.fn(async(input:string)=>{requests.push(String(input));return {ok:!fail,json:async()=>({roles:[dataRole],total:25,offset:0,limit:12,families:['15','17'],method:'Source-backed US occupations; confirm interpretations.'})};}));});
afterEach(()=>vi.unstubAllGlobals());
function Harness({initial=[]}:{initial?:string[]}){const [interests,setInterests]=useState(initial),[aspirations,setAspirations]=useState<CareerAspiration[]>([]);return <><CareerDiscovery interests={interests} aspirations={aspirations} titles={{'15-2051.00':'Data Scientists'}} onChange={(i,a)=>{setInterests(i);setAspirations(a);}}/><output aria-label="Saved interests">{JSON.stringify({interests,aspirations})}</output></>;}
function visit(initial:string[]=[]){render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><Harness initial={initial}/></QueryClientProvider>);}

it('searches, filters and paginates the catalogue with bounded server requests',async()=>{
  visit();await screen.findByText('25 occupations match · 0/5 targets selected');
  fireEvent.change(screen.getByRole('searchbox',{name:'Search careers'}),{target:{value:'software'}});
  await waitFor(()=>expect(requests.some(path=>path.includes('q=software'))).toBe(true));
  fireEvent.change(screen.getByRole('combobox',{name:'Career family'}),{target:{value:'15'}});
  await waitFor(()=>expect(requests.some(path=>path.includes('family=15'))).toBe(true));
  fireEvent.click(await screen.findByRole('button',{name:'More careers'}));
  await waitFor(()=>expect(requests.some(path=>path.includes('offset=12'))).toBe(true));
  fireEvent.click(await screen.findByRole('checkbox',{name:'Data Scientists'}));
  expect(screen.getByLabelText('Saved interests')).toHaveTextContent('"interests":["15-2051.00"]');
});

it('keeps an exact custom title and requires confirmation before mapping it to an occupation',async()=>{
  visit();await screen.findByRole('checkbox',{name:'Data Scientists'});
  fireEvent.change(screen.getByRole('textbox',{name:'Your career title'}),{target:{value:'Machine Learning Engineer'}});
  fireEvent.click(screen.getByRole('button',{name:'Find interpretations'}));
  expect(screen.getByLabelText('Saved interests')).toHaveTextContent('"aspirations":[]');
  expect(screen.getByRole('button',{name:'Confirm 0 interpretations'})).toBeDisabled();
  fireEvent.click(screen.getByRole('checkbox',{name:'Data Scientists'}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm 1 interpretation'}));
  expect(screen.getByLabelText('Saved interests')).toHaveTextContent('"title":"Machine Learning Engineer","role_ids":["15-2051.00"],"status":"confirmed"');
  expect(screen.getByLabelText('Saved interests')).toHaveTextContent('"interests":[]');
});

it('saves unknown aspirations honestly and preserves existing targets when career search fails',async()=>{
  fail=true;visit(['15-2051.00']);
  await screen.findByRole('alert');
  expect(screen.getByRole('button',{name:'Remove target Data Scientists'})).toBeInTheDocument();
  fireEvent.change(screen.getByRole('textbox',{name:'Your career title'}),{target:{value:'A specialty without a supported mapping'}});
  fireEvent.click(screen.getByRole('button',{name:'Keep as an unmapped interest'}));
  expect(screen.getByLabelText('Saved interests')).toHaveTextContent('"role_ids":[],"status":"unmapped"');
  expect(screen.getByLabelText('Saved interests')).toHaveTextContent('"interests":["15-2051.00"]');
  fail=false;fireEvent.click(screen.getByRole('button',{name:'Retry career search'}));
  await screen.findByRole('checkbox',{name:'Data Scientists'});
});
