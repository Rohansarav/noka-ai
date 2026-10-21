"""Verified O*NET software imports; aliases are Noka search aids, never broad-skill credit."""
import csv
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models import Role, RoleTechnology, Skill, Source
from backend.app.ingestion.runner import upsert
from backend.app.ingestion.sources import ONET_ROOT

SOFTWARE_URL = ONET_ROOT+'software_skills.csv'
HEADER = {'O*NET-SOC Code','Title','Workplace Example','Element ID','Element Name','Hot Technology','In Demand'}
# Exact spelling aids only. They do not establish skill equivalence or proficiency.
SEARCH_ALIASES = {'python':['python programming'], 'javascript':['js'], 'structured query language sql':['sql'],
    'microsoft excel':['excel'], 'hypertext markup language html':['html'], 'cascading style sheets css':['css'],
    'react':['react.js','reactjs'], 'node.js':['nodejs'], 'r':['r language','r programming']}


def parse_software(raw, role_ids, broad_names=()):
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if set(reader.fieldnames or []) != HEADER:
        raise ValueError('Unsupported software source schema.')
    concepts,links={},{}
    broad={name.casefold() for name in broad_names}
    for row in reader:
        if row['Hot Technology'] not in {'Y','N'} or row['In Demand'] not in {'Y','N'}:
            raise ValueError('Invalid source software flag.')
        if row['O*NET-SOC Code'] not in role_ids:
            continue
        name=' '.join(row['Workplace Example'].split())
        if not name or len(name)>150 or not row['Element ID'] or not row['Element Name']:
            raise ValueError('Invalid software identity.')
        normalized=name.casefold()
        if normalized in broad:
            continue
        sid='tech:'+hashlib.sha256(normalized.encode()).hexdigest()[:24]
        aliases=SEARCH_ALIASES.get(normalized,[])
        concepts.setdefault(sid,{'id':sid,'canonical_name':name,'aliases':aliases,'category':'software'})
        key=(row['O*NET-SOC Code'],sid)
        item=links.setdefault(key,{'role_id':key[0],'skill_id':sid,'classifications':[], 'hot_technology':False,'in_demand':False})
        classification={'id':row['Element ID'],'name':row['Element Name']}
        if classification not in item['classifications']:item['classifications'].append(classification)
        item['hot_technology'] |= row['Hot Technology']=='Y'
        item['in_demand'] |= row['In Demand']=='Y'
    if not concepts or not links:
        raise ValueError('No supported software evidence.')
    return list(concepts.values()),list(links.values())


def import_software(engine, directory:Path):
    raw=(directory/'software_skills.csv').read_bytes()
    metadata=json.loads((directory/'manifest.json').read_text())['software_skills.csv']
    checksum=hashlib.sha256(raw).hexdigest()
    if metadata['url'] != SOFTWARE_URL or metadata['sha256'] != checksum:
        raise ValueError('Software origin/checksum validation failed.')
    source_id=hashlib.sha256(('onet-software'+checksum).encode()).hexdigest()[:40]
    with Session(engine) as db,db.begin():
        skills,links=parse_software(raw,set(db.scalars(select(Role.id))),list(db.scalars(select(Skill.canonical_name).where(Skill.category!='software'))))
        source={'id':source_id,'dataset':'onet-software','title':'O*NET 31.0 Software Skills','canonical_url':'https://www.onetcenter.org/dictionary/31.0/csv/software_skills.html',
            'file_url':SOFTWARE_URL,'publisher':'USDOL/ETA, National Center for O*NET Development','publication_date':None,
            'retrieved_at':datetime.fromisoformat(metadata['retrieved_at']),'version':'31.0','sha256':checksum,
            'license':'CC BY 4.0','license_url':'https://www.onetcenter.org/license_db.html','geography':'US','granularity':'occupation / software association',
            'notes':'Published workplace software examples, not rated skill requirements. Hot/in-demand flags describe the source, not current local demand. Noka spelling aliases are search aids. No inferred broad-skill proficiency. '+('REAL-ROW FIXTURE SUBSET; parent SHA-256 '+metadata.get('parent_sha256','') if metadata.get('is_subset') else '')}
        upsert(db,Source,[source])
        for item in skills:item['source_id']=source_id
        for item in links:item['source_id']=source_id
        upsert(db,Skill,skills)
        upsert(db,RoleTechnology,links)
    from backend.app.occupation_catalogue import invalidate_catalogue
    invalidate_catalogue(engine)
    return {'software_skills':len(skills),'occupation_associations':len(links),'source_id':source_id}
