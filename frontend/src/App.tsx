import { useEffect, useState } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, ArrowUpRight, AudioLines, BookOpen, ChartNoAxesCombined, Check, ChevronRight, Compass, FlaskConical, Globe2, Home, Layers3, Leaf, Menu, Radar, Route as RouteIcon, Sparkles, Target, UserRound, X } from 'lucide-react';
import { Button, EmptyState, ErrorState, EvidenceBadge, GlassCard, LoadingSkeleton, PageHeader, SiteFooter } from './components';

const pages = [
  { path: '/', label: 'Overview', icon: Home },
  { path: '/profile', label: 'My profile', icon: UserRound, title: 'Your next chapter starts with you.', description: 'A place for your experience, strengths, and ambitions.', empty: 'Your profile has room to grow', detail: 'Resume upload and editable skills will arrive in a later phase. No personal information has been collected.' },
  { path: '/signals', label: 'Signals', icon: Radar, title: 'See what’s shaping work.', description: 'Dated evidence on AI developments and labour-market shifts.', empty: 'Awaiting the first source refresh', detail: 'No sources have been ingested. Publication dates, retrieval dates, and last-successful refresh will appear with connected evidence.' },
  { path: '/forecast', label: 'Forecast', icon: ChartNoAxesCombined, title: 'Look ahead, with perspective.', description: 'Four-week sector demand forecasts, grounded in observed data.', empty: 'No trained forecast yet', detail: 'Forecasts require verified sector time series and time-valid evaluation. Geography, uncertainty, model version, and forecast timestamps will accompany every result.' },
  { path: '/matches', label: 'Role matches', icon: Target, title: 'Find where your strengths fit.', description: 'Explore future roles through the skills you bring and the skills you can build.', empty: 'Your possibilities start with a profile', detail: 'Role matching is not available in Phase 0. Curated roles and explainable skill gaps will appear once the catalogue and profiles are connected.' },
  { path: '/roadmap', label: 'My roadmap', icon: RouteIcon, title: 'Small steps. New possibilities.', description: 'Turn a skill gap into a practical reskilling pathway.', empty: 'A fresh page for your learning journey', detail: 'Personalized pathways and saved learning progress will become available in a later phase.' },
  { path: '/sdgs', label: 'SDG impact', icon: Globe2, title: 'Build skills with a bigger purpose.', description: 'Connect career pathways to applicable UN Sustainable Development Goals.', empty: 'Impact needs a clear connection', detail: 'Role and skill mappings will be linked to official UN goals and targets. No impact or endorsement is claimed at this stage.' },
  { path: '/model-lab', label: 'Model Lab', icon: FlaskConical, title: 'Understand the evidence behind it.', description: 'A transparent view of data, assumptions, and model evaluation.', empty: 'The lab is ready for its first experiment', detail: 'There are no trained models or evaluation metrics yet. Four-week forecasts and long-run scenario planning indices will be clearly distinguished.' },
];

type Health = { status: 'ok'; service: 'noka-api' };
async function fetchHealth(): Promise<Health> {
  const response = await fetch('/api/health', { signal: AbortSignal.timeout(8000) });
  if (!response.ok) throw new Error('API unavailable');
  const data: unknown = await response.json();
  if (!data || typeof data !== 'object' || !('status' in data) || data.status !== 'ok' || !('service' in data) || data.service !== 'noka-api') throw new Error('Unexpected health response');
  return data as Health;
}

function ServiceStatus() {
  const query = useQuery({ queryKey: ['health'], queryFn: fetchHealth });
  if (query.isPending) return <LoadingSkeleton/>;
  if (query.isError) return <ErrorState message="API unavailable · refresh to retry"/>;
  return <span className="service-status"><i/> API connected <span>· checked {new Date(query.dataUpdatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></span>;
}

function Overview() {
  return <>
    <div className="welcome-line"><span>YOUR NEXT CHAPTER</span><EvidenceBadge>Phase 0 · Foundation</EvidenceBadge></div>
    <section className="hero">
      <div className="hero-copy"><span className="hero-kicker"><Sparkles size={14}/> A little clarity. A world of possibility.</span><h1>Tomorrow’s work.<br/>Your <em>way forward.</em></h1><p>The world of work is changing. Find your bearings, explore emerging possibilities, and build the skills to move forward.</p><Button asChild><Link to="/profile">Explore your profile <ArrowRight size={17}/></Link></Button><span className="hero-note">Your journey, informed by evidence.</span></div>
      <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><span className="art-spark spark-one">✦</span><span className="art-spark spark-two">✧</span><div className="floating-tag tag-top"><span className="tag-icon"><Compass size={19}/></span> Find your direction</div><div className="compass-card"><div className="compass-face"><span className="north">N</span><span className="east">E</span><span className="south">S</span><span className="west">W</span><div className="compass-ring"/><div className="needle"/><div className="needle-pin"/></div></div><div className="floating-tag tag-bottom"><span className="tag-icon mint"><Leaf size={18}/></span> Grow into what’s next <Check size={14}/></div><div className="art-caption">A future full of possibilities</div></div>
    </section>
    <div className="section-heading"><div><p className="eyebrow">MAKE YOUR NEXT MOVE</p><h2>A clearer path, one step at a time.</h2></div><span className="muted">Designed around you</span></div>
    <div className="journey-grid">{[
      { icon: UserRound, color: 'blue', number: '01', title: 'Start with your strengths', text: 'Bring your experience and skills into focus.', path: '/profile', link: 'Meet your profile' },
      { icon: AudioLines, color: 'mint', number: '02', title: 'Understand the change', text: 'Explore the signals shaping tomorrow’s work.', path: '/signals', link: 'Explore signals' },
      { icon: BookOpen, color: 'peach', number: '03', title: 'Make room to grow', text: 'Turn new possibilities into practical next steps.', path: '/roadmap', link: 'See your roadmap' },
    ].map(item => <GlassCard key={item.number} className="journey-card"><div className="card-top"><span className={`feature-icon ${item.color}`}><item.icon size={22}/></span><span className="step-number">{item.number}</span></div><h3>{item.title}</h3><p>{item.text}</p><Link to={item.path}>{item.link}<ArrowUpRight size={16}/></Link></GlassCard>)}</div>
    <GlassCard className="foundation-banner"><span className="feature-icon mint"><Layers3 size={22}/></span><div><h3>A thoughtful foundation. More to come.</h3><p>You’re exploring the initial Noka shell. Profiles, signals, forecasts, and pathways aren’t connected yet.</p></div><Link to="/model-lab">See Model Lab <ChevronRight size={16}/></Link></GlassCard>
    <div className="trust-line"><EvidenceBadge>Evidence before predictions</EvidenceBadge><span>No live feeds or model results are available yet.</span></div>
  </>;
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  useEffect(() => { setMenuOpen(false); document.title = `Noka — ${pages.find(p => p.path === location.pathname)?.label ?? 'Page not found'}`; }, [location.pathname]);
  return <div className="app"><a href="#main" className="skip-link">Skip to content</a><aside id="main-navigation" className={`sidebar ${menuOpen ? 'is-open' : ''}`}><Link className="brand" to="/" aria-label="Noka home"><span className="brand-mark"><Compass size={24}/></span>noka<span className="brand-dot">.</span></Link><p className="sidebar-caption">YOUR WORK. REIMAGINED.</p><nav aria-label="Main navigation">{pages.map(page => <NavLink key={page.path} to={page.path} end={page.path === '/'}><page.icon size={19}/>{page.label}</NavLink>)}</nav><div className="sidebar-bottom"><div className="purpose-icon"><Leaf size={22}/></div><h3>Grow with purpose.</h3><p>A better future for you.<br/>A positive impact for all.</p><Link to="/sdgs">Explore SDG impact <ArrowUpRight size={14}/></Link></div><div className="sidebar-version">NOKA <span>EARLY PREVIEW</span></div></aside><div className="workspace"><header className="topbar"><div className="breadcrumb"><Compass size={16}/><span>Workspace</span><ChevronRight size={13}/><strong>{pages.find(p => p.path === location.pathname)?.label ?? 'Not found'}</strong></div><div className="topbar-right"><span className="preview-pill">Foundation preview</span><span className="avatar" aria-label="Guest workspace">N</span><button className="menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="main-navigation">{menuOpen ? <X/> : <Menu/>}</button></div></header><main id="main"><Routes><Route path="/" element={<Overview/>}/>{pages.slice(1).map(page => <Route key={page.path} path={page.path} element={<><PageHeader eyebrow="YOUR NOKA WORKSPACE" title={page.title!} description={page.description!}/><GlassCard><EmptyState title={page.empty!}>{page.detail}</EmptyState></GlassCard></>}/>)}<Route path="*" element={<><PageHeader eyebrow="LET’S FIND YOUR WAY" title="This path doesn’t exist yet." description="Head back to your overview to keep exploring."/><Button asChild><Link to="/">Back to overview <ArrowRight size={16}/></Link></Button></>}/></Routes><div className="system-line"><ServiceStatus/><span>Private by design · No resume collected</span></div><SiteFooter/></main></div></div>;
}
