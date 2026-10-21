import { describe, expect, it } from 'vitest';
import { filterGraph, layoutNodes, relatedNodeIds } from './universe-layout';
import type { CareerGraphData, CareerNode } from './universe-types';

const nodes = [{id:'profile:p',type:'profile'},{id:'skill:a',type:'owned_skill'},{id:'skill:b',type:'required_skill'}, {id:'role:a',type:'role',score:40,label:'First role'}, {id:'role:b',type:'role',score:30,label:'Second role'}, {id:'sdg_target:4.4',type:'sdg_target'},{id:'sdg:4',type:'sdg'}] as CareerNode[];
const edges = [{id:'owned',type:'has_skill',source:'profile:p',target:'skill:a'}, {id:'req',type:'requires_skill',source:'role:a',target:'skill:a',gap:.35},{id:'partial',type:'missing_skill',source:'role:a',target:'skill:a',gap:.35},{id:'missing',type:'missing_skill',source:'role:a',target:'skill:b',gap:1},{id:'other',type:'requires_skill',source:'role:b',target:'skill:a'},{id:'sdg-link',type:'contributes_to_target',source:'role:a',target:'sdg_target:4.4'},{id:'goal-link',type:'target_belongs_to_goal',source:'sdg_target:4.4',target:'sdg:4'}] as CareerGraphData['edges'];
const graph = {nodes,edges} as CareerGraphData;
describe('deterministic Universe presentation',()=>{
  it('keeps the complete reviewed skill-to-target path visible without implying another career',()=>{
    const contextGraph={nodes:[...nodes,{id:'skill:context',type:'context_skill'}],edges:[...edges.filter(e=>e.type!=='contributes_to_target'),{id:'context',type:'context_requirement',source:'role:a',target:'skill:context'},{id:'reviewed-context',type:'contributes_to_target',source:'skill:context',target:'sdg_target:4.4'}]} as CareerGraphData;
    const related=relatedNodeIds(contextGraph,'role:a');
    expect(related.has('skill:context')&&related.has('sdg_target:4.4')&&related.has('sdg:4')).toBe(true);
    expect(related.has('role:b')).toBe(false);
    const filtered=filterGraph(contextGraph,'sdgs');
    expect(filtered.edges.some(e=>e.id==='context')).toBe(true);
  });
  it('places every technology and the SDG lane below the tallest real content lane',()=>{
    const more=[...nodes,...Array.from({length:11},(_,i)=>({id:'role:extra'+i,type:'role',score:i,label:'Role '+i})),{id:'skill:software',type:'technology'}] as CareerNode[];
    const positions=layoutNodes(more);
    expect(positions['skill:software']).toBeDefined();
    expect(positions['sdg_target:4.4'].y).toBeGreaterThan(Math.max(...more.filter(n=>n.type==='role').map(n=>positions[n.id].y+160)));
  });
  it('keeps stable non-overlapping lane positions',()=>{
    expect(layoutNodes(nodes)).toEqual(layoutNodes([...nodes].reverse()));
    const positions = Object.values(layoutNodes(nodes)).map(p=>`${p.x}:${p.y}`);
    expect(new Set(positions).size).toBe(positions.length);
  });
  it('retains partial owned skills as owned in the gap filter',()=>{
    const filtered = filterGraph(graph,'gaps');
    expect(filtered.nodes.find(n=>n.id==='skill:a')?.type).toBe('owned_skill');
    expect(filtered.edges.every(e=>filtered.nodes.some(n=>n.id===e.source)&&filtered.nodes.some(n=>n.id===e.target))).toBe(true);
  });
  it('removes absent skills and gap emphasis in owned mode',()=>{
    const filtered = filterGraph(graph,'owned');
    expect(filtered.nodes.some(n=>n.id==='skill:b')).toBe(false);
    expect(filtered.edges.some(e=>e.type==='missing_skill')).toBe(false);
  });
  it('highlights the selected role and its SDG chain without implying other careers',()=>{
    const related=relatedNodeIds(graph,'role:a');
    expect([...related]).toEqual(expect.arrayContaining(['role:a','skill:a','skill:b','sdg_target:4.4','sdg:4','profile:p']));
    expect(related.has('role:b')).toBe(false);
  });
});
