import time
from selenium import webdriver
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import TRUSTWAVE_BASE_URL, TRUSTWAVE_THREAT_REPORT_BASE_URL, \
    TRUSTWAVE_THREAT_REPORT_DIR, TRUSTWAVE_URL_TO_FILENAME_MAP_PATH
#from config.root_settings import CHROME_DRIVER_PATH
import os
from bs4 import BeautifulSoup
class TrustwaveHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(TRUSTWAVE_BASE_URL, TRUSTWAVE_THREAT_REPORT_BASE_URL, TRUSTWAVE_THREAT_REPORT_DIR,
                         TRUSTWAVE_URL_TO_FILENAME_MAP_PATH, "trustwave_report_crawler")

    def get_report_urls(self):
        report_urls = []
        page_number = 0
        page_failed_count = 0

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
                if not response:
                    self.logger.warning(f"No response for page {page_number}. Ending crawl.")
                    break
                    
                soup = BeautifulSoup(response.text, "html.parser")
                
                article_links = soup.find_all("a", class_="tw-blog__card")

                if not article_links:
                    self.logger.info(f"No articles found on page {page_number}. Assuming it's the last page.")
                    break

                for link in article_links:
                    if link.has_attr('href'):
                        report_urls.append(link['href'])

            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))
        
        return report_urls

    # @staticmethod
    # def get_driver():
    #     chrome_options = webdriver.ChromeOptions()
    #     chrome_options.add_argument('--headless')
    #     chrome_options.add_argument('--no-sandbox')
    #     chrome_options.add_argument('--disable-dev-shm-usage')        
    #     driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)
    #     return driver

    # def get_report_urls(self):
    #     # Use Selenium
    #     report_urls = []
    #     driver = self.get_driver()
    #     driver.get(self.threat_report_base_url)
    #     count = 0
    #     hrefs_prev = None

    #     while True:
    #         # Keep clicking the "LOAD MORE" button until the end
    #         try:
    #             count += 1  # Maximum 27 confirmed on 07/16/2020
    #             self.logger.info("Clicking 'LOAD MORE' button for {} times".format(count))
    #             load_more_button = driver.find_element_by_id("loadmore")
    #             driver.execute_script("arguments[0].click();", load_more_button)

    #             # Get current hrefs
    #             hrefs = []
    #             for title in driver.find_elements_by_xpath("//h1[@class='blog-post-title mbs']/a"):
    #                 hrefs.append(title.get_property('href'))

    #             self.logger.info("Current number of hrefs: {}".format(len(hrefs)))

    #             if hrefs_prev is None:
    #                 hrefs_prev = hrefs
    #             else:
    #                 if hrefs_prev == hrefs:
    #                     self.logger.info("No new hrefs. Exit loop.")
    #                     break
    #                 else:
    #                     hrefs_prev = hrefs

    #             if count > 1000:
    #                 # Only crawl the latest 1000 pages
    #                 self.logger.info("Clicking 'LOAD MORE' for more than {} times. Exit loop.".format(1000))
    #                 break
    #         except Exception as e:
    #             self.logger.exception(e)
    #             break

    #         time.sleep(1)
    #         break
    #     # Get all hrefs
    #     title_list = driver.find_elements_by_xpath("//h1[@class='blog-post-title mbs']/a")
    #     self.logger.info("Crawled {} articles".format(len(title_list)))
    #     for title in title_list:
    #         report_urls.append(title.get_property('href'))

    #     driver.close()

    #     return report_urls


if __name__ == "__main__":
    crawler = TrustwaveHTMLCrawler()
    crawler.run()
