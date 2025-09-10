import time
from selenium import webdriver
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import UNIT42_PALOALTO_BASE_URL, UNIT42_PALOALTO_THREAT_REPORT_BASE_URL, \
    UNIT42_PALOALTO_THREAT_REPORT_DIR, UNIT42_PALOALTO_URL_TO_FILENAME_MAP_PATH
from config.root_settings import CHROME_DRIVER_PATH

# from bs4 import BeautifulSoup
# import os
from selenium.webdriver.common.by import By
class Unit42PaloAltoHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(UNIT42_PALOALTO_BASE_URL, UNIT42_PALOALTO_THREAT_REPORT_BASE_URL, UNIT42_PALOALTO_THREAT_REPORT_DIR,
                         UNIT42_PALOALTO_URL_TO_FILENAME_MAP_PATH, "unit42_paloalto_report_crawler")
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-2]
        return report_name

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
        #hrefs_prev = None

        while True:
            # Keep clicking the "See more" button until the end
            try:
                count += 1
                self.logger.info("Clicking 'See more' button for {} times".format(count))
                see_more_button = driver.find_element(By.CSS_SELECTOR, "a.l-btn") #driver.find_elements_by_css_selector("div.loadmore.text-center.loadmore_main2 > button")[0]
                driver.execute_script("arguments[0].click();", see_more_button)

                time.sleep(2)

                # Get current hrefs
                # hrefs = []
                # for title in driver.find_elements_by_xpath("//h3[@class='h5 news__title mb-15']/a"):
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
            except Exception as e:
                self.logger.exception(e)
                break
            time.sleep(3)

        # Get all hrefs
        title_list = driver.find_elements(By.XPATH, "//h4[@class='post-title']/parent::a") #title_list = driver.find_elements_by_xpath("//h3[@class='h5 news__title mb-15']/a")
        self.logger.info("Crawled {} articles".format(len(title_list)))
        for title in title_list:
            report_urls.append(title.get_property('href'))

        driver.close()

        return report_urls


if __name__ == "__main__":
    crawler = Unit42PaloAltoHTMLCrawler()
    crawler.run()
