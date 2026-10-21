import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Check, Compass, FileText, ShieldCheck } from 'lucide-react';
import { Button, ErrorState, LoadingSkeleton } from './components';
import { profileRequest, useProfile, type Candidate, type Extraction, type OnboardingDraft, type Profile } from './profile-api';
import { useCatalogue } from './ProfilePages';
import { useFuture } from './future-api';
import SkillReview from './SkillReview';
import CareerDiscovery from './CareerDiscovery';
import './onboarding.css';
import './skill-review.css';

const countries = { MY:'Malaysia', SG:'Singapore', US:'United States', GB:'United Kingdom', AU:'Australia', OTHER:'Another location' };
const steps = ['About You', 'Your Skills', 'Your Direction'];
const blank: OnboardingDraft = {step:0,status:'student',current_field:'',experience_years:0,country:'MY',market:'MY',goal:'',interests:[],weekly_hours:6,skills:[]};

/** Route guard waits for the owned profile before deciding; legacy confirmed profiles are complete. */
export function FutureEntry({children}:{children:React.ReactNode}) {
  const current=useProfile();
  if(current.isPending)return <LoadingSkeleton label="Opening your private workspace"/>;
  if(current.isError)return <ErrorState message="Your private workspace could not be checked. Refresh to retry."/>;
  if(!current.data?.profile?.confirmed)return <Navigate to="/profile/intake" replace/>;
  return children;
}

export function IntakeWizard() {
  const current=useProfile(),catalogue=useCatalogue(),cache=useQueryClient(),navigate=useNavigate();
  const savedFuture=useFuture();
  const [draft,setDraft]=useState<OnboardingDraft>(blank),[profile,setProfile]=useState<Profile|null>(null);
  const [mode,setMode]=useState<'upload'|'manual'>('upload'),[file,setFile]=useState<File|null>(null),[text,setText]=useState(''),[useAI,setUseAI]=useState(true);
  const [candidates,setCandidates]=useState<Candidate[]>([]),[warnings,setWarnings]=useState<string[]>([]);
  const [fieldErrors,setFieldErrors]=useState<Record<string,string>>({});
  const [reviewReady,setReviewReady]=useState(false);
  const canReviewSkills=!!profile&&(profile.confirmed||reviewReady||draft.skills.length>0);
  const reviewExisting=mode==='manual'&&!text.trim()&&draft.skills.length>0;
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[demo,setDemo]=useState(false),[draftStatus,setDraftStatus]=useState('');
  const initialized=useRef(false),heading=useRef<HTMLHeadingElement>(null),draftRef=useRef(draft),profileRef=useRef(profile),savedDraft=useRef(''),finished=useRef(false),queue=useRef(Promise.resolve());
  draftRef.current=draft;profileRef.current=profile;
  const creating=useRef<Promise<Profile>|null>(null);
  async function ensureProfile(){if(profileRef.current)return profileRef.current;if(!creating.current)creating.current=profileRequest<Profile>('','POST',{is_demo:demo});try{const p=await creating.current;profileRef.current=p;setProfile(p);cache.setQueryData(['private-profile'],{profile:p});return p;}finally{creating.current=null;}}
  useEffect(()=>{if(initialized.current||!current.data||(current.data.profile?.confirmed&&!savedFuture.data))return;initialized.current=true;const p=current.data.profile;setProfile(p);if(p){setDemo(p.is_demo);if(p.confirmed)setMode("manual");const d=p.onboarding;setReviewReady(!!d&&d.step>0);setDraft(d?{...d,step:p.confirmed?0:d.step,completed:undefined,weekly_hours:savedFuture.data?.weekly_hours??d.weekly_hours}:{...blank,country:p.country,market:p.country,interests:p.interests,skills:p.skills,weekly_hours:savedFuture.data?.weekly_hours??6});}},[current.data,savedFuture.data]);
  useEffect(()=>{heading.current?.focus();},[draft.step]);
  // Debounced structured drafts stay server-side under the same HttpOnly session.
  // No raw document, extracted excerpt or cookie is written to browser storage.
  useEffect(()=>{if(!initialized.current||finished.current||(!profile&&!draft.current_field.trim()))return;const timer=setTimeout(()=>{void (async()=>{await ensureProfile();await persist(draftRef.current);})().catch(()=>{setDraftStatus('Progress not saved yet.');setError('Draft could not be saved. Keep this page open and retry Continue.');});},700);return()=>clearTimeout(timer);},[draft,profile?.id]);
  function update(patch:Partial<OnboardingDraft>){setDraftStatus('Changes waiting to save…');setDraft(d=>({...d,...patch}));setError('');}
  function clean(d:OnboardingDraft){const {completed:_completed,...fields}=d;return fields;}
  async function persist(d:OnboardingDraft){const p=profileRef.current;if(!p||finished.current)return;if(!Number.isFinite(d.experience_years)||d.experience_years<0||d.experience_years>60){setDraftStatus('Correct your experience years to save progress.');return;}const body=clean(d),key=JSON.stringify(body);const operation=queue.current.catch(()=>{}).then(async()=>{if(savedDraft.current===key||finished.current)return;setDraftStatus('Saving progress…');await profileRequest(`/${p.id}/onboarding`,'PUT',body);savedDraft.current=key;setDraftStatus('Progress saved privately.');});queue.current=operation;await operation;}
  // Editing saved steps only persists structured changes; analysis is an explicit separate action.
  async function next(step:number){if(step>0&&!canReviewSkills||step===2&&draft.skills.length<3)return;setBusy(true);setError('');setFieldErrors({});try{const d={...draft,step};await persist(d);setDraft(d);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  function validateFile(value:File|null){return !value?'Choose a PDF or DOCX, or switch to manual entry.':value.size>5*1024*1024?'Choose a file up to 5 MB.':!/\.(pdf|docx)$/i.test(value.name)?'Only PDF and DOCX documents are supported.':'';}
  async function begin(){
    const issues:Record<string,string>={};
    if(!draft.current_field.trim())issues.current_field='Add your current role or field of study.';
    if(!Number.isFinite(draft.experience_years)||draft.experience_years<0||draft.experience_years>60)issues.experience_years='Experience must be between 0 and 60 years.';
    if(mode==='upload'){const problem=validateFile(file);if(problem)issues.file=problem;}
    else if(text.trim().length<20)issues.text='Describe your experience in at least 20 characters, including tasks, projects or skills.';
    setFieldErrors(issues);setError('');
    if(Object.keys(issues).length){document.getElementById(Object.keys(issues)[0]==='text'?'experience-text':Object.keys(issues)[0])?.focus();return;}
    setBusy(true);
    try{
      const p=await ensureProfile();
      {
        const form=new FormData();if(mode==='upload'&&file)form.set('file',file);else form.set('text',text.trim());
        form.set('use_ai',String(useAI));
        const result=await profileRequest<Extraction>(`/${p.id}/analysis`,'POST',form);
        if(!Array.isArray(result.candidates)||result.candidates.some(c=>!Array.isArray(c.options)))throw new Error('The analysis response could not be reviewed safely. Retry or use local suggestions.');
        setCandidates(result.candidates);setWarnings(result.warnings??[]);setNotice(result.message+(result.truncated?' The document was limited to the first 20,000 characters.':''));
      }
      const d={...draft,step:1};await persist(d);setReviewReady(true);setDraft(d);setFile(null);setText('');
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  async function finish(){if(!profile)return;setBusy(true);setError('');try{
    await persist(draft);
    finished.current=true;
    const saved=await profileRequest<Profile>(`/${profile.id}/skills`,'PUT',{skills:draft.skills,country:draft.market,interests:draft.interests,onboarding:clean(draft)});
    cache.setQueryData(['private-profile'],{profile:saved});
    cache.removeQueries({queryKey:['career-graph']});cache.removeQueries({queryKey:['private-matches']});cache.removeQueries({queryKey:['future']});
    await cache.invalidateQueries({queryKey:['private-profile']});navigate('/',{replace:true});
  }catch(e){finished.current=false;setError((e as Error).message);}finally{setBusy(false);}}
  if(current.isPending||(current.data?.profile?.confirmed&&savedFuture.isPending))return <LoadingSkeleton label="Finding your saved starting point"/>;
  if(current.data?.profile?.confirmed&&savedFuture.isError)return <><ErrorState message="Learning preferences unavailable. Retry to keep your saved pathway pace."/><Button onClick={()=>void savedFuture.refetch()}>Retry learning preferences</Button></>;
  if(current.isError)return <><ErrorState message="Your private session could not be loaded."/><Button onClick={()=>void current.refetch()}>Retry</Button></>;
  return <section className="onboarding"><header className="onboarding-welcome"><span className="onboarding-symbol"><Compass size={30}/></span><p className="eyebrow">A LITTLE ABOUT YOU. A WORLD AHEAD.</p><h1>{current.data?.profile?.confirmed?'Make room for your next chapter.':'Let’s find your direction.'}</h1><p>Three small steps to a future that starts with you.</p></header>
    <ol className="onboarding-progress" aria-label="Profile setup progress">{steps.map((s,i)=><li key={s} className={i<=draft.step?'active':''}><button type="button" aria-current={draft.step===i?'step':undefined} disabled={busy||i===1&&!canReviewSkills||i===2&&(!canReviewSkills||draft.skills.length<3)} onClick={()=>void next(i)}><span>{i<draft.step?<Check size={17}/>:`0${i+1}`}</span>{s}</button></li>)}</ol>
    <div className="onboarding-stage" aria-busy={busy}><div className="onboarding-stage-meta"><span>STEP {draft.step+1} OF 3</span><span><ShieldCheck size={15}/> Private session</span></div><h2 ref={heading} tabIndex={-1}>{steps[draft.step]}</h2>{demo&&<p className="onboarding-hint">Demo profile · illustrative experience</p>}
    {draft.step===0&&<fieldset className="onboarding-inputs" disabled={busy}><p>Bring your experience, however you’ve built it.</p><div className="onboarding-fields"><label>Where are you now?<select value={draft.status} onChange={e=>update({status:e.target.value as OnboardingDraft['status']})}><option value="student">Studying</option><option value="employed">Employed</option><option value="self_employed">Self-employed</option><option value="seeking">Looking for work</option><option value="other">Exploring my next step</option></select></label><label>Current role or field of study<input id="current_field" maxLength={160} value={draft.current_field} onChange={e=>{update({current_field:e.target.value});setFieldErrors(v=>({...v,current_field:''}));}} placeholder="e.g. Computer science student" aria-invalid={!!fieldErrors.current_field} aria-describedby={fieldErrors.current_field?'current-field-error':undefined}/>{fieldErrors.current_field&&<span className="field-error" id="current-field-error" role="alert">{fieldErrors.current_field}</span>}</label><label>Experience in years<input id="experience_years" type="number" min={0} max={60} step={0.5} value={draft.experience_years} onChange={e=>{update({experience_years:Number(e.target.value)});setFieldErrors(v=>({...v,experience_years:''}));}} aria-invalid={!!fieldErrors.experience_years}/>{fieldErrors.experience_years&&<span className="field-error" role="alert">{fieldErrors.experience_years}</span>}</label><label>Country<select value={draft.country} onChange={e=>update({country:e.target.value})}>{Object.entries(countries).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label></div>
    {!profile&&<button type="button" className="text-link onboarding-demo" onClick={()=>{setDemo(true);setMode('manual');setUseAI(false);setText('Demo profile — illustrative experience. I used Python programming to build software. My projects involved critical thinking, writing, mathematics, active learning and active listening.');update({current_field:'Demo — exploring technology careers'});setFieldErrors({});}}>Try a labelled demo</button>}
    <div className="input-modes" role="group" aria-label="Experience input method">{(['upload','manual'] as const).map(m=><button type="button" key={m} aria-pressed={mode===m} onClick={()=>{setMode(m);setError('');setFieldErrors({});}}>{m==='upload'?'Upload resume':'Enter manually'}</button>)}</div>
    {mode==='upload'?<><label className="upload-zone"><FileText size={30}/><strong>Your experience, ready to explore.</strong><span>Choose a PDF or DOCX · up to 5 MB · text documents only</span><input id="file" type="file" aria-label="Resume file" accept=".pdf,.docx" aria-invalid={!!fieldErrors.file} aria-describedby={fieldErrors.file?'file-error':undefined} onChange={e=>{const selected=e.target.files?.[0]??null;setFile(selected);setFieldErrors(v=>({...v,file:validateFile(selected)}));setError('');}}/>{file&&<span>{file.name}</span>}</label>{fieldErrors.file&&<p className="field-error" id="file-error" role="alert">{fieldErrors.file}</p>}</>:<label className="field-label manual-experience">Tell us about your experience <textarea id="experience-text" rows={5} value={text} maxLength={20000} aria-label="Your experience" aria-invalid={!!fieldErrors.text} aria-describedby="experience-help experience-error" onChange={e=>{setText(e.target.value);setFieldErrors(v=>({...v,text:''}));setError('');}} placeholder="What have you worked on or studied? Describe tasks, projects and skills. For example: I used Python to analyse data, wrote project reports and coordinated a small team."/><small id="experience-help">{reviewExisting?'Your reviewed skills are saved. Continue without retyping, or add experience for new suggestions.':'At least 20 characters. Leave out names, contact details and other personal information.'} <span>{text.length.toLocaleString()} / 20,000</span></small>{fieldErrors.text&&<span className="field-error" id="experience-error" role="alert">{fieldErrors.text}</span>}</label>}
    <div className="analysis-choice"><label className="checkbox-field"><input type="checkbox" checked={useAI} onChange={e=>setUseAI(e.target.checked)}/><span>Use AI to understand my experience<small>OpenAI reasons over the text and suggests supported skills for your review. Both input methods use the same validation.</small></span></label><details><summary>How your experience is handled</summary><p>PDFs are read with pypdf; DOCX files are read as text. With AI selected, document or manual text is sent to OpenAI. Contact patterns are removed first, but names may remain. Noka discards raw text and documents. API storage is disabled; provider retention policies apply. Nothing is sent to search providers.</p></details></div>
    {canReviewSkills&&<div className="saved-profile-navigation"><p>Your reviewed skills are saved. Move between steps without uploading a document or contacting OpenAI. Analyse experience only when you want new suggestions.</p><Button disabled={busy} className="button-secondary" onClick={()=>void next(1)}>{file||text.trim()?'Continue with saved skills':'Review my skills'}<ArrowRight size={17}/></Button></div>}
    {!reviewExisting&&<Button disabled={busy||!catalogue.skills.data} onClick={()=>void begin()}>{busy?'Analysing your experience…':'Analyse my experience'}<ArrowRight size={17}/></Button>}</fieldset>}
    {draft.step===1&&<><p>Choose what belongs in your profile. Nothing is confirmed automatically.</p>{notice&&<p role="status" className="onboarding-hint">{notice}</p>}{warnings.map(w=><p key={w} className="review-warning" role="status">{w}</p>)}<SkillReview skills={catalogue.skills.data?.skills??[]} candidates={candidates} selected={draft.skills} onChange={skills=>update({skills})} disabled={busy}/><p className="caption">At least three reviewed skills unlock your first analysis. Proficiency affects fit; years do not change scores.</p><div className="wizard-actions"><Button disabled={busy||draft.skills.length<3} onClick={()=>void next(2)}>Find my direction <ArrowRight size={17}/></Button><Button disabled={busy} className="button-secondary" onClick={()=>void next(0)}>Back</Button></div></>}
    {draft.step===2&&<><p>A few choices to help turn possibilities into a plan.</p><label className="field-label">What would you like to work toward?<textarea rows={2} maxLength={400} value={draft.goal} onChange={e=>update({goal:e.target.value})} placeholder="e.g. Move into a role building useful AI tools"/></label><CareerDiscovery interests={draft.interests} aspirations={draft.aspirations} titles={Object.fromEntries((catalogue.roles.data?.roles??[]).map(r=>[r.id,r.title]))} disabled={busy} onChange={(interests,aspirations)=>update({interests,aspirations})}/><label className="field-label">Projects or practical experience (optional)<textarea rows={3} maxLength={2000} value={draft.projects??''} onChange={e=>update({projects:e.target.value})} placeholder="Describe work you want your career exploration to consider. This is saved profile context, not verified proficiency."/></label><label className="field-label">Learning constraints or preferences (optional)<textarea rows={2} maxLength={600} value={draft.constraints??''} onChange={e=>update({constraints:e.target.value})} placeholder="For example: free resources, evening study, accessible learning formats. Used as context for Guide; no automatic eligibility decisions."/></label><div className="onboarding-fields"><label>Preferred career market<select value={draft.market} onChange={e=>update({market:e.target.value})}>{Object.entries(countries).map(([id,name])=><option key={id} value={id}>{name}</option>)}</select></label><label>Weekly learning time <strong>{draft.weekly_hours} hours</strong><input type="range" min={1} max={40} value={draft.weekly_hours} onChange={e=>update({weekly_hours:Number(e.target.value)})}/></label></div><p className="onboarding-hint">Skills determine readiness. Confirmed targets remain visible without a score bonus. Goals, background and project terms provide separate discovery relevance; they do not prove proficiency. Hours set your pace. Requirements use US O*NET; market is a preference.</p><div className="wizard-actions"><Button disabled={busy} onClick={()=>void finish()}>{busy?'Building your first analysis…':'Explore My Future'}<ArrowRight size={17}/></Button><Button disabled={busy} className="button-secondary" onClick={()=>void next(1)}>Back</Button></div></>}
    {draftStatus&&<p className="onboarding-save-status" role="status">{draftStatus}</p>}{error&&<ErrorState message={error}/>} {catalogue.skills.isError&&<ErrorState message="Skills could not be loaded. Refresh to retry."/>}{catalogue.roles.isError&&<p role="alert">Career interests unavailable. You can continue without them.</p>}
    </div><p className="onboarding-footnote">Structured progress saves privately as you go. Original resumes and unconfirmed suggestions are never saved.</p></section>;
}
