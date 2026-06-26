import subprocess
import os
from pathlib import Path

# Define the dangling tree SHAs to recover
trees = [
    "1790774bf80c32a86a8c9274545034bc089a2d4b",
    "8510c475e128db4451c5cca367f9c4ba73f9811d",
    "25e85b1fec925aa74e5973937082431351babf19",
]

repo_root = Path.cwd()
recovered_dir = repo_root / "recovered_from_git"
recovered_dir.mkdir(parents=True, exist_ok=True)

for tree in trees:
    # List all files in the tree
    result = subprocess.run(["git", "ls-tree", "-r", tree], cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to list tree {tree}: {result.stderr}")
        continue
    lines = result.stdout.strip().splitlines()
    for line in lines:
        # Format: <mode> <type> <hash>\t<path>
        try:
            meta, path = line.split('\t', 1)
            _, obj_type, blob_hash = meta.split()
        except ValueError:
            continue
        if obj_type != "blob":
            continue
        # Extract file content
        show_res = subprocess.run(["git", "show", f"{tree}:{path}"], cwd=repo_root, capture_output=True, text=True)
        if show_res.returncode != 0:
            print(f"Failed to show {path} in tree {tree}: {show_res.stderr}")
            continue
        content = show_res.stdout
        # Build output path with tree hash appended before extension
        out_path = recovered_dir / path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        stem, suffix = os.path.splitext(out_path.name)
        new_name = f"{stem}_{tree[:7]}{suffix}"
        out_path = out_path.with_name(new_name)
        out_path.write_text(content)
        print(f"Recovered {path} -> {out_path.relative_to(repo_root)}")
print("Recovery completed.")
