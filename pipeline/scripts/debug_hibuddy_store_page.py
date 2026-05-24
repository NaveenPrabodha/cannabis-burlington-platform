"""Check what data a HiBuddy store page exposes (hours, phone, website, lat/lng, etc.)."""

import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("/tmp/hibuddy_debug")
OUT.mkdir(exist_ok=True)


def main():
    # Test against 3 different stores
    stores = [
        ("5c04f28e66a4e58a346a25970fc2ae2d", "mont-kailash-cannabis"),
        ("8a91ceb91d495050ab8cc5ef992737b4", "budssmoke"),
        ("1ec83335426f4ade5dffc0c4c75a5f5b", "burlington-cannabis-co"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1400, "height": 1000},
        )
        page = ctx.new_page()

        # Capture any API responses
        json_responses = []
        def on_response(r):
            ctype = r.headers.get("content-type", "")
            if "json" in ctype and ("api" in r.url or "store" in r.url or "graphql" in r.url):
                try:
                    json_responses.append((r.url, r.json()))
                except Exception:
                    pass

        page.on("response", on_response)

        for sid, slug in stores:
            url = f"https://hibuddy.ca/store/{sid}/{slug}"
            print(f"\n========== {slug} ==========")
            print(f"URL: {url}")

            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(4000)

            # Save full text
            text = page.evaluate("document.body && document.body.innerText") or ""
            (OUT / f"{slug}.txt").write_text(text)

            # Look for hours patterns
            patterns = {
                "hours_text_block": re.compile(r"(hours|open|closed).{0,300}", re.I | re.S),
                "day_with_time": re.compile(
                    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\s*[:\-]?\s*\d{1,2}", re.I
                ),
                "open_now": re.compile(r"open now|closed now|open until|closed until", re.I),
                "phone": re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
                "website_link": re.compile(r"website|visit website|store website", re.I),
                "lat_lng": re.compile(r"(-?\d{2}\.\d{4,}),\s*(-?\d{2,3}\.\d{4,})"),
            }
            for label, rx in patterns.items():
                m = rx.search(text)
                if m:
                    snippet = m.group(0)[:200].replace("\n", " | ")
                    print(f"  ✓ {label}: {snippet}")
                else:
                    print(f"  ✗ {label}: not found")

            # Look for JSON-LD or structured data
            jsonld = page.locator('script[type="application/ld+json"]').all()
            print(f"  json-ld blocks: {len(jsonld)}")
            for j in jsonld:
                try:
                    data = json.loads(j.inner_html())
                    keys = list(data.keys()) if isinstance(data, dict) else "array"
                    print(f"    keys: {keys}")
                    if isinstance(data, dict):
                        if "openingHours" in data or "openingHoursSpecification" in data:
                            print(f"    ★ HOURS IN JSON-LD: {data.get('openingHours') or data.get('openingHoursSpecification')}")
                        if "address" in data:
                            print(f"    address: {data['address']}")
                        if "geo" in data:
                            print(f"    geo: {data['geo']}")
                        if "telephone" in data:
                            print(f"    phone: {data['telephone']}")
                        if "url" in data:
                            print(f"    url: {data['url']}")
                except Exception as e:
                    print(f"    parse error: {e}")

            # Capture full HTML for offline inspection
            (OUT / f"{slug}.html").write_text(page.content())

        # Print captured JSON API responses
        print(f"\n\n=== Captured JSON API responses: {len(json_responses)} ===")
        for url, payload in json_responses[:5]:
            print(f"\n{url}")
            print(json.dumps(payload, indent=2)[:1000])

        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
