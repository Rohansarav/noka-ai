"""Read-only Phase 2 acceptance probe; never prints DATABASE_URL."""
import argparse
import json
import sys
from pathlib import Path
from sqlalchemy import func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.database import engine
from backend.app.models import DemandObservation, Role, RoleSkill, SDG, SDGLink, SDGTarget, Skill, Source


def verify(require_postgres: bool):
    if require_postgres and engine.dialect.name != "postgresql":
        raise ValueError("PostgreSQL acceptance requires a PostgreSQL DATABASE_URL.")
    with Session(engine) as session:
        counts = {m.__tablename__: session.scalar(select(func.count()).select_from(m)) for m in [DemandObservation, Role, Skill, RoleSkill, SDG, SDGTarget, SDGLink, Source]}
        expected = {"job_demand_observations":114821, "roles":25, "skills":35, "role_skills":875, "sdgs":17, "sdg_targets":169, "sdg_links":7}
        for name, count in expected.items():
            if counts[name] != count:
                raise ValueError("Unexpected verified-source count for " + name)
        first, last = session.execute(select(func.min(DemandObservation.date), func.max(DemandObservation.date))).one()
        if first.isoformat() != "2020-02-01" or last.isoformat() != "2026-10-09":
            raise ValueError("Unexpected observation range.")
        if session.scalar(select(func.count()).select_from(DemandObservation).outerjoin(Source, DemandObservation.source_id == Source.id).where(Source.id.is_(None))):
            raise ValueError("Missing observation source attribution.")
        if session.scalar(select(func.count()).select_from(SDGLink).where(SDGLink.curation_status != "human_reviewed")):
            raise ValueError("Human review remains outstanding.")
        return {"database":engine.dialect.name, "postgresql_acceptance":engine.dialect.name == "postgresql", "counts":counts, "first_observation":first.isoformat(), "last_observation":last.isoformat(), "status":"verified"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-postgres", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.require_postgres), indent=2))
    except ValueError as exc:
        # All ValueError messages here are fixed application strings, never provider text.
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print("Acceptance check failed (" + type(exc).__name__ + "). Check database access and migrations.", file=sys.stderr)
        sys.exit(1)
