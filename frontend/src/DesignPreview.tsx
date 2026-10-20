import { ArrowRight } from 'lucide-react';
import { Badge, Button, EmptyState, ErrorState, EvidenceBadge, GlassCard, LoadingSkeleton, PageHeader, ProgressBar } from './components';
import { useToast } from './toasts';

const colors = [
  ['Cream', '--color-cream', '#FAFBF7'], ['Mist mint', '--color-mint', '#E5F5E9'],
  ['Light aqua', '--color-aqua', '#DEF5F4'], ['Powder blue', '--color-powder', '#E3EEFF'],
  ['Dark ink', '--color-ink', '#183029'], ['Primary blue', '--color-primary', '#2979F5'],
];
export default function DesignPreview() {
  const notify = useToast();
  return <>
    <PageHeader eyebrow="NOKA DESIGN GALLERY" title="A little calm. A lot of clarity." description="The building blocks of Noka. All values below are visual examples, not profile or market results."/>
    <div className="gallery-grid">
      <GlassCard className="gallery-panel gallery-wide"><h2>Colour, with breathing room.</h2><p>Light surfaces, grounded text, and a bright sense of direction.</p><div className="swatch-grid">{colors.map(([name, token, hex]) => <div className="swatch" key={token}><div style={{ background: `var(${token})` }}/><strong>{name}</strong><code>{hex}</code></div>)}</div></GlassCard>
      <GlassCard className="gallery-panel"><h2>Typography</h2><div className="type-specimen"><span className="eyebrow">A CLEARER PATH FORWARD</span><p className="type-display">Your next chapter.</p><h3>Make space for possibility.</h3><p>Comfortable reading, simple language, and an optimistic outlook. System fonts keep every screen fast and familiar.</p><span className="caption">Caption · Source and retrieval dates belong beside evidence.</span></div></GlassCard>
      <GlassCard className="gallery-panel"><h2>Actions & notifications</h2><p>Keyboard focus stays visible. Notifications announce without moving focus.</p><div className="gallery-actions"><Button onClick={() => notify('Preview notification', 'This is a design-system example. Nothing was saved.')}>Show sample notification <ArrowRight size={16}/></Button><Button className="button-secondary" disabled>Unavailable action</Button></div><div className="badge-row"><Badge>Not connected</Badge><Badge tone="mint">Example badge</Badge><Badge tone="blue">Preview</Badge><Badge tone="warning">Awaiting evidence</Badge><EvidenceBadge>Source required</EvidenceBadge></div></GlassCard>
      <GlassCard className="gallery-panel"><h2>Progress, clearly labelled</h2><p>Component samples only. These values do not represent learning progress.</p><ProgressBar label="Example progress" value={40}/><ProgressBar label="Example empty progress" value={0}/></GlassCard>
      <GlassCard className="gallery-panel"><h2>Chart palette</h2><p>Use labels and line styles alongside colour. No market series is shown here.</p><ul className="chart-palette">{['Demand', 'Comparison', 'Scenario', 'Uncertainty'].map((name, index) => <li key={name}><span className={`chart-key chart-key-${index + 1}`}/>{name} <small>Example series</small></li>)}</ul></GlassCard>
      <GlassCard className="gallery-panel"><h2>Loading & error states</h2><p>Visual samples. No request is running or failing in this panel.</p><div className="loading-sample"><LoadingSkeleton label="Example loading state"/><LoadingSkeleton label="Example secondary loading state"/></div><ErrorState message="Example error: evidence is unavailable. Please try again later."/></GlassCard>
      <GlassCard className="gallery-panel"><h2>Soft gradients</h2><div className="gradient-sample gradient-scout"><strong>Scout</strong><span>Mint → aqua</span></div><div className="gradient-sample gradient-oracle"><strong>Oracle</strong><span>Aqua → powder blue</span></div><div className="gradient-sample gradient-guide"><strong>Guide</strong><span>Cream → mint</span></div></GlassCard>
      <GlassCard className="gallery-wide"><EmptyState title="Example empty state">A clear explanation, a useful next step, and no invented results. This is a component sample.</EmptyState></GlassCard>
    </div>
  </>;
}
