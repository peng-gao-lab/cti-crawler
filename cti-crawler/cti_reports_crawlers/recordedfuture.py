import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import RECORDEDFUTURE_BASE_URL, RECORDEDFUTURE_THREAT_REPORT_BASE_URL,\
    RECORDEDFUTURE_THREAT_REPORT_DIR, RECORDEDFUTURE_URL_TO_FILENAME_MAP_PATH

import json
class RecordedFutureHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(RECORDEDFUTURE_BASE_URL, RECORDEDFUTURE_THREAT_REPORT_BASE_URL,
                         RECORDEDFUTURE_THREAT_REPORT_DIR, RECORDEDFUTURE_URL_TO_FILENAME_MAP_PATH,
                         "recordedfuture_report_crawler")
        
    def get_report_urls(self):
        report_urls = []
        
        self.logger.info(f"Crawling report URLs from JSON source: {self.threat_report_base_url}")
        try:
            response = self.scraper.scrape(self.threat_report_base_url)
            response.raise_for_status()
            
            data = response.json()

            if 'data' in data and isinstance(data['data'], list):
                for page_data in data['data']:
                    if 'path' in page_data and page_data['path'].startswith('/blog/'):
                        full_url = os.path.join(self.base_url, page_data['path'].lstrip('/'))
                        report_urls.append(full_url)
                
                self.logger.info(f"Successfully filtered and extracted {len(report_urls)} blog URLs.")
            else:
                self.logger.warning("JSON data from query-index.json is not in the expected format.")

        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Failed to fetch or parse blog data from query-index.json.")

        return report_urls
    
    # def get_report_urls(self):
    #     page_number = 0  # Maximum 124 confirmed on 07/14/2020
    #     page_failed_count = 0
    #     report_urls = []

    #     while True:  # For each page
    #         if page_failed_count > 5:
    #             self.logger.warning("Failed page URLs greater than 5. Exit.")
    #             break

    #         page_number += 1
    #         self.logger.info("Crawling report URLs for page {}".format(page_number))

    #         page_url = self.threat_report_base_url
    #         if page_number > 1:
    #             # Every page has 10 articles
    #             page_url = os.path.join(page_url, "page", str(page_number))

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "html.parser")
    #             title_list = soup.find_all(class_="card")
    #             if len(title_list) == 0:
    #                 raise Exception("The page does not contain report URLs")

    #             report_url_pattern = re.compile(
    #                 r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    #             for title in title_list:
    #                 report_url = re.findall(report_url_pattern, str(title))[0]
    #                 report_urls.append(report_url)

    #         except Exception as e:
    #             page_failed_count += 1
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))

    #     return report_urls

    def get_report_name(self, report_url):
        return report_url.replace(self.base_url, "").strip("/").replace("/", ":") + ".html"

    def get_file_path(self, report_name):
        # Overload parent method
        return os.path.join(self.threat_report_dir, report_name)


if __name__ == "__main__":
    crawler = RecordedFutureHTMLCrawler()
    crawler.run()
