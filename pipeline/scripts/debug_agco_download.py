"""
Debug runner: visit the AGCO export URL, capture screenshots + page state at intervals,
so we can see what the Drupal batch UI actually does.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("/tmp/agco_debug")
OUT.mkdir(exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
        )
        page = context.new_page()

        responses: list[tuple[int, str, str]] = []
        page.on("response", lambda r: responses.append((r.status, r.headers.get("content-type", ""), r.url)))
        page.on("download", lambda d: print(f"DOWNLOAD EVENT: {d.url}  filename={d.suggested_filename}"))

        print("=== Loading landing page ===")
        page.goto(
            "https://www.agco.ca/en/cannabis/status-current-cannabis-retail-store-applications",
            wait_until="networkidle",
        )
        page.screenshot(path=str(OUT / "01_landing.png"))

        print("=== Looking for download link ===")
        links = page.locator("a[href*='cannabis-license-applications-download']").all()
        print(f"Found {len(links)} download links")
        for i, link in enumerate(links):
            print(f"  [{i}] href={link.get_attribute('href')}  text={link.inner_text()}")

        print("=== Triggering download via direct navigation ===")
        page.goto(
            "https://www.agco.ca/en/cannabis-license-applications-download?_format=csv",
            wait_until="commit",
        )

        for i in range(20):
            page.wait_for_timeout(2000)
            try:
                title = page.title()
                url = page.url
                body_text = page.evaluate("document.body && document.body.innerText.slice(0, 400)") or ""
                print(f"[{i*2}s] url={url!r}  title={title!r}  body[0..200]={body_text[:200]!r}")
                page.screenshot(path=str(OUT / f"02_step{i:02d}.png"))
            except Exception as e:
                print(f"[{i*2}s] error: {e}")
                break

        print("\n=== Responses captured ===")
        for status, ctype, url in responses[-25:]:
            print(f"  {status}  {ctype:50s}  {url}")

        context.close()
        browser.close()


if __name__ == "__main__":
    main()
