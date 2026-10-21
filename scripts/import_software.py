"""Explicit software evidence import, with bounded official download and verified offline mode."""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.database import engine
from backend.app.software_skills import SOFTWARE_URL, import_software


def download(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with urlopen(Request(SOFTWARE_URL,headers={'User-Agent':'Noka public-evidence-import'}),timeout=35) as response:
        raw=response.read(12_000_001)
    if len(raw)>12_000_000:raise ValueError('Software download exceeds limit.')
    (directory/'software_skills.csv').write_bytes(raw)
    path=directory/'manifest.json'
    manifest=json.loads(path.read_text()) if path.exists() else {}
    manifest['software_skills.csv']={'url':SOFTWARE_URL,'sha256':hashlib.sha256(raw).hexdigest(),'retrieved_at':datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('data/raw'))
    parser.add_argument('--download',action='store_true')
    args=parser.parse_args()
    try:
        if args.download:download(args.directory)
        print(json.dumps(import_software(engine,args.directory)))
    except Exception as exc:
        print('Software import stopped: '+type(exc).__name__,file=sys.stderr)
        sys.exit(1)
