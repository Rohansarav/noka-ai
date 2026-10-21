"""Strict parsing of verified public source schemas. No synthetic filling."""
import csv
import io
import json
import math
from datetime import date

INDEED_HEADERS = {"date", "jobcountry", "indeed_job_postings_index", "variable", "display_name"}
ONET_SKILL_HEADERS = {"O*NET-SOC Code", "Element ID", "Element Name", "Scale ID", "Data Value", "Recommend Suppress"}


class DataValidationError(ValueError):
    pass


def csv_rows(content: bytes, required: set[str], *, exact: bool = False):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    actual = set(reader.fieldnames or [])
    if not required <= actual or (exact and actual != required):
        raise DataValidationError("Source column schema changed; import rejected.")
    for row in reader:
        if None in row or any(row.get(key) is None for key in required):
            raise DataValidationError("Malformed source row.")
        yield row


def parse_indeed(content: bytes):
    """Keep US seasonally adjusted TOTAL indices; reject missing/conflicting data."""
    records = {}
    skipped_new = 0
    for row in csv_rows(content, INDEED_HEADERS, exact=True):
        if row["jobcountry"] != "US" or not row["display_name"].strip():
            raise DataValidationError("Unexpected country or empty sector.")
        if row["variable"] not in {"new postings", "total postings"}:
            raise DataValidationError("Unexpected postings variable.")
        try:
            day = date.fromisoformat(row["date"])
            value = float(row["indeed_job_postings_index"])
        except (ValueError, TypeError):
            raise DataValidationError("Missing/invalid observation date or index.") from None
        if not math.isfinite(value) or value < 0 or day < date(2020, 2, 1) or day > date.today():
            raise DataValidationError("Out-of-range observation.")
        if row["variable"] == "new postings":
            skipped_new += 1
            continue
        key = (row["display_name"], day)
        if key in records and records[key]["indexed_value"] != value:
            raise DataValidationError("Conflicting duplicate observation.")
        records[key] = {"country": "US", "sector": key[0], "date": day, "indexed_value": value, "adjusted_flag": True}
    if not records:
        raise DataValidationError("No total-posting observations.")
    return sorted(records.values(), key=lambda r: (r["sector"], r["date"])), skipped_new


def parse_un(content: bytes):
    goals = json.loads(content)
    if not isinstance(goals, list) or {str(g.get("code")) for g in goals} != {str(i) for i in range(1, 18)} or len(goals) != 17:
        raise DataValidationError("Expected all 17 official goals.")
    goal_rows, targets = [], {}
    for g in goals:
        if not g.get("title"):
            raise DataValidationError("Missing goal title.")
        goal_rows.append({"id": int(g["code"]), "title": g["title"], "description": g.get("description") or g["title"]})
        for t in g.get("targets", []):
            code, text = t.get("code", ""), t.get("title", "")
            if not code.startswith(str(g["code"]) + ".") or not text or code in targets:
                raise DataValidationError("Invalid or duplicate official target.")
            targets[code] = {"id": code, "goal_id": int(g["code"]), "description": text}
    if len(targets) != 169:
        raise DataValidationError("Expected 169 official targets; schema requires review.")
    return goal_rows, list(targets.values())


def parse_onet(occupations: bytes, skill_files: dict[str, bytes], crosswalk: list[dict], sectors: set[str]):
    occupation_rows = {r["O*NET-SOC Code"]: r for r in csv_rows(occupations, {"O*NET-SOC Code", "Title", "Description"}, exact=True)}
    roles, skills, links = [], {}, {}
    codes = [item["occupation_code"] for item in crosswalk]
    if len(codes) != len(set(codes)):
        raise DataValidationError("Curated occupations must be unique.")
    # Import source occupations independently of optional, human-reviewed sector proxies.
    curated = {item['occupation_code']: item for item in crosswalk}
    for code in occupation_rows:
        if code not in curated:
            crosswalk = [*crosswalk, {"occupation_code":code, "sector":None,
                "rationale":"Source occupation; no reviewed sector forecast crosswalk.", "curation_status":"source_imported"}]
    codes = [item['occupation_code'] for item in crosswalk]
    for item in crosswalk:
        code = item["occupation_code"]
        if code not in occupation_rows or (item["sector"] is not None and item["sector"] not in sectors):
            raise DataValidationError("Invalid occupation or crosswalk sector.")
        if not item.get("rationale"):
            raise DataValidationError("Crosswalk judgement must be documented.")
        r = occupation_rows[code]
        roles.append({"id": code, "title": r["Title"], "description": r["Description"], "occupation_code": code,
                      "country": "US", "sector": item["sector"], "crosswalk_rationale": item["rationale"],
                      "evidence_status": "sector_proxy_only" if item["sector"] else "not_covered",
                      "curation_status": item.get("curation_status", "pending_human_review")})
    for category, content in skill_files.items():
        for r in csv_rows(content, ONET_SKILL_HEADERS):
            code = r["O*NET-SOC Code"]
            if code not in codes or r["Scale ID"] != "IM" or r["Recommend Suppress"] == "Y":
                continue
            try:
                value = float(r["Data Value"])
            except (ValueError, TypeError):
                raise DataValidationError("Missing O*NET importance rating.") from None
            if not math.isfinite(value) or not 1 <= value <= 5 or not r["Element ID"] or not r["Element Name"]:
                raise DataValidationError("Invalid O*NET skill rating or identity.")
            sid = r["Element ID"]
            skills[sid] = {"id": sid, "canonical_name": r["Element Name"], "aliases": [], "category": category}
            key = (code, sid)
            if key in links and links[key]["required_importance"] != value:
                raise DataValidationError("Conflicting O*NET rating.")
            links[key] = {"role_id": code, "skill_id": sid, "required_importance": value, "category": category}
    supported = {link['role_id'] for link in links.values()}
    if any(code not in supported for code in curated):
        raise DataValidationError("Curated role has no compatible O*NET skill mapping.")
    # Occupations without published compatible skill evidence cannot be scored.
    return [role for role in roles if role['id'] in supported], list(skills.values()), list(links.values())
