import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import HOTFORSECURITY_BASE_URL, HOTFORSECURITY_THREAT_REPORT_BASE_URL, \
    HOTFORSECURITY_THREAT_REPORT_DIR, HOTFORSECURITY_URL_TO_FILENAME_MAP_PATH


class HotForSecurityHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(HOTFORSECURITY_BASE_URL, HOTFORSECURITY_THREAT_REPORT_BASE_URL,
                         HOTFORSECURITY_THREAT_REPORT_DIR, HOTFORSECURITY_URL_TO_FILENAME_MAP_PATH, "hotforsecurity_report_crawler")
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-1]
        return report_name

    def get_report_urls(self):
        page_number = 0  # Maximum 423 confirmed on 07/13/2020
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
                # Every page has 10 articles
                page_url = page_url + "?page={}".format(page_number)

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                title_tags = soup.find_all("h3") #title_list = soup.find_all(class_="entry-title h3")
                if len(title_tags) == 0:
                    raise Exception("The page does not contain report URLs")

                urls_found_on_page = 0
                for title in title_tags:
                    link_tag = title.find_parent('a')
                    if link_tag and link_tag.has_attr('href'):
                        relative_url = link_tag['href']
                        if relative_url.startswith('/'):
                            full_url = self.base_url + relative_url
                            report_urls.append(full_url)
                            urls_found_on_page += 1

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))
        return report_urls


if __name__ == "__main__":
    crawler = HotForSecurityHTMLCrawler()
    crawler.run()
