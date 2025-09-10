import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import DARKNET_BASE_URL, DARKNET_THREAT_REPORT_BASE_URL, \
    DARKNET_THREAT_REPORT_DIR, DARKNET_URL_TO_FILENAME_MAP_PATH


class DarknetHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(DARKNET_BASE_URL, DARKNET_THREAT_REPORT_BASE_URL, DARKNET_THREAT_REPORT_DIR,
                         DARKNET_URL_TO_FILENAME_MAP_PATH, "darknet_report_crawler")
        
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-2] #report_url.replace(self.base_url, "").strip("/").replace("/", ":")
        return report_name
    
    def get_report_urls(self):
        page_number = 0  # Maximum 347 confirmed on 07/13/2020
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
                # Every page has 5 articles #6
                page_url = os.path.join(page_url, "page", str(page_number))

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                title_list = soup.find_all("h2", class_="entry-title")
                if len(title_list) == 0:
                    raise Exception("The page does not contain report URLs")

                report_url_pattern = re.compile(
                    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
                for title in title_list:
                    report_url = re.findall(report_url_pattern, str(title))[0]
                    report_urls.append(report_url)

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))

        return report_urls


if __name__ == "__main__":
    crawler = DarknetHTMLCrawler()
    crawler.run()
