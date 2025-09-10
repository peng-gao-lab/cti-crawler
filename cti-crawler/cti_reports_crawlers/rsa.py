from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import RSA_BASE_URL, RSA_THREAT_REPORT_BASE_URL, RSA_THREAT_REPORT_DIR, \
    RSA_URL_TO_FILENAME_MAP_PATH
import os

class RSAHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(RSA_BASE_URL, RSA_THREAT_REPORT_BASE_URL, RSA_THREAT_REPORT_DIR,
                         RSA_URL_TO_FILENAME_MAP_PATH, "rsa_report_crawler", use_headers=True)

    def get_report_urls(self):
        page_number = 0
        page_failed_count = 0
        report_urls = []

        while True:
            if page_failed_count > 5:
                self.logger.warning("Failed page URLs greater than 5. Exit.")
                break

            page_number += 1
            self.logger.info("Crawling report URLs for page {}".format(page_number))

            page_url = self.threat_report_base_url
            if page_number > 1:
                page_url = os.path.join(self.threat_report_base_url, "page", str(page_number))

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                
                article_list = soup.find_all("article", class_="blog-articles-item")

                if not article_list:
                    self.logger.info(f"No articles found on page {page_number}. Assuming it's the last page.")
                    break  

                for article in article_list:
                    link_tag = article.find("a")
                    if link_tag and link_tag.has_attr("href"):
                        report_urls.append(link_tag["href"])

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))
        return report_urls
    
    # def get_report_urls(self):
    #     # Only 1 page available
    #     self.logger.info("Crawling report URLs for page {}".format(1))
    #     page_url = self.threat_report_base_url
    #     report_urls = []

    #     try:
    #         response = self.scraper.scrape(page_url)
    #         soup = BeautifulSoup(response.text, "html.parser")
    #         title_list = soup.find_all(class_="c57-title")
    #         if len(title_list) == 0:
    #             raise Exception("The page does not contain report URLs")

    #         for title in title_list:
    #             hrefs = title.find_all("a")
    #             for href in hrefs:
    #                 report_urls.append(self.base_url + href["href"])

    #     except Exception as e:
    #         self.logger.exception(e)
    #         self.logger.warning("Page {} failed".format(1))

    #     return report_urls


if __name__ == "__main__":
    crawler = RSAHTMLCrawler()
    crawler.run()
