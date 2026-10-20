import { Compass } from 'lucide-react';
import './universe-loading.css';

export default function UniverseLoading() {
  return <div className="universe-forming universe-canvas" aria-busy="true">
    <div className="forming-map" aria-hidden="true"><svg viewBox="0 0 500 300"><path d="M80 70 Q250 50 250 150 T420 240 M80 240 Q200 290 250 150 T420 70 M130 150 Q250 20 370 150"/></svg><span className="forming-compass"><Compass size={42}/></span>{Array.from({length: 8}, (_, i) => <i key={i} className={`forming-dot forming-dot-${i}`}/>)}</div>
    <div role="status" aria-label="Loading your career connections"><p className="eyebrow">A LITTLE SPACE FOR POSSIBILITY</p><h2>Your Universe is taking shape.</h2><p>Your saved connections will appear as soon as they’re available.</p></div>
    <details><summary>What will I discover?</summary><p>Your confirmed skills, roles ranked by heuristic skill fit, priority gaps and any existing human-reviewed SDG connections. A sparse profile may have fewer connections.</p></details>
  </div>;
}
