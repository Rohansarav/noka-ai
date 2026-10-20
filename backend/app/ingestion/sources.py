"""Pinned public downloads with verified local re-import and complete metadata."""
import hashlib
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("noka.ingestion")
INDEED_VERSION = "554e4673d0b9a9fd64d4b0da354e5bb5e112beda"
INDEED_ROOT = f"https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/{INDEED_VERSION}/"
ONET_ROOT = "https://www.onetcenter.org/dl_files/database/db_31_0_csv/"
UN_URL = "https://unstats.un.org/SDGAPI/v1/sdg/Goal/List?includechildren=true"
WEF_URL = "https://www.weforum.org/publications/the-future-of-jobs-report-2025/"
URLS = {
    "indeed.csv": INDEED_ROOT + "US/job_postings_by_sector_US.csv",
    "indeed-readme.md": INDEED_ROOT + "README.md",
    "indeed-license.txt": INDEED_ROOT + "LICENSE",
    "un-goals.json": UN_URL,
    "occupation_data.csv": ONET_ROOT + "occupation_data.csv",
    "essential_skills.csv": ONET_ROOT + "essential_skills.csv",
    "transferable_skills.csv": ONET_ROOT + "transferable_skills.csv",
    "onet-license.html": "https://www.onetcenter.org/license_db.html",
}


def download_sources(directory: Path, offline: bool = False):
    """Offline import requires recorded origin/checksum; failed fetch never invents data."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8")) if manifest_path.exists() else {}
    for name, url in URLS.items():
        path = directory / name
        if offline:
            item = manifest.get(name)
            if not item or item["url"] != url or not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Offline file origin/checksum verification failed: " + name)
            continue
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "Noka/0.2 public-evidence-import"})
                with urllib.request.urlopen(request, timeout=35) as response:
                    content = response.read(30_000_001)
                    if len(content) > 30_000_000:
                        raise ValueError("Source exceeds download size limit.")
                path.write_bytes(content)
                manifest[name] = {"url": url, "sha256": hashlib.sha256(content).hexdigest(), "retrieved_at": datetime.now(timezone.utc).isoformat()}
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf8")
                log.info("download file=%s bytes=%d sha256=%s", name, len(content), manifest[name]["sha256"])
                break
            except Exception:
                if attempt == 2:
                    raise RuntimeError("Public source unavailable: " + name) from None
                time.sleep(attempt + 1)
    return manifest
