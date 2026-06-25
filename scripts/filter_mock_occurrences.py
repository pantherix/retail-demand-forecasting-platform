import json


def filter_occurrences():
    json_path = r"C:\Users\statu\.gemini\antigravity\brain\dfb8cd1b-58f2-4f58-8847-0c3ceb53ed17\mock_occurrences.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered = []
    for item in data:
        fpath = item["file"]
        # Skip history, build cache, and external scripts
        if "tsconfig.tsbuildinfo" in fpath or ".aider.chat.history.md" in fpath:
            continue
        if "scratch_" in fpath or "scratch/" in fpath:
            continue
        filtered.append(item)

    print(f"Filtered occurrences: {len(filtered)}")
    print(json.dumps(filtered, indent=2))


if __name__ == "__main__":
    filter_occurrences()
