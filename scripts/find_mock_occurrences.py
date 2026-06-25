import os
import re

KEYWORDS = [
    "mock",
    "fake",
    "sample",
    "demo",
    "seed",
    "fallbackData",
    "staticData",
    "defaultProducts",
]
EXCLUDE_DIRS = [
    ".git",
    "node_modules",
    ".next",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".aider.tags.cache.v4",
    "chrome_profile",
]
EXCLUDE_EXTS = [".png", ".jpg", ".jpeg", ".db", ".bak", ".pyc", ".pdf"]


def find_occurrences():
    root_dir = (
        r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform"
    )
    results = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter directories in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in EXCLUDE_EXTS:
                continue

            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        for kw in KEYWORDS:
                            # Search word boundaries or case-insensitive keyword
                            if re.search(
                                r"\b" + re.escape(kw) + r"\b", line, re.IGNORECASE
                            ):
                                results.append(
                                    {
                                        "file": rel_path,
                                        "line": line_num,
                                        "keyword": kw,
                                        "content": line.strip(),
                                    }
                                )
            except Exception:
                pass

    print(f"Total occurrences found: {len(results)}")

    # Save results to JSON
    out_path = r"C:\Users\statu\.gemini\antigravity\brain\dfb8cd1b-58f2-4f58-8847-0c3ceb53ed17\mock_occurrences.json"
    import json

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Occurrences saved to {out_path}")


if __name__ == "__main__":
    find_occurrences()
