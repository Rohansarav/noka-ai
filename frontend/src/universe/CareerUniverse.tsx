import { Suspense, lazy, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Compass, List, RotateCcw } from 'lucide-react';
import { Badge, Button, ErrorState, GlassCard, PageHeader } from '../components';
import UniverseLoading from './UniverseLoading';
import AgentActivityPanel from './AgentActivityPanel';
import type { Effects } from './agent-api';
import CareerDetailPanel from './CareerDetailPanel';
import CareerGraphLegend from './CareerGraphLegend';
import { getCareerGraph } from './universe-api';
import { FILTERS, filterGraph } from './universe-layout';
import type { UniverseFilter } from './universe-types';
import './universe.css';

const CareerGraph = lazy(() => import('./CareerGraph'));

export default function CareerUniverse() {
  const query = useQuery({ queryKey: ['career-graph'], queryFn: getCareerGraph, retry: false });
  const [highlighted, setHighlighted] = useState<string[]>([]);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  function selectNode(id: string | null) { setSelected(id); setHighlighted([]); setEvidenceId(null); }
  function applyEffects(effects: Effects) { setFilter('all'); setSelected(effects.focus_role); setHighlighted(effects.highlight_skills); setEvidenceId(effects.open_evidence); }
  const [filter, setFilter] = useState<UniverseFilter>('all');
  const [selected, setSelected] = useState<string | null>(null);
  const graph = query.data;
  const visible = graph ? filterGraph(graph, filter) : null;
  const node = graph?.nodes.find(n => n.id === selected) ?? null;
  const roles = graph?.nodes.filter(n => n.type === 'role').sort((a, b) => (b.score ?? 0) - (a.score ?? 0) || a.label.localeCompare(b.label)) ?? [];
  function changeFilter(value: UniverseFilter) { setFilter(value); selectNode(null); }
  return <div className="career-universe-page"><PageHeader eyebrow="YOUR STRENGTHS. CONNECTED." title="Explore your possible futures." description="A living map of what you bring, where it could lead, and the skills you can grow."/>
    {query.isPending ? <UniverseLoading/> : query.isError ? <GlassCard className="universe-loading"><ErrorState message="Your Universe is unavailable. No substitute connections have been generated."/><Button className="button-secondary" onClick={() => void query.refetch()}>Retry Universe</Button></GlassCard> : graph && graph.status === 'no_profile' ? <GlassCard className="universe-onboarding"><span className="feature-icon mint"><Compass size={30}/></span><Badge tone="blue">Your Universe starts with you</Badge><h2>A few strengths. A world to explore.</h2><p>No profile yet. Bring your experience or choose your skills manually, then discover your real connections.</p><Button asChild><Link to="/profile/intake">Build my skill profile <ArrowRight size={17}/></Link></Button><p className="caption">Private session · Original resumes are not retained</p></GlassCard> : graph && visible && <>
      <div className="universe-intro"><div><Badge tone="mint">{graph.nodes.find(n => n.type === 'profile')?.is_demo ? 'Demo profile' : 'Your reviewed profile'}</Badge><span>Skill fit, not a future-demand forecast</span></div><Link className="text-link" to="/profile/intake">Edit my skills <ArrowRight size={15}/></Link></div>
      {graph.status === 'insufficient_profile_information' && <div className="data-notice" role="status">Your profile and skills are ready to explore. Confirm at least three skills to unlock ranked role connections. <Link to="/profile/intake">Review my skills</Link></div>}
      {roles.length > 0 && <div className="universe-role-picker" role="group" aria-label="Choose a career direction">{roles.map((role, i) => <button key={role.id} aria-pressed={selected === role.id} onClick={() => selectNode(role.id)}><span>0{i + 1} <strong>{role.label}</strong></span><span>{role.score}<small> / 100 skill fit</small></span></button>)}</div>}
      <div className="universe-toolbar"><div className="universe-filters" role="group" aria-label="Filter career connections">{FILTERS.map(option => <button key={option.id} aria-pressed={filter === option.id} onClick={() => changeFilter(option.id)}>{option.label}</button>)}</div><a className="text-link" href="#universe-list"><List size={15}/>List view</a></div>
      <div className="universe-workspace"><div className="universe-graph-column"><Suspense fallback={<UniverseLoading/>}><CareerGraph graph={graph} filter={filter} selected={selected} highlighted={highlighted} onSelect={selectNode}/></Suspense><CareerGraphLegend/><div className="universe-graph-caption"><span aria-live="polite">{selected ? `Exploring ${node?.label ?? 'a connection'}. Details follow the graph.` : 'Select a career to explore its connections.'}</span>{selected && <button className="text-link" onClick={() => selectNode(null)}><RotateCcw size={13}/>Reset selection</button>}</div>{filter === 'sdgs' && !visible.nodes.some(n => n.type === 'sdg_target') && <p className="universe-filter-notice">No reviewed SDG connections exist for the displayed skills and roles. No links have been inferred.</p>}{filter === 'gaps' && !visible.edges.some(e => e.type === 'missing_skill') && <p className="universe-filter-notice">No priority skill gaps are available in this view.</p>}</div><CareerDetailPanel graph={graph} node={node}/></div>
      <AgentActivityPanel graph={graph} role={node?.type === 'role' ? node : null} onEffects={applyEffects}/>
      {evidenceId && graph.sources.filter(source => source.id === evidenceId).map(source => <aside key={source.id} className="data-notice" aria-label="Evidence selected by Matchmaker"><strong>{source.title}</strong><p>{source.publisher} · {source.version}</p><a className="text-link" href={source.canonical_url} target="_blank" rel="noreferrer">Read original evidence</a></aside>)}
      <section id="universe-list" className="universe-accessible-list" aria-labelledby="universe-list-title"><div className="section-heading"><div><p className="eyebrow">THE SAME CONNECTIONS, ANOTHER WAY</p><h2 id="universe-list-title">Explore without the canvas.</h2></div><Badge>{visible.nodes.length} nodes · {visible.edges.length} evidence edges</Badge></div><p>Choose any connection below. Its requirements, role-specific gaps and source details appear in the detail panel above.</p><div className="universe-list-grid">{visible.nodes.map(item => <button key={item.id} aria-pressed={selected === item.id} onClick={() => selectNode(item.id)}><span>{item.type.replaceAll('_', ' ')}</span><strong>{item.label}</strong><small>{item.type === 'role' ? `${item.score}/100 heuristic fit` : item.level ? `${item.level} · self-reported` : item.type === 'required_skill' ? 'A displayed role’s priority requirement' : 'Select to review connections'}</small></button>)}</div>{node && <a className="text-link" href="#universe-details">Read details for {node.label} <ArrowRight size={15}/></a>}</section>
      <details className="universe-limitations"><summary>About this map & its limits</summary><p>{graph.methodology}</p><ul>{graph.limitations.map(text => <li key={text}>{text}</li>)}</ul><p>Generated {new Date(graph.generated_at).toLocaleString()} from your saved profile revision. Filters and selection never change your profile.</p></details>
    </>}
  </div>;
}
