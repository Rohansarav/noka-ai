"""Operator import/review entrypoint. Never exposes public approval endpoints."""
import argparse, hashlib, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.database import engine
from backend.app.market_evidence import import_bundle, Review, KINDS
from backend.app.models import IntelligenceRecord

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='command',required=True)
    imp=sub.add_parser('import');imp.add_argument('path',nargs='?',default='data/market/baseline.json')
    rev=sub.add_parser('review');rev.add_argument('kind',choices=['mappings','claims']);rev.add_argument('id');rev.add_argument('--decision',choices=['approved','rejected'],required=True);rev.add_argument('--reviewer',required=True);rev.add_argument('--reason',required=True)
    args=parser.parse_args();now=datetime.now(timezone.utc)
    with Session(engine) as db:
        try:
            if args.command=='import':
                result=import_bundle(db,json.loads(Path(args.path).read_text(encoding='utf-8-sig')))
            else:
                rid=hashlib.sha256(f'{KINDS[args.kind]}:{args.id}'.encode()).hexdigest()
                row=db.get(IntelligenceRecord,rid)
                if row is None:raise ValueError('Unknown evidence ID')
                review=Review(status=args.decision,reviewer=args.reviewer,reviewed_at=now,reason=args.reason)
                previous=row.payload.get('review')
                row.payload={**row.payload,'review':review.model_dump(mode='json')}
                db.add(IntelligenceRecord(id=uuid.uuid4().hex,kind='market_review',created_at=now,payload={'entity_id':args.id,'entity_kind':args.kind,'previous':previous,'review':review.model_dump(mode='json')}))
                result={'reviewed':args.id,'decision':args.decision}
            db.add(IntelligenceRecord(id=uuid.uuid4().hex,kind='market_run',created_at=now,payload={'status':'succeeded','operation':args.command,'completed_at':now.isoformat(),**result}))
            db.commit();print(json.dumps(result))
        except Exception as exc:
            db.rollback()
            db.add(IntelligenceRecord(id=uuid.uuid4().hex,kind='market_run',created_at=now,payload={'status':'failed','operation':args.command,'completed_at':now.isoformat(),'error_type':type(exc).__name__}))
            db.commit()
            raise SystemExit(f'{args.command} failed ({type(exc).__name__}); previous successful evidence retained.') from None

if __name__=='__main__':main()
