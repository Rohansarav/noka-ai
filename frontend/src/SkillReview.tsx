import { useEffect, useMemo, useRef, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Check, Plus, Search, X } from 'lucide-react';
import type { Skill } from './evidence-api';
import type { Candidate, CustomSkill, Level, ProfileSkill } from './profile-api';
import aliases from '../../data/skill_aliases.json';

type Results={skills:Skill[];catalogue_total:number;matched_total:number;offset:number;limit:number;counts:{core:number;software:number};method:string};
const levels:Level[]=['learning','working','strong'];
const names:Record<Level,string>={learning:'Learning',working:'Working',strong:'Strong'};
async function loadSkills(path:string,signal?:AbortSignal):Promise<Results>{
  const response=await fetch(path,{signal});if(!response.ok)throw new Error('Catalogue unavailable');
  const value=await response.json() as Results;
  if(!Array.isArray(value.skills)||!Number.isFinite(value.catalogue_total))throw new Error('Catalogue unavailable');
  return value;
}

/** Specific software stays distinct from broad competencies; custom skills never create source evidence. */
export default function SkillReview({skills,candidates,selected,onChange,disabled=false,custom=[],onCustomChange=()=>{},roleIds=[]}:{skills:Skill[];candidates:Candidate[];selected:ProfileSkill[];onChange:(value:ProfileSkill[])=>void;disabled?:boolean;custom?:CustomSkill[];onCustomChange?:(value:CustomSkill[])=>void;roleIds?:string[]}) {
  const [query,setQuery]=useState(''),[search,setSearch]=useState(''),[category,setCategory]=useState('all'),[offset,setOffset]=useState(0),[feedback,setFeedback]=useState('');
  const input=useRef<HTMLInputElement>(null);
  useEffect(()=>{const timer=setTimeout(()=>{setSearch(query.trim());setOffset(0);},250);return()=>clearTimeout(timer);},[query]);
  const missing=[...new Set([...selected.map(s=>s.skill_id),...candidates.flatMap(c=>c.options)])].filter(id=>!skills.some(s=>s.id===id)).sort();
  const labels=useQuery({queryKey:['review-skill-labels',missing.join(',')],enabled:missing.length>0,queryFn:async({signal})=>{
    const batches=[];for(let i=0;i<missing.length;i+=40)batches.push(missing.slice(i,i+40));
    const results=await Promise.all(batches.map(ids=>loadSkills('/api/skill-catalogue?limit=50&ids='+encodeURIComponent(ids.join(',')),signal)));
    return results.flatMap(result=>result.skills);
  },retry:false});
  const catalogue=useQuery({queryKey:['skill-search',search,category,offset,roleIds.join(',')],queryFn:({signal})=>loadSkills('/api/skill-catalogue?'+new URLSearchParams({q:search,category,offset:String(offset),limit:'20',roles:roleIds.join(',')}),signal),retry:false,placeholderData:keepPreviousData});
  const known=useMemo(()=>new Map([...skills,...(labels.data??[]),...(catalogue.data?.skills??[])].map(s=>[s.id,s])),[skills,labels.data,catalogue.data]);
  const chosen=new Set(selected.map(s=>s.skill_id));
  const suggestions=useMemo(()=>{
    const grouped=new Map<string,{skill:Skill;mentions:Set<string>;years:number|null;excerpt:string;ambiguous:boolean}>(),unmapped=new Set<string>();
    for(const candidate of candidates){
      if(!candidate.options.length)unmapped.add(candidate.mention);
      for(const id of new Set(candidate.options)){
        const skill=known.get(id);if(!skill)continue;
        const existing=grouped.get(id);
        if(existing){for(const term of candidate.mentions?.length?candidate.mentions:[candidate.mention])existing.mentions.add(term);if(existing.years!==candidate.years)existing.years=null;}
        else grouped.set(id,{skill,mentions:new Set(candidate.mentions?.length?candidate.mentions:[candidate.mention]),years:candidate.years,excerpt:candidate.evidence_excerpt,ambiguous:candidate.options.length>1});
      }
    }
    return {pending:[...grouped.values()].filter(s=>!chosen.has(s.skill.id)),ids:new Set(grouped.keys()),unmapped:[...unmapped]};
  },[candidates,known,selected]);
  function add(skill:Skill,years:number|null=null){if(disabled||chosen.has(skill.id)||selected.length>=60)return;onChange([...selected,{skill_id:skill.id,level:'working',years}]);setFeedback(skill.canonical_name+' added. Review your level below.');}
  function addCustom(name:string){name=name.trim();if(name.length<2||name.length>100||custom.length>=20||custom.some(s=>s.name.toLowerCase()===name.toLowerCase()))return;onCustomChange([...custom,{name,level:'working',years:null}]);setFeedback(name+' saved as an unmapped custom skill.');}
  const local=skills.filter(s=>(category==='all'||(s.category==='software')===(category==='software'))&&(s.canonical_name+' '+s.aliases.join(' ')+' '+Object.entries(aliases).filter(([,list])=>list.includes(s.canonical_name)).map(([name])=>name).join(' ')).toLowerCase().includes(query.toLowerCase().trim()));
  const results=(catalogue.isError?local.slice(offset,offset+20):catalogue.data?.skills??[]).filter(s=>!chosen.has(s.id)&&!suggestions.ids.has(s.id));
  const total=catalogue.data?.matched_total??local.length;
  function proficiency(name:string,level:Level,change:(value:Level)=>void){return <div className="skill-level-options" role="group" aria-label={name+' proficiency'}>{levels.map(value=><button type="button" key={value} disabled={disabled} aria-pressed={level===value} onClick={()=>change(value)}>{names[value]}</button>)}</div>;}
  return <div className="skill-review">
    {labels.isPending&&missing.length>0&&<p role="status">Loading skill names and sources…</p>}
    {labels.isError&&<p role="status">Some saved skill details could not be loaded. IDs are retained; retry the catalogue before making changes.</p>}
    {suggestions.pending.length>0&&<section className="skill-suggestions" aria-label="Suggested skills"><div className="skill-section-heading"><div><span className="eyebrow">FROM YOUR EXPERIENCE</span><h3>Does this sound like you?</h3></div><span>{suggestions.pending.length} to review</span></div><p>Choose only the skills you recognise. Software knowledge does not automatically confirm a broad competency.</p><div className="suggested-skill-grid">{suggestions.pending.map(item=><article key={item.skill.id} className="suggested-skill"><div><strong>{item.skill.canonical_name}</strong><small>{item.ambiguous?'Possible interpretation':'From'}: {[...item.mentions].join(', ')}</small><small>{item.skill.category==='software'?'Specific software / tool':'Broad occupational skill'}</small></div><button type="button" className="skill-add" aria-label={'Add '+item.skill.canonical_name} disabled={disabled||selected.length>=60} onClick={()=>add(item.skill,item.years)}><Plus size={16}/>Add</button>{item.excerpt&&<details><summary>See the connection</summary><blockquote>{item.excerpt}</blockquote><p>Confirm this connection and your proficiency yourself.</p></details>}</article>)}</div></section>}
    {suggestions.unmapped.length>0&&<aside className="unmapped-skills"><strong>A few terms need your help</strong><p>Search for a supported concept, or explicitly keep a term as an unmapped custom skill.</p>{suggestions.unmapped.map(term=><button type="button" key={term} disabled={disabled||custom.length>=20||custom.some(s=>s.name===term)} onClick={()=>addCustom(term)}>Keep {term} as a custom skill</button>)}<button type="button" className="text-link" onClick={()=>input.current?.focus()}>Find a related skill</button></aside>}
    <section className="skill-library" aria-label="Find skills"><label htmlFor="skill-search">Add your strengths</label><div className="skill-search"><Search size={18}/><input id="skill-search" ref={input} type="search" maxLength={120} value={query} disabled={disabled} onChange={e=>setQuery(e.target.value)} placeholder="Search Python, SQL, Excel, writing…" aria-describedby="skill-search-help"/></div><p id="skill-search-help">Find specific software or broad skills. Selected and suggested skills are shown separately.</p>
      <div role="group" aria-label="Skill categories" className="skill-category-tabs">{[['all','All skills'],['software','Software and tools'],['core','Broad skills']].map(([id,label])=><button type="button" key={id} aria-pressed={category===id} disabled={disabled} onClick={()=>{setCategory(id);setOffset(0);}}>{label}</button>)}</div>
      {catalogue.data&&<p className="caption">Catalogue: {catalogue.data.catalogue_total.toLocaleString()} skills · {catalogue.data.counts.core} broad · {catalogue.data.counts.software.toLocaleString()} software and tools. {total} search matches.</p>}
      {catalogue.isError&&<p role="status">Full catalogue search is unavailable. Showing cached skills; your selections are retained. <button type="button" onClick={()=>void catalogue.refetch()}>Retry skill search</button></p>}
      {catalogue.isPending&&<p role="status">Searching skills…</p>}
      <div className="skill-picker" aria-label="Skill search results">{results.map(skill=><div key={skill.id}><button type="button" disabled={disabled||selected.length>=60||catalogue.isPlaceholderData} aria-label={'Choose '+skill.canonical_name} onClick={()=>add(skill)}><Plus size={13}/>{skill.canonical_name}</button><small>{skill.category==='software'?'Software / tool':'Broad skill'}{skill.relevant_to_targets?' · linked to your targets':''}</small>{skill.source_url&&<a href={skill.source_url} target="_blank" rel="noreferrer">Source {skill.source_version}</a>}</div>)}</div>
      {!catalogue.isPending&&!results.length&&<p className="skill-empty">No additional matches on this page. A matching skill may already be suggested above or selected below. Try another term or category.</p>}
      <div className="skill-search-pages"><button type="button" disabled={disabled||offset===0||catalogue.isFetching} onClick={()=>setOffset(Math.max(0,offset-20))}>Previous skills</button><span>{total?offset+1:0}–{Math.min(offset+20,total)} of {total}</span><button type="button" disabled={disabled||offset+20>=total||catalogue.isFetching} onClick={()=>setOffset(offset+20)}>More skills</button></div>
      {query.trim().length>=2&&query.trim().length<=100&&!custom.some(s=>s.name.toLowerCase()===query.trim().toLowerCase())&&![...known.values()].some(s=>s.canonical_name.toLowerCase()===query.trim().toLowerCase()||s.aliases.some(a=>a.toLowerCase()===query.trim().toLowerCase()))&&<button type="button" className="text-link" disabled={disabled||custom.length>=20} onClick={()=>addCustom(query)}>Keep “{query.trim()}” as an unmapped custom skill</button>}
    </section>
    <section className="confirmed-skill-section" aria-label="Your confirmed skills"><div className="skill-section-heading"><div><span className="eyebrow">REVIEWED BY YOU</span><h3>Your skills, your level.</h3></div><span>{selected.length} catalogue · {custom.length} custom</span></div>{!selected.length&&!custom.length?<p className="skill-empty">Add a suggestion or choose a skill above. Nothing is confirmed automatically.</p>:<div className="confirmed-skill-list">{selected.map(item=>{const skill=known.get(item.skill_id),name=skill?.canonical_name??'Saved skill (details unavailable)';return <article className="confirmed-skill" key={item.skill_id}><div className="confirmed-skill-title"><span><Check size={15}/>{name}</span><button type="button" className="icon-button" disabled={disabled} aria-label={'Remove '+name} onClick={()=>onChange(selected.filter(s=>s.skill_id!==item.skill_id))}><X size={16}/></button></div><small>{skill?.category==='software'?'Specific software · technical alignment only':'Broad occupational skill'}</small>{proficiency(name,item.level,value=>onChange(selected.map(s=>s.skill_id===item.skill_id?{...s,level:value}:s)))}<label className="skill-years">Years using this skill <span>(optional)</span><input type="number" aria-label={name+' years'} min={0} max={60} step={.5} disabled={disabled} value={item.years??''} onChange={e=>{const value=e.target.value===''?null:Number(e.target.value);if(value===null||Number.isFinite(value)&&value>=0&&value<=60)onChange(selected.map(s=>s.skill_id===item.skill_id?{...s,years:value}:s));}}/></label></article>;})}{custom.map((item,index)=><article className="confirmed-skill" key={'custom:'+item.name}><div className="confirmed-skill-title"><strong>{item.name}</strong><button type="button" disabled={disabled} aria-label={'Remove custom '+item.name} onClick={()=>onCustomChange(custom.filter((_,i)=>i!==index))}>Remove</button></div><small>Custom · unmapped. Saved for context; no occupational score or connection is invented.</small>{proficiency(item.name,item.level,value=>onCustomChange(custom.map((s,i)=>i===index?{...s,level:value}:s)))}</article>)}</div>}<p className="skill-rating-help">Learning: building the basics. Working: can use it in a task. Strong: can apply it independently. These are self-ratings, not certificates.</p></section>
    {selected.length>=60&&<p role="alert">You can review up to 60 catalogue skills. Remove one before adding another.</p>}<p className="sr-only" role="status" aria-live="polite">{feedback}</p>
  </div>;
}
