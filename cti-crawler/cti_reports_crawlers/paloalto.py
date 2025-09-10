import time
from selenium import webdriver
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import PALOALTO_BASE_URL, PALOALTO_THREAT_REPORT_BASE_URL, \
    PALOALTO_THREAT_REPORT_DIR, PALOALTO_URL_TO_FILENAME_MAP_PATH, UNIT42_PALOALTO_BASE_URL
from config.root_settings import CHROME_DRIVER_PATH
import os

import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from config.root_settings import NUM_THREADS_DOWNLOAD_HTML
import json
from utils.multithreaded_task_scheduler import MultiThreadedTaskScheduler


class PaloAltoHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(PALOALTO_BASE_URL, PALOALTO_THREAT_REPORT_BASE_URL, PALOALTO_THREAT_REPORT_DIR,
                         PALOALTO_URL_TO_FILENAME_MAP_PATH, "paloalto_report_crawler")
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
        self.logger.info("Starting Palo Alto blog URL crawl.")
        all_report_urls = set()
        driver = self.get_driver()
        
        try:
            self.logger.info(f"Navigating to base URL: {self.threat_report_base_url}")
            driver.get(self.threat_report_base_url)
            
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'button-link') and contains(text(), 'See all')]"))
            )
            
            category_links_elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'button-link') and contains(text(), 'See all')]")
            category_urls = [link.get_attribute('href') for link in category_links_elements]
            self.logger.info(f"Found {len(category_urls)} category pages to crawl.")

            for category_url in category_urls:
                if not category_url or category_url == UNIT42_PALOALTO_BASE_URL:
                    continue
                self.logger.info(f"Crawling category page: {category_url}")
                driver.get(category_url)

                while True:
                    try:
                        initial_article_count = len(driver.find_elements(By.CSS_SELECTOR, "div.article-card h2.title a"))
                        load_more_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Load more blogs')]")
                        visible_button = None
                        for button in load_more_buttons:
                            if button.is_displayed():
                                visible_button = button
                                break
                        
                        if visible_button:
                            driver.execute_script("arguments[0].scrollIntoView(true);", visible_button)
                            time.sleep(1)
                            driver.execute_script("arguments[0].click();", visible_button)
                            self.logger.info(f"Clicked 'Load more blogs' on {category_url}. Waiting for new content...")
                            #time.sleep(3)
                            #print(len(driver.find_elements(By.CSS_SELECTOR, "div.article-card h2.title a")))
                            WebDriverWait(driver, 3).until(
                                lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.article-card h2.title a")) > initial_article_count
                            )
                        else:
                            self.logger.info(f"No visible 'Load more blogs' button found. Assuming all content is loaded.")
                            break
                    except Exception as e:
                        self.logger.exception(e)
                        #self.logger.error(f"An error occurred while trying to click 'Load more blogs': {e}")
                        #break
                article_elements = driver.find_elements(By.CSS_SELECTOR, "div.article-card h2.title a")
                page_urls = {elem.get_attribute('href') for elem in article_elements}
                self.logger.info(f"Found {len(page_urls)} articles in category: {category_url}")
                all_report_urls.update(page_urls)
        except Exception as e:
            self.logger.exception(f"A critical error occurred during URL crawling: {e}")
        finally:
            driver.quit()

        self.logger.info(f"Total unique article URLs crawled: {len(all_report_urls)}")
        return list(all_report_urls)
    
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
            
            try:
                cookie_close_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '.onetrust-close-btn-handler'))
                )
                #self.logger.info(f"Thread {threading.get_ident()}: Cookie banner found on {report_url}. Clicking close button.")
                cookie_close_button.click()
                time.sleep(1)
            except TimeoutException:
                #self.logger.info(f"Thread {threading.get_ident()}: No cookie banner found on {report_url}, proceeding.")
                pass

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".article-container > section.article")))
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
                tasks=list(self.report_urls)
            ) 
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

        self.logger.info("Crawling paloalto HTML files --- done")

    # def get_report_urls(self):
    #     # Use Selenium
    #     report_urls = []
    #     driver = self.get_driver()
    #     driver.get(self.threat_report_base_url)
    #     count = 0
    #     hrefs_prev = None

    #     while True:
    #         # Keep clicking the "See more" button until the end
    #         try:
    #             count += 1  # Maximum 403 confirmed on 07/16/2020
    #             self.logger.info("Clicking 'See more' button for {} times".format(count))
    #             see_more_button = driver.find_elements_by_css_selector("div.loadmore.text-center.loadmore_main2 > button")[0]
    #             driver.execute_script("arguments[0].click();", see_more_button)

    #             # Get current hrefs
    #             hrefs = []
    #             for title in driver.find_elements_by_css_selector("div.feed-card-content > h3 > a"):
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
    #                 self.logger.info("Clicking 'See more' for more than {} times. Exit loop.".format(1000))
    #                 break
    #         except Exception as e:
    #             self.logger.exception(e)
    #             break

    #         time.sleep(3)

    #     # Get all hrefs
    #     title_list = driver.find_elements_by_css_selector("div.feed-card-content > h3 > a")
    #     self.logger.info("Crawled {} articles".format(len(title_list)))
    #     for title in title_list:
    #         report_urls.append(title.get_property('href'))

    #     driver.close()

    #     return report_urls


if __name__ == "__main__":
    crawler = PaloAltoHTMLCrawler()
    crawler.run()
