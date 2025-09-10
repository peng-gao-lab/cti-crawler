import os
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import KASPERSKYDAILY_BASE_URL, KASPERSKYDAILY_THREAT_REPORT_BASE_URL, \
    KASPERSKYDAILY_THREAT_REPORT_DIR, KASPERSKYDAILY_URL_TO_FILENAME_MAP_PATH


class KasperskyDailyHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(KASPERSKYDAILY_BASE_URL, KASPERSKYDAILY_THREAT_REPORT_BASE_URL, KASPERSKYDAILY_THREAT_REPORT_DIR,
                         KASPERSKYDAILY_URL_TO_FILENAME_MAP_PATH, "kasperskydaily_report_crawler")
        
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-3] 
        return report_name
    
    def get_report_urls(self):
        page_number = 0  # Maximum 140 confirmed on 08/25/2020
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
                # Every page has 6 articles
                page_url = os.path.join(page_url, "page", str(page_number), '?orderby=latest_first&db_posts_per_page=100#038;db_posts_per_page=100#bloglisting')

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                
                h3s = soup.findAll("h3", attrs={"class": "c-card__title"})

                for h3 in h3s:
                    a = h3.find("a")
                    report_url = a['href']
                    report_urls.append(report_url)

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))
        return report_urls

    # def get_report_name(self, report_url):
    #     return report_url.replace(os.path.join(self.base_url, "blog"), "").strip("/").replace("/", ":") + ".html"

    # def get_file_path(self, report_name):
    #     # Overload parent method
    #     return os.path.join(self.threat_report_dir, report_name)

if __name__ == "__main__":
    crawler = KasperskyDailyHTMLCrawler()
    crawler.run()
