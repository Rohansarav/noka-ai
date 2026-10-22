"""Bounded scheduled research. External text is data; no LLM or privileged tool execution."""
import hashlib
import uuid
import re
from html.parser import HTMLParser
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.app.config import get_settings
from backend.app.models import IntelligenceRecord, Role, Skill

QUERIES = [
    ("MY", "Malaysia MyCOL 2024/2025 latest critical occupations DOSM workforce 2026", ["talentcorp.com.my", "dosm.gov.my", "open.dosm.gov.my"]),
    ("MY", "Malaysia artificial intelligence governance cybersecurity workforce skills latest", ["digital.gov.my", "mosti.gov.my", "nacsa.gov.my"]),
    ("Global", "latest AI model capabilities agents workplace automation", ["openai.com", "anthropic.com", "deepmind.google"]),
    ("Global", "Future of Jobs 2025 growing declining jobs skills", ["weforum.org"]),
]


def canonical(url):
    try:
        parsed=urlsplit(url)
        port=parsed.port
    except ValueError:
        return None
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password: return None
    if port not in (None,443): return None
    # Preserve publication identifiers; discard tracking and credential parameters.
    query=urlencode(sorted((key,value) for key,value in parse_qsl(parsed.query) if key.lower() in {'id','article_id','release_id','doc_id','p'}))
    return urlunsplit(("https",parsed.netloc,parsed.path.rstrip("/"),query,""))


class PublicationMetadata(HTMLParser):
    """Use explicit publisher metadata only; arbitrary dates in article prose are not publication dates."""
    def __init__(self):
        super().__init__(); self.date=None

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='meta' and (attrs.get('property') or attrs.get('name','')).lower() in {'article:published_time','datepublished','date','pubdate'}:
            value=attrs.get('content','')
            if re.match(r'^\d{4}-\d{2}-\d{2}',value): self.date=value[:10]


def publication_date(client,url):
    """Bound publisher inspection to 1 MiB and never follow redirects."""
    with client.stream('GET',url,headers={'User-Agent':'Noka research provenance/1.0'}) as response:
        if not response.is_success or 'text/html' not in response.headers.get('content-type',''): return None
        data=bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data)>1024*1024: return None
        parser=PublicationMetadata();parser.feed(data.decode('utf-8',errors='replace'))
        return parser.date


def refresh(bind):
    """At most four searches and one batch extraction. PostgreSQL lock prevents overlapping jobs."""
    now=datetime.now(timezone.utc)
    run_id=uuid.uuid4().hex
    run={"id":run_id,"started_at":now.isoformat(),"status":"running","events":[],"findings":0}
    with Session(bind) as db:
        if bind.dialect.name=="postgresql":
            if not db.scalar(text("SELECT pg_try_advisory_xact_lock(726625)")):
                return {"status":"already_running"}
        last=db.scalar(select(IntelligenceRecord).where(IntelligenceRecord.kind=="scout_run",IntelligenceRecord.created_at>now-timedelta(hours=1)))
        if last: return {"status":"rate_limited","message":"At most one scheduled refresh per hour."}
        settings=get_settings()
        from backend.app.market_evidence import load_evidence, import_bundle
        from backend.app.market_research import extract_proposals, proposal_bundle
        mappings=[m for m in load_evidence(db)['mappings'] if m['taxonomy'].startswith('MyCOL')]
        # Two rotating public occupations plus two global searches. No profile access.
        selected=[]
        if mappings:
            mappings.sort(key=lambda m:m['id'])
            start=(now.toordinal()*2)%len(mappings)
            selected=[mappings[(start+i)%len(mappings)] for i in range(min(2,len(mappings)))]
        queries=[('MY', 'Malaysia '+m['occupation_title']+' employment shortage emerging changing skills report', ['talentcorp.com.my','dosm.gov.my','open.dosm.gov.my']) for m in selected]+QUERIES[2:] if selected else QUERIES
        extracted={}
        run['proposals']=0
        run['proposal_status']='no_extracted_sources'
        try:
            if not settings.tavily_api_key:
                run["status"]="unavailable"
                run["error"]="Research credentials unavailable"
            else:
                headers={"Authorization":"Bearer "+settings.tavily_api_key.get_secret_value()}
                findings={}
                with httpx.Client(timeout=25,follow_redirects=False) as client:
                    for market,query,domains in queries:
                        result=client.post("https://api.tavily.com/search",headers=headers,json={
                            "query":query,"max_results":4,"include_domains":domains,"exclude_domains":["community.openai.com"],"time_range":"year","search_depth":"basic","include_raw_content":False})
                        result.raise_for_status()
                        run["events"].append({"type":"search_completed","query":query,"at":datetime.now(timezone.utc).isoformat()})
                        for item in result.json().get("results",[])[:4]:
                            url=canonical(item.get("url",""))
                            if not url or urlsplit(url).hostname=='community.openai.com' or not any(urlsplit(url).hostname==d or urlsplit(url).hostname.endswith("."+d) for d in domains): continue
                            fid=hashlib.sha256(url.encode()).hexdigest()
                            findings[fid]={"id":fid,"title":str(item.get("title","Source"))[:300],"url":url,
                                "market":market,"publication_date":item.get("published_date"),
                                "retrieved_at":now.isoformat(),"source_statement":str(item.get("content",""))[:1600],
                                "evidence_type":"Source discovery","quality":"Primary publisher; relevance needs review",
                                "review_status":"pending_review","inspection":"search excerpt","role_ids":[],"skill_ids":[],
                                "interpretation":"Discovery is not proof of changing employment demand.","research_window":"Past year requested; publication date must be inspected independently."}
                    if findings:
                        result=client.post("https://api.tavily.com/extract",headers=headers,json={"urls":[f["url"] for f in list(findings.values())[:5]],"extract_depth":"basic"})
                        if result.is_success:
                            for item in result.json().get("results",[]):
                                url=canonical(item.get("url",""))
                                fid=hashlib.sha256((url or "").encode()).hexdigest()
                                if fid in findings:
                                    findings[fid]["inspection"]="source content retrieved"
                                    # Keep bounded excerpts only. No source instructions are executed.
                                    findings[fid]["source_statement"]=str(item.get("raw_content",""))[:1600]
                                    extracted[fid]=str(item.get("raw_content",""))[:12000]
                            run["events"].append({"type":"extract_completed","at":datetime.now(timezone.utc).isoformat()})
                    for finding in list(findings.values())[:3]:
                        if finding['publication_date']: continue
                        try:
                            finding['publication_date']=publication_date(client,finding['url'])
                            if finding['publication_date']:
                                finding['publication_date_basis']='Publisher HTML metadata'
                        except httpx.HTTPError:
                            pass
                        run['events'].append({'type':'publisher_metadata_inspected','url':finding['url'],'at':datetime.now(timezone.utc).isoformat()})
                    # Extraction failure never erases prior evidence. At most two LLM calls.
                    if extracted and selected:
                        run['proposal_status']='unconfigured' if not settings.openai_api_key else 'completed'
                        for fid,content in list(extracted.items())[:2]:
                            if not settings.openai_api_key:break
                            try:
                                proposed=extract_proposals(content,selected,settings)
                                bundle=proposal_bundle(findings[fid],content,selected,proposed)
                                with db.begin_nested():
                                    result=import_bundle(db,bundle)
                                run['proposals']+=result['claims']
                            except Exception:
                                run['proposal_status']='partial_or_failed'
                                run['events'].append({'type':'proposal_validation_failed','at':datetime.now(timezone.utc).isoformat()})
                    roles=list(db.scalars(select(Role)))
                    skills=list(db.scalars(select(Skill)))
                    for fid,finding in findings.items():
                        content=(finding["title"]+" "+finding["source_statement"]).lower()
                        finding["role_ids"]=[r.id for r in roles if r.title.lower() in content]
                        finding["skill_ids"]=[s.id for s in skills if s.canonical_name.lower() in content]
                        db.merge(IntelligenceRecord(id=fid,kind="finding",payload=finding,created_at=now))
                    run["findings"]=len(findings)
                    run["status"]="succeeded"
        except Exception as exc:
            run["status"]="failed"
            run["error"]=type(exc).__name__  # Never persist keys, response bodies or request headers.
        run["completed_at"]=datetime.now(timezone.utc).isoformat()
        db.add(IntelligenceRecord(id=run_id,kind="scout_run",payload=run,created_at=now))
        db.commit()
    return run


if __name__=="__main__":
    import json
    from backend.app.database import engine
    result=refresh(engine)
    print(json.dumps(result,indent=2))
    if result["status"] in {"failed","unavailable"}: raise SystemExit(1)
