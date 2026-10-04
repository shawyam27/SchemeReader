import asyncio
import json
import re
from urllib.parse import urljoin

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode
)

from sources import SOURCES
from data import save_category_data


# ---------------------------------------------------------
# TEST SETTINGS
# ---------------------------------------------------------

# Start with 1.
# Once it works, change to None.
MAX_CATEGORIES = 1

# Keep browser visible while testing.
HEADLESS = False

# How many times to retry a category before giving up.
MAX_RETRIES = 2

# Seconds to wait between retries (multiplied by attempt number).
RETRY_BACKOFF = 5


# ---------------------------------------------------------
# STEALTH CONFIG HELPERS
# ---------------------------------------------------------
#
# magic / simulate_user / override_navigator make the
# automated browser look and behave more like a real user,
# which reduces the chance of antibot systems killing the
# page mid-crawl.
# ---------------------------------------------------------

def stealth_kwargs():

    return dict(
        magic=True,
        simulate_user=True,
        override_navigator=True
    )


# ---------------------------------------------------------
# JS RESULT PARSING
# ---------------------------------------------------------
#
# Crawl4AI exposes the return value of js_code via
# result.js_execution_result, shaped roughly like:
#
#   {"success": True, "results": [<return value 1>, ...]}
#
# Our scripts return a JSON string via JSON.stringify(...),
# so we parse that string here.
# ---------------------------------------------------------

def read_js_result(result):

    js_result = getattr(result, "js_execution_result", None)

    if not js_result or not isinstance(js_result, dict):
        return None

    results_list = js_result.get("results")

    if not results_list:
        return None

    raw = results_list[0]

    if raw is None:
        return None

    if isinstance(raw, str):

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            print("DEBUG: js_execution_result string was not valid JSON.")
            print("DEBUG:", raw[:500])
            return None

    return raw


# ---------------------------------------------------------
# FIND CATEGORY CARDS
# ---------------------------------------------------------
#
# Single page load: navigate, wait for body, click "View
# More" via injected JS, then let Crawl4AI capture the
# resulting HTML/links in the SAME result object. No
# second call, no session needed.
# ---------------------------------------------------------

async def get_categories(crawler, source):

    print("\nOpening:", source["url"])

    js_click_view_more = """
    (async () => {

        const elements = [...document.querySelectorAll("*")];

        const button = elements.find(
            el =>
                (el.innerText || "")
                .replace(/\\s+/g, " ")
                .trim()
                .toLowerCase()
                === "view more"
        );

        if (button) {
            button.click();
            // give newly-loaded content time to render
            await new Promise(r => setTimeout(r, 2000));
            return "clicked";
        }

        return "not_found";

    })();
    """

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for="css:body",
        delay_before_return_html=3,
        js_code=js_click_view_more,
        **stealth_kwargs()
    )

    result = await crawler.arun(
        url=source["url"],
        config=config
    )

    if not result.success:
        print("ERROR opening main page:")
        print(result.error_message)
        return []

    print("Main page loaded (View More handled:", read_js_result(result), ")")

    categories = []
    seen = set()

    for links in result.links.values():

        for link in links:

            name = link.get("text", "").strip()
            href = link.get("href", "").strip()

            if not name or not href:
                continue

            name = " ".join(name.split())

            if not name.lower().startswith("ministry"):
                continue

            url = urljoin(source["url"], href)

            if url in seen:
                continue

            seen.add(url)

            categories.append({
                "name": name,
                "url": url
            })

    if MAX_CATEGORIES is not None:
        categories = categories[:MAX_CATEGORIES]

    print()
    print("Categories found:", len(categories))

    for i, category in enumerate(categories, 1):
        print(f"{i}. {category['name']}")
        print(f"   {category['url']}")

    return categories


# ---------------------------------------------------------
# SCRAPE ONE CATEGORY (single attempt, no retry)
# ---------------------------------------------------------
#
# Single page load: navigate, wait for the scheme count
# text, then run the extraction JS on that same loaded
# page as part of the same call.
# ---------------------------------------------------------

async def scrape_category_once(crawler, category):

    print()
    print("=" * 70)
    print("OPENING CATEGORY")
    print("=" * 70)

    print(category["name"])
    print(category["url"])

    wait_for_schemes = """
    js:() => {
        return /Total\\s+\\d+\\s+schemes?\\s+available/i
            .test(document.body.innerText);
    }
    """

    extraction_js = """
    (() => {

        function clean(text) {
            return (text || "").replace(/\\s+/g, " ").trim();
        }

        const schemes = [];

        const elements = [...document.querySelectorAll("*")];

        const totalElement = elements.find(el => {
            const text = clean(el.innerText);
            return /Total\\s+\\d+\\s+schemes?\\s+available/i.test(text);
        });

        if (!totalElement) {
            return JSON.stringify({ success: false, reason: "total_not_found" });
        }

        let container = totalElement.parentElement;
        let best = null;

        for (let i = 0; i < 10 && container; i++) {
            const text = clean(container.innerText);
            if (text.length > 500 && text.length < 150000) {
                best = container;
            }
            container = container.parentElement;
        }

        if (!best) {
            return JSON.stringify({ success: false, reason: "container_not_found" });
        }

        const links = [...best.querySelectorAll("a")];

        for (const link of links) {

            const title = clean(link.innerText);
            const url = link.href;

            if (!title || !url) continue;

            let card = link.parentElement;
            let cardText = "";

            for (let level = 0; level < 6 && card; level++) {
                const text = clean(card.innerText);
                if (text.length > title.length + 30 && text.length < 3000) {
                    cardText = text;
                }
                card = card.parentElement;
            }

            if (!cardText) continue;

            let description = cardText;

            if (description.startsWith(title)) {
                description = description.substring(title.length).trim();
            }

            if (description.length < 20) continue;

            const lower = title.toLowerCase();

            if ([
                "home", "schemes", "documents",
                "search", "acts & rules",
                "constitution of india"
            ].includes(lower)) continue;

            const duplicate = schemes.some(item => item.url === url);
            if (duplicate) continue;

            schemes.push({ title, description, url });

        }

        return JSON.stringify({ success: true, schemes });

    })();
    """

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_for=wait_for_schemes,
        delay_before_return_html=3,
        page_timeout=60000,
        js_code=extraction_js,
        **stealth_kwargs()
    )

    result = await crawler.arun(
        url=category["url"],
        config=config
    )

    if not result.success:
        print()
        print("CATEGORY FAILED")
        print(result.error_message)
        return []

    print()
    print("Category page loaded.")

    # -----------------------------------------------------
    # Primary path: parse the real JS return value.
    # -----------------------------------------------------

    parsed = read_js_result(result)

    if parsed and parsed.get("success") and parsed.get("schemes"):

        schemes = parsed["schemes"]

        print()
        print("SUCCESS (JS path):", len(schemes), "schemes extracted.")

        return schemes

    if parsed and not parsed.get("success"):
        print("DEBUG: JS extraction reported failure reason:", parsed.get("reason"))

    # -----------------------------------------------------
    # Fallback: markdown-based extraction (loses URLs).
    # -----------------------------------------------------

    print("Falling back to markdown extraction (URLs will be empty).")

    markdown = result.markdown or ""

    if hasattr(markdown, "raw_markdown"):
        markdown = markdown.raw_markdown

    print("Rendered content length:", len(markdown))

    schemes = extract_from_markdown(markdown)

    if schemes:
        print()
        print("SUCCESS (markdown fallback):", len(schemes), "schemes extracted.")
        return schemes

    print()
    print("No schemes extracted.")
    print()
    print("First 3000 characters of rendered page:")
    print(markdown[:3000])

    return []


# ---------------------------------------------------------
# SCRAPE ONE CATEGORY, WITH RETRY
# ---------------------------------------------------------
#
# No session to recover here — every arun() call already
# gets its own fresh, isolated browser context, so a retry
# is just "try again."
# ---------------------------------------------------------

async def scrape_category(crawler, category):

    for attempt in range(MAX_RETRIES + 1):

        try:

            schemes = await scrape_category_once(crawler, category)

            if schemes:
                return schemes

        except Exception as error:

            print()
            print(f"Attempt {attempt + 1} raised an exception:")
            print(error)

        if attempt < MAX_RETRIES:
            wait_time = RETRY_BACKOFF * (attempt + 1)
            print(f"Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

    print()
    print("All attempts failed for:", category["name"])

    return []


# ---------------------------------------------------------
# MARKDOWN FALLBACK
# ---------------------------------------------------------

def extract_from_markdown(markdown):

    if not markdown:
        return []

    lines = []

    for line in markdown.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    start = -1

    for i, line in enumerate(lines):
        if re.search(
            r"Total\s+\d+\s+schemes?\s+available",
            line,
            re.IGNORECASE
        ):
            start = i
            break

    if start == -1:
        print("DEBUG: 'Total N schemes available' not found in markdown.")
        return []

    lines = lines[start + 1:]

    schemes = []
    i = 0

    while i < len(lines):

        title = lines[i]

        if not title:
            i += 1
            continue

        if title.lower() in [
            "home", "schemes", "search",
            "documents", "acts & rules",
            "constitution of india"
        ]:
            i += 1
            continue

        description = []
        j = i + 1

        while j < len(lines):

            next_line = lines[j]

            if looks_like_title(next_line):
                break

            description.append(next_line)
            j += 1

        description_text = " ".join(description).strip()

        if len(title) >= 3 and len(description_text) >= 20:

            schemes.append({
                "title": title,
                "description": description_text,
                "url": ""
            })

        i = j

    return schemes


# ---------------------------------------------------------
# TITLE DETECTION
# ---------------------------------------------------------

def looks_like_title(text):

    if not text:
        return False

    if len(text) > 180:
        return False

    if len(text.split()) < 2:
        return False

    if text.endswith("."):
        return False

    keywords = [
        "Pradhan", "PM", "Yojana", "Scheme",
        "Mission", "Programme", "Program",
        "National", "Kisan", "Krishi"
    ]

    return any(keyword.lower() in text.lower() for keyword in keywords)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

async def main():

    source = SOURCES[0]

    browser_config = BrowserConfig(
        headless=HEADLESS,
        verbose=True,
        viewport_width=1920,
        viewport_height=1080
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:

        categories = await get_categories(crawler, source)

        if not categories:
            print("No categories found.")
            return

        for category in categories:

            schemes = await scrape_category(crawler, category)

            if schemes:

                try:
                    save_category_data(
                        category_name=category["name"],
                        category_url=category["url"],
                        schemes=schemes
                    )
                except Exception as error:
                    print("SAVE FAILED for", category["name"], ":", error)

            else:
                print("Nothing to save for:", category["name"])


if __name__ == "__main__":
    asyncio.run(main())