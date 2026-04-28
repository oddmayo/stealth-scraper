from dataclasses import dataclass
from bs4 import BeautifulSoup
from seleniumbase import SB
from urllib.parse import urljoin


@dataclass
class SiteConfig:
    search_url_template: str
    name_selector: str
    price_selector: str
    wait_selector: str = ""
    custom_url: str | None = "try"
    headless: bool = False
    use_uc: bool = True


class SiteScraper:
    def __init__(self, config: SiteConfig):
        self.config = config

    @staticmethod
    def is_likely_product_url(href, part_number):
        if not href:
            return False

        href = href.strip()
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            return False

        lowered = href.lower()
        search_like = ("search", "results", "filter", "query")
        if any(token in lowered for token in search_like) and part_number not in href:
            return False

        return True

    def find_product_url(self, search_soup, base_url, part_number):
        candidates = []

        for link in search_soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            if not self.is_likely_product_url(href, part_number):
                continue

            text = " ".join(link.stripped_strings)
            aria_label = link.get("aria-label", "")
            title_attr = link.get("title", "")
            data_attrs = " ".join(
                str(value)
                for key, value in link.attrs.items()
                if key.startswith("data-")
            )

            score = 0
            if part_number in href:
                score += 5
            if part_number in text:
                score += 4
            if part_number in aria_label:
                score += 2
            if part_number in title_attr:
                score += 2
            if part_number in data_attrs:
                score += 2
            if len(href) > 1 and not href.startswith("/"):
                score += 1

            candidates.append((score, urljoin(base_url, href), text))

        if not candidates:
            return ""

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def find_product_url_by_pattern(self, search_soup, base_url, part_number, pattern):
        candidates = []

        for link in search_soup.find_all("a", href=True):
            href = link.get("href", "").strip()
            if not self.is_likely_product_url(href, part_number):
                continue
            if pattern not in href:
                continue

            text = " ".join(link.stripped_strings)
            score = 0
            if part_number in href:
                score += 5
            if part_number in text:
                score += 3
            candidates.append((score, urljoin(base_url, href)))

        if not candidates:
            return ""

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def resolve_product_url(self, search_soup, base_url, part_number):
        if self.config.custom_url is None:
            return ""

        if self.config.custom_url == "try":
            return self.find_product_url(search_soup, base_url, part_number)

        return self.find_product_url_by_pattern(
            search_soup,
            base_url,
            part_number,
            self.config.custom_url,
        )

    def extract_part_info(self, part_number):
        print(f"Starting extraction for {part_number}...", flush=True)
        html = ""
        final_url = ""
        product_url = ""
        search_url = self.config.search_url_template.format(part_number=part_number)

        try:
            with SB(uc=self.config.use_uc, headless=self.config.headless) as sb:
                print(f"Opening {search_url}", flush=True)
                sb.open(search_url)

                if sb.is_element_visible('iframe[src*="cloudflare"]'):
                    sb.sleep(5)
                    sb.uc_gui_click_captcha()

                if self.config.wait_selector:
                    try:
                        sb.wait_for_element(self.config.wait_selector, timeout=15)
                    except Exception:
                        print(
                            f"Timed out waiting for {self.config.wait_selector}.",
                            flush=True,
                        )

                search_html = sb.get_page_source()
                search_soup = BeautifulSoup(search_html, "html.parser")
                product_url = self.resolve_product_url(search_soup, search_url, part_number)

                if product_url:
                    print(f"Derived product URL: {product_url}", flush=True)
                else:
                    print(
                        "Could not find product link on the search page; staying on search URL.",
                        flush=True,
                    )

                final_url = product_url or sb.get_current_url()
                html = search_html
                print("Page source captured.", flush=True)

        except Exception as e:
            print(f"An error occurred during browser execution: {e}", flush=True)

        if not html:
            print("Failed to retrieve HTML.", flush=True)
            return {
                "part_number": part_number,
                "name": None,
                "price": None,
                "url": final_url or product_url,
                "error": "Failed to retrieve HTML",
            }

        soup = BeautifulSoup(html, "html.parser")

        name_tag = soup.select_one(self.config.name_selector)
        part_name = name_tag.get_text(strip=True) if name_tag else "Name not found"

        price_tag = soup.select_one(self.config.price_selector)
        price = price_tag.get_text(strip=True) if price_tag else "Price not found"

        print("\n--- Extraction Results ---", flush=True)
        print(f"Name:  {part_name}", flush=True)
        print(f"Price: {price}", flush=True)
        print(f"URL:   {final_url}", flush=True)

        return {
            "part_number": part_number,
            "name": part_name,
            "price": price,
            "url": final_url,
        }

    def scrape_many(self, part_numbers):
        results = {}
        for part_number in part_numbers:
            results[part_number] = self.extract_part_info(part_number)
        return results


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
        custom_url=None,
        headless=False,
        use_uc=True,
    )

    scraper = SiteScraper(site)
    results = scraper.scrape_many(part_numbers)

    print("\n--- All Results ---", flush=True)
    print(results, flush=True)
