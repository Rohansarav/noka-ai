import { useEffect, useRef, useState } from 'react';
import { Button } from '../components';
import { agentRequest, executionFailure, validEffects, type Execution, type Effects } from './agent-api';
import type { CareerGraphData, CareerNode } from './universe-types';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Compass, Send, Sparkles } from 'lucide-react';

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
  const waiting=busy || !!run && !terminal(run.status);
  return <section id="noka-exploration" className="agent-activity" aria-label="Ask Noka" aria-busy={waiting}><div className="companion-intro"><span className={`noka-compass ${waiting?'is-thinking':''}`} aria-hidden="true"><Compass size={28}/></span><span className="eyebrow">A LITTLE CLARITY, TOGETHER</span><h2>{run?.result?'Here’s your next perspective.':'Where shall we go next?'}</h2><p>{role ? <>Let’s explore <strong>{role.label}</strong> through your strengths.</> : 'Choose a career in your Universe to begin.'}</p></div>
    {run?.result && <div className="agent-result"><h3 className="sr-only">Exploration of {contextLabel}</h3>{run.result.sections.map((section, i) => <EvidenceSection key={i} kind={section.kind} data={section.data}/>)}{(() => {const effects = validEffects(run.result, graph); const source = effects?.open_evidence ? graph.sources.find(s=>s.id===effects.open_evidence) : null; return source ? <a className="text-link" href={source.canonical_url} target="_blank" rel="noreferrer">Open cited evidence <ArrowUpRight size={13}/></a> : null;})()}<details><summary>About this answer</summary><p>{run.result.notice}</p><p>{contextLabel}</p></details><div className="companion-followups"><Link to="/roadmap">Shape my next step <ArrowUpRight size={12}/></Link><button onClick={()=>setQuestion('Which skills should I focus on for this role?')}>What should I learn next? <ArrowUpRight size={12}/></button></div></div>}
    {!run?.result&&<div className="companion-prompts" aria-label="Suggested questions">{['Which skills should I focus on for this role?','How does this role change across the three worlds?','What can I work on this week?'].map((prompt,i)=><button key={prompt} disabled={waiting||!role} onClick={()=>setQuestion(prompt)}><span>{['Find my next skill','Compare the three worlds','Plan my next step'][i]}</span><ArrowUpRight size={14}/></button>)}</div>}
    <div className="companion-composer"><label className="sr-only" htmlFor="exploration-question">What would you like to understand?</label><textarea id="exploration-question" placeholder="Ask about your next move…" value={question} maxLength={1000} onChange={e => setQuestion(e.target.value)} disabled={waiting}/><Button aria-label="Send question to Noka" onClick={() => void start()} disabled={!role || question.trim().length < 3 || waiting}>{waiting?<Compass size={17} className="thinking-icon"/>:<Send size={17}/>}<span>{waiting?'Working on it…':'Ask Noka'}</span></Button></div>
    <div className="companion-status" role="status" aria-live="polite">{waiting&&<span className="thinking-pulse" aria-hidden="true"/>}{run ? run.status==='queued'?'Noka is readying your question…':run.status==='running'?'Reading your saved context and evidence…':run.status==='completed'?'Grounded in your saved context.':run.status==='cancelled'?'Exploration cancelled. Your profile is unchanged.':'This exploration could not finish.' : busy?'Preparing your request…':actionMessage}</div>
    {run && !terminal(run.status) && <button className="text-link" onClick={() => void cancel()}>Cancel exploration</button>}
    {error && <p role="alert">{error}</p>}
    {run?.status === 'failed' && <><p role="alert">{executionFailure(run.error_code)} Your skill matches and evidence remain available.</p><details><summary>Failure details</summary><p>{run.error_code}</p>{run.events.at(-1)?.payload.stage&&<p>Step: {run.events.at(-1)!.payload.stage}{run.events.at(-1)!.payload.http_status ? ` · OpenAI HTTP ${run.events.at(-1)!.payload.http_status}` : ''}{run.events.at(-1)!.payload.provider_code ? ` · ${run.events.at(-1)!.payload.provider_code}` : ''}{run.events.at(-1)!.payload.reason ? ` · ${run.events.at(-1)!.payload.reason}` : ''}</p>}</details></>}
    {run && <details className="activity-drawer" open={expanded} onToggle={e => setExpanded(e.currentTarget.open)}><summary><Sparkles size={13}/>Activity · {run.events.length} recorded events</summary><p className="caption">Execution {run.id} · Guide: {run.status} · {run.tool_count} tools</p><ol>{run.events.map(e => <li key={e.sequence}><strong>{e.message}</strong>{e.payload.tool && <code>{e.payload.tool}</code>}{e.payload.related_entity && graph.nodes.some(n=>n.id===e.payload.related_entity) && <button className="text-link" onClick={()=>onEffects({focus_role:e.payload.related_entity!,highlight_skills:[],open_evidence:null})}>View role</button>}</li>)}</ol></details>}
    <details className="companion-privacy"><summary>Private by design</summary><p>Your question, confirmed skills and saved learning context go to OpenAI. The last 30 questions are saved privately with this profile. Avoid personal identifiers. No profile changes or web searches.</p></details>
  </section>;
}

function EvidenceSection({kind, data}: {kind: string; data: unknown}) {
  // Only server-assembled sections have display handlers; no raw JSON commands or HTML.
  const rows = Array.isArray(data) ? data as Record<string, unknown>[] : [];
  const record = data && typeof data === 'object' ? data as Record<string, unknown> : {};
  if(kind==='scenario') return <div><h4>Your role, three possibilities.</h4><div className="answer-worlds">{Object.entries((record.comparisons ?? {}) as Record<string,{planning_index:number;priority_skills:string[]}|null>).map(([world,match])=><div key={world}><strong>{{acceleration:'AI Acceleration',governed:'Governed AI',collaboration:'Human–AI Collaboration'}[world] ?? world}</strong><p>{match?.priority_skills.length ? `Build ${match.priority_skills.join(', ')}.` : 'No additional skill priorities in the recorded context.'}</p><details><summary>Planning context</summary><p>Planning index {match?.planning_index}. {String(record.method ?? 'No saved world context yet.')}</p></details></div>)}</div></div>;
  if(kind==='pathway') return <div><h4>Your saved pathway</h4><p>{String(record.weekly_hours ?? 6)} hours each week.</p><details><summary>Plan assumptions</summary><p>{String(record.notice)}</p></details><ul>{((record.tasks??[]) as {skill_id:string;name:string;end_week:number;status:string}[]).slice(0,5).map(t=><li key={t.skill_id}>{t.name} · week {t.end_week} · {t.status}</li>)}</ul><Link to="/roadmap">Review and save pathway changes →</Link></div>;
  if(kind==='forecast') return <div><h4>Evaluated US sector context</h4><p>{String(record.sector ?? 'No supported sector crosswalk')}. {String(record.limitation)}</p><ul>{((record.forecasts??[]) as {horizon_weeks:number;forecast:number;model:string}[]).map(f=><li key={f.horizon_weeks}>{f.horizon_weeks} weeks · index {f.forecast.toFixed(1)} · {f.model}</li>)}</ul><Link to="/model-lab">Inspect evaluation →</Link></div>;
  if(kind==='signals') return <div><h4>Related source discoveries</h4>{rows.length?rows.map((r,i)=><p key={i}>{String(r.title)} · {String(r.market)} · {String(r.review_status)}</p>):<p>No exact mapped findings. No evidence has been inferred.</p>}<Link to="/signals">Inspect sources in Intelligence Radar →</Link></div>;
  return <div><h4>{kind.charAt(0).toUpperCase()+kind.slice(1)}</h4>{kind === 'fit' ? <p>{String(record.title)} · {String(record.score)}/100 heuristic skill fit. {String(record.explanation)}</p> : kind === 'evidence' ? <p>{String(record.evidence_status)}. {String(record.limitation)}</p> : <ul>{rows.slice(0,5).map((r,i)=><li key={i}>{String(r.name ?? r.target_id)}{kind==='requirements' ? ` · role importance ${r.importance}/5` : kind==='gaps' ? ` · ${r.critical ? 'key requirement · ' : ''}${Math.round(Number(r.gap)*100)}% skill gap` : ` · ${r.rationale}`}</li>)}</ul>}{rows.length>5&&<details><summary>{rows.length-5} more connections</summary><ul>{rows.slice(5).map((r,i)=><li key={i}>{String(r.name ?? r.target_id)} · {String(r.rationale ?? r.importance ?? r.gap ?? '')}</li>)}</ul></details>}{rows.length===0 && ['gaps','requirements','sdgs'].includes(kind) && <p>No records available for this section. No connections have been inferred.</p>}</div>;
}
