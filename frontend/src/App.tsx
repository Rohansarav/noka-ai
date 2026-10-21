import WorkspaceBoundary from './WorkspaceBoundary';
import { WorldDial, MyFuture as FuturePage, PathwayPage, ImpactPage, RadarPage, ModelLab } from './FuturePages';
import { FutureEntry, IntakeWizard } from './Onboarding';
import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, ArrowUpRight, BookOpen, ChartNoAxesCombined, Check, ChevronRight, Compass, FileText, FlaskConical, Globe2, Home, Leaf, Menu, Palette, Radar, Route as RouteIcon, Sparkles, Target, UserRound, X } from 'lucide-react';
import { Badge, Button, EmptyState, ErrorState, EvidenceBadge, GlassCard, LoadingSkeleton, PageHeader, SiteFooter } from './components';
import DesignPreview from './DesignPreview';
import UniverseLoading from './universe/UniverseLoading';
import { useProfile } from './profile-api';
import { MatchesPage, ProfilePage, ProfileSummaryCard } from './ProfilePages';
import { ToastProvider } from './toasts';
import { EvidenceOverview, RoleCatalogue, SDGExplorer } from './EvidencePages';
import { dateLabel, getEvidence, timeLabel, type Summary } from './evidence-api';

const UniversePage = lazy(() => import('./universe/CareerUniverse'));
const MyFuture = () => <FutureEntry><FuturePage/></FutureEntry>;
const CareerUniverse = () => <FutureEntry><UniversePage/></FutureEntry>;

const pages = [
  { path: '/', label: 'My Future', icon: Home },
  { path: '/universe', label: 'Career Universe', icon: Compass },
  { path: '/profile', label: 'My profile', icon: UserRound, title: 'Your next chapter starts with you.', description: 'A place for your experience, strengths, and ambitions.', empty: 'No profile yet', detail: 'Start with your experience and the skills you want to build. Intake is a preview for now; no personal information has been collected.' },
  { path: '/signals', label: 'Intelligence Radar', icon: Radar, title: 'See what’s shaping work.', description: 'Dated evidence on AI developments and labour-market shifts.', empty: 'Awaiting the first source refresh', detail: 'No sources have been ingested. Publication dates, retrieval dates, and last-successful refresh will appear with connected evidence.' },
  { path: '/forecast', label: 'Forecast', icon: ChartNoAxesCombined, title: 'Look ahead, with perspective.', description: 'Four-week sector demand forecasts, grounded in observed data.', empty: 'No trained forecast yet', detail: 'Forecasts require verified sector time series and time-valid evaluation. Geography, uncertainty, model version, and forecast timestamps will accompany every result.' },
  { path: '/matches', label: 'Role matches', icon: Target, title: 'Find where your strengths fit.', description: 'Explore future roles through the skills you bring and the skills you can build.', empty: 'No profile yet', detail: 'A profile will help connect your strengths to curated roles and explainable skill gaps. Role matching is not connected in this preview.' },
  { path: '/roadmap', label: 'My Pathway', icon: RouteIcon, title: 'Small steps. New possibilities.', description: 'Turn a skill gap into a practical reskilling pathway.', empty: 'No profile yet', detail: 'Your learning journey starts with your skills. Personalized pathways and saved progress are not connected in this preview.' },
  { path: '/sdgs', label: 'My Impact', icon: Globe2, title: 'Build skills with a bigger purpose.', description: 'Connect career pathways to applicable UN Sustainable Development Goals.', empty: 'Impact needs a clear connection', detail: 'Role and skill mappings will be linked to official UN goals and targets. No impact or endorsement is claimed at this stage.' },
  { path: '/model-lab', label: 'Model Lab', icon: FlaskConical, title: 'Understand the evidence behind it.', description: 'A transparent view of data, assumptions, and model evaluation.', empty: 'The lab is ready for its first experiment', detail: 'There are no trained models or evaluation metrics yet. Four-week forecasts and long-run scenario planning indices will be clearly distinguished.' },
];
const intakePath = '/profile/intake';
const needsProfile = ['/profile', '/matches', '/roadmap'];

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
function CompassIllustration() {
  return <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><span className="art-spark spark-one">✦</span><span className="art-spark spark-two">✧</span><div className="floating-tag tag-top"><span className="tag-icon"><Compass size={19}/></span> Find your direction</div><div className="compass-card"><div className="compass-face"><span className="north">N</span><span className="east">E</span><span className="south">S</span><span className="west">W</span><div className="compass-ring"/><div className="needle"/><div className="needle-pin"/></div></div><div className="floating-tag tag-bottom"><span className="tag-icon mint"><Leaf size={18}/></span> Grow into what’s next <Check size={14}/></div><div className="art-caption">A future full of possibilities</div></div>;
}
function IntelligenceStatus() {
  // API liveness never implies successful ingestion or a live signal feed.
  const query = useQuery({ queryKey: ['datasets'], queryFn: ({ signal }) => getEvidence<Summary>('/api/datasets/summary', 'sources', signal) });
  const run = query.data?.last_successful_imports.find(item => item.dataset === 'indeed-us-sectors');
  const imported = !!run && (query.data?.counts.job_demand_observations ?? 0) > 0;
  return <GlassCard className="intelligence-card"><div className="tile-heading"><span className="feature-icon aqua"><Radar size={23} aria-hidden="true"/></span><Badge>{imported ? 'Historical data' : 'Not connected'}</Badge></div><h3>Live intelligence</h3>{query.isPending ? <LoadingSkeleton label="Checking dataset imports"/> : query.isError ? <p className="tile-status">Evidence status unavailable</p> : <p className="tile-status">{imported ? 'US market history imported' : 'No data yet'}</p>}<p>Research findings and freshness are available in Intelligence Radar. {imported ? 'Dated US sector observations are available; these are historical indices, not a live posting feed.' : 'Historical market evidence appears only after a successful source import.'}</p><dl className="refresh-details"><div><dt>Last successful market import</dt><dd>{timeLabel(run?.completed_at ?? null)}</dd></div><div><dt>Observations through</dt><dd>{dateLabel(query.data?.end_date ?? null)}</dd></div></dl>{query.data?.last_attempt?.status === 'failed' && <p className="caption">Latest import failed. Showing last-successful data.</p>}<Link className="text-link" to="/datasets">View data & provenance <ArrowUpRight size={16} aria-hidden="true"/></Link></GlassCard>;
}
function Overview() {
  const journey = useProfile();
  return <>
    <div className="welcome-line"><span className="eyebrow">YOUR NEXT CHAPTER</span><EvidenceBadge>Your confirmed strengths</EvidenceBadge></div>
    <section className="hero" aria-labelledby="hero-title"><div className="hero-copy"><span className="hero-kicker"><Sparkles size={15} aria-hidden="true"/> A little clarity. A world of possibility.</span><h1 id="hero-title"><span className="hero-brand">Noka<span>.</span></span>Navigate tomorrow’s<br/>work, <em>today.</em></h1><p>The world of work is changing. Find your bearings, explore emerging possibilities, and build the skills to move forward.</p><Button asChild><Link to={journey.journeyPath}>Build My Future <ArrowRight size={18} aria-hidden="true"/></Link></Button><span className="hero-note">Your journey, informed by evidence.</span></div><CompassIllustration/></section>
    <section aria-labelledby="how-title"><div className="section-heading"><div><p className="eyebrow">FROM POSSIBILITY TO A PLAN</p><h2 id="how-title">How Noka works</h2></div><span className="muted">Three steps. Your own direction.</span></div><div className="journey-grid">{[
      { icon: Radar, color: 'mint', number: '01', title: 'Scout', text: 'Discover the signals shaping work, and put your strengths in context.', path: '/signals', link: 'Explore the signals' },
      { icon: Compass, color: 'blue', number: '02', title: 'Oracle', text: 'Explore sector outlooks and future roles, with evidence and assumptions in view.', path: '/forecast', link: 'Look ahead' },
      { icon: BookOpen, color: 'aqua', number: '03', title: 'Guide', text: 'Turn the skills you want to build into a practical path forward.', path: '/roadmap', link: 'Find your next step' },
    ].map(item => <GlassCard key={item.number} className="journey-card"><div className="card-top"><span className={`feature-icon ${item.color}`}><item.icon size={23} aria-hidden="true"/></span><span className="step-number">{item.number}</span></div><h3>{item.title}</h3><p>{item.text}</p><Link className="text-link" to={item.path}>{item.link}<ArrowUpRight size={16} aria-hidden="true"/></Link></GlassCard>)}</div></section>
    <section aria-labelledby="workspace-title"><div className="section-heading"><div><p className="eyebrow">A PLACE TO BEGIN</p><h2 id="workspace-title">Your future, taking shape.</h2></div><Badge tone="blue">Early preview</Badge></div><div className="dashboard-grid"><ProfileSummaryCard/><IntelligenceStatus/></div></section>
    <section className="module-section" aria-labelledby="module-title"><div className="section-heading"><div><p className="eyebrow">KEEP EXPLORING</p><h2 id="module-title">A wider view of what’s next.</h2></div></div><div className="module-grid">{[
      { path: '/matches', icon: Target, title: 'Role matches', description: 'Where your strengths could take you.' },
      { path: '/sdgs', icon: Globe2, title: 'SDG impact', description: 'Connect your growth to a bigger purpose.' },
      { path: '/model-lab', icon: FlaskConical, title: 'Model Lab', description: 'Understand the evidence and its limits.' },
    ].map(item => <Link className="module-link" key={item.path} to={item.path}><item.icon size={21} aria-hidden="true"/><div><h3>{item.title}</h3><p>{item.description}</p></div><ArrowUpRight size={17} aria-hidden="true"/></Link>)}</div></section>
    <div className="trust-line"><EvidenceBadge>Evidence before predictions</EvidenceBadge><span>Historical evidence is separate from live feeds. Evaluated forecasts and limitations are available in Model Lab.</span></div>
  </>;
}
function Shell() {
  const workspaceProfile=useProfile();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const main = useRef<HTMLElement>(null);
  const location = useLocation();
  const previousPath = useRef(location.pathname);
  const pageLabel = location.pathname === '/roles' ? 'Role catalogue' : location.pathname === '/datasets' ? 'Data provenance' : location.pathname === '/design-preview' ? 'Design gallery' : location.pathname === intakePath ? 'Profile intake' : pages.find(p => p.path === location.pathname)?.label ?? 'Not found';
  // Client navigation announces the new page through main focus; initial load stays untouched.
  useEffect(() => {
    setMenuOpen(false);
    document.title = `Noka — ${pageLabel}`;
    if (previousPath.current !== location.pathname) {
      main.current?.focus();
      window.scrollTo?.({ top: 0, behavior: 'instant' });
      previousPath.current = location.pathname;
    }
  }, [location.pathname, pageLabel]);
  useEffect(() => {
    if (!menuOpen) return;
    // The disclosed links precede the toggle in DOM order, so focus their first item.
    document.querySelector<HTMLAnchorElement>('#main-navigation nav a')?.focus();
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') { setMenuOpen(false); menuButton.current?.focus(); }
    }
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [menuOpen]);
  return <div className={`app ${location.pathname==='/'||location.pathname==='/universe'?'map-workspace':''}`}><a href="#main" className="skip-link">Skip to content</a>
    <aside id="main-navigation" className={`sidebar ${menuOpen ? 'is-open' : ''}`}><Link className="brand" to="/" aria-label="Noka home"><span className="brand-mark"><Compass size={24} aria-hidden="true"/></span>noka<span className="brand-dot">.</span></Link><p className="sidebar-caption">YOUR WORK. REIMAGINED.</p><nav aria-label="Main navigation" onClick={() => { if (menuOpen) { setMenuOpen(false); main.current?.focus(); } }}>{pages.filter(page => ['/', '/signals', '/roadmap', '/sdgs', '/profile', '/model-lab'].includes(page.path)).map(page => <NavLink key={page.path} to={page.path} end={page.path === '/'}><page.icon size={19} aria-hidden="true"/>{page.label}</NavLink>)}</nav><div className="sidebar-bottom"><Leaf size={22} aria-hidden="true"/><h2>Grow with purpose.</h2><p>Your next chapter starts here.</p><Link to="/sdgs">Explore SDG impact <ArrowUpRight size={14} aria-hidden="true"/></Link></div><NavLink onClick={() => { if (menuOpen) { setMenuOpen(false); main.current?.focus(); } }} className="gallery-nav" to="/design-preview"><Palette size={17} aria-hidden="true"/>Design gallery</NavLink><div className="sidebar-version">NOKA <span>PRIVATE WORKSPACE</span></div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb" aria-label="Breadcrumb"><Compass size={16} aria-hidden="true"/><Link to="/">Workspace</Link><ChevronRight size={13} aria-hidden="true"/><span aria-current="page">{pageLabel}</span></div><div className="topbar-right"><span className="preview-pill">{workspaceProfile.data?.profile?.is_demo ? "Demo workspace" : "Personal workspace"}</span><span className="avatar" aria-label="Guest workspace">N</span><button type="button" ref={menuButton} className="menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="main-navigation">{menuOpen ? <X/> : <Menu/>}</button></div></header>
      <main id="main" ref={main} tabIndex={-1}><WorldDial/><Routes><Route path="/" element={<MyFuture/>}/><Route path="/welcome" element={<Overview/>}/><Route path="/roadmap" element={<PathwayPage/>}/><Route path="/model-lab" element={<ModelLab/>}/><Route path="/forecast" element={<ModelLab/>}/><Route path="/universe" element={<Suspense fallback={<UniverseLoading/>}><CareerUniverse/></Suspense>}/><Route path={intakePath} element={<IntakeWizard/>}/><Route path="/design-preview" element={<DesignPreview/>}/><Route path="/datasets" element={<EvidenceOverview/>}/><Route path="/signals" element={<RadarPage/>}/><Route path="/matches" element={<MatchesPage/>}/><Route path="/roles" element={<RoleCatalogue/>}/><Route path="/profile" element={<ProfilePage/>}/><Route path="/sdgs" element={<ImpactPage/>}/><Route path="/goals" element={<SDGExplorer/>}/>{pages.slice(1).filter(page => !['/universe', '/profile', '/signals', '/matches', '/sdgs', '/roadmap', '/forecast', '/model-lab'].includes(page.path)).map(page => <Route key={page.path} path={page.path} element={<><PageHeader eyebrow="YOUR NOKA WORKSPACE" title={page.title!} description={page.description!}/><GlassCard><EmptyState title={page.empty!} action={needsProfile.includes(page.path) && <Button asChild><Link to={intakePath}>Explore profile intake <ArrowRight size={16} aria-hidden="true"/></Link></Button>}>{page.detail}</EmptyState></GlassCard></>}/>)}<Route path="*" element={<><PageHeader eyebrow="LET’S FIND YOUR WAY" title="This path doesn’t exist yet." description="Head back to your overview to keep exploring."/><Button asChild><Link to="/">Back to overview <ArrowRight size={16} aria-hidden="true"/></Link></Button></>}/></Routes><div className="system-line"><ServiceStatus/><span>Private by design · Original resumes not retained</span></div><SiteFooter/></main>
    </div>
  </div>;
}
export default function App() { return <WorkspaceBoundary><ToastProvider><Shell/></ToastProvider></WorkspaceBoundary>; }
