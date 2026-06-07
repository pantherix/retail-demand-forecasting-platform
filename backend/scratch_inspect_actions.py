import re
from pathlib import Path

root_dir = Path(".")
for file_path in root_dir.glob("**/[a-zA-Z0-9]*.py"):
    # skip .venv
    if ".venv" in file_path.parts:
        continue
    try:
        content = file_path.read_text(encoding="utf-8")
        for word in ["decision_action", "recommended_action", "Reorder Immediately"]:
            matches = list(re.finditer(word, content))
            if matches:
                print(f"File: {file_path} contains '{word}'")
    except Exception as e:
        pass
