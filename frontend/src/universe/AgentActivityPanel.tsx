import { useEffect, useRef, useState } from 'react';
import { Button } from '../components';
import { agentRequest, executionFailure, validEffects, type Execution, type Effects } from './agent-api';
import type { CareerGraphData, CareerNode } from './universe-types';
import { Link } from 'react-router-dom';

const terminal = (status: string) => ['completed','failed','cancelled'].includes(status);

export default function AgentActivityPanel({graph, role, onEffects, executionId, onRecorded, onScenarioRequest, selectedNode}: {selectedNode?: CareerNode | null; graph: CareerGraphData; role: CareerNode | null; onEffects: (effects: Effects) => void; executionId?: string; onRecorded?: () => void; onScenarioRequest?: (scenario:'acceleration'|'governed'|'collaboration')=>Promise<unknown>}) {
  const [question, setQuestion] = useState('Which skills should I focus on for this role?');
  const [run, setRun] = useState<Execution | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [contextLabel, setContextLabel] = useState('');
  const [actionMessage,setActionMessage]=useState('');
  const callback = useRef(onEffects);
  callback.current = onEffects;
  const applied = useRef<string | null>(null);
  useEffect(() => {
    if (!executionId) return;
    let cancelled=false;
    setError(''); setContextLabel('Saved conversation · recorded profile context');
    void agentRequest('/'+executionId).then(value=>{if(!cancelled)setRun(value);}).catch(()=>{if(!cancelled)setError('This saved conversation is unavailable.');});
    return ()=>{cancelled=true;};
  },[executionId]);
  useEffect(() => {
    if (!run?.result || run.status !== 'completed' || applied.current === run.id) return;
    const effects = validEffects(run.result, graph);
    if (effects) { applied.current = run.id; callback.current(effects); }
  }, [run, graph]);
  useEffect(() => {
    if (!run || terminal(run.status)) return;
    let stopped = false;
    let fetching = false;
    let polling: ReturnType<typeof setTimeout> | undefined;
    const refresh = async () => {
      if (fetching || stopped) return;
      fetching = true;
      clearTimeout(polling);
      try { const value = await agentRequest('/'+run.id); if (!stopped) {setError(''); setRun(value); if (!terminal(value.status)) polling = setTimeout(refresh, 1500);} }
      catch {if (!stopped) { setError('Activity connection interrupted. Retrying saved execution status.'); polling = setTimeout(refresh, 3000); }}
      finally {fetching = false;}
    };
    // SSE carries persisted activity. GET remains the authoritative result/poll fallback.
    const source = typeof EventSource !== 'undefined' ? new EventSource('/api/agent-executions/'+run.id+'/events') : null;
    source?.addEventListener('activity', () => { void refresh(); });
    source?.addEventListener('done', () => {source.close(); void refresh();});
    source?.addEventListener('error', () => {source.close();});
    polling = setTimeout(refresh, 1500);
    return () => { stopped = true; source?.close(); clearTimeout(polling); };
  }, [run?.id, run?.status]);
  async function start() {
    if (!role) return;
    const command=question.trim().match(/^(?:please\s+)?(?:switch|change)(?:\s+(?:world|scenario))?\s+to\s+(AI Acceleration|Governed AI|Human[-– ]AI Collaboration)[.!]?$/i);
    if(command && onScenarioRequest){
      setBusy(true);setError('');setRun(null);
      const name=command[1].toLowerCase();
      const scenario=name.startsWith('ai ')?'acceleration':name.startsWith('governed')?'governed':'collaboration';
      try{await onScenarioRequest(scenario);setActionMessage('Your world is now '+command[1]+'.');}catch{setError('Your world could not be saved. Please retry.');}finally{setBusy(false);}
      return;
    }
    setActionMessage('');
    setBusy(true); setError(''); setExpanded(false); setContextLabel(role.label);
    try {setRun(await agentRequest('', {agent:'matchmaker', question, role_id:role.entity_id, ...(selectedNode && selectedNode.type!=='profile' ? {node_id:selectedNode.id} : {})})); onRecorded?.();}
    catch (e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  async function cancel() { if (!run) return; try {setRun(await agentRequest('/'+run.id+'/cancel', {}));} catch {setError('Cancellation could not be confirmed. Please retry.');} }
  return <section id="noka-exploration" className="agent-activity" aria-label="Explore with Noka"><div className="section-heading"><div><p className="eyebrow">GUIDE · YOUR CAREER COMPANION</p><h2>Explore with Noka</h2></div></div>
    <p>{role ? `Explore ${role.label} using your confirmed skills and existing evidence.` : 'Select a career direction to ask Guide about its connections.'}</p>
    <label htmlFor="exploration-question">What would you like to understand?</label><textarea id="exploration-question" value={question} maxLength={1000} onChange={e => setQuestion(e.target.value)} disabled={busy || !!run && !terminal(run.status)}/>
    <p className="caption">Your question, confirmed skills and saved learning context go to OpenAI. The last 30 questions are saved privately with this profile. Avoid personal identifiers. No profile changes or web searches.</p>
    <Button onClick={() => void start()} disabled={!role || question.trim().length < 3 || busy || !!run && !terminal(run.status)}>{busy ? 'Submitting exploration…' : 'Explore selected role'}</Button>
    {run && <p className="caption">Current exploration: {contextLabel}</p>}
    <div role="status" aria-live="polite">{run ? `Guide: ${run.status.replaceAll('_',' ')}${run.events.at(-1) ? '. '+run.events.at(-1)!.message : ''}` : actionMessage}</div>
    {run && !terminal(run.status) && <Button className="button-secondary" onClick={() => void cancel()}>Cancel exploration</Button>}
    {error && <p role="alert">{error}</p>}
    {run?.status === 'failed' && <><p role="alert">{executionFailure(run.error_code)} ({run.error_code}). Your skill matches and evidence remain available.</p>{run.events.at(-1)?.payload.stage && <details><summary>Failure details</summary><p>Step: {run.events.at(-1)!.payload.stage}{run.events.at(-1)!.payload.http_status ? ` · OpenAI HTTP ${run.events.at(-1)!.payload.http_status}` : ''}{run.events.at(-1)!.payload.provider_code ? ` · ${run.events.at(-1)!.payload.provider_code}` : ''}{run.events.at(-1)!.payload.reason ? ` · ${run.events.at(-1)!.payload.reason}` : ''}</p></details>}</>}
    {run?.status === 'cancelled' && <p>Exploration cancelled. Your profile is unchanged.</p>}
    {run && <details open={expanded} onToggle={e => setExpanded(e.currentTarget.open)}><summary>Execution activity · {run.events.length} recorded events</summary><ol>{run.events.map(e => <li key={e.sequence}><strong>{e.agent}</strong> · {e.message} {e.payload.tool && <code>{e.payload.tool}</code>}{e.payload.related_entity && graph.nodes.some(n=>n.id===e.payload.related_entity) && <button className="text-link" onClick={()=>onEffects({focus_role:e.payload.related_entity!,highlight_skills:[],open_evidence:null})}>View role</button>}</li>)}</ol></details>}
    {run?.result && <div className="agent-result"><h3>Exploration of {contextLabel}</h3><p>{run.result.notice}</p>{run.result.sections.map((section, i) => <EvidenceSection key={i} kind={section.kind} data={section.data}/>)}{(() => {const effects = validEffects(run.result, graph); const source = effects?.open_evidence ? graph.sources.find(s=>s.id===effects.open_evidence) : null; return source ? <a className="text-link" href={source.canonical_url} target="_blank" rel="noreferrer">Open cited evidence</a> : null;})()}</div>}
  </section>;
}

function EvidenceSection({kind, data}: {kind: string; data: unknown}) {
  // Only server-assembled sections have display handlers; no raw JSON commands or HTML.
  const rows = Array.isArray(data) ? data as Record<string, unknown>[] : [];
  const record = data && typeof data === 'object' ? data as Record<string, unknown> : {};
  if(kind==='scenario') return <div><h4>Your scenario comparison</h4><p>{String(record.method ?? 'No saved world context yet.')}</p><ul>{Object.entries((record.comparisons ?? {}) as Record<string,{planning_index:number;priority_skills:string[]}|null>).map(([world,match])=><li key={world}>{world}: planning index {match?.planning_index}; priorities {match?.priority_skills.join(', ')}</li>)}</ul></div>;
  if(kind==='pathway') return <div><h4>Your saved pathway</h4><p>{String(record.weekly_hours ?? 6)} hours each week. {String(record.notice)}</p><ul>{((record.tasks??[]) as {skill_id:string;name:string;end_week:number;status:string}[]).slice(0,5).map(t=><li key={t.skill_id}>{t.name} · week {t.end_week} · {t.status}</li>)}</ul><Link to="/roadmap">Review and save pathway changes →</Link></div>;
  if(kind==='forecast') return <div><h4>Evaluated US sector context</h4><p>{String(record.sector ?? 'No supported sector crosswalk')}. {String(record.limitation)}</p><ul>{((record.forecasts??[]) as {horizon_weeks:number;forecast:number;model:string}[]).map(f=><li key={f.horizon_weeks}>{f.horizon_weeks} weeks · index {f.forecast.toFixed(1)} · {f.model}</li>)}</ul><Link to="/model-lab">Inspect evaluation →</Link></div>;
  if(kind==='signals') return <div><h4>Related source discoveries</h4>{rows.length?rows.map((r,i)=><p key={i}>{String(r.title)} · {String(r.market)} · {String(r.review_status)}</p>):<p>No exact mapped findings. No evidence has been inferred.</p>}<Link to="/signals">Inspect sources in Intelligence Radar →</Link></div>;
  return <div><h4>{kind.charAt(0).toUpperCase()+kind.slice(1)}</h4>{kind === 'fit' ? <p>{String(record.title)} · {String(record.score)}/100 heuristic skill fit. {String(record.explanation)}</p> : kind === 'evidence' ? <p>{String(record.evidence_status)}. {String(record.limitation)}</p> : <ul>{rows.slice(0,12).map((r,i)=><li key={i}>{String(r.name ?? r.target_id)}{kind==='requirements' ? ` · importance ${r.importance}/5` : kind==='gaps' ? ` · ${r.critical ? 'critical requirement; ' : ''}proficiency gap ${r.gap}` : ` · ${r.rationale}`}</li>)}</ul>}{rows.length===0 && ['gaps','requirements','sdgs'].includes(kind) && <p>No records available for this section. No connections have been inferred.</p>}</div>;
}
