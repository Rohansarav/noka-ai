import type { CareerGraphData } from './universe-types';

/** Every displayed contribution is an actual reviewed edge, never a keyword-generated SDG. */
export default function ImpactConnections({graph,selected,onSelect}:{graph:CareerGraphData;selected:string|null;onSelect:(id:string|null)=>void}) {
  const node=graph.nodes.find(n=>n.id===selected);
  const sources=new Set([selected]);
  if(node?.type==='role')graph.edges.filter(e=>(e.type==='requires_skill'||e.type==='context_requirement')&&e.source===selected).forEach(e=>sources.add(e.target));
  const reviewed=graph.edges.filter(e=>e.type==='contributes_to_target');
  const links=node?.type==='role'?reviewed.filter(e=>sources.has(e.source)):reviewed;
  return <section className="impact-evidence" aria-label="SDG connection evidence"><h2>Where your work could contribute</h2><p>{graph.impact?.message??(reviewed.length?'These connections come from attributed, human-reviewed relationships.':'No reviewed relationship is recorded for the displayed careers and skills. Missing evidence does not establish no impact.')}</p>
    {node?.type==='role'&&<p>Showing evidence for <strong>{node.label}</strong> and its published skill context. Context-only links are not priority gaps or direct career impact.</p>}
    {links.map(edge=><div key={edge.id}><button type="button" onClick={()=>onSelect(edge.target)}>{graph.nodes.find(n=>n.id===edge.source)?.label} → {graph.nodes.find(n=>n.id===edge.target)?.label}<span> · reviewed relationship</span></button><p>{edge.rationale}</p></div>)}
    {!links.length&&<p>{node?.type==='role'?'No reviewed connection is recorded for this selected career or its displayed requirements.':'No reviewed connectors are available in this view.'} No connection has been inferred from a career title or tool name.</p>}
    {node?.type==='role'&&reviewed.length>links.length&&<button type="button" onClick={()=>onSelect(null)}>See other reviewed connections in this map</button>}
    {!!graph.impact?.pending_links&&<p>{graph.impact.pending_links} proposals for displayed entities remain pending human review and are excluded from the connectors.</p>}
    <p>Skill-to-target relevance provides context; it does not establish measured career impact, UN endorsement or a direct role-to-goal relationship.</p>
  </section>;
}
