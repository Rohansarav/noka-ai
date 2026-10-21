import { useEffect, useRef, useState } from 'react';
import type { Future, Scenario } from '../future-api';

/** Compare actual server-computed scenario snapshots, including honest ties. */
export default function ScenarioInsight({future}:{future:Future}) {
  const last=useRef(future.scenario),[previous,setPrevious]=useState<Scenario|null>(null);
  useEffect(()=>{if(last.current!==future.scenario){setPrevious(last.current);last.current=future.scenario;}},[future.scenario]);
  const match=future.matches.find(m=>m.role_id===future.role_id)??future.matches[0];
  const before=previous?future.comparisons[previous].find(m=>m.role_id===match?.role_id):undefined;
  const priorities=match?.priority_skills??[];
  const added=priorities.filter(s=>!before?.priority_skills.includes(s));
  const removed=before?.priority_skills.filter(s=>!priorities.includes(s))??[];
  const rank=match?future.matches.findIndex(m=>m.role_id===match.role_id)+1:0;
  const oldRank=previous&&match?future.comparisons[previous].findIndex(m=>m.role_id===match.role_id)+1:rank;
  const changed=before&&(before.scenario_emphasis!==match?.scenario_emphasis||added.length>0||removed.length>0||rank!==oldRank);
  return <section className={`scenario-insight scenario-${future.scenario}`} aria-label="Scenario planning lens"><div><span className="eyebrow">WHAT IF · {future.scenarios[future.scenario].name}</span><h2>{priorities.length?`A closer look at ${priorities.slice(0,2).join(' & ')}.`:'Your existing foundation still matters.'}</h2><p>{future.scenarios[future.scenario].assumption}</p>{match&&<p><strong>{match.title}</strong> · planning position {rank} of {future.matches.length} · {match.readiness_status==='not_assessed'?'broad readiness not assessed':match.score+' skill fit'} · +{match.scenario_emphasis} scenario emphasis</p>}<div className="scenario-priorities">{priorities.map(s=><span key={s}>{s}</span>)}</div>{!priorities.length&&<p>No above-threshold requirements match this scenario’s named skills for this role. The evidence does not justify extra emphasis.</p>}</div><span className="scenario-lens-count">Highlighted skills follow<br/>this role’s O*NET requirements.</span>{previous&&<details className="scenario-change" open><summary>What changed? {future.scenarios[previous].name} → {future.scenarios[future.scenario].name}</summary><div role="status">{changed?<><p>{added.length?`New emphasis: ${added.join(', ')}.`:'No newly prioritised skills.'} {removed.length?`Leaving this lens: ${removed.join(', ')}.`:''}</p><p>{rank===oldRank?`Planning position stays ${rank}.`:`Planning position ${oldRank} → ${rank}.`} Scenario emphasis {before?.scenario_emphasis} → {match?.scenario_emphasis}. {match?.readiness_status==='not_assessed'?'Broad readiness remains unassessed.':'Skill fit stays '+match?.score+'.'}</p></>:<p>The computed priorities, emphasis and planning position for this role are unchanged. The evidence does not justify a change.</p>}</div></details>}</section>;
}
