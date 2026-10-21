import { ArrowRight, Layers3, Route } from 'lucide-react';
import type { Future } from './future-api';

export default function PathwayIntro({future,hours}:{future:Future;hours:number}) {
  const weeks=Math.ceil(future.pathway.filter(t=>t.status!=='completed').reduce((sum,t)=>sum+t.effort_hours,0)/hours);
  return <section className="pathway-project">
    <div className="pathway-intro-heading"><span className="pathway-project-icon"><Route size={23} aria-hidden="true"/></span><div><span className="eyebrow">ONE PROJECT · CONNECTED EVIDENCE</span><h2>{future.pathway_scope?.project_title??'Your career portfolio'}</h2></div></div>
    <p>One practical career case study. Each milestone builds on your previous work, bringing your skills together in a portfolio you can review and improve.</p>
    <div className="pathway-facts"><div><span>FOCUS MILESTONES</span><strong>{future.pathway.length}<Layers3 size={18} aria-hidden="true"/></strong><small>{future.pathway_scope?`From ${future.pathway_scope.total_development_areas} development or validation areas`:'Connected work samples'}</small></div><div><span>REMAINING TIMEBOXES</span><strong>{weeks}<small>{weeks===1?'week':'weeks'}</small></strong><small>At your chosen weekly pace</small></div><div><span>YOUR STUDY RHYTHM</span><strong>{hours}<small>h / week</small></strong><small>{hours===future.weekly_hours?'Saved commitment':'Preview · save your commitment'}</small></div></div>
    <div className="pathway-project-note"><ArrowRight size={15} aria-hidden="true"/><span>{future.pathway.length?'Start small, collect evidence, then refine your next step. This cycle does not cover the entire occupation.':'No priority gaps at your recorded levels. Validate your strengths in a role-relevant work sample.'} Timeboxes guide practice; they are not a qualification timeline.</span></div>
  </section>;
}
