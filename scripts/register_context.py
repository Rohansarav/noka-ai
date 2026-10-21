"""Source-checked background context, separate from autonomous Scout execution claims."""
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.database import engine
from backend.app.models import IntelligenceRecord

CONTEXT=[
    {"title":"Malaysia opens engagement on a proposed AI governance bill","url":"https://www.digital.gov.my/en-GB/siaran/Kementerian-Digital-Mulakan-Libat-Urus-Cadangan-Rang-Undang-Undang-Tadbir-Urus-Kecerdasan-Buatan-(AI)","market":"MY","publication_date":"2026-07-10","source_statement":"Malaysia's Ministry of Digital announced stakeholder engagement on a proposed AI Governance Bill. The release describes a risk-based lifecycle approach and consultation; it does not establish that the bill is enacted.","interpretation":"Governance and evaluation are relevant planning considerations. This announcement does not quantify hiring demand or establish new legal obligations."},
    {"title":"Enterprise AI moves toward connected agent workflows","url":"https://openai.com/index/next-phase-of-enterprise-ai","market":"Global","publication_date":"2026-04-08","source_statement":"OpenAI described its enterprise strategy around agents working across business systems and employees' daily workflows.","interpretation":"Vendor-reported direction supports exploring systems integration and human oversight. It is not an independent capability benchmark or measured employment forecast."},
    {"title":"MyCOL identifies Malaysian occupational shortages","url":"https://www.talentcorp.com.my/mycol","market":"MY","publication_date":None,"source_statement":"TalentCorp describes MyCOL as employer-informed research identifying occupations where demand exceeds talent supply. Its current publication collection includes the 2024/2025 edition.","interpretation":"Locally relevant workforce context. A shortage list is not a time-series growth forecast, and specific Noka role crosswalks require separate review."},
]


def register(db):
    now=datetime.now(timezone.utc)
    for source in CONTEXT:
        record={**source,"id":hashlib.sha256(("context:"+source['url']).encode()).hexdigest(),
            "retrieved_at":now.isoformat(),"evidence_type":"Source-checked context",
            "quality":"Original publisher; vendor claims are identified","review_status":"Source checked during build; mappings not approved",
            "inspection":"Original source inspected during build; separate from Scout run events",
            "role_ids":(["15-1211.00","15-1212.00"] if source["market"]=="MY" and source["publication_date"] else ["15-1252.00","15-1211.00"] if source["market"]=="Global" else []),"skill_ids":(["2.B.4.h","2.B.4.e"] if source["market"]=="MY" and source["publication_date"] else ["2.B.3.e","2.B.4.g"] if source["market"]=="Global" else []),"mapping_method":"Possible responsibility/skill relevance inferred during build; pending review, not evidence of employment growth.","publication_date_basis":"Visible publisher dateline" if source['publication_date'] else "Unknown"}
        db.merge(IntelligenceRecord(id=record['id'],kind='context',payload=record,created_at=now))
    db.commit()
    return len(CONTEXT)


if __name__=='__main__':
    with Session(engine) as db: print({'source_checked_context_records':register(db)})
