"""Atomic, repeatable imports for the verified Phase 2 sources."""
import hashlib
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session
from backend.app.models import DemandObservation, IngestionRun, Role, RoleSkill, SDG, SDGLink, SDGTarget, Skill, Source, StructuralDirection
from backend.app.ingestion.parsers import DataValidationError, parse_indeed, parse_onet, parse_un
from backend.app.ingestion.sources import INDEED_VERSION, UN_URL, URLS, WEF_URL, download_sources

log = logging.getLogger("noka.ingestion")
ROOT = Path(__file__).resolve().parents[3]


def curation_fingerprint(curation: dict):
    payload = {"roles": [{k: r[k] for k in ["occupation_code", "sector", "rationale"]} for r in curation["roles"]],
               "sdg_links": curation["sdg_links"], "wef_directions": curation["wef_directions"]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def upsert(session: Session, model, rows: list[dict]):
    """Use database-native conflict handling, with bounded parameter batches."""
    if not rows:
        return
    table = model.__table__
    insert = pg_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
    batch_size = 2000 if session.bind.dialect.name == "postgresql" else 500
    keys = [c.name for c in table.primary_key]
    log.info("upsert_start table=%s rows=%d", table.name, len(rows))
    for offset in range(0, len(rows), batch_size):
        statement = insert(table).values(rows[offset:offset + batch_size])
        updates = {c.name: getattr(statement.excluded, c.name) for c in table.columns if c.name not in keys}
        session.execute(statement.on_conflict_do_update(index_elements=keys, set_=updates))
        if len(rows) > 10000 and (offset % 10000 == 0 or offset + batch_size >= len(rows)):
            log.info("upsert_progress table=%s processed=%d total=%d", table.name, min(offset + batch_size, len(rows)), len(rows))


def source_row(name: str, manifest: dict, *, dataset: str, title: str, publisher: str, version: str, license: str, license_url: str, geography: str, granularity: str, canonical_url: str, notes: str, publication_date: date | None = None):
    m = manifest[name]
    return {"id": hashlib.sha256((dataset + m["sha256"]).encode()).hexdigest()[:40], "dataset": dataset, "title": title, "publisher": publisher,
            "canonical_url": canonical_url, "file_url": m["url"], "publication_date": publication_date, "retrieved_at": datetime.fromisoformat(m["retrieved_at"]),
            "version": version, "sha256": m["sha256"], "license": license, "license_url": license_url, "geography": geography, "granularity": granularity,
            "notes": notes + (" REAL-ROW FIXTURE SUBSET; not the complete upstream dataset. Parent SHA-256: " + m["parent_sha256"] if m.get("is_subset") else "")}


def prepare(directory: Path, manifest: dict, curation_path: Path):
    """Validate every source and crosswalk before any database writes."""
    read = lambda name: (directory / name).read_bytes()
    observations, skipped = parse_indeed(read("indeed.csv"))
    goals, targets = parse_un(read("un-goals.json"))
    curation = json.loads(curation_path.read_text(encoding="utf8"))
    roles, skills, role_skills = parse_onet(read("occupation_data.csv"), {"essential": read("essential_skills.csv"), "transferable": read("transferable_skills.csv")}, curation["roles"], {r["sector"] for r in observations})
    # Approval is bound to the reviewed content; later edits cannot inherit it.
    reviewed = curation.get("reviewed_by") and curation.get("reviewed_at") and curation.get("reviewed_content_sha256") == curation_fingerprint(curation)
    status = "human_reviewed" if reviewed else "pending_human_review"
    # WEF is a reviewed reference document, not a time-series download. Its
    # verified PDF retrieval/checksum is retained without redistributing the PDF.
    manifest = {**manifest, "wef-reference": json.loads((ROOT / "data/curation/wef_source.json").read_text(encoding="utf8"))}
    sources = [source_row("indeed.csv", manifest, dataset="indeed-us-sectors", title="Indeed US sector total-posting index", publisher="Indeed Hiring Lab", version=INDEED_VERSION, license="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/", geography="US", granularity="occupational sector / daily", canonical_url="https://github.com/hiring-lab/job_postings_tracker", notes="Seasonally adjusted, seven-day trailing average, 2020-02-01=100. Total postings only. Historical revisions; no vintage backtest claims.")]
    for name, dataset, title in [("occupation_data.csv", "onet-occupations", "O*NET 31.0 occupations"), ("essential_skills.csv", "onet-essential", "O*NET 31.0 essential skills"), ("transferable_skills.csv", "onet-transferable", "O*NET 31.0 transferable skills")]:
        sources.append(source_row(name, manifest, dataset=dataset, title=title, publisher="USDOL/ETA, National Center for O*NET Development", version="31.0", license="CC BY 4.0", license_url="https://www.onetcenter.org/license_db.html", geography="US", granularity="occupation / skill", canonical_url="https://www.onetcenter.org/database.html", notes="All source occupations with compatible skill evidence; sector crosswalks remain limited to reviewed selections. Importance uses original 1–5 IM scale, not skill-demand probabilities. Empty aliases mean no verified aliases imported. Crosswalk/SDG additions are Noka judgements; USDOL/ETA has not endorsed these modifications."))
    sources.append(source_row("un-goals.json", manifest, dataset="un-sdgs", title="Official UN SDG goals and targets", publisher="United Nations Statistics Division", version="API snapshot " + manifest["un-goals.json"]["sha256"][:12], license="UN terms of use; no CC licence asserted", license_url="https://www.un.org/en/about-us/terms-of-use", geography="Global", granularity="17 goals / 169 targets", canonical_url="https://sdgs.un.org/goals", publication_date=date(2015, 9, 25), notes="Official API title fields are retained verbatim; nested indicator/series data is not imported. Original agenda adoption date is distinct from API retrieval date. Reference-only UN text; no UN logos or endorsement. Review UN terms before commercial redistribution."))
    sources.append(source_row("wef-reference", manifest, dataset="wef-context", title="The Future of Jobs Report 2025", publisher="World Economic Forum", version="2025 report", license="WEF copyright; short attributed paraphrases only", license_url="https://www.weforum.org/about/privacy-and-terms-of-use/", geography="Global (employer survey)", granularity="structural role/skill context", canonical_url=WEF_URL, publication_date=date(2025, 1, 7), notes="Manually curated qualitative context for 2025–2030, subject to recorded human review. Official PDF retrieval/checksum recorded; full PDF is not redistributed. No WEF numeric forecasts are used or treated as model outputs."))
    by_dataset = {s["dataset"]: s["id"] for s in sources}
    for r in observations:
        r["source_id"] = by_dataset["indeed-us-sectors"]
    for r in roles:
        r.update(source_id=by_dataset["onet-occupations"], curation_status=status if r['curation_status'] != 'source_imported' else 'source_imported')
    for r in skills:
        r["source_id"] = by_dataset["onet-" + r["category"]]
    for r in role_skills:
        r["source_id"] = by_dataset["onet-" + r.pop("category")]
    for r in goals + targets:
        r["source_id"] = by_dataset["un-sdgs"]
    role_ids, skill_ids, target_ids = {r["id"] for r in roles}, {r["id"] for r in skills}, {r["id"] for r in targets}
    sdg_links = []
    for r in curation["sdg_links"]:
        if r["target_id"] not in target_ids or (r.get("role_id") and r["role_id"] not in role_ids) or (r.get("skill_id") and r["skill_id"] not in skill_ids) or bool(r.get("role_id")) == bool(r.get("skill_id")):
            raise DataValidationError("Curation contains an invalid role/skill/target reference.")
        identity = (r.get("role_id") or r["skill_id"]) + ":" + r["target_id"]
        sdg_links.append({**r, "id": hashlib.sha256(identity.encode()).hexdigest()[:40], "role_id": r.get("role_id"), "skill_id": r.get("skill_id"), "source_id": by_dataset["un-sdgs"], "curation_status": status, "reviewed_by": curation.get("reviewed_by") if reviewed else None, "reviewed_at": datetime.fromisoformat(curation["reviewed_at"]) if reviewed else None})
    directions = [{**r, "horizon": "2025–2030", "source_id": by_dataset["wef-context"], "curation_status": status} for r in curation["wef_directions"]]
    batches = [(Source, sources), (Role, roles), (Skill, skills), (RoleSkill, role_skills), (DemandObservation, observations), (SDG, goals), (SDGTarget, targets), (SDGLink, sdg_links), (StructuralDirection, directions)]
    counts = {model.__tablename__: len(rows) for model, rows in batches}
    return batches, {"counts": counts, "skipped_new_posting_rows": skipped, "first_date": min(r["date"] for r in observations).isoformat(), "last_date": max(r["date"] for r in observations).isoformat(), "curation_status": status}


def import_all(engine, directory: Path, *, offline: bool = False, dry_run: bool = False, curation_path: Path = ROOT / "data/curation/catalogue.json"):
    started = datetime.now(timezone.utc)
    try:
        manifest = download_sources(directory, offline=offline)
        batches, summary = prepare(directory, manifest, curation_path)
        if dry_run:
            log.info("dry_run validated=%s dates=%s..%s", summary["counts"], summary["first_date"], summary["last_date"])
            return {"dry_run": True, **summary}
        # One transaction prevents a source refresh from exposing half an ontology.
        with Session(engine) as session, session.begin():
            for model, rows in batches:
                upsert(session, model, rows)
            for dataset in ["indeed-us-sectors", "onet-catalogue", "un-sdgs", "wef-context"]:
                session.add(IngestionRun(id=uuid4().hex, dataset=dataset, started_at=started, completed_at=datetime.now(timezone.utc), status="success", row_count={"indeed-us-sectors": summary["counts"]["job_demand_observations"], "onet-catalogue": summary["counts"]["roles"], "un-sdgs": 17, "wef-context": len(batches[-1][1])}[dataset], message="Validated atomic public-source import; " + summary["curation_status"]))
        log.info("import_success counts=%s dates=%s..%s", summary["counts"], summary["first_date"], summary["last_date"])
        from backend.app.occupation_catalogue import invalidate_catalogue
        invalidate_catalogue(engine)
        return {"dry_run": False, **summary}
    except Exception as exc:
        # Failure status is committed separately; previous successful rows survive.
        if not dry_run:
            with Session(engine) as session, session.begin():
                session.add(IngestionRun(id=uuid4().hex, dataset="phase2-bundle", started_at=started, completed_at=datetime.now(timezone.utc), status="failed", row_count=0, message="Import rejected: " + type(exc).__name__))
        log.error("import_failed error_type=%s; last-successful data preserved", type(exc).__name__)
        raise
