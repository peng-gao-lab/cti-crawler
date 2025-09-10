from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import FORCEPOINT_BASE_URL, FORCEPOINT_THREAT_REPORT_BASE_URL, \
    FORCEPOINT_THREAT_REPORT_DIR, FORCEPOINT_URL_TO_FILENAME_MAP_PATH


class ForcepointHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(FORCEPOINT_BASE_URL, FORCEPOINT_THREAT_REPORT_BASE_URL, FORCEPOINT_THREAT_REPORT_DIR,
                         FORCEPOINT_URL_TO_FILENAME_MAP_PATH, "forcepoint_report_crawler")
        
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-1]
        return report_name
    
    def get_report_urls(self):
        page_number = 0  # Maximum 98 confirmed on 07/13/2020
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
                page_url = page_url + "?page={}".format(page_number)

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                all_links = soup.find_all("a")
                unique_urls_on_page = set()
                
                for link in all_links:
                    if link.has_attr("href"):
                        href = link["href"]
                        if href.startswith("/blog/insights/") or href.startswith("/blog/x-labs/"):
                            report_url = self.base_url + href
                            unique_urls_on_page.add(report_url)
                
                if not unique_urls_on_page:
                    if page_number > 1:
                        self.logger.info("No more blog URLs found on page {}. Reached the last page.".format(page_number))
                        break
                    raise Exception("The page does not contain report URLs with the expected structure")

                report_urls.extend(list(unique_urls_on_page))

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))

        return report_urls


if __name__ == "__main__":
    crawler = ForcepointHTMLCrawler()
    crawler.run()
