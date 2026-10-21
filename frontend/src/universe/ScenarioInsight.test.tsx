import { describe,it,expect } from 'vitest';
import {render,screen} from '@testing-library/react';
import ScenarioInsight from './ScenarioInsight';
import CareerDetailPanel from './CareerDetailPanel';
import type {Future,FutureMatch} from '../future-api';
import type {CareerGraphData,CareerNode} from './universe-types';
import {MemoryRouter} from 'react-router-dom';

const base={role_id:'test',title:'Test career',score:45,coverage:40,transferable_coverage:35,interest_adjustment:0,explanation:'Factual fit',source_ids:[],gaps:[],scenario_reason:'Explicit test assumption'};
const acceleration:FutureMatch={...base,planning_index:47,scenario_emphasis:2,priority_skills:['Programming']};
const governed:FutureMatch={...base,planning_index:46,scenario_emphasis:1,priority_skills:['Monitoring']};
const data={scenario:'acceleration',role_id:'test',matches:[acceleration],comparisons:{acceleration:[acceleration],governed:[governed],collaboration:[acceleration]},scenarios:{acceleration:{name:'AI Acceleration',assumption:'Test acceleration'},governed:{name:'Governed AI',assumption:'Test governance'},collaboration:{name:'Human-AI Collaboration',assumption:'Test collaboration'}}} as Future;
describe('computed scenario presentation',()=>{
 it('compares actual priorities and explains an unchanged rank and fit',()=>{const view=render(<ScenarioInsight future={data}/>);view.rerender(<ScenarioInsight future={{...data,scenario:'governed',matches:[governed]}}/>);expect(screen.getByRole('status')).toHaveTextContent('New emphasis: Monitoring');expect(screen.getByRole('status')).toHaveTextContent('Planning position stays 1');expect(screen.getByRole('status')).toHaveTextContent('Skill fit stays 45');});
 it('explicitly explains a computed tie without inventing differences',()=>{const view=render(<ScenarioInsight future={data}/>);view.rerender(<ScenarioInsight future={{...data,scenario:'collaboration'}}/>);expect(screen.getByRole('status')).toHaveTextContent('The evidence does not justify a change');});
 it('refreshes role scenario context while preserving factual requirements and scores',()=>{const node={id:'role:test',type:'role',entity_id:'test',label:'Test career',score:45,coverage:40,source_ids:[],description:'Factual description',review_status:null,level:null,years:null,skill_count:null,country:'US',is_demo:true,explanation:'Factual fit',goal_id:null} as CareerNode;const graph={nodes:[node],edges:[],sources:[],methodology:'Factual methodology'} as unknown as CareerGraphData;const view=render(<MemoryRouter><CareerDetailPanel graph={graph} node={node} future={data}/></MemoryRouter>);view.rerender(<MemoryRouter><CareerDetailPanel graph={graph} node={node} future={{...data,scenario:'governed',matches:[governed]}}/></MemoryRouter>);expect(screen.getByRole('region',{name:'Role scenario context'})).toHaveTextContent('Monitoring');expect(screen.getByRole('region',{name:'Role scenario context'})).toHaveTextContent('documented coverage 45');expect(screen.getByText('Requirements in this view')).toBeInTheDocument();});
});
