import { ActivityStatus } from './components';
import { useQuery } from '@tanstack/react-query';
import { api } from './future-api';
import type { Opportunity } from './OpportunityEvidence';

type Interpretation = {status:'suggestion'|'unavailable';label?:'emerging'|'transforming'|'uncertain';explanation?:string;source_ids?:string[];notice?:string;message?:string};

// Generation is explicitly requested; changing occupation/market cannot leak an old result.
export default function WorkChanges({row}:{row:Opportunity}) {
  const evidence=row.evidence.filter(c=>c.current&&c.dimension==='change'&&['emerging','transforming'].includes(c.category));
  if(row.dimensions.change?.status!=='supported'||!evidence.length)return null;
  return <WorkChangeExplanation key={row.role_id+row.market} row={row} evidence={evidence}/>;
}

function WorkChangeExplanation({row,evidence}:{row:Opportunity;evidence:Opportunity['evidence']}) {
  const q=useQuery({queryKey:['work-changes-v2',row.role_id,row.market,evidence],enabled:false,retry:false,
    queryFn:()=>api<Interpretation>(`/opportunities/roles/${encodeURIComponent(row.role_id)}/work-changes?market=${encodeURIComponent(row.market)}`,'POST')});
  const citations=evidence.filter(c=>q.data?.source_ids?.includes(c.id));
  const supported=q.data?.status==='suggestion'&&q.data.label!=='uncertain'&&!!q.data.explanation?.trim()&&citations.length===q.data.source_ids?.length&&citations.length>0;
  return <details className="work-change-card"><summary>How work could change <span>Understand the reviewed evidence</span></summary>
    <p>Explain the task and skill changes described in these sources. AI explanations remain unreviewed.</p>
    <button className="work-change-action" disabled={q.isFetching} onClick={()=>void q.refetch()}>{q.isFetching?'Preparing explanation…':q.data?'Refresh explanation':'Explain these work changes'}</button>
    {q.isFetching&&<ActivityStatus>Preparing your explanation…</ActivityStatus>}{q.isError&&<p role="alert">Interpretation unavailable. Please retry; a private session is required.</p>}
    {q.data?.status==='unavailable'&&<p role="status">{q.data.message}</p>}
    {q.data?.status==='suggestion'&&supported&&<section aria-label="Unreviewed AI explanation"><p className="suggestion-notice">AI explanation · pending human review</p><p>{q.data.explanation}</p></section>}
    {q.data?.status==='suggestion'&&!supported&&<p role="status">An explanation could not be generated from the available sources.</p>}
    {q.data&&<div aria-label="Work change sources">{evidence.map(c=><p key={c.id}><a href={c.source.url} target="_blank" rel="noreferrer">{c.source.title} ↗</a> · {c.market} · {c.observation_period}</p>)}</div>}
  </details>;
}
