import os
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import NCCGROUP_BASE_URL, NCCGROUP_THREAT_REPORT_BASE_URL, \
    NCCGROUP_THREAT_REPORT_DIR, NCCGROUP_URL_TO_FILENAME_MAP_PATH

import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from config.root_settings import HEADERS, CHROME_DRIVER_PATH

class NCCGroupHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(NCCGROUP_BASE_URL, NCCGROUP_THREAT_REPORT_BASE_URL, NCCGROUP_THREAT_REPORT_DIR,
                         NCCGROUP_URL_TO_FILENAME_MAP_PATH, "nccgroup_report_crawler")
    def get_report_urls(self):
        """
        Fetches all blog post URLs from the NCC Group research blog by using a headless browser
        to interact with the "Show more" button and load all content dynamically.
        """
        self.logger.info("Starting to fetch report URLs using Selenium browser automation.")
        report_urls = []

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)
        driver.set_page_load_timeout(60)

        try:
            self.logger.info(f"Navigating to page: {self.threat_report_base_url}")
            driver.get(self.threat_report_base_url)
            page_num = 0
            while page_num<=1000:
                try:
                    show_more_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "js-show-more"))
                    )
                    driver.execute_script("arguments[0].click();", show_more_button)
                    self.logger.info(f"Clicked 'Show more' button. Page: {page_num + 1}. Waiting for new content to load...")
                    time.sleep(2)
                except TimeoutException:
                    self.logger.info("'Show more' button not found. All content is assumed to be loaded.")
                    break
                except ElementClickInterceptedException:
                    self.logger.warning("Could not click 'Show more' button due to interception. Retrying...")
                    driver.execute_script("window.scrollBy(0, 100);")
                    time.sleep(1)
                except Exception as e:
                    self.logger.error(f"An unexpected error occurred while clicking 'Show More': {e}")
                    break
                page_num+=1
            self.logger.info("Parsing the fully loaded page source to extract report URLs.")
            soup = BeautifulSoup(driver.page_source, "html.parser")

            content_hub = soup.find('div', id='content-hub-items')
            if content_hub:
                list_items = content_hub.find_all('div', class_='js-item')
                self.logger.info(f"Found {len(list_items)} post entries in the HTML.")
                
                for item in list_items:
                    link_tag = item.find('h3', class_='c-lb__title')
                    if link_tag and link_tag.find('a'):
                        href = link_tag.find('a')['href']
                        full_url = urljoin(self.base_url, href)
                        report_urls.append(full_url)

        except Exception as e:
            self.logger.error("An error occurred during the Selenium process.")
            self.logger.exception(e)
        finally:
            self.logger.info("Closing the Selenium browser.")
            driver.quit()

        self.logger.info(f"Finished fetching URLs. Total URLs found: {len(report_urls)}")
        return report_urls
    
    # def get_report_urls(self):
    #     page_number = 0 # 9 pages last checked 8/11/2020
    #     page_failed_count = 0
    #     report_urls = []

    #     while True:  # For each page
    #         if page_failed_count > 5:
    #             self.logger.warning("Failed page URLs greater than 5. Exit.")
    #             break

    #         page_number += 1
    #         self.logger.info("Crawling report URLs for page {}".format(page_number))

    #         page_url = self.threat_report_base_url + "/{}".format(page_number)

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "html.parser")
    #             article_list = soup.find_all("article") #, {"class": "post type-post"})
    #             if len(article_list) == 0:
    #                 raise Exception("The page does not contain report URLs")

    #             tmp_report_urls = []
    #             for article in article_list:
    #                 h1 = article.find("h1", {"class": "entry-title"})
    #                 a = h1.find("a")
    #                 report_url = a["href"]
    #                 tmp_report_urls.append(report_url)

    #             if len(tmp_report_urls) == 0:
    #                 raise Exception("The page does not contain report URLs")
    #             for report_url in tmp_report_urls:
    #                 self.report_urls.append(report_url)

    #         except Exception as e:
    #             page_failed_count += 1
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))

    #     return report_urls

    def get_report_name(self, report_url):
        return report_url.replace(self.base_url, "").strip("/").replace("/", ":") + ".html"

    def get_file_path(self, report_name):
        # Overload parent method
        return os.path.join(self.threat_report_dir, report_name)

if __name__ == "__main__":
    crawler = NCCGroupHTMLCrawler()
    crawler.run()
