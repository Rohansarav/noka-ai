import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Info, X } from 'lucide-react';

type Notice = { id: number; title: string; message: string };
const ToastContext = createContext<((title: string, message: string) => void) | null>(null);
export function useToast() {
  const notify = useContext(ToastContext);
  if (!notify) throw new Error('ToastProvider is required');
  return notify;
}
function Toast({ notice, dismiss }: { notice: Notice; dismiss: (id: number) => void }) {
  const [paused, setPaused] = useState(false);
  // Give readers a fresh timeout after hovering/focusing; never steal focus.
  useEffect(() => {
    if (paused) return;
    const timeout = setTimeout(() => dismiss(notice.id), 8000);
    return () => clearTimeout(timeout);
  }, [paused, dismiss, notice.id]);
  return <div className="toast" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false); }}>
    <Info size={20} aria-hidden="true"/><div><strong>{notice.title}</strong><p>{notice.message}</p></div><button type="button" className="icon-button" onClick={() => dismiss(notice.id)} aria-label={`Dismiss ${notice.title}`}><X size={18}/></button>
  </div>;
}
export function ToastProvider({ children }: { children: ReactNode }) {
  const [notices, setNotices] = useState<Notice[]>([]);
  const sequence = useRef(0);
  const dismiss = useRef((id: number) => setNotices(current => current.filter(notice => notice.id !== id))).current;
  function notify(title: string, message: string) {
    setNotices(current => [...current.slice(-2), { id: ++sequence.current, title, message }]);
  }
  return <ToastContext.Provider value={notify}>{children}<div className="toast-region" role="region" aria-label="Notifications" aria-live="polite" aria-relevant="additions">{notices.map(notice => <Toast key={notice.id} notice={notice} dismiss={dismiss}/>)}</div></ToastContext.Provider>;
}
