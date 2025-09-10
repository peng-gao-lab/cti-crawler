import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import MCAFEE_BASE_URL, MCAFEE_THREAT_REPORT_BASE_URL, \
    MCAFEE_THREAT_REPORT_DIR, MCAFEE_URL_TO_FILENAME_MAP_PATH

import time
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from config.root_settings import CHROME_DRIVER_PATH
from config.root_settings import NUM_THREADS_DOWNLOAD_HTML
from utils.multithreaded_task_scheduler import MultiThreadedTaskScheduler
import json

class McafeeHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(MCAFEE_BASE_URL, MCAFEE_THREAT_REPORT_BASE_URL, MCAFEE_THREAT_REPORT_DIR,
                         MCAFEE_URL_TO_FILENAME_MAP_PATH, "mcafee_report_crawler", use_headers=False)
        self.thread_local = threading.local()
        self.drivers_to_close = []
    @staticmethod
    def get_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)
        return driver

    def get_report_urls(self):

        self.logger.info("Starting crawl with Selenium to get report URLs...")
        all_report_urls = set()
        driver = self.get_driver()
        wait = WebDriverWait(driver, 20)

        category_urls = []
        try:
            self.logger.info(f"Accessing main page: {self.threat_report_base_url}")
            driver.get(self.threat_report_base_url)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.topics h3 a")))
            topic_divs = driver.find_elements(By.CSS_SELECTOR, "div.topics")
            if not topic_divs:
                self.logger.warning("Could not find any category divs on the main page.")
                driver.quit()
                return []
            for div in topic_divs:
                link_element = div.find_element(By.CSS_SELECTOR, "h3 a")
                category_url = link_element.get_attribute('href')
                if category_url:
                    category_urls.append(category_url)

            self.logger.info(f"Found {len(category_urls)} categories to crawl.")
        except (WebDriverException, TimeoutException) as e:
            self.logger.exception("Failed to scrape category URLs from the main page.")
            driver.quit()
            return []
        finally:
            driver.quit()

        for category_url in category_urls:
            driver = self.get_driver()
            wait = WebDriverWait(driver, 20)
            self.logger.info(f"--- Starting category: {category_url} ---")
            
            try:
                page_number = 1
                while True: 
                    current_page_url = f"{category_url.strip('/')}/page/{page_number}/" if page_number > 1 else category_url
                    self.logger.info(f"Crawling page {page_number}: {current_page_url}")
                    print(current_page_url)
                    try:
                        driver.get(current_page_url)
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.left-main-content")))
                    except TimeoutException:
                        self.logger.warning(f"Page load timed out for {current_page_url}. Assuming end of category.")
                        break
                    article_links = driver.find_elements(By.CSS_SELECTOR, "h5.card-title a")
                    if not article_links:
                        self.logger.info(f"No articles found on {current_page_url}. Ending crawl for this category.")
                        break
                    
                    for link in article_links:
                        report_url = link.get_attribute('href')
                        if report_url:
                            all_report_urls.add(report_url)
                    page_number += 1
                    time.sleep(1)
            except WebDriverException as e:
                self.logger.error(f"Error crawling category '{category_url}': {e}", exc_info=True)
            finally:
                self.logger.info(f"--- Finished category: {category_url}. ---")
                driver.quit()

        unique_urls = sorted(list(all_report_urls))
        self.logger.info(f"URL gathering finished. Found {len(unique_urls)} unique URLs.")
        return unique_urls
    
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
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "article")))
            return driver.page_source
        except (WebDriverException, TimeoutException) as e:
            self.logger.exception(f"Failed to download HTML from {report_url}")
            try:
                report_name = self.get_report_name(report_url)
                timestamp = int(time.time())
                error_screenshot_path = os.path.join(self.threat_report_dir, f"error_{report_name}_{timestamp}.png")
                driver.save_screenshot(error_screenshot_path)
                self.logger.info(f"Saved error screenshot to {error_screenshot_path}")
            except Exception as screenshot_error:
                self.logger.error(f"Could not save screenshot: {screenshot_error}")
            return None

    def run(self):
        self.logger.info("Crawling report HTML files --- start")
        try:
            if not os.path.exists(self.threat_report_dir):
                os.makedirs(self.threat_report_dir)

            self.logger.info("Crawling all report URLs --- start")
            self.report_urls = self.get_report_urls()
            self.logger.info(f"Crawling all report URLs --- done. Found {len(self.report_urls)} URLs.")

            if not self.report_urls:
                self.logger.warning("No URLs to download. Exiting.")
                return
            
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

        self.logger.info("Crawling mcafee HTML files --- done")

    
    # def get_report_urls(self):
    #     page_number = 0  # Maximum 32 confirmed on 08/25/2020
    #     page_failed_count = 0
    #     report_urls = []

    #     while True:  # For each page
    #         if page_failed_count > 5:
    #             self.logger.warning("Failed page URLs greater than 5. Exit.")
    #             break

    #         page_number += 1
    #         self.logger.info("Crawling report URLs for page {}".format(page_number))

    #         page_url = self.threat_report_base_url
    #         if page_number > 1:
    #             # Every page has 6 articles
    #             page_url = os.path.join(page_url, "page", str(page_number), '?orderby=latest_first&db_posts_per_page=100#038;db_posts_per_page=100#bloglisting')

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "html.parser")
                
    #             outer_div = soup.find("div", attrs={"class": "wrap-section padding-top-small padding-bottom-xs resources"})
    #             div_container_medium = outer_div.find("div", attrs={"class": "container medium"})
    #             div_row_same_height_parent = div_container_medium.find("div", attrs={"class": "row same-height-parent"})
    #             # print(div_row_same_height_parent)
    #             h3_reds = div_row_same_height_parent.findAll("h3", attrs={"class": "red"})

    #             if len(h3_reds) == 0:
    #                 raise Exception(f"No report urls found on page {page_number}")

    #             for h3 in h3_reds:
    #                 a = h3.find("a")
    #                 report_url =  a['href']
    #                 report_urls.append(report_url)

    #         except Exception as e:
    #             page_failed_count += 1
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))

    #     return report_urls


if __name__ == "__main__":
    crawler = McafeeHTMLCrawler()
    crawler.run()
