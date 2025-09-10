import os
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import ATTCYBERSECURITY_BASE_URL, ATTCYBERSECURITY_THREAT_REPORT_BASE_URL, \
    ATTCYBERSECURITY_THREAT_REPORT_DIR, ATTCYBERSECURITY_URL_TO_FILENAME_MAP_PATH


class AttCybersecurityHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(ATTCYBERSECURITY_BASE_URL, ATTCYBERSECURITY_THREAT_REPORT_BASE_URL,
                         ATTCYBERSECURITY_THREAT_REPORT_DIR, ATTCYBERSECURITY_URL_TO_FILENAME_MAP_PATH,
                         "attcybersecurity_report_crawler")

    def get_report_urls(self):
        page_number = 0  # Maximum 19 confirmed on 07/10/2020
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
                # Every page has 12 articles
                page_url = os.path.join(page_url, "P" + str((page_number - 1) * 9))

            # Find all report urls on the page
            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                #title_list = soup.find_all(class_="grid-item") #grid-item #blog-card-header
                # if len(title_list) == 0:
                #     raise Exception("The page does not contain report URLs")
                # for title in title_list:
                #     hrefs = title.find_all("a", {"class": "grid-img"})
                #     if len(hrefs) > 0:
                #         report_url = self.base_url + hrefs[0]["href"]
                #         report_urls.append(report_url)
                blog_cards = soup.find_all("div", class_="card blog-card")
                if len(blog_cards) == 0:
                     raise Exception("The page does not contain report URLs")
                for card in blog_cards:
                    read_more = card.find("a", class_="icon-link icon-link-hover")
                    if read_more and "href" in read_more.attrs:
                        report_url = self.base_url + read_more["href"]
                        report_urls.append(report_url)
            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))

        return report_urls


if __name__ == "__main__":
    crawler = AttCybersecurityHTMLCrawler()
    crawler.run()
