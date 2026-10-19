import os
import sys
from pathlib import Path
import uvicorn

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    # Access logs are disabled so user-controlled paths never enter deployment logs.
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), access_log=False)
