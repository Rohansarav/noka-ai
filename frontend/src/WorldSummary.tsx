import { ArrowUpRight, Check, Layers3, Sparkles, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Future } from './future-api';

/** Present the saved scenario as context, a direction and actionable focus. */
export default function WorldSummary({future,saving}:{future?:Future;saving:boolean}) {
  if(!future)return null;
  const direction=future.matches.find(m=>m.role_id===future.role_id);
  const focus=direction?.priority_skills??[];
  return <div className="world-outcome" aria-live="polite">
    <div className="world-context"><span className="surface-kicker"><Sparkles size={14} aria-hidden="true"/> YOUR PLANNING LENS</span><div className="world-context-title"><h2>{future.scenarios[future.scenario].name}</h2><span className="world-save-state"><Check size={12} aria-hidden="true"/>{saving?'Saving…':'Saved planning lens'}</span></div><p>{future.scenarios[future.scenario].assumption}</p></div>
    <div className="world-direction"><span className="surface-kicker"><Target size={14} aria-hidden="true"/> {direction?'YOUR DIRECTION':'START EXPLORING'}</span>{direction?<><h3>{direction.title}</h3><span className="world-milestones"><Layers3 size={14} aria-hidden="true"/>{future.pathway.length} connected portfolio milestones</span></>:<><h3>A world of possibilities.</h3><p>Choose a career in the graph to compare its learning priorities and build a pathway in each world.</p></>}</div>
    <div className="world-focus"><span className="surface-kicker">CAPABILITIES IN FOCUS</span><div className="focus-chip-list">{focus.map(skill=><span key={skill}>{skill}</span>)}</div>{!focus.length&&<p>{direction?'No additional emphasis is supported for this role.':'Your selected career will shape this focus.'}</p>}<Link to={direction?'/roadmap':'/'}>{direction?'Explore your pathway':'Explore career connections'}<ArrowUpRight size={14} aria-hidden="true"/></Link></div>
    <details className="world-explainer"><summary>What changes with this lens?</summary><p>The lens changes planning order and skill emphasis. Profile coverage, published requirements and reviewed SDG evidence stay fixed. These are explicit scenarios, not 2030 predictions.</p></details>
  </div>;
}
