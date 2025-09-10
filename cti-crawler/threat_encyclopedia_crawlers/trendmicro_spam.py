from utils.base_crawler import BaseCrawler
from bs4 import BeautifulSoup
import os
from config.threat_encyclopedia_crawlers_settings import TRENDMICRO_THREAT_REPORT_BASE_URL, \
    TRENDMICRO_THREAT_REPORT_SPAM_URL, TRENDMICRO_THREAT_REPORT_SPAM_DIR, TRENDMICRO_SPAM_URL_TO_FILENAME_MAP_PATH

#PAGE_LIMIT = 40
import re
from urllib.parse import urljoin
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
import os
from config.root_settings import CHROME_DRIVER_PATH

class TrendmicroHTMLSpamCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(TRENDMICRO_THREAT_REPORT_BASE_URL, TRENDMICRO_THREAT_REPORT_SPAM_URL,
                         TRENDMICRO_THREAT_REPORT_SPAM_DIR, TRENDMICRO_SPAM_URL_TO_FILENAME_MAP_PATH,
                         "threat_encyclopedia_trendmicro_spam")

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
        report_urls = []
        self.logger.info("Initializing a dedicated browser for URL discovery.")
        driver = self.get_driver()

        try:
            self.logger.info("Navigating to the first page to determine the total page count.")
            driver.get(self.threat_report_base_url)
            
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.paginationContainer'))
                )
            except TimeoutException:
                self.logger.warning("Pagination container not found. Assuming a single page.")

            soup = BeautifulSoup(driver.page_source, "lxml")
            
            total_pages = 1
            pagination_container = soup.find('div', class_='paginationContainer')
            if pagination_container:
                page_text = pagination_container.find('li').get_text(strip=True)
                match = re.search(r'of\s+(\d+)', page_text)
                if match:
                    total_pages = int(match.group(1))
            
            self.logger.info(f"Found {total_pages} pages of malware reports.")

            for page_number in range(1, total_pages + 1):
                self.logger.info(f"Crawling report URLs for page {page_number}")
                
                page_url = f"{self.threat_report_base_url}/page/{page_number}" if page_number > 1 else self.threat_report_base_url

                driver.get(page_url)
                
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.listContent"))
                )

                soup = BeautifulSoup(driver.page_source, "lxml")
                
                link_elements = soup.select('div.ContainerListTitle1 > a')
                for link in link_elements:
                    relative_url = link.get('href')
                    if relative_url:
                        absolute_url = urljoin(self.base_url, relative_url)
                        if absolute_url not in report_urls:
                            report_urls.append(absolute_url)
                self.logger.info(f"Successfully finished crawling report URLs for page {page_number}")

        except Exception as e:
            self.logger.exception("A critical error occurred during URL discovery.")
        finally:
            self.logger.info("Closing the dedicated browser for URL discovery.")
            driver.quit() 

        return report_urls
    # def get_report_urls(self):
    #     report_urls = []

    #     self.logger.info("Determining the total number of pages to crawl.")
    #     try:
    #         response = self.scraper.scrape(self.threat_report_base_url)
    #         soup = BeautifulSoup(response.text, "lxml")
            
    #         pagination_container = soup.find('div', class_='paginationContainer')
    #         if pagination_container:
    #             page_text = pagination_container.find('li').get_text(strip=True)
    #             match = re.search(r'of\s+(\d+)', page_text)
    #             if match:
    #                 total_pages = int(match.group(1))
    #             else:
    #                 total_pages = 1 
    #         else:
    #             total_pages = 1
            
    #         self.logger.info(f"Found {total_pages} pages of malware reports.")

    #     except Exception as e:
    #         self.logger.exception(e)
    #         self.logger.error("Failed to determine the total number of pages. Aborting crawl.")
    #         return []

    #     for page_number in range(1, total_pages + 1):
    #         self.logger.info(f"Crawling report URLs for page {page_number}")
            
    #         if page_number == 1:
    #             page_url = self.threat_report_base_url
    #         else:
    #             page_url = f"{self.threat_report_base_url}/page/{page_number}"

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "lxml")
                
    #             link_elements = soup.select('div.ContainerListTitle1 > a')

    #             for link in link_elements:
    #                 relative_url = link.get('href')
    #                 if relative_url:
    #                     absolute_url = urljoin(self.base_url, relative_url)
    #                     report_urls.append(absolute_url)

    #             self.logger.info(f"Successfully finished crawling report URLs for page {page_number}")

    #         except Exception as e:
    #             self.logger.exception(e)
    #             self.logger.warning(f"Crawling failed for page {page_number}")
    #         if page_number>1:
    #             break
    #     return report_urls
    
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

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.TEArticle")))
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

        self.logger.info("Crawling paloalto HTML files --- done")
    # def get_report_urls(self):
    #     report_urls = []

    #     for page_number in range(1, PAGE_LIMIT + 1):
    #         self.logger.info("Crawling report URLs for page {}".format(page_number))

    #         try:
    #             url = self.threat_report_base_url + "/page/" + str(page_number)
    #             req = self.scraper.scrape(url)
    #             soup = BeautifulSoup(req.text, "lxml")

    #             divs = soup.findAll('div', attrs={"class": "ContainerListTitle1"})
    #             for i in range(len(divs)):
    #                 href = divs[i].find('a')['href'].strip('\\')
    #                 report_url = self.base_url + href
    #                 report_urls.append(report_url)

    #             self.logger.info("Successfully finished crawling report URLs for page {}".format(page_number))

    #         except Exception as e:
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))

    #     return report_urls

    def get_file_path(self, report_url):
        split_partial_url = report_url.replace(self.threat_report_base_url, "").split("/")
        spam_name = split_partial_url[len(split_partial_url) - 1]
        file_path = os.path.join(self.threat_report_dir, spam_name + ".html")

        return file_path


if __name__ == "__main__":
    crawler = TrendmicroHTMLSpamCrawler()
    crawler.run()
