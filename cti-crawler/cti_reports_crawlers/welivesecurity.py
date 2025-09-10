import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import WELIVESECURITY_BASE_URL, WELIVESECURITY_THREAT_REPORT_BASE_URL, \
    WELIVESECURITY_THREAT_REPORT_DIR, WELIVESECURITY_URL_TO_FILENAME_MAP_PATH
import time

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from utils.multithreaded_task_scheduler import MultiThreadedTaskScheduler
from config.root_settings import NUM_THREADS_DOWNLOAD_HTML
from selenium.webdriver.support import expected_conditions as EC
from config.root_settings import CHROME_DRIVER_PATH
from selenium import webdriver
from selenium.webdriver.common.by import By
import threading
import json

class WeLiveSecurityHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(WELIVESECURITY_BASE_URL, WELIVESECURITY_THREAT_REPORT_BASE_URL,
                         WELIVESECURITY_THREAT_REPORT_DIR, WELIVESECURITY_URL_TO_FILENAME_MAP_PATH,
                         "welivesecurity_report_crawler")
        self.thread_local = threading.local()   
        self.drivers_to_close = []
    
    @staticmethod
    def get_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)
        return driver
    
    def get_report_urls(self):
        page_number = 0  # Maximum 263 confirmed on 07/15/2020
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
                page_url = os.path.join(page_url, "?page=" + str(page_number))

            try:
                response = self.scraper.scrape(page_url)
                soup = BeautifulSoup(response.text, "html.parser")
                title_list = soup.find_all("div", class_="article-list-card")
                if len(title_list) == 0:
                    raise Exception("The page does not contain report URLs")

                tmp_report_urls = []
                for article in title_list:
                    link_tag = article.find('a', href=True)
                    if link_tag:
                        full_url = self.base_url + link_tag['href']
                        tmp_report_urls.append(full_url)
                
                if not tmp_report_urls:
                    raise Exception("Could not extract any URLs from the article list.")
                
                report_urls.extend(tmp_report_urls)
            except Exception as e:
                page_failed_count += 1
                self.logger.exception(e)
                self.logger.warning("Page {} failed".format(page_number))
            time.sleep(3)
        return report_urls

    def get_report_html_with_selenium(self, report_url):
        if not hasattr(self.thread_local, 'driver'):
            self.logger.info(f"Thread {threading.get_ident()}: No driver found, creating a new one.")
            driver = self.get_driver()
            self.thread_local.driver = driver
            with self.lock:
                self.drivers_to_close.append(driver)
        
        driver = self.thread_local.driver
        
        try:
            driver.get(report_url)
            
            # try:
            #     cookie_close_button = WebDriverWait(driver, 10).until(
            #         EC.element_to_be_clickable((By.CSS_SELECTOR, '.onetrust-close-btn-handler'))
            #     )
            #     #self.logger.info(f"Thread {threading.get_ident()}: Cookie banner found on {report_url}. Clicking close button.")
            #     cookie_close_button.click()
            #     time.sleep(1)
            # except TimeoutException:
            #     #self.logger.info(f"Thread {threading.get_ident()}: No cookie banner found on {report_url}, proceeding.")
            #     pass

            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.article-body")))
            return driver.page_source
        
        except (WebDriverException, TimeoutException):
            self.logger.exception(f"CRITICAL FAILURE while downloading HTML from {report_url}")
            
            # try:
            #     report_name = self.get_report_name(report_url)
            #     timestamp = int(time.time())
            #     error_screenshot_path = os.path.join(self.threat_report_dir, f"final_error_{report_name}_{timestamp}.png")
            #     driver.save_screenshot(error_screenshot_path)
            #     self.logger.info(f"Saved FINAL error screenshot to {error_screenshot_path}")
            # except Exception as screenshot_error:
            #     self.logger.error(f"Could not save screenshot: {screenshot_error}")

            return None
        
    def run(self):
        self.logger.info("Crawling report HTML files --- start")
        try:
            if not os.path.exists(self.threat_report_dir):
                os.makedirs(self.threat_report_dir)

            self.logger.info("Crawling all report URLs --- start")
            self.report_urls = self.get_report_urls()
            self.logger.info(f"Crawling all report URLs --- done. Found {len(self.report_urls)} URLs.")

            urls_to_filename_map = {}
            if os.path.exists(self.urls_to_filename_map_path):
                with open(self.urls_to_filename_map_path, "r") as read_file:
                    urls_to_filename_map = json.load(read_file)

            def report_urls_handler(url):
                report_name = self.get_report_name(url)
                report_file_path = self.get_file_path(report_name)
                
                self.lock.acquire()
                already_exists = url in urls_to_filename_map or os.path.exists(report_file_path)
                self.lock.release()

                if already_exists:
                    self.logger.info(f"{report_file_path} already exists, skipping.")
                else:
                    report_html = self.get_report_html_with_selenium(url)
                    if report_html:
                        with open(report_file_path, "w", encoding='utf-8') as f:
                            f.write(report_html)
                            self.logger.info(f"Finished crawling: {report_file_path}")

                        try:
                            self.lock.acquire()
                            urls_to_filename_map[url] = report_name
                            with open(self.urls_to_filename_map_path, "w+") as write_file:
                                json.dump(urls_to_filename_map, write_file)
                        finally:
                            self.lock.release()
            
            self.logger.info(f"Starting multi-threaded download with {NUM_THREADS_DOWNLOAD_HTML} threads.")
            mtts = MultiThreadedTaskScheduler(num_threads=NUM_THREADS_DOWNLOAD_HTML, 
                                              fn=report_urls_handler, 
                                              logger_prefix=self.crawler_name,
                                              tasks=list(self.report_urls)) 
            mtts.start()
            mtts.wait()

        except Exception as e:
            self.logger.error("An exception occurred in the main run function", exc_info=True)
        finally:
            self.logger.info(f"Closing all {len(self.drivers_to_close)} browser instances.")
            for driver in self.drivers_to_close:
                try:
                    driver.quit()
                except Exception as e:
                    self.logger.error(f"Error closing a driver: {e}")

        self.logger.info("Crawling welivesecurity HTML files --- done")
        
if __name__ == "__main__":
    crawler = WeLiveSecurityHTMLCrawler()
    crawler.run()
