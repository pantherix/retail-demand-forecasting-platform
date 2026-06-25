"""
RetailGPT - Quick Start Runner
Run from project root: python run.py
"""

import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
BACKEND = str(BACKEND_DIR)


def build_python_bootstrap(port: int) -> str:
    """
    Ensure sys.path injection also applies to uvicorn reload worker processes.
    We do both:
      1) set PYTHONPATH for the subprocess environment
      2) inject backend into sys.path inside the python -c bootstrap before importing uvicorn
    """
    # NOTE: use a raw string in the injected code for path safety
    return (
        "import sys, os; "
        f"sys.path.insert(0, r'{BACKEND}'); "
        "import uvicorn; "
        f"uvicorn.run('app:app', host='0.0.0.0', port={port}, reload=True, reload_dirs=[r'{BACKEND}'])"
    )


if __name__ == "__main__":
    import subprocess
    # Ensure backend is on PYTHONPATH for both the main process and reload workers
    project_root = str(Path(__file__).resolve().parent)
    backend_path = str(Path(__file__).resolve().parent / "backend")
    existing = os.getenv("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = f"{project_root}{os.pathsep}{backend_path}{os.pathsep}{existing}" if existing else f"{project_root}{os.pathsep}{backend_path}"
    logger.info(f"Starting RetailGPT API with backend path injected: {backend_path}")
    port = 8000
    bootstrap_code = build_python_bootstrap(port)
    subprocess.run([sys.executable, "-c", bootstrap_code])
