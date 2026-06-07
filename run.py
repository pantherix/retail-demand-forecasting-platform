"""
RetailGPT - Quick Start Runner
Run from project root: python run.py
"""

import os
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
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
        f"uvicorn.run('app:app', host='0.0.0.0', port={port}, reload=True)"
    )


if __name__ == "__main__":
    port = 8000
    print(f"Starting RetailGPT API on http://localhost:{port}")
    print(f"Docs available at http://localhost:{port}/docs")
    print("Press CTRL+C to stop.\n")

    # Ensure reload workers inherit the module path
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BACKEND}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(
        os.pathsep
    )

    subprocess.run(
        [
            PYTHON,
            "-c",
            build_python_bootstrap(port),
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        check=False,
    )
