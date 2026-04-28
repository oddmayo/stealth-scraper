from scraping_class import SiteConfig, SiteScraper
from pprint import pprint


if __name__ == "__main__":
    part_numbers = [
        "11427953125",
        "11428593186",
        "11428570590",
    ]

    site = SiteConfig(
        search_url_template="https://www.bmwdirectparts.com/search?search_str={part_number}",
        name_selector=".product-title",
        price_selector=".sale-pricing",
        wait_selector=".product-title",
        custom_url="try",
        headless=False,
        use_uc=True,
    )

    scraper = SiteScraper(site)
    results = scraper.scrape_many(part_numbers)

    print("\n--- All Results ---", flush=True)
    pprint(results)
