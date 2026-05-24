"""Inspect what the AGCO application table looks like rendered."""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = ctx.new_page()

        url = "https://www.agco.ca/en/cannabis/status-current-cannabis-retail-store-applications"
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(3000)

        # Take screenshot
        page.screenshot(path="/tmp/agco_table.png", full_page=False)

        # Find any tables on the page
        table_count = page.locator("table").count()
        print(f"Tables found: {table_count}")
        for i in range(table_count):
            t = page.locator("table").nth(i)
            print(f"\n--- Table {i} ---")
            header_row = t.locator("thead tr").first
            if header_row.count():
                headers = header_row.locator("th").all_inner_texts()
                print(f"Headers: {headers}")
            rows = t.locator("tbody tr").all()
            print(f"Body rows: {len(rows)}")
            for j, row in enumerate(rows[:3]):
                cells = row.locator("td").all_inner_texts()
                print(f"  Row {j}: {cells}")

        # Look for pagination info
        pager = page.locator(".pager, .pagination, [class*='pager']").all()
        print(f"\nPager elements: {len(pager)}")
        for p_ in pager[:3]:
            print(f"  text: {p_.inner_text()[:200]}")

        # Search for filter/limit controls
        filter_inputs = page.locator("input[type='search'], input[type='text'], select").all()
        print(f"\nFilter inputs: {len(filter_inputs)}")
        for inp in filter_inputs[:10]:
            print(f"  name={inp.get_attribute('name')!r} placeholder={inp.get_attribute('placeholder')!r} type={inp.get_attribute('type')!r}")

        # Is there an "items per page" select?
        for sel in page.locator("select").all():
            print(f"Select: name={sel.get_attribute('name')!r}")
            opts = sel.locator("option").all_inner_texts()
            print(f"  options: {opts}")

        # Look at the URL after any AJAX
        print(f"\nFinal URL: {page.url}")

        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
