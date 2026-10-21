import { useMemo, useRef, useState } from 'react';
import { Check, Plus, Search, X } from 'lucide-react';
import type { Skill } from './evidence-api';
import type { Candidate, Level, ProfileSkill } from './profile-api';
import aliases from '../../data/skill_aliases.json';

const levels: {id:Level; label:string; description:string}[] = [
  {id:'learning',label:'Learning',description:'I am building the basics'},
  {id:'working',label:'Working',description:'I can use this in a task'},
  {id:'strong',label:'Strong',description:'I can apply this independently'},
];

/** Canonical IDs are the only values that enter confirmed skills, for either input method. */
export default function SkillReview({skills,candidates,selected,onChange,disabled=false}:{skills:Skill[];candidates:Candidate[];selected:ProfileSkill[];onChange:(skills:ProfileSkill[])=>void;disabled?:boolean}) {
  const [query,setQuery]=useState(''),[showAll,setShowAll]=useState(false),[feedback,setFeedback]=useState('');
  const search=useRef<HTMLInputElement>(null);
  const chosen=new Set(selected.map(s=>s.skill_id));
  const {suggestions,unmapped}=useMemo(()=>{
    const index=new Map<string,{skill:Skill;mentions:Set<string>;excerpt:string;years:number|null;ambiguous:boolean}>();
    const unmatched=new Set<string>();
    for(const c of candidates){
      const options=[...new Set(c.options)].map(id=>skills.find(s=>s.id===id)).filter((s):s is Skill=>!!s);
      if(!options.length)unmatched.add(c.mention);
      for(const skill of options){const existing=index.get(skill.id);if(existing){for(const name of c.mentions?.length?c.mentions:[c.mention])existing.mentions.add(name);if(existing.years!==c.years)existing.years=null;existing.ambiguous=existing.ambiguous&&options.length>1;}else index.set(skill.id,{skill,mentions:new Set(c.mentions?.length?c.mentions:[c.mention]),excerpt:c.evidence_excerpt,years:c.years,ambiguous:options.length>1});}
    }
    return {suggestions:[...index.values()],unmapped:[...unmatched]};
  },[candidates,skills]);
  const searchText=(s:Skill)=>(s.canonical_name+' '+s.aliases.join(' ')+' '+Object.entries(aliases).filter(([,names])=>names.includes(s.canonical_name)).map(([name])=>name).join(' ')).toLowerCase();
  const available=skills.filter(s=>!chosen.has(s.id)&&!suggestions.some(item=>item.skill.id===s.id)&&searchText(s).includes(query.trim().toLowerCase()));
  function add(skill:Skill,years:number|null=null){if(disabled||chosen.has(skill.id)||selected.length>=60)return;onChange([...selected,{skill_id:skill.id,level:'working',years}]);setFeedback(`${skill.canonical_name} added. Review your level below.`);}
  const pending=suggestions.filter(s=>!chosen.has(s.skill.id));
  return <div className="skill-review">
    {pending.length>0&&<section className="skill-suggestions" aria-label="Suggested skills"><div className="skill-section-heading"><div><span className="eyebrow">FROM YOUR EXPERIENCE</span><h3>Does this sound like you?</h3></div><span>{pending.length} to review</span></div><p>These are suggestions. Choose only the skills you recognise.</p><div className="suggested-skill-grid">{pending.map(item=><article key={item.skill.id} className="suggested-skill"><div><strong>{item.skill.canonical_name}</strong><small>{item.ambiguous?'Possible interpretation':'From'}: {[...item.mentions].join(', ')}</small></div><button type="button" className="skill-add" aria-label={`Add ${item.skill.canonical_name}`} disabled={disabled||selected.length>=60} onClick={()=>add(item.skill,item.years)}><Plus size={16}/>Add</button>{item.excerpt&&<details><summary>See the connection</summary><blockquote>{item.excerpt}</blockquote><p>A broad occupational skill suggested from your experience. Confirm the connection and your level yourself.</p></details>}</article>)}</div></section>}
    {unmapped.length>0&&<aside className="unmapped-skills"><strong>A few terms need your help</strong><p>{unmapped.join(', ')}. These terms have no supported match in our current occupational catalogue. Search for the broader skill you use, or leave them out.</p><button type="button" className="text-link" onClick={()=>search.current?.focus()}>Find a related skill</button></aside>}
    <section className="skill-library" aria-label="Find skills"><label htmlFor="skill-search">Add your strengths</label><div className="skill-search"><Search size={18}/><input id="skill-search" ref={search} type="search" value={query} disabled={disabled} onChange={e=>setQuery(e.target.value)} placeholder="Search skills or tools, e.g. Python, writing…" aria-describedby="skill-search-help"/></div><p id="skill-search-help">Search the skill catalogue. Your chosen skills appear below.</p><div className="skill-picker" aria-label="Skill search results">{(query.trim()||showAll?available:available.slice(0,10)).map(skill=><button type="button" key={skill.id} disabled={disabled||selected.length>=60} aria-label={`Choose ${skill.canonical_name}`} onClick={()=>add(skill)}><Plus size={13}/>{skill.canonical_name}</button>)}</div>{!available.length&&<p className="skill-empty">{query.trim()?`No unselected catalogue skills match “${query}”. Try a broader skill such as Programming or Coordination.`:'You have selected every available catalogue skill.'}</p>}{!query.trim()&&available.length>10&&<button type="button" className="text-link" onClick={()=>setShowAll(!showAll)}>{showAll?'Show fewer skills':`Browse all ${available.length} skills`}</button>}</section>
    <section className="confirmed-skill-section" aria-label="Your confirmed skills"><div className="skill-section-heading"><div><span className="eyebrow">REVIEWED BY YOU</span><h3>Your skills, your level.</h3></div><span>{selected.length} selected</span></div>{!selected.length?<p className="skill-empty">Add a suggestion or choose a skill above. Nothing is confirmed automatically.</p>:<div className="confirmed-skill-list">{selected.map(s=>{const skill=skills.find(k=>k.id===s.skill_id);const name=skill?.canonical_name??'Saved skill';return <article className="confirmed-skill" key={s.skill_id}><div className="confirmed-skill-title"><span><Check size={15}/>{name}</span><button type="button" className="icon-button" disabled={disabled} aria-label={`Remove ${name}`} onClick={()=>{onChange(selected.filter(k=>k.skill_id!==s.skill_id));setFeedback(`${name} removed.`);}}><X size={16}/></button></div><div className="skill-level-options" role="group" aria-label={`${name} proficiency`}>{levels.map(level=><button type="button" key={level.id} title={level.description} disabled={disabled} aria-pressed={s.level===level.id} onClick={()=>onChange(selected.map(k=>k.skill_id===s.skill_id?{...k,level:level.id}:k))}>{level.label}</button>)}</div><label className="skill-years">Years using this skill <span>(optional)</span><input type="number" aria-label={`${name} years`} min={0} max={60} step={0.5} disabled={disabled} value={s.years??''} onChange={e=>{const years=e.target.value===''?null:Number(e.target.value);if(years===null||Number.isFinite(years)&&years>=0&&years<=60)onChange(selected.map(k=>k.skill_id===s.skill_id?{...k,years}:k));}}/></label></article>;})}</div>}<p className="skill-rating-help">Learning: building the basics. Working: can use it in a task. Strong: can apply it independently. These are self-ratings.</p></section>
    {selected.length>=60&&<p role="alert">You can review up to 60 skills. Remove one before adding another.</p>}<p className="sr-only" role="status" aria-live="polite">{feedback}</p>
  </div>;
}
