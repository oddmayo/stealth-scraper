from scraping_class import SiteConfig, SiteScraper, format_seconds
import io
import csv
import time

# The data in CSV format
csv_data = """country,brand,product_hierarchy,MANU_MATNR,url,CHILE,general_segmentation
CHILE,BMW,B34356792289,34356792289,https://www.bmwdirectparts.com/search?search_str=34356792289,1,AA
CHILE,BMW,M36121178869,36121178869,https://www.bmwdirectparts.com/search?search_str=36121178869,1,AA
CHILE,BMW,B64115A1BDB6,64115A1BDB6,https://www.bmwdirectparts.com/search?search_str=64115A1BDB6,1,AA
CHILE,BMW,B51475B3C4F2,51475B3C4F2,https://www.bmwdirectparts.com/search?search_str=51475B3C4F2,1,AB
CHILE,BMW,B83125A7DCA2,83125A7DCA2,https://www.bmwdirectparts.com/search?search_str=83125A7DCA2,1,AB
CHILE,BMW,B31108854989,31108854989,https://www.bmwdirectparts.com/search?search_str=31108854989,1,AC
CHILE,BMW,B36116883758,36116883758,https://www.bmwdirectparts.com/search?search_str=36116883758,1,AC
CHILE,BMW,B36122232323,36122232323,https://www.bmwdirectparts.com/search?search_str=36122232323,1,AC
CHILE,BMW,B41515A38652,41515A38652,https://www.bmwdirectparts.com/search?search_str=41515A38652,1,AC
CHILE,BMW,B51317440770,51317440770,https://www.bmwdirectparts.com/search?search_str=51317440770,1,AC
"""

# Read into rows without pandas so the runner does not depend on binary packages
df = list(csv.DictReader(io.StringIO(csv_data)))


if __name__ == "__main__":
    site = SiteConfig(
        search_url_template="",
        name_selector=".product-title",
        sale_price_selector=".sale-pricing",
        wait_selector=".product-title",
        custom_url="/oem-parts/",
        headless=False,
        use_uc=True,
        list_price_selector=".list-price-value",
    )

    scraper = SiteScraper(site)

    results = {}
    total_start = time.perf_counter()
    for row in df:
        part_number = row["MANU_MATNR"]
        search_url = row["url"]
        results[part_number] = scraper.extract_part_info(part_number, search_url=search_url)
    total_elapsed = time.perf_counter() - total_start
    print(f"Total execution time for {len(df)} parts: {format_seconds(total_elapsed)}", flush=True)
