"""
RetailGPT Dashboard Launcher
Run from project root: python run_dashboard.py
"""
import subprocess
import sys
from pathlib import Path

PYTHON    = str(Path(__file__).parent / ".venv" / "Scripts" / "python.exe")
DASHBOARD = str(Path(__file__).parent / "dashboard" / "app.py")

if __name__ == "__main__":
    print("Starting RetailGPT Dashboard on http://localhost:8501")
    print("Press CTRL+C to stop.\n")
    subprocess.run([PYTHON, "-m", "streamlit", "run", DASHBOARD, "--server.port=8501"])
