"""Explicit CLI only: no public web endpoint can trigger downloads or imports."""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.database import engine
from backend.app.ingestion.runner import import_all

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Noka verified public-source importer")
    parser.add_argument("--directory", type=Path, default=Path("data/raw"))
    parser.add_argument("--offline", action="store_true", help="Verify manifest/checksums and import already-downloaded files")
    parser.add_argument("--dry-run", action="store_true", help="Download/validate sources without any database writes")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        print(json.dumps(import_all(engine, args.directory, offline=args.offline, dry_run=args.dry_run), indent=2))
    except Exception as exc:
        # Do not print DB URLs, credentials, raw SQL parameters or provider payloads.
        logging.error("Import stopped (%s). Check source availability, schema and migration status.", type(exc).__name__)
        sys.exit(1)
