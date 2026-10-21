"""Source-bound qualitative outlooks. Never extrapolate US indices to Malaysia."""
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.models import Role, Skill, IntelligenceRecord

JOBS="https://www.weforum.org/publications/the-future-of-jobs-report-2025/2-jobs-outlook"
SKILLS="https://www.weforum.org/publications/the-future-of-jobs-report-2025/3-skills-outlook"
# Explicit, inspectable crosswalks. No fuzzy model-generated classifications.
ROLE_EVIDENCE={
    "15-1252.00":("growing","Software and applications developers feature in the employer survey's expected growth groups."),
    "15-1212.00":("growing","Information security analysts appear among the expected fastest-growing occupations."),
    "17-2081.00":("growing","Environmental engineers feature among the expected fastest-growing occupations."),
    "29-1141.00":("growing","Nursing professionals are expected to expand; this is a broader group than registered nurses."),
    "25-2031.00":("growing","Secondary education teachers are among expected large job creators."),
    "13-2011.00":("declining","Accountants and auditors appear in the survey's expected declining groups. This does not mean obsolete."),
}
SKILL_EVIDENCE={
    "Reading Comprehension":("declining","The broader reading, writing and mathematics group has a small anticipated net decline in relative importance, while remaining foundational."),
    "Writing":("declining","The broader reading, writing and mathematics group has a small anticipated net decline in relative importance, while remaining foundational."),
    "Mathematics":("declining","The broader reading, writing and mathematics group has a small anticipated net decline in relative importance, while remaining foundational."),
    "Programming":("transforming","Employers associate technology with both growth and decline in programming use; net importance is comparatively stable."),
    "Quality Control Analysis":("stable","Quality control is among the comparatively stable future skill groups; O*NET analysis is a narrower interpretation."),
    "Active Learning":("growing","Curiosity and lifelong learning are expected to rise. Active learning is an explicitly narrower O*NET crosswalk."),
}
METHOD="Exact, versioned canonical crosswalk to dated WEF employer-survey statements. Qualitative categories; no probability. Broader source groups are labelled. Absent directional evidence returns insufficient evidence. Scout discoveries do not automatically promote classifications."


def refresh_outlooks(db):
    now=datetime.now(timezone.utc)
    count=0
    for kind,entities,mapping in (("role",db.scalars(select(Role)).all(),ROLE_EVIDENCE),("skill",db.scalars(select(Skill)).all(),SKILL_EVIDENCE)):
        for entity in entities:
            name=entity.title if kind=="role" else entity.canonical_name
            evidence=mapping.get(entity.id if kind=="role" else name)
            payload={"entity_id":entity.id,"entity_type":kind,"name":name,
                "category":evidence[0] if evidence else "insufficient_evidence",
                "market":"Global","local_market":"MY","local_category":"insufficient_evidence",
                "method":METHOD,"version":"outlook-wef-2025-v1","generated_at":now.isoformat(),
                "evidence_type":"Evidence-based outlook","review_status":"AI-authored crosswalk; pending human review",
                "explanation":evidence[1] if evidence else "No mapped, dated directional evidence is available for this canonical entity.",
                "sources":[{"url":JOBS if kind=="role" else SKILLS,"publication_date":"2025-01-07","retrieved_at":now.isoformat(),"horizon":"2025–2030","publisher":"World Economic Forum"}] if evidence else [],
                "conflicts":"No conflicting source has been systematically reviewed; absence of listed conflict is not consensus."}
            db.merge(IntelligenceRecord(id=hashlib.sha256(f"outlook:{kind}:{entity.id}".encode()).hexdigest(),kind="outlook",payload=payload,created_at=now))
            count+=1
    db.commit()
    return count


if __name__=="__main__":
    from sqlalchemy.orm import Session
    from backend.app.database import engine
    with Session(engine) as db:
        print({"persisted_outlooks":refresh_outlooks(db)})
