import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Check, FileText, LockKeyhole, Plus, Trash2 } from 'lucide-react';
import { Badge, Button, EmptyState, ErrorState, GlassCard, LoadingSkeleton, PageHeader, ProgressBar } from './components';
import { getEvidence, type Role, type Skill } from './evidence-api';
import { profileRequest, useProfile, type Candidate, type Extraction, type Level, type Matches, type Profile, type ProfileSkill } from './profile-api';
import { useToast } from './toasts';

const STEPS = ['Your experience', 'Review skills', 'Your direction', 'Confirm'];
const COUNTRIES: Record<string, string> = { MY: 'Malaysia', US: 'United States', SG: 'Singapore', GB: 'United Kingdom', AU: 'Australia', OTHER: 'Another location' };
function useCatalogue() {
  const skills = useQuery({ queryKey: ['canonical-skills'], queryFn: () => getEvidence<{ skills: Skill[] }>('/api/skills', 'skills') });
  const roles = useQuery({ queryKey: ['roles'], queryFn: () => getEvidence<{ roles: Role[] }>('/api/roles', 'roles') });
  return { skills, roles };
}
export function ProfileSummaryCard() {
  const query = useProfile();
  const profile = query.data?.profile;
  return <GlassCard className="profile-card"><div className="tile-heading"><span className="feature-icon blue"><FileText size={23}/></span><Badge>{profile?.confirmed ? 'Reviewed by you' : 'Your starting point'}</Badge></div><h3>{query.isError ? 'Profile status unavailable' : query.isPending ? 'Your private profile' : profile?.confirmed ? `${profile.skills.length} skills, new possibilities.` : 'No profile yet'}</h3><p>Your experience belongs to you. Upload a resume, paste experience, or start with manual skills.</p><div className="profile-note"><LockKeyhole size={18}/><span>Private session · Originals discarded<br/><small>Only confirmed skills and preferences are saved.</small></span></div><Button asChild className="button-secondary"><Link to={profile?.confirmed ? '/matches' : '/profile/intake'}>{profile?.confirmed ? 'See my matches' : 'Explore profile intake'}<ArrowRight size={17}/></Link></Button></GlassCard>;
}

export function ProfilePage() {
  const query = useProfile();
  const cache = useQueryClient();
  const notify = useToast();
  const { skills } = useCatalogue();
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const profile = query.data?.profile;
  async function remove() {
    if (!profile) return;
    setDeleting(true);
    try { await profileRequest(`/${profile.id}`, 'DELETE'); cache.removeQueries({ queryKey: ['private-matches'] }); await cache.invalidateQueries({ queryKey: ['private-profile'] }); notify('Profile deleted', 'Your saved skills and preferences were removed.'); }
    catch (e) { setError((e as Error).message); } finally { setDeleting(false); }
  }
  return <><PageHeader eyebrow="YOUR PRIVATE PROFILE" title="Your next chapter starts with you." description="Keep your skills and ambitions in focus. Your browser session protects this profile."/>{query.isPending ? <LoadingSkeleton label="Loading private profile"/> : query.isError ? <><ErrorState message="Private profile unavailable. Refresh to retry."/><Button onClick={() => void query.refetch()}>Retry profile</Button></> : !profile?.confirmed ? <GlassCard><EmptyState title="No profile yet" action={<Button asChild><Link to="/profile/intake">Explore profile intake</Link></Button>}>Bring your experience or add skills manually. Review every suggestion before saving.</EmptyState></GlassCard> : <GlassCard className="private-card"><div className="tile-heading"><Badge tone="mint">{profile.is_demo ? 'Demo profile' : 'Reviewed by you'}</Badge><span className="caption">{COUNTRIES[profile.country]} · Private session</span></div><h2>Your strengths, in one place.</h2><div className="skill-chips">{profile.skills.map(s => <span className="skill-chip" key={s.skill_id}>{skills.data?.skills.find(k => k.id === s.skill_id)?.canonical_name ?? s.skill_id}<small>{s.level}{s.years !== null ? ` · ${s.years} years` : ''}</small></span>)}</div><div className="wizard-actions"><Button asChild><Link to="/matches">See my role matches <ArrowRight size={17}/></Link></Button><Button asChild className="button-secondary"><Link to="/profile/intake">Edit skills & preferences</Link></Button></div><p className="caption">Original resumes, names, contact details and extraction excerpts are not stored. This session expires after 30 days; clearing cookies removes access.</p><button className="text-link danger-link" onClick={() => setConfirmDelete(true)}>Delete my profile</button>{confirmDelete && <div className="data-notice"><p>Delete all saved skills and preferences for this session?</p><Button disabled={deleting} onClick={() => void remove()}>{deleting ? 'Deleting…' : 'Confirm deletion'}</Button><Button className="button-secondary" onClick={() => setConfirmDelete(false)}>Keep profile</Button></div>}</GlassCard>}{error && <ErrorState message={error}/>}</>;
}

export function IntakeWizard() {
  const current = useProfile();
  const { skills: skillsQuery, roles: rolesQuery } = useCatalogue();
  const skills = skillsQuery.data?.skills ?? [];
  const roles = rolesQuery.data?.roles ?? [];
  const cache = useQueryClient();
  const navigate = useNavigate();
  const notify = useToast();
  const [step, setStep] = useState(0);
  const [mode, setMode] = useState<'upload' | 'paste' | 'manual'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const [text, setText] = useState('');
  const [useAI, setUseAI] = useState(false);
  const [demo, setDemo] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [selected, setSelected] = useState<ProfileSkill[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateChoices, setCandidateChoices] = useState<Record<number, string>>({});
  const [country, setCountry] = useState('MY');
  const [interests, setInterests] = useState<string[]>([]);
  const [addSkill, setAddSkill] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const initialized = useRef(false);
  useEffect(() => {
    if (!initialized.current && current.data) {
      initialized.current = true;
      const p = current.data.profile;
      if (p) { setProfile(p); setSelected(p.skills); setCountry(p.country); setInterests(p.interests); setDemo(p.is_demo); }
    }
  }, [current.data]);
  useEffect(() => { heading.current?.focus(); }, [step]);
  function add(id: string, years: number | null = null) {
    if (id && !selected.some(s => s.skill_id === id)) setSelected(s => [...s, { skill_id: id, level: 'working', years }]);
  }
  async function begin() {
    setError(''); setBusy(true);
    try {
      if (mode === 'upload' && (!file || file.size > 5 * 1024 * 1024)) throw new Error('Choose a PDF or DOCX up to 5 MB, or use manual entry.');
      if (mode === 'paste' && !text.trim()) throw new Error('Paste experience or choose manual entry.');
      const p = profile ?? await profileRequest<Profile>('', 'POST', { is_demo: demo });
      setProfile(p);
      if (mode !== 'manual') {
        const form = new FormData();
        if (mode === 'upload' && file) form.set('file', file); else form.set('text', text);
        form.set('use_ai', String(useAI));
        const result = await profileRequest<Extraction>(`/${p.id}/resume`, 'POST', form);
        setCandidates(result.candidates); setCandidateChoices({}); setNotice(result.message + (result.truncated ? ' Input was capped at 20,000 characters.' : ''));
      } else { setCandidates([]); setNotice('Manual entry. Choose the skills you can demonstrate.'); }
      setText(''); setFile(null); if (fileRef.current) fileRef.current.value = '';
      setStep(1);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function save() {
    if (!profile) return;
    setBusy(true); setError('');
    try {
      await profileRequest(`/${profile.id}/skills`, 'PUT', { skills: selected, country, interests });
      setCandidates([]); cache.removeQueries({ queryKey: ['private-matches'] });
      await cache.invalidateQueries({ queryKey: ['private-profile'] });
      notify('Profile saved', `${selected.length} reviewed skills are ready for matching.`); navigate('/matches');
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <><PageHeader eyebrow="YOUR EXPERIENCE → YOUR DIRECTION" title="Start with what makes you, you." description="Four thoughtful steps. Review your strengths, choose a direction, and discover where you could fit."/><ol className="wizard-steps" aria-label="Profile setup progress">{STEPS.map((name, i) => <li key={name} className={i <= step ? 'active' : ''} aria-current={i === step ? 'step' : undefined}><span>{i < step ? <Check size={16}/> : i + 1}</span>{name}</li>)}</ol><GlassCard className="wizard-card"><div className="tile-heading"><Badge tone="blue">Step {step + 1} of 4</Badge><span className="caption"><LockKeyhole size={14}/> Private by design</span></div><h2 ref={heading} tabIndex={-1}>{STEPS[step]}</h2>{demo && <Badge tone="warning">Demo profile · illustrative experience</Badge>}
      {step === 0 && <><p>Bring a resume or start from a blank page. Originals are discarded; only skills and preferences you confirm are saved.</p><div className="input-modes" role="group" aria-label="Experience input method">{(['upload', 'paste', 'manual'] as const).map(m => <button key={m} aria-pressed={mode === m} onClick={() => { setMode(m); setError(''); }}>{m === 'upload' ? 'Upload CV' : m === 'paste' ? 'Paste experience' : 'Manual only'}</button>)}</div>{mode === 'upload' && <label className="upload-zone"><FileText size={30}/><strong>Choose your PDF or DOCX</strong><span>Up to 5 MB · text documents only · no OCR</span><input ref={fileRef} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" aria-label="Resume file" onChange={e => { setFile(e.target.files?.[0] ?? null); setError(''); }}/></label>}{mode === 'paste' && <label className="field-label">Your experience<textarea value={text} onChange={e => setText(e.target.value)} maxLength={20000} rows={7} placeholder="Describe projects, responsibilities, and skills. Remove contact details first."/><small>{text.length.toLocaleString()} / 20,000 characters</small></label>}{mode === 'manual' ? <div className="data-notice">No resume needed. Choose canonical skills and rate your current level in the next step.</div> : <label className="checkbox-field"><input type="checkbox" checked={useAI} onChange={e => setUseAI(e.target.checked)}/><span>Use OpenAI for extraction (optional)<small>Send document text to OpenAI. Contact patterns are removed first, but names may remain. API storage is disabled; provider retention policies still apply. Never sent to search providers. Leave unchecked for local suggestions.</small></span></label>}<label className="checkbox-field"><input type="checkbox" checked={demo} disabled={!!profile} onChange={e => setDemo(e.target.checked)}/>This is a demo profile (illustrative experience)</label><div className="wizard-actions"><Button disabled={busy || current.isPending || current.isError || !skills.length} onClick={() => void begin()}>{busy ? 'Reading experience…' : mode === 'manual' ? 'Choose my skills' : 'Extract & review skills'}<ArrowRight size={17}/></Button>{!profile && <button className="text-link" disabled={busy} onClick={() => { setDemo(true); setMode('paste'); setUseAI(false); setText('Demo profile — illustrative experience, not a real person.\nI used Python programming to build software. My projects involved critical thinking, active learning, writing, mathematics and complex problem solving. I coordinated team work and practised active listening.'); }}>Try a labelled demo</button>}</div><p className="caption">{profile?.confirmed ? "Your existing reviewed fields stay saved until you confirm changes." : "An empty private profile is created when you continue. Skills are saved only after your final confirmation."}</p>{current.isError && <Button className="button-secondary" onClick={() => void current.refetch()}>Retry private session</Button>}</>}
      {step === 1 && <><p>Suggestions are starting points. Add only skills you recognize, then adjust your level. Ambiguous mentions need your choice.</p>{notice && <div role="status" className="data-notice">{notice}</div>}{candidates.length > 0 && <div className="candidate-list">{candidates.map((c, i) => <div className="candidate" key={`${c.mention}-${i}`}><div><strong>{c.mention}</strong><span className="caption">{c.mapping} · {c.confidence} qualitative confidence</span>{c.evidence_excerpt && <blockquote>{c.evidence_excerpt}</blockquote>}</div><div className="candidate-controls"><label className="sr-only" htmlFor={`candidate-${i}`}>Canonical skill for {c.mention}</label><select id={`candidate-${i}`} value={candidateChoices[i] ?? (c.options.length === 1 ? c.options[0] : '')} onChange={e => setCandidateChoices(s => ({ ...s, [i]: e.target.value }))}><option value="">Choose a skill…</option>{skills.map(s => <option key={s.id} value={s.id}>{s.canonical_name}{c.options.includes(s.id) ? ' · suggested' : ''}</option>)}</select><Button className="button-secondary" disabled={!(candidateChoices[i] ?? (c.options.length === 1 ? c.options[0] : ''))} onClick={() => { add(candidateChoices[i] ?? c.options[0], c.years); setCandidates(s => s.filter((_, n) => n !== i)); setCandidateChoices({}); }}>Confirm skill</Button><button className="icon-button" aria-label={`Dismiss ${c.mention}`} onClick={() => { setCandidates(s => s.filter((_, n) => n !== i)); setCandidateChoices({}); }}><Trash2 size={16}/></button></div></div>)}</div>}<label className="field-label">Add a canonical skill<div className="add-skill"><select value={addSkill} onChange={e => setAddSkill(e.target.value)}><option value="">Select a skill…</option>{skills.filter(s => !selected.some(p => p.skill_id === s.id)).map(s => <option value={s.id} key={s.id}>{s.canonical_name}</option>)}</select><Button className="button-secondary" disabled={!addSkill} onClick={() => { add(addSkill); setAddSkill(''); }}><Plus size={16}/>Add skill</Button></div></label><SkillEditor selected={selected} skills={skills} onChange={setSelected}/><p className="caption">Learning = 0.25 · Working = 0.65 · Strong = 1.0 in matching. Years are optional and do not affect scores. Add at least three skills for ranked matches.</p><div className="wizard-actions"><Button disabled={!selected.length} onClick={() => { setCandidates([]); setStep(2); }}>Continue with {selected.length} reviewed skills<ArrowRight size={17}/></Button><Button className="button-secondary" onClick={() => setStep(0)}>Back</Button></div>{candidates.length > 0 && <p className="caption">Unconfirmed suggestions will be discarded when you continue.</p>}</>}
      {step === 2 && <><p>Your location helps describe your preferences. The current role catalogue uses US occupational skills; local vacancies and demand are not inferred.</p><label className="field-label">Preferred location<select value={country} onChange={e => setCountry(e.target.value)}>{Object.entries(COUNTRIES).map(([code, name]) => <option key={code} value={code}>{name}</option>)}</select></label><fieldset className="interest-options"><legend>Target interests <span className="caption">Optional · up to 5 roles · +5 heuristic points</span></legend>{roles.map(role => <label className="checkbox-field" key={role.id}><input type="checkbox" checked={interests.includes(role.id)} disabled={interests.length >= 5 && !interests.includes(role.id)} onChange={e => setInterests(s => e.target.checked ? [...s, role.id] : s.filter(id => id !== role.id))}/>{role.title}</label>)}</fieldset>{rolesQuery.isError && <ErrorState message="Role interests unavailable. You can continue without them."/>}<div className="wizard-actions"><Button onClick={() => setStep(3)}>Review my profile<ArrowRight size={17}/></Button><Button className="button-secondary" onClick={() => setStep(1)}>Back</Button></div></>}
      {step === 3 && <><p>Save only these reviewed fields. Your resume, pasted text and evidence excerpts will not be saved.</p><dl className="confirmation"><div><dt>Preferred location</dt><dd>{COUNTRIES[country]}</dd></div><div><dt>Target interests</dt><dd>{interests.map(id => roles.find(r => r.id === id)?.title).join(', ') || 'Open to possibilities'}</dd></div></dl><div className="skill-chips">{selected.map(s => <span className="skill-chip" key={s.skill_id}>{skills.find(k => k.id === s.skill_id)?.canonical_name}<small>{s.level}{s.years !== null ? ` · ${s.years} years` : ''}</small></span>)}</div>{selected.length < 3 && <div className="data-notice">You can save now, but at least three confirmed skills are needed for ranked roles.</div>}<div className="wizard-actions"><Button disabled={busy} onClick={() => void save()}>{busy ? 'Saving reviewed skills…' : 'Save profile & see matches'}<ArrowRight size={17}/></Button><Button disabled={busy} className="button-secondary" onClick={() => setStep(2)}>Back</Button></div></>}
      {busy && <p role="status" className="caption">{step === 0 ? 'Reading text and preparing reviewable suggestions. This can take up to 30 seconds.' : 'Saving your confirmed fields securely.'}</p>}{error && <ErrorState message={error}/>} {skillsQuery.isError && <><ErrorState message="Canonical skills unavailable. Retry before continuing."/><Button onClick={() => void skillsQuery.refetch()}>Retry skills</Button></>}
    </GlassCard><p className="privacy-footnote"><LockKeyhole size={15}/> Anonymous session · HttpOnly cookie · No resume retention · No search-provider sharing</p></>;
}

function SkillEditor({ selected, skills, onChange }: { selected: ProfileSkill[]; skills: Skill[]; onChange: (s: ProfileSkill[]) => void }) {
  return <div className="reviewed-skills">{selected.map(s => { const name = skills.find(k => k.id === s.skill_id)?.canonical_name ?? s.skill_id; return <div className="reviewed-skill" key={s.skill_id}><strong>{name}</strong><label>Current level<select value={s.level} onChange={e => onChange(selected.map(k => k.skill_id === s.skill_id ? { ...k, level: e.target.value as Level } : k))}><option value="learning">Learning</option><option value="working">Working</option><option value="strong">Strong</option></select></label><label>Years (optional)<input type="number" min={0} max={60} step={0.5} value={s.years ?? ''} onChange={e => { const value = e.target.value === '' ? null : Number(e.target.value); if (value === null || value >= 0 && value <= 60) onChange(selected.map(k => k.skill_id === s.skill_id ? { ...k, years: value } : k)); }}/></label><button className="icon-button" aria-label={`Remove ${name}`} onClick={() => onChange(selected.filter(k => k.skill_id !== s.skill_id))}><Trash2 size={17}/></button></div>; })}</div>;
}

export function MatchesPage() {
  const current = useProfile();
  const profile = current.data?.profile;
  const query = useQuery({ queryKey: ['private-matches', profile?.id, profile?.updated_at], queryFn: () => profileRequest<Matches>(`/${profile!.id}/matches`), enabled: !!profile?.confirmed, retry: false });
  return <><PageHeader eyebrow="YOUR STRENGTHS → NEW POSSIBILITIES" title="Find where your strengths fit." description="A transparent skill-fit guide, grounded in real occupational requirements. These scores are heuristics, not probabilities or forecasts."/>{current.isPending ? <LoadingSkeleton label="Loading private profile"/> : current.isError ? <><ErrorState message="Private session unavailable."/><Button onClick={() => void current.refetch()}>Retry profile</Button></> : !profile?.confirmed ? <GlassCard><EmptyState title="No profile yet" action={<Button asChild><Link to="/profile/intake">Explore profile intake</Link></Button>}>Review your experience or add skills manually to see personalized role matches.</EmptyState></GlassCard> : query.isPending ? <LoadingSkeleton label="Comparing your reviewed skills"/> : query.isError ? <><ErrorState message="Matches unavailable. Your saved skills are safe."/><Button onClick={() => void query.refetch()}>Retry matches</Button></> : query.data && <>{profile.is_demo && <div className="data-notice"><Badge tone="warning">Demo profile</Badge> Illustrative experience, matched against real O*NET skill requirements.</div>}<div className="match-intro"><p>{profile.skills.length} reviewed skills · {COUNTRIES[profile.country]} preference</p><Link className="text-link" to="/profile/intake">Edit skills & preferences <ArrowRight size={16}/></Link></div>{query.data.status === 'insufficient_profile_information' ? <GlassCard><h2>Insufficient profile information</h2><p>Add at least three confirmed skills to receive ranked roles.</p><Button asChild><Link to="/profile/intake">Add more skills</Link></Button></GlassCard> : <div className="match-grid">{query.data.matches.map((match, i) => <GlassCard className="match-card" key={match.role_id}><div className="tile-heading"><Badge tone="blue">Possibility {i + 1}</Badge><span className="match-score">{match.score}<small>/ 100 skill fit</small></span></div><h2>{match.title}</h2><p>{match.explanation}</p><ProgressBar label="Weighted skill coverage" value={match.coverage}/><p className="caption">Transferable coverage: {match.transferable_coverage}% · Interest adjustment: +{match.interest_adjustment}</p><h3>Skills to build</h3>{!match.gaps.length && <p>No gaps at your self-rated levels. This does not establish professional qualification.</p>}<div className="gap-list">{match.gaps.slice(0, 5).map(gap => <div key={gap.skill_id}><div className="gap-heading"><span>{gap.name}</span>{gap.critical && <Badge tone="warning">Critical requirement</Badge>}</div><ProgressBar label={`${gap.name} gap`} value={Math.round(gap.gap * 100)}/></div>)}</div><details><summary>All gaps & source attribution</summary><ul>{match.gaps.map(g => <li key={g.skill_id}>{g.name}: {Math.round(g.gap * 100)}% proficiency gap · O*NET importance {g.importance}/5</li>)}</ul><p className="caption">Sources: {match.source_ids.join(', ')}. <Link to="/datasets">View source provenance</Link>. <Link to="/roles">Explore full role requirements</Link>.</p></details></GlassCard>)}</div>}<GlassCard className="match-method"><h2>How your match is calculated</h2><p>{query.data.methodology}</p><p>{query.data.geography_note}</p><p>No forecast dependency. The score does not establish qualification, hiring likelihood, salary or job availability.</p></GlassCard></>}<Link className="text-link catalogue-back" to="/roles">Explore the public role catalogue <ArrowRight size={16}/></Link></>;
}
