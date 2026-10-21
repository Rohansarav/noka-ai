"""Expand only occupational evidence from the verified cache; do not refresh demand data."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database import engine
from backend.app.models import Role, RoleSkill, Skill, Source
from backend.app.ingestion.sources import URLS
from backend.app.ingestion.parsers import parse_onet
from backend.app.ingestion.runner import ROOT, curation_fingerprint, upsert


def import_careers(database, directory):
    manifest = json.loads((directory/'manifest.json').read_text())
    files = ['occupation_data.csv','essential_skills.csv','transferable_skills.csv']
    for name in files:
        if manifest[name]['url'] != URLS[name] or hashlib.sha256((directory/name).read_bytes()).hexdigest() != manifest[name]['sha256']:
            raise ValueError('Public career cache failed origin/checksum validation.')
    curation = json.loads((ROOT/'data/curation/catalogue.json').read_text())
    roles, skills, links = parse_onet((directory/files[0]).read_bytes(),
        {'essential':(directory/files[1]).read_bytes(),'transferable':(directory/files[2]).read_bytes()},
        curation['roles'], {r['sector'] for r in curation['roles'] if r['sector']})
    reviewed = bool(curation.get('reviewed_by') and curation.get('reviewed_at') and curation.get('reviewed_content_sha256') == curation_fingerprint(curation))
    with Session(database) as db, db.begin():
        sources = {}
        for name,dataset in zip(files,['onet-occupations','onet-essential','onet-transferable']):
            source = db.scalar(select(Source).where(Source.dataset == dataset, Source.sha256 == manifest[name]['sha256']))
            if not source:
                raise ValueError('Import the verified baseline sources before expanding careers.')
            sources[dataset] = source.id
            source.notes = 'All source occupations with compatible importance ratings. Sector proxies exist only for reviewed crosswalks. No local vacancy or specialty-level equivalence is inferred.'
        for role in roles:
            role['source_id'] = sources['onet-occupations']
            if role['curation_status'] != 'source_imported':
                role['curation_status'] = 'human_reviewed' if reviewed else 'pending_human_review'
        for skill in skills:
            skill['source_id'] = sources['onet-'+skill['category']]
        for link in links:
            link['source_id'] = sources['onet-'+link.pop('category')]
        upsert(db,Role,roles)
        upsert(db,Skill,skills)
        upsert(db,RoleSkill,links)
    from backend.app.occupation_catalogue import invalidate_catalogue
    invalidate_catalogue(database)
    return {'roles':len(roles),'skills':len(skills),'requirements':len(links),'source':'verified O*NET cache'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=ROOT/'data/raw')
    args=parser.parse_args()
    try:
        print(json.dumps(import_careers(engine,args.directory)))
    except Exception as exc:
        print('Career import stopped: '+type(exc).__name__,file=sys.stderr)
        sys.exit(1)
