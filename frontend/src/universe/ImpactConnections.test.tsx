import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import ImpactConnections from './ImpactConnections';
import type { CareerGraphData, CareerNode, CareerEdge } from './universe-types';

function node(id:string,type:CareerNode['type'],label:string):CareerNode{return {id,type,label,entity_id:id.split(':')[1],description:'',source_ids:[],review_status:null,level:null,years:null,skill_count:null,country:null,is_demo:false,score:null,coverage:null,explanation:null,goal_id:null};}
function edge(value:Partial<CareerEdge>&Pick<CareerEdge,'id'|'type'|'source'|'target'>):CareerEdge{return {source_ids:[],importance:null,gap:null,critical:false,review_status:null,rationale:null,supporting_id:null,...value};}

const graph:CareerGraphData={status:'ready',profile_revision:'fixture',generated_at:'2026-10-21T00:00:00Z',sources:[],methodology:'Fixture explanation.',limitations:[],
  nodes:[node('role:software','role','Software Developers'),node('skill:science','context_skill','Science'),node('sdg_target:9.5','sdg_target','Target 9.5'),node('sdg:9','sdg','Goal 9')],
  edges:[edge({id:'context',type:'context_requirement',source:'role:software',target:'skill:science',importance:2.12,rationale:'Published occupational skill context.'}),
    edge({id:'reviewed',type:'contributes_to_target',source:'skill:science',target:'sdg_target:9.5',review_status:'human_reviewed',rationale:'Reviewed scientific skill relationship; not direct career impact.'}),
    edge({id:'goal',type:'target_belongs_to_goal',source:'sdg_target:9.5',target:'sdg:9'})],impact:{reviewed_links:1,pending_links:2,message:'Only attributed, reviewed connections are shown.'}};

it('shows the actual skill-level path and lets the user open its target evidence',()=>{
  const select=vi.fn();render(<ImpactConnections graph={graph} selected="role:software" onSelect={select}/>);
  const button=screen.getByRole('button',{name:/Science → Target 9.5/});
  expect(screen.queryByRole('button',{name:/Software Developers → Target/})).not.toBeInTheDocument();
  expect(screen.getByText(/2 proposals/)).toBeInTheDocument();
  fireEvent.click(button);expect(select).toHaveBeenCalledWith('sdg_target:9.5');
});

it('explains missing reviewed evidence without creating substitute SDG connections',()=>{
  render(<ImpactConnections graph={{...graph,edges:[],impact:{reviewed_links:0,pending_links:0,message:'No reviewed relationship is recorded.'}}} selected="role:software" onSelect={()=>{}}/>);
  expect(screen.getByText('No reviewed relationship is recorded.')).toBeInTheDocument();
  expect(screen.getByText(/No connection has been inferred/)).toBeInTheDocument();
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
