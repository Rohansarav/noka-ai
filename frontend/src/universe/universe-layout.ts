import type { CareerGraphData, CareerNode, UniverseFilter } from './universe-types';

export const FILTERS: { id: UniverseFilter; label: string }[] = [
  { id: 'all', label: 'All connections' }, { id: 'owned', label: 'My existing skills' },
  { id: 'gaps', label: 'Skill gaps' }, { id: 'sdgs', label: 'SDG connections' },
];

/** Filtering changes presentation only. A partial skill retains its owned identity. */
export function filterGraph(graph: CareerGraphData, filter: UniverseFilter) {
  if (filter === 'all') return { nodes: graph.nodes, edges: graph.edges };
  const keep = new Set(graph.nodes.filter(n => n.type === 'profile' || n.type === 'role').map(n => n.id));
  if (filter === 'owned') graph.nodes.filter(n => n.type === 'owned_skill').forEach(n => keep.add(n.id));
  if (filter === 'gaps') graph.edges.filter(e => e.type === 'missing_skill').forEach(e => { keep.add(e.source); keep.add(e.target); });
  if (filter === 'sdgs') graph.edges.filter(e => e.type === 'contributes_to_target' || e.type === 'target_belongs_to_goal').forEach(e => { keep.add(e.source); keep.add(e.target); });
  return { nodes: graph.nodes.filter(n => keep.has(n.id)), edges: graph.edges.filter(e => keep.has(e.source) && keep.has(e.target) && (filter !== 'owned' || e.type !== 'missing_skill')) };
}

/** Stable lanes keep nodes apart without a layout engine or server-side coordinates. */
export function layoutNodes(nodes: CareerNode[]) {
  const positions: Record<string, { x: number; y: number }> = {};
  const groups = (type: CareerNode['type']) => nodes.filter(n => n.type === type).sort((a, b) => a.id.localeCompare(b.id));
  const owned = groups('owned_skill');
  const rows = Math.max(3, Math.ceil(owned.length / 2));
  const height = Math.max(520, rows * 100);
  groups('profile').forEach(n => { positions[n.id] = { x: 390, y: height / 2 - 40 }; });
  owned.forEach((n, i) => { positions[n.id] = { x: i % 2 === 0 ? 10 : 200, y: 20 + Math.floor(i / 2) * 100 }; });
  groups('role').sort((a, b) => (b.score ?? 0) - (a.score ?? 0) || a.label.localeCompare(b.label)).forEach((n, i) => { positions[n.id] = { x: 690, y: 35 + i * 165 }; });
  nodes.filter(n=>n.type==='required_skill'||n.type==='context_skill').sort((a,b)=>a.id.localeCompare(b.id)).forEach((n, i) => { positions[n.id] = { x: 960 + (i % 2) * 190, y: 20 + Math.floor(i / 2) * 110 }; });
  groups('technology').forEach((n,i)=>{positions[n.id]={x:1350+(i%2)*190,y:20+Math.floor(i/2)*110};});
  const contentBottom=Math.max(height,...Object.values(positions).map(p=>p.y+165));
  groups('sdg_target').forEach((n, i) => { positions[n.id] = { x: 690 + i * 225, y: contentBottom + 70 }; });
  groups('sdg').forEach((n, i) => { positions[n.id] = { x: 690 + i * 225, y: contentBottom + 220 }; });
  return positions;
}

/** Highlight direct requirements plus their goal chain; do not imply links to other careers. */
export function relatedNodeIds(graph: Pick<CareerGraphData, 'nodes' | 'edges'>, selected: string | null) {
  const ids = new Set<string>();
  if (!selected) return ids;
  ids.add(selected);
  graph.edges.filter(e => e.source === selected || e.target === selected).forEach(e => { ids.add(e.source); ids.add(e.target); });
  const selectedNode=graph.nodes.find(n=>n.id===selected);
  const sources=new Set([selected]);
  if(selectedNode?.type==='role')graph.edges.filter(e=>(e.type==='requires_skill'||e.type==='context_requirement')&&e.source===selected).forEach(e=>sources.add(e.target));
  graph.edges.filter(e=>e.type==='contributes_to_target'&&sources.has(e.source)).forEach(e=>{ids.add(e.source);ids.add(e.target);});
  graph.edges.filter(e => e.type === 'target_belongs_to_goal' && (ids.has(e.source) || ids.has(e.target))).forEach(e => { ids.add(e.source); ids.add(e.target); });
  graph.nodes.filter(n => n.type === 'profile').forEach(n => ids.add(n.id));
  return ids;
}
