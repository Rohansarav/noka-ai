import { useEffect, useMemo, useRef, useState } from 'react';
import { Background, BackgroundVariant, Controls, ReactFlow, type Edge, type ReactFlowInstance } from '@xyflow/react';
import { Focus, Maximize2, RotateCcw } from 'lucide-react';
import { Button } from '../components';
import CareerNodeCard, { type UniverseFlowNode } from './CareerNodes';
import { filterGraph, layoutNodes, relatedNodeIds } from './universe-layout';
import type { CareerGraphData, UniverseFilter } from './universe-types';
import '@xyflow/react/dist/style.css';

const nodeTypes = { career: CareerNodeCard };

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false);
  useEffect(() => {
    const media = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!media) return;
    const update = () => setReduced(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  return reduced;
}

export default function CareerGraph({ graph, filter, selected, onSelect, highlighted = [], annotations = {} }: { annotations?: Record<string,string>; highlighted?: string[]; graph: CareerGraphData; filter: UniverseFilter; selected: string | null; onSelect: (id: string | null) => void }) {
  const [instance, setInstance] = useState<ReactFlowInstance<UniverseFlowNode, Edge> | null>(null);
  const reduced = useReducedMotion();
  const duration = reduced ? 0 : 240;
  const previousFilter = useRef(filter);
  const visible = useMemo(() => filterGraph(graph, filter), [graph, filter]);
  const positions = useMemo(() => layoutNodes(graph.nodes), [graph.nodes]);
  const related = useMemo(() => relatedNodeIds(visible, selected), [visible, selected]);
  const nodes: UniverseFlowNode[] = useMemo(() => visible.nodes.map(n => ({ id: n.id, type: 'career', position: positions[n.id], data: { entity: n, scenarioLabel: annotations[n.id], dimmed: !!selected && !related.has(n.id) && !highlighted.includes(n.id) }, selected: n.id === selected || highlighted.includes(n.id), draggable: false, connectable: false, focusable: true,
    ariaLabel: `${n.label}, ${n.type.replaceAll('_', ' ')}${n.score !== null ? `, ${n.score} out of 100 heuristic skill fit` : ''}. ${annotations[n.id] ?? ''} Select for details.`, ariaRole: 'button' })), [visible.nodes, positions, selected, related, highlighted, annotations]);
  const edges: Edge[] = useMemo(() => {
    // The API retains both evidence and gap edges; draw the gap once to avoid overlapping lines.
    const gapPairs = new Set(visible.edges.filter(e => e.type === 'missing_skill').map(e => `${e.source}:${e.target}`));
    return visible.edges.filter(e => !(e.type === 'requires_skill' && gapPairs.has(`${e.source}:${e.target}`))).map(e => {
      const highlighted = !!selected && related.has(e.source) && related.has(e.target);
      const color = e.type === 'missing_skill' ? 'var(--color-warning)' : e.type === 'contributes_to_target' || e.type === 'target_belongs_to_goal' ? 'var(--color-green)' : 'var(--color-action)';
      const vertical = e.type === 'contributes_to_target' || e.type === 'target_belongs_to_goal';
      return { id: e.id, source: e.source, target: e.target, sourceHandle: vertical ? 'source-bottom' : 'source-left', targetHandle: vertical ? 'target-top' : 'target-right', type: 'default', focusable: false, animated: false,
        style: { stroke: color, strokeWidth: highlighted ? 2.5 : 1.4, opacity: selected ? highlighted ? 0.85 : 0.12 : 0.3, strokeDasharray: e.type === 'missing_skill' ? '5 5' : undefined },
        ariaLabel: `${e.type.replaceAll('_', ' ')}${e.importance ? `, importance ${e.importance} of 5` : ''}` };
    });
  }, [visible.edges, related, selected]);
  useEffect(() => {
    if (!instance) return;
    const filterChanged = previousFilter.current !== filter;
    previousFilter.current = filter;
    // A frame lets React Flow measure newly filtered nodes before fitting.
    const frame = requestAnimationFrame(() => {
      const focused = selected ? visible.nodes.filter(n => related.has(n.id)).map(n => ({ id: n.id })) : undefined;
      void instance.fitView({ nodes: focused, padding: 0.18, duration: filterChanged ? 0 : duration, maxZoom: 1.15 });
    });
    return () => cancelAnimationFrame(frame);
  }, [instance, filter, selected, visible.nodes, related, duration]); // Selection/filter drive focus, not pointer hover.
  return <div className="universe-canvas" role="region" aria-label="Interactive career connections">
    <div className="universe-canvas-heading"><span className="eyebrow">YOUR LIVING CAREER UNIVERSE</span><span>Pan to explore · pinch or scroll to zoom</span></div>
    <ReactFlow<UniverseFlowNode, Edge> nodes={nodes} edges={edges} nodeTypes={nodeTypes} onInit={setInstance}
      onNodeClick={(_, node) => onSelect(node.id)}
      onNodesChange={changes => {
        for (const change of changes) if (change.type === 'select' && change.selected) { onSelect(change.id); return; }
        for (const change of changes) if (change.type === 'select' && !change.selected && change.id === selected) onSelect(null);
      }}
      onPaneClick={() => onSelect(null)} nodesDraggable={false} nodesConnectable={false} edgesReconnectable={false}
      elementsSelectable deleteKeyCode={null} minZoom={0.12} maxZoom={1.8} fitView fitViewOptions={{ padding: 0.18, maxZoom: 1.15 }}
      colorMode="light" preventScrolling={false} panOnDrag zoomOnPinch selectionOnDrag={false} ariaLabelConfig={{ 'controls.zoomIn.ariaLabel': 'Zoom in career graph', 'controls.zoomOut.ariaLabel': 'Zoom out career graph', 'controls.fitView.ariaLabel': 'Fit career graph' }}>
      <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="#cddcd3"/>
      <Controls showInteractive={false} fitViewOptions={{ duration, padding: 0.18 }}/>
    </ReactFlow>
    <div className="universe-floating-controls"><Button className="button-secondary" onClick={() => void instance?.fitView({ padding: 0.18, duration })}><Maximize2 size={14}/>Fit view</Button><Button className="button-secondary" disabled={!selected} onClick={() => void instance?.fitView({ nodes: nodes.filter(n => related.has(n.id)), padding: 0.18, duration })}><Focus size={14}/>Focus</Button><Button className="button-secondary" onClick={() => { onSelect(null); void instance?.fitView({ padding: 0.18, duration }); }}><RotateCcw size={14}/>Reset</Button></div>
  </div>;
}
