import time
from selenium import webdriver
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import THREATPOST_BASE_URL, THREATPOST_THREAT_REPORT_BASE_URL, \
    THREATPOST_THREAT_REPORT_DIR, THREATPOST_URL_TO_FILENAME_MAP_PATH
from config.root_settings import CHROME_DRIVER_PATH

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
class ThreatPostHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(THREATPOST_BASE_URL, THREATPOST_THREAT_REPORT_BASE_URL, THREATPOST_THREAT_REPORT_DIR,
                         THREATPOST_URL_TO_FILENAME_MAP_PATH, "threatpost_report_crawler")

    @staticmethod
    def get_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')        
        driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)
        return driver

    def get_report_urls(self):
        # Use Selenium
        report_urls = set()
        driver = self.get_driver()
        driver.get(self.threat_report_base_url)
        count = 0
        #hrefs_prev = None
        fail_num = 0
        while True:
            # Keep clicking the "Load more latest news" button until the end
            try:
                if fail_num >= 5:
                    break
                initial_article_count = len(driver.find_elements(By.CSS_SELECTOR, "h2.c-card__title > a"))
                self.logger.info(f"current num of hef: {initial_article_count}")
                count += 1 # Maximum 539 confirmed on August 12, 2020
                self.logger.info("Clicking 'See more' button for {} times".format(count))
                see_more_button = driver.find_elements_by_css_selector("#load_more_news")[0]
                if not see_more_button:
                    break
                driver.execute_script("arguments[0].click();", see_more_button)

                #time.sleep(4)
                WebDriverWait(driver, 20).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "h2.c-card__title > a")) > initial_article_count
                )
                # Get current hrefs
                # hrefs = []
                # for title in driver.find_elements_by_css_selector("h2.c-card__title > a"):
                #     hrefs.append(title.get_property('href'))

                # self.logger.info("Current number of hrefs: {}".format(len(hrefs)))

                # if hrefs_prev is None:
                #     hrefs_prev = hrefs
                # else:
                #     if hrefs_prev == hrefs:
                #         self.logger.info("No new hrefs. Exit loop.")
                #         break
                #     else:
                #         hrefs_prev = hrefs

                if count > 1000:
                    # Only crawl the latest 1000 pages
                    self.logger.info("Clicking 'See more' for more than {} times. Exit loop.".format(1000))
                    break
                fail_num = 0
            except Exception as e:
                self.logger.exception(e)
                fail_num += 1
                #break

            time.sleep(1.5)

        # Get all hrefs
        title_list = driver.find_elements_by_css_selector("h2.c-card__title > a")
        self.logger.info("Crawled {} articles".format(len(title_list)))
        for title in title_list:
            report_urls.add(title.get_property('href'))

        driver.close()

        return report_urls


if __name__ == "__main__":
    crawler = ThreatPostHTMLCrawler()
    crawler.run()
