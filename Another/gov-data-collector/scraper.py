# import asyncio
# import json
# import re
# from pathlib import Path
# from urllib.parse import urljoin

# from crawl4ai import (
#     AsyncWebCrawler,
#     BrowserConfig,
#     CrawlerRunConfig,
#     CacheMode,
# )


# START_URL = "https://www.india.gov.in/my-government/schemes"

# OUTPUT_FOLDER = Path("dataV3")
# SESSION_ID = "1787054618212"

# # How many cards to scrape
# MAX_CARDS = 5


# def safe_filename(name):
#     """
#     Convert card/page name into a safe filename.
#     """

#     name = re.sub(
#         r"[^a-zA-Z0-9_-]+",
#         "_",
#         name
#     )

#     return name.strip("_")


# async def get_card_links(crawler):
#     """
#     Open the main page and extract ministry card links.
#     """

#     config = CrawlerRunConfig(
#         session_id=SESSION_ID,
#         cache_mode=CacheMode.BYPASS,
#         wait_for="body",
#     )

#     result = await crawler.arun(
#         url=START_URL,
#         config=config
#     )

#     if not result.success:
#         print("Failed to open main page")
#         print(result.error_message)
#         return []

#     print("Main page loaded.")

#     # JavaScript extracts the ministry card links.
#     js_extract_cards = """
#     (() => {

#         const targetNames = [
#             "Ministry Of Social Justice and Empowerment",
#             "Ministry of Education",
#             "Ministry Of Science And Technology",
#             "Ministry Of Agriculture and Farmers Welfare",
#             "Ministry Of Commerce And Industry",
#             "Ministry Of Micro, Small and Medium Enterprises",
#             "Ministry Of Finance",
#             "Ministry Of Textiles",
#             "Ministry Of Health & Family Welfare",
#             "Ministry Of Culture",
#             "Ministry Of Defence",
#             "Ministry Of Fisheries, Animal Husbandry and Dairying",
#             "Ministry Of Home Affairs",
#             "Ministry Of Minority Affairs",
#             "Ministry Of Rural Development"
#         ];

#         const results = [];

#         const links = Array.from(
#             document.querySelectorAll("a")
#         );

#         for (const link of links) {

#             const text = link.innerText
#                 ?.replace(/\\s+/g, " ")
#                 .trim();

#             if (!text) {
#                 continue;
#             }

#             const matchedName = targetNames.find(
#                 name => text.toLowerCase() === name.toLowerCase()
#             );

#             if (!matchedName) {
#                 continue;
#             }

#             const href = link.href;

#             if (!href) {
#                 continue;
#             }

#             results.push({
#                 name: matchedName,
#                 url: href
#             });
#         }

#         return results;

#     })();
#     """

#     # Run JS on the already-open page.
#     config = CrawlerRunConfig(
#         session_id=SESSION_ID,
#         js_code=js_extract_cards,
#         js_only=True,
#         cache_mode=CacheMode.BYPASS,
#     )

#     result = await crawler.arun(
#         url=START_URL,
#         config=config
#     )

#     if not result.success:
#         print("Failed to extract cards")
#         print(result.error_message)
#         return []

#     # The easiest reliable method is to inspect the HTML after JS.
#     # We will extract links from Crawl4AI's result.links.
#     cards = []

#     for link_type, links in result.links.items():

#         for link in links:

#             href = link.get("href", "")
#             text = link.get("text", "").strip()

#             if not href or not text:
#                 continue

#             for target_name in [
#                 "Ministry Of Social Justice and Empowerment",
#                 "Ministry of Education",
#                 "Ministry Of Science And Technology",
#                 "Ministry Of Agriculture and Farmers Welfare",
#                 "Ministry Of Commerce And Industry",
#                 "Ministry Of Micro, Small and Medium Enterprises",
#                 "Ministry Of Finance",
#                 "Ministry Of Textiles",
#                 "Ministry Of Health & Family Welfare",
#                 "Ministry Of Culture",
#                 "Ministry Of Defence",
#                 "Ministry Of Fisheries, Animal Husbandry and Dairying",
#                 "Ministry Of Home Affairs",
#                 "Ministry Of Minority Affairs",
#                 "Ministry Of Rural Development",
#             ]:

#                 if text.lower() == target_name.lower():

#                     cards.append({
#                         "name": target_name,
#                         "url": urljoin(
#                             START_URL,
#                             href
#                         )
#                     })

#                     break

#     # Remove duplicate URLs
#     unique_cards = []

#     seen_urls = set()

#     for card in cards:

#         if card["url"] in seen_urls:
#             continue

#         seen_urls.add(card["url"])
#         unique_cards.append(card)

#     return unique_cards[:MAX_CARDS]


# async def scrape_card(
#     crawler,
#     card
# ):
#     """
#     Visit one ministry card and save its page.
#     """

#     name = card["name"]
#     url = card["url"]

#     print("\n" + "=" * 70)
#     print("Scraping:", name)
#     print("URL:", url)
#     print("=" * 70)

#     config = CrawlerRunConfig(
#         session_id=SESSION_ID,

#         cache_mode=CacheMode.BYPASS,

#         wait_for="body",

#         # Execute JavaScript if the page is dynamic.
#         js_code="""
#         window.scrollTo(
#             0,
#             document.body.scrollHeight
#         );
#         """,

#         delay_before_return_html=2,
#     )

#     result = await crawler.arun(
#         url=url,
#         config=config
#     )

#     if not result.success:

#         print("FAILED")
#         print(result.error_message)

#         return None

#     # Crawl4AI's final Markdown.
#     markdown = result.markdown

#     if not markdown:

#         print("No Markdown content found.")

#         return None

#     # Create folder.
#     folder_name = safe_filename(name)

#     output_folder = (
#         OUTPUT_FOLDER /
#         folder_name
#     )

#     output_folder.mkdir(
#         parents=True,
#         exist_ok=True
#     )

#     # Save Markdown.
#     output_file = (
#         output_folder /
#         f"{folder_name}.md"
#     )

#     final_content = f"""# {name}

# Source URL: {result.url}

# ---

# {markdown}
# """

#     output_file.write_text(
#         final_content,
#         encoding="utf-8"
#     )

#     # Save metadata separately.
#     metadata = {
#         "name": name,
#         "source_url": result.url,
#         "source_file": str(output_file),
#     }

#     metadata_file = (
#         output_folder /
#         "metadata.json"
#     )

#     metadata_file.write_text(
#         json.dumps(
#             metadata,
#             indent=2,
#             ensure_ascii=False
#         ),
#         encoding="utf-8"
#     )

#     print("Saved:")
#     print(output_file)

#     print(
#         "Characters:",
#         len(markdown)
#     )

#     return metadata


# async def main():

#     browser_config = BrowserConfig(
#         headless=False,
#         verbose=True
#     )

#     async with AsyncWebCrawler(
#         config=browser_config
#     ) as crawler:

#         # --------------------------------------------------
#         # STEP 1
#         # Find ministry cards
#         # --------------------------------------------------

#         cards = await get_card_links(
#             crawler
#         )

#         if not cards:

#             print(
#                 "No ministry cards found."
#             )

#             return

#         print(
#             f"\nFound {len(cards)} cards:\n"
#         )

#         for index, card in enumerate(
#             cards,
#             start=1
#         ):

#             print(
#                 f"{index}. "
#                 f"{card['name']}"
#             )

#             print(
#                 f"   {card['url']}"
#             )

#         # --------------------------------------------------
#         # STEP 2
#         # Visit each card
#         # --------------------------------------------------

#         results = []

#         for card in cards:

#             metadata = await scrape_card(
#                 crawler,
#                 card
#             )

#             if metadata:

#                 results.append(
#                     metadata
#                 )

#         # --------------------------------------------------
#         # STEP 3
#         # Save crawl index
#         # --------------------------------------------------

#         index_file = (
#             OUTPUT_FOLDER /
#             "crawl_index.json"
#         )

#         index_file.parent.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#         index_file.write_text(
#             json.dumps(
#                 results,
#                 indent=2,
#                 ensure_ascii=False
#             ),
#             encoding="utf-8"
#         )

#         print("\n" + "=" * 70)
#         print("CRAWL COMPLETE")
#         print("=" * 70)

#         print(
#             f"Successfully scraped: "
#             f"{len(results)} pages"
#         )

#         print(
#             f"Index saved to: "
#             f"{index_file}"
#         )

#         # --------------------------------------------------
#         # STEP 4
#         # Kill persistent session
#         # --------------------------------------------------

#         await crawler.kill_session(
#             SESSION_ID
#         )


# if __name__ == "__main__":
#     asyncio.run(main())
    
import asyncio
from urllib.parse import urljoin

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode
)

from sources import SOURCES

from data import (
    save_scraped_page,
    save_rag_document,
    save_metadata
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

SESSION_ID = "1787054618212"

# Keep this small while testing.
# Change to None when ready to scrape everything.
MAX_CARDS = 5


# ---------------------------------------------------------
# MINISTRY NAMES
# ---------------------------------------------------------

MINISTRY_NAMES = [

    "Ministry Of Social Justice and Empowerment",

    "Ministry of Education",

    "Ministry Of Science And Technology",

    "Ministry Of Agriculture and Farmers Welfare",

    "Ministry Of Commerce And Industry",

    "Ministry Of Micro, Small and Medium Enterprises",

    "Ministry Of Finance",

    "Ministry Of Textiles",

    "Ministry Of Health & Family Welfare",

    "Ministry Of Culture",

    "Ministry Of Defence",

    "Ministry Of Fisheries, Animal Husbandry and Dairying",

    "Ministry Of Home Affairs",

    "Ministry Of Minority Affairs",

    "Ministry Of Rural Development"

]


# ---------------------------------------------------------
# GET SOURCE
# ---------------------------------------------------------

def get_source(source_id):

    for source in SOURCES:

        if source["id"] == source_id:
            return source

    return None


# ---------------------------------------------------------
# GET CARD LINKS
# ---------------------------------------------------------

async def get_card_links(
    crawler,
    source
):
    """
    Open the source page and find ministry cards.
    """

    url = source["url"]

    config = CrawlerRunConfig(

        session_id=SESSION_ID,

        cache_mode=CacheMode.BYPASS,

        wait_for="body"

    )

    result = await crawler.arun(

        url=url,

        config=config

    )

    if not result.success:

        print(
            "Failed to open:",
            url
        )

        print(
            result.error_message
        )

        return []

    print(
        "\nMain page loaded:"
    )

    print(url)


    cards = []

    seen_urls = set()


    # Crawl4AI provides discovered links
    for link_type, links in result.links.items():

        for link in links:

            href = link.get(
                "href",
                ""
            )

            text = link.get(
                "text",
                ""
            ).strip()


            if not href or not text:
                continue


            # Normalize text
            normalized_text = (
                " ".join(
                    text.split()
                )
                .lower()
            )


            for ministry_name in MINISTRY_NAMES:

                target_text = (
                    " ".join(
                        ministry_name.split()
                    )
                    .lower()
                )


                if normalized_text == target_text:

                    full_url = urljoin(
                        url,
                        href
                    )


                    if full_url in seen_urls:
                        continue


                    seen_urls.add(
                        full_url
                    )


                    cards.append({

                        "name":
                            ministry_name,

                        "url":
                            full_url

                    })


                    break


    # Apply test limit
    if MAX_CARDS is not None:

        cards = cards[
            :MAX_CARDS
        ]


    return cards


# ---------------------------------------------------------
# SCRAPE ONE CARD
# ---------------------------------------------------------

async def scrape_card(
    crawler,
    source,
    card
):
    """
    Visit one ministry card and save its data.
    """

    name = card["name"]

    url = card["url"]


    print("\n")
    print("=" * 70)

    print(
        "Scraping:",
        name
    )

    print(
        "URL:",
        url
    )

    print("=" * 70)


    config = CrawlerRunConfig(

        session_id=SESSION_ID,

        cache_mode=CacheMode.BYPASS,

        wait_for="body",

        # JavaScript execution
        js_code="""

        window.scrollTo(
            0,
            document.body.scrollHeight
        );

        """,

        delay_before_return_html=2

    )


    result = await crawler.arun(

        url=url,

        config=config

    )


    if not result.success:

        print(
            "FAILED:"
        )

        print(
            result.error_message
        )

        return None


    markdown = result.markdown


    if not markdown:

        print(
            "No content found."
        )

        return None


    # -----------------------------------------------------
    # SAVE RAW / SCRAPED DATA
    # -----------------------------------------------------

    scraped_file = save_scraped_page(

        source=source,

        page_name=name,

        url=result.url,

        content=markdown,

        page_type="ministry"

    )


    # -----------------------------------------------------
    # SAVE RAG DOCUMENT
    # -----------------------------------------------------

    rag_file = save_rag_document(

        source=source,

        page_name=name,

        url=result.url,

        content=markdown,

        category="ministries"

    )


    # -----------------------------------------------------
    # SAVE METADATA
    # -----------------------------------------------------

    metadata = save_metadata(

        source=source,

        page_name=name,

        url=result.url,

        scraped_file=scraped_file,

        rag_file=rag_file,

        page_type="ministry"

    )


    print(
        "Characters:",
        len(markdown)
    )


    return metadata


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

async def main():

    browser_config = BrowserConfig(

        headless=False,

        verbose=True

    )


    async with AsyncWebCrawler(

        config=browser_config

    ) as crawler:


        # -------------------------------------------------
        # SOURCE
        # -------------------------------------------------

        source = get_source(
            "india_gov_schemes"
        )


        if not source:

            print(
                "Source not found."
            )

            return


        # -------------------------------------------------
        # FIND MINISTRY CARDS
        # -------------------------------------------------

        cards = await get_card_links(

            crawler,

            source

        )


        if not cards:

            print(
                "No ministry cards found."
            )

            return


        print(
            f"\nFound {len(cards)} cards:\n"
        )


        for index, card in enumerate(

            cards,

            start=1

        ):

            print(

                f"{index}. "
                f"{card['name']}"

            )

            print(
                f"   {card['url']}"
            )


        # -------------------------------------------------
        # SCRAPE CARDS
        # -------------------------------------------------

        results = []


        for card in cards:

            metadata = await scrape_card(

                crawler,

                source,

                card

            )


            if metadata:

                results.append(
                    metadata
                )


        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        print("\n")
        print("=" * 70)

        print(
            "CRAWL COMPLETE"
        )

        print("=" * 70)


        print(
            "Successfully scraped:",
            len(results)
        )


        # -------------------------------------------------
        # CLOSE SESSION
        # -------------------------------------------------

        await crawler.kill_session(

            SESSION_ID

        )


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":

    asyncio.run(
        main()
    )