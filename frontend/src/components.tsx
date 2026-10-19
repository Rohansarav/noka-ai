import type { ReactNode } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { ArrowUpRight, CircleDashed, ShieldCheck } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Shared shadcn-style button primitive keeps navigation and actions consistent.
export function Button({ children, asChild = false, className = '' }: { children: ReactNode; asChild?: boolean; className?: string }) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={twMerge(clsx('button', className))}>{children}</Comp>;
}
export function GlassCard({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`glass-card ${className}`}>{children}</section>; }
export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <header className="page-header"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></header>; }
export function EvidenceBadge({ children }: { children: ReactNode }) { return <span className="evidence-badge"><ShieldCheck size={14}/>{children}</span>; }
export function EmptyState({ title, children }: { title: string; children: ReactNode }) { return <div className="empty-state"><span className="empty-icon"><CircleDashed size={30}/></span><h2>{title}</h2><p>{children}</p><EvidenceBadge>Not connected yet</EvidenceBadge></div>; }
export function ErrorState({ message }: { message: string }) { return <p role="alert" className="error-state">{message}</p>; }
export function LoadingSkeleton() { return <div role="status" aria-label="Loading API status" className="skeleton"/>; }
export function SiteFooter() { return <footer><span>© {new Date().getFullYear()} Noka. A clearer path forward.</span><span>Built with purpose <ArrowUpRight size={13}/></span></footer>; }
