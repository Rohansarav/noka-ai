import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { ArrowUpRight, CircleAlert, CircleDashed, ShieldCheck, Compass } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Shared shadcn-style primitive gives links and buttons the same focus treatment.
export function Button({ children, asChild = false, className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={twMerge(clsx('button', className))} {...props}>{children}</Comp>;
}
export function GlassCard({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`glass-card ${className}`}>{children}</section>;
}
export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="page-header"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></header>;
}
export function EvidenceBadge({ children }: { children: ReactNode }) {
  return <span className="evidence-badge"><ShieldCheck size={14} aria-hidden="true"/>{children}</span>;
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'mint' | 'blue' | 'warning' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function EmptyState({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <div className="empty-state"><span className="empty-icon"><CircleDashed size={30} aria-hidden="true"/></span><h2>{title}</h2><p>{children}</p><EvidenceBadge>Not connected yet</EvidenceBadge>{action && <div className="empty-action">{action}</div>}</div>;
}
export function ErrorState({ message }: { message: string }) {
  return <div role="alert" className="error-state"><CircleAlert size={17} aria-hidden="true"/><p>{message}</p></div>;
}
export function LoadingSkeleton({ label = 'Loading API status' }: { label?: string }) {
  return <div role="status" aria-label={label} aria-busy="true" className="noka-wait"><span className="noka-wait-compass" aria-hidden="true"><Compass size={27}/></span><span>{label}<span className="noka-wait-line" aria-hidden="true"/></span></div>;
}
// Use only during an active operation; completion and errors have separate states.
export function ActivityStatus({ children }: { children: ReactNode }) {
  return <div className="activity-status" role="status" aria-live="polite" aria-busy="true"><span className="activity-spinner" aria-hidden="true"/><span>{children}</span></div>;
}
// A named native progress element exposes its value to assistive technology.
export function ProgressBar({ label, value }: { label: string; value: number }) {
  return <label className="progress-field"><span>{label}<strong>{value}%</strong></span><progress max={100} value={value}>{value}%</progress></label>;
}
export function SiteFooter() {
  return <footer><span>© {new Date().getFullYear()} Noka. A clearer path forward.</span><span>Built with purpose <ArrowUpRight size={13} aria-hidden="true"/></span></footer>;
}
