from dataclasses import dataclass
from bs4 import BeautifulSoup
from seleniumbase import SB
from urllib.parse import urljoin
import time


@dataclass
class SiteConfig:
    name_selector: str
    sale_price_selector: str
    search_url_template: str = ""
    wait_selector: str = ""
    custom_url: str | None = "try"
    headless: bool = False
    use_uc: bool = True
    list_price_selector: str | None = None


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

    def extract_part_info(self, part_number, search_url=None):
        print(f"Starting extraction for {part_number}...", flush=True)
        start_time = time.perf_counter()
        html = ""
        final_url = ""
        product_url = ""
        search_url = search_url or self.config.search_url_template.format(part_number=part_number)

        try:
            with SB(uc=self.config.use_uc, headless=self.config.headless) as sb:
                print(f"Opening {search_url}", flush=True)
                sb.open(search_url)

                if sb.is_element_visible('iframe[src*="cloudflare"]'):
                    sb.sleep(5)
                    sb.uc_gui_click_captcha()

                if self.config.wait_selector:
                    try:
                        sb.wait_for_element(self.config.wait_selector, timeout=10)
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
            elapsed = time.perf_counter() - start_time
            print(f"Extraction time for {part_number}: {elapsed:.3f} seconds", flush=True)
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

        sale_price_tag = soup.select_one(self.config.sale_price_selector)
        sale_price = sale_price_tag.get_text(strip=True) if sale_price_tag else "Price not found"

        list_price = None
        if self.config.list_price_selector:
            list_price_tag = soup.select_one(self.config.list_price_selector)
            list_price = list_price_tag.get_text(strip=True) if list_price_tag else "Price not found"

        print("\n--- Extraction Results ---", flush=True)
        print(f"Name:  {part_name}", flush=True)
        print(f"Sale Price: {sale_price}", flush=True)
        if list_price:
            print(f"List Price: {list_price}", flush=True)
        print(f"URL:   {final_url}", flush=True)
        elapsed = time.perf_counter() - start_time
        print(f"Extraction time for {part_number}: {elapsed:.3f} seconds", flush=True)

        result = {
            "part_number": part_number,
            "name": part_name,
            "sale_price": sale_price,
            "url": final_url,
        }
        if list_price:
            result["list_price"] = list_price
        return result

    def scrape_many(self, part_numbers, return_results: bool = False):
        """Scrape multiple part numbers.

        By default this prints per-part progress and the total elapsed time
        but does not return the full results dictionary (avoids caller printing it).

        Set `return_results=True` to receive the results dict.
        """
        results = {} if return_results else None
        total_start = time.perf_counter()
        for part_number in part_numbers:
            res = self.extract_part_info(part_number)
            if return_results:
                results[part_number] = res
        total_elapsed = time.perf_counter() - total_start
        print(f"Total scraping time for {len(part_numbers)} parts: {total_elapsed:.3f} seconds", flush=True)
        if return_results:
            return results
