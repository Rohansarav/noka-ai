import { ActivityStatus } from './components';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from './components';
import { useFuture, type Task } from './future-api';

// Notes are saved separately; completion never discards an unsaved draft or awards proficiency.
export default function PathwayReview({task}:{task:Task}) {
  const future=useFuture();
  const [note,setNote]=useState(task.note??'');
  useEffect(()=>setNote(task.note??''),[task.note]);
  const dirty=note!==(task.note??'');
  const canComplete=!dirty&&(task.note??'').trim().length>=20&&!future.saving;
  return <section className="milestone-review" aria-label={`${task.name} review`}>
    <div className="review-heading"><div><span className="eyebrow">BEFORE YOU FINISH</span><h3>Review your work</h3></div><span className="review-self-report">Self-reported progress</span></div>
    <p>Use these checks to review your deliverable.</p>
    <ul className="review-criteria">{task.acceptance_criteria?.map(item=><li key={item}><label><input type="checkbox"/>{item}</label></li>)}</ul>
    <label className="review-evidence-label" htmlFor={`evidence-${task.skill_id}`}>Evidence and reflection</label>
    <p id={`evidence-help-${task.skill_id}`}>Link your work or describe the result, a check, and what you would improve. Save at least 20 characters before completing this step.</p>
    <textarea id={`evidence-${task.skill_id}`} aria-label={`${task.name} notes`} aria-describedby={`evidence-help-${task.skill_id}`} placeholder="Work sample link, observations, feedback, limitations and next improvement…" maxLength={1000} rows={4} value={note} onChange={e=>setNote(e.target.value)}/>
    <div className="review-save-row"><Button className="button-secondary" disabled={future.saving||!dirty} onClick={()=>future.progress.mutate({skill_id:task.skill_id,note})}>Save evidence</Button>{future.progress.isPending?<ActivityStatus>Saving evidence…</ActivityStatus>:<span role="status">{dirty?"Unsaved changes":task.note?"Saved":"No evidence saved yet"}</span>}</div>
    {future.progress.isError&&<p role="alert">Your change was not saved. Please retry. Your draft is still here.</p>}
    <div className="review-complete-row"><label>My progress <select aria-label={`${task.name} progress`} disabled={future.saving} value={task.status} onChange={e=>future.progress.mutate({skill_id:task.skill_id,status:e.target.value as Task['status']})}><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed" disabled={!canComplete}>Completed</option></select></label><Button disabled={!canComplete||task.status==='completed'} onClick={()=>future.progress.mutate({skill_id:task.skill_id,status:'completed'})}>{task.status==='completed'?'Step completed':'Mark step complete'}</Button></div>
    {task.status!=='completed'&&!canComplete&&<p className="review-hint">{dirty?'Save your changes before completing this step.':'Save your evidence above to unlock completion.'}</p>}
    <small>Completion records your own progress. It does not verify competence or change your profile proficiency. Checklist ticks are a temporary review aid.</small>
    {task.assessment_needed&&<details className="assessment-advice"><summary>Already comfortable with this?</summary><p>Try a short independent attempt first. If you can already demonstrate this skill, review your profile before committing to more practice.</p><Link to="/profile/intake">Review my skills →</Link></details>}
  </section>;
}
