import asyncio

import httpx

BASE_URL = "http://127.0.0.1:8000"

# Primary router groups requested
ROUTER_PREFIXES = [
    "/api/auth",
    "/api/dataset",
    "/api/forecast",  # should match /api/forecasting and /api/forecast depending on router prefix
    "/api/copilot",
]

# Keep smoke tests fast & “happy-path-ish”
PREFERRED_METHODS = ["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH"]


def _matches_requested_router(path: str) -> bool:
    return any(path.startswith(p) for p in ROUTER_PREFIXES)


async def _pick_and_probe(
    client: httpx.AsyncClient, paths: dict
) -> list[tuple[str, str, int]]:
    # Collect candidate endpoints under the desired router prefixes
    candidates: list[tuple[str, str]] = []
    method_priority = {m: i for i, m in enumerate(PREFERRED_METHODS)}

    for path, methods in paths.items():
        if not _matches_requested_router(path):
            continue

        allowed = list(methods.keys())
        # Skip endpoints that are heavily path-param driven (best-effort heuristic)
        if "{" in path and "}" in path:
            continue

        allowed_sorted = sorted(
            allowed,
            key=lambda m: method_priority.get(m.upper(), 999),
        )

        if allowed_sorted:
            candidates.append((allowed_sorted[0].upper(), path))

    # Keep it small for speed
    candidates = candidates[:12]

    results: list[tuple[str, str, int]] = []
    for method, url in candidates:
        r = await client.request(method, url, headers={"accept": "application/json"})
        results.append((method, url, r.status_code))

    return results


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=20) as client:
        openapi = await client.get("/openapi.json")
        openapi.raise_for_status()
        spec = openapi.json()

        paths = spec.get("paths", {})
        if not paths:
            raise RuntimeError("No paths found in /openapi.json")

        results = await _pick_and_probe(client, paths)

    print("=== Router smoke test (happy-path probe) ===")
    ok = 0
    for method, url, code in results:
        status = "OK" if (200 <= code < 300) else "WARN"
        if 200 <= code < 300:
            ok += 1
        print(f"{status:4} {code:3} {method:5} {url}")

    print(f"\nSummary: {ok}/{len(results)} endpoints returned 2xx.")
    print(
        "Note: 401/403 can occur if auth is required; 404/500 indicate routing/import issues."
    )


if __name__ == "__main__":
    asyncio.run(main())
