"""Idempotent candidate curation. Never fabricates human review or changes approved links."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database import engine
from backend.app.models import Role, SDGTarget, SDGLink

CANDIDATES = [
    ("29-1141.00","3.8","Nursing care can contribute to access to quality essential health services when practised in accessible care settings."),
    ("29-1051.00","3.8","Pharmacy responsibilities can support safe access to essential medicines; contribution depends on the service and population reached."),
    ("25-2031.00","4.1","Secondary-school teaching can contribute to effective learning outcomes within inclusive, quality education."),
    ("17-2081.00","6.3","Environmental engineering work on wastewater and pollution controls can support improved water quality."),
    ("17-2051.00","9.1","Civil infrastructure design can support reliable and resilient infrastructure when access and sustainability are explicit project goals."),
    ("13-1199.05","12.6","Sustainability specialists can help organisations adopt sustainable practices and report relevant sustainability information."),
    ("15-1212.00","16.6","Security analysis can support accountable institutions by protecting the integrity of information systems; institutional accountability also requires governance beyond security."),
    ("17-2112.00","9.4","Industrial engineering projects can support resource efficiency when upgrading industrial processes with sustainability objectives."),
]


def propose(db):
    added=0
    for role_id,target_id,rationale in CANDIDATES:
        role,target=db.get(Role,role_id),db.get(SDGTarget,target_id)
        if not role or not target: continue
        key=f"candidate:{role_id}:{target_id}"
        if db.scalar(select(SDGLink).where(SDGLink.role_id==role_id,SDGLink.target_id==target_id)): continue
        db.add(SDGLink(id=key,role_id=role_id,skill_id=None,target_id=target_id,
                      rationale=rationale,source_id=target.source_id,curation_status="pending_review",
                      reviewed_by=None,reviewed_at=None))
        added+=1
    db.commit()
    return added


if __name__=="__main__":
    with Session(engine) as db:
        print({"new_pending_candidates":propose(db),"human_approvals_created":0})
