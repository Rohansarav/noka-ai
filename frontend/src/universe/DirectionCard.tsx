import { ArrowUpRight, Check, Code2, Compass, Target } from 'lucide-react';
import type { FutureMatch } from '../future-api';

export default function DirectionCard({match,selected,disabled,onSelect}:{match:FutureMatch;selected:boolean;disabled:boolean;onSelect:()=>void}) {
  const assessed=match.readiness_status!=='not_assessed';
  const Icon=match.is_target?Target:Compass;
  return <button className={`direction-card ${match.is_target?'direction-target':'direction-discovery'}`} type="button" disabled={disabled} aria-pressed={selected} onClick={onSelect}>
    <span className="direction-card-top"><span className="direction-card-icon"><Icon size={18} aria-hidden="true"/></span><span className="direction-card-kind">{match.is_target?'YOUR TARGET':'POSSIBLE DIRECTION'}</span><span className="direction-card-arrow">{selected?<Check size={16} aria-hidden="true"/>:<ArrowUpRight size={17} aria-hidden="true"/>}</span></span>
    <strong className="direction-card-title">{match.title}</strong>
    <span className="direction-card-measure"><span className="direction-card-score">{assessed?match.score:'—'}</span><span>{assessed?<>/100<br/>documented coverage</>:'Broad readiness not assessed'}</span></span>
    {assessed&&<span className="direction-meter" aria-hidden="true"><span style={{width:Math.min(100,Math.max(0,match.score))+'%'}}/></span>}
    {match.assessment&&<span className="direction-evidence-count">{match.assessment.recorded_count}/{match.assessment.required_count} requirements recorded · {match.assessment.unrecorded_count} unassessed</span>}
    <span className="direction-card-footer">{match.is_target?<span>Your confirmed target · interest adds no points</span>:<><span><Code2 size={13} aria-hidden="true"/>{match.technical?.matched_count??0} software matches</span><span>World emphasis +{match.scenario_emphasis}</span></>}</span>
    {!match.is_target&&<span className="direction-context">Context relevance +{match.context_emphasis??0} · select to explore</span>}
  </button>;
}
