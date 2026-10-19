"""Run the Vite frontend and FastAPI API together for local development."""
import os
import shutil
import subprocess
import sys

if __name__ == "__main__":
    pnpm = shutil.which("pnpm.cmd" if os.name == "nt" else "pnpm")
    if not pnpm:
        raise SystemExit("Install pnpm before starting development.")
    api = subprocess.Popen([sys.executable, "scripts/start.py"])
    frontend = subprocess.Popen([pnpm, "dev"])
    try:
        while True:
            try:
                frontend.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                if api.poll() is not None:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        frontend.terminate()
        api.terminate()
        frontend.wait()
        api.wait()
