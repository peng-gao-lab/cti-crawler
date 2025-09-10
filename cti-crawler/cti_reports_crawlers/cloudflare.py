import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import CLOUDFLARE_BASE_URL, CLOUDFLARE_THREAT_REPORT_BASE_URL, \
    CLOUDFLARE_THREAT_REPORT_DIR, CLOUDFLARE_URL_TO_FILENAME_MAP_PATH

class CloudflareHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(CLOUDFLARE_BASE_URL, CLOUDFLARE_THREAT_REPORT_BASE_URL, CLOUDFLARE_THREAT_REPORT_DIR,
                         CLOUDFLARE_URL_TO_FILENAME_MAP_PATH, "cloudflare_report_crawler")

    def get_report_urls(self):
        page_number = 0  # Maximum 300 confirmed on 07/12/2020
        page_failed_count = 0
        report_urls = []

        while True:  # For each page
            if page_failed_count > 5:
                self.logger.warning("Failed page URLs greater than 5. Exit.")
                break

            page_number += 1
            self.logger.info("Crawling report URLs for page {}".format(page_number))

            page_url = self.threat_report_base_url
            if page_number > 1:
                # Every page has 5 articles
                page_url = os.path.join(page_url, "page", str(page_number))

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                title_list = soup.find_all("article") #soup.find_all("a", {"data-testid": "post-title"}) #soup.find_all(class_="flex flex-row flex-wrap mw8 center items-start")
                if len(title_list) == 0:
                    raise Exception("The page does not contain report URLs")

                for title in title_list:
                    hrefs = title.find_all("a", {"class": "fw5 no-underline gray1"})
                    if len(hrefs) > 0:
                        for href in hrefs:
                            report_url = self.base_url + href["href"]
                            report_urls.append(report_url)

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))

        return report_urls


if __name__ == "__main__":
    crawler = CloudflareHTMLCrawler()
    crawler.run()
