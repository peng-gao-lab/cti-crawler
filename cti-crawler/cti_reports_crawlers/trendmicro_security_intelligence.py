import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import TRENDMICROSECURITYINTELLIGENCE_BASE_URL, \
    TRENDMICROSECURITYINTELLIGENCE_THREAT_REPORT_BASE_URL, TRENDMICROSECURITYINTELLIGENCE_THREAT_REPORT_DIR, \
        TRENDMICROSECURITYINTELLIGENCE_URL_TO_FILENAME_MAP_PATH


class TrendMicroSecurityIntelligenceHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(TRENDMICROSECURITYINTELLIGENCE_BASE_URL, TRENDMICROSECURITYINTELLIGENCE_THREAT_REPORT_BASE_URL,
                         TRENDMICROSECURITYINTELLIGENCE_THREAT_REPORT_DIR,
                         TRENDMICROSECURITYINTELLIGENCE_URL_TO_FILENAME_MAP_PATH,
                         "trendmicrosecurityintelligence_report_crawler", use_headers=True)

    def get_report_urls(self):
        page_number = 0  # Maximum 799 confirmed on 07/12/2020
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
                title_list = soup.find_all(class_="post-title")
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
    crawler = TrendMicroSecurityIntelligenceHTMLCrawler()
    crawler.run()
