import { Link } from 'react-router-dom';
export type Assessment = {required_count:number;recorded_count:number;unrecorded_count:number;evidence_completeness:number;assessed_proficiency:number|null;status:'complete'|'partial'|'unassessed';method:string};

/** Keep incomplete evidence visibly distinct from an assessment of ability. */
export default function ReadinessEvidence({assessment}:{assessment?:Assessment|null}) {
  if(!assessment)return null;
  return <section className="readiness-evidence" aria-label="Skill evidence breakdown"><strong>{assessment.status==='complete'?'All broad requirements recorded':assessment.status==='partial'?'Partial profile evidence':'Broad requirements not assessed'}</strong><p>{assessment.recorded_count} of {assessment.required_count} important requirements recorded · {assessment.unrecorded_count} unassessed.</p><dl><dt>Weighted evidence completeness</dt><dd>{assessment.evidence_completeness}%</dd><dt>Self-rated proficiency on recorded requirements</dt><dd>{assessment.assessed_proficiency===null?'Not assessed':assessment.assessed_proficiency+'%'}</dd></dl><p>Low documented coverage can mean missing information. It does not establish low ability or hiring readiness.</p><details><summary>How this number works</summary><p>{assessment.method}</p><p>Learning = 25%, working = 65%, strong = 100%. Published importance weights each requirement.</p></details><Link to="/profile/intake">Review my skills →</Link></section>;
}
