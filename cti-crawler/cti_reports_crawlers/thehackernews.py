import time
from selenium import webdriver
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import THEHACKERNEWS_BASE_URL, THEHACKERNEWS_THREAT_REPORT_BASE_URL, \
    THEHACKERNEWS_THREAT_REPORT_DIR, THEHACKERNEWS_URL_TO_FILENAME_MAP_PATH
from config.root_settings import CHROME_DRIVER_PATH

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
class TheHackerNewsHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(THEHACKERNEWS_BASE_URL, THEHACKERNEWS_THREAT_REPORT_BASE_URL, THEHACKERNEWS_THREAT_REPORT_DIR,
                         THEHACKERNEWS_URL_TO_FILENAME_MAP_PATH, "thehackernews_report_crawler")

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
        report_urls = []
        driver = self.get_driver()
        driver.get(self.threat_report_base_url)
        count = 0

        while True:
            # Keep clicking the "Next Page" button until the end
            try:
                count += 1
                self.logger.info("Clicking 'Next Page' button for {} times".format(count))

                # Find hrefs on the current page
                title_list = driver.find_elements_by_xpath("//div[@class='body-post clear']/a")
                for title in title_list:
                    report_urls.append(title.get_property('href'))

                # Click the "Next Page" button
                next_page_button = driver.find_element_by_xpath('//*[@id="Blog1_blog-pager-older-link"]')
                driver.execute_script("arguments[0].click();", next_page_button)
            except Exception as e:
                self.logger.exception(e)
                break

            time.sleep(1)

        driver.close()

        return report_urls


if __name__ == "__main__":
    crawler = TheHackerNewsHTMLCrawler()
    crawler.run()
