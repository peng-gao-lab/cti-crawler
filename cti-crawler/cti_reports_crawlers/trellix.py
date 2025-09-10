import os
#import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import Trellix_BASE_URL, Trellix_THREAT_REPORT_BASE_URL, \
    Trellix_THREAT_REPORT_DIR, Trellix_URL_TO_FILENAME_MAP_PATH
from config.root_settings import HEADERS, CHROME_DRIVER_PATH
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
class TrellixHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(Trellix_BASE_URL, Trellix_THREAT_REPORT_BASE_URL, Trellix_THREAT_REPORT_DIR,
                         Trellix_URL_TO_FILENAME_MAP_PATH, "trellix_report_crawler")
    def get_report_urls(self):

        options = webdriver.ChromeOptions()
        options.add_argument("--headless") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)
        driver.set_page_load_timeout(30) 

        try:
            self.logger.info(f"Navigating to page: {self.threat_report_base_url}")
            driver.get(self.threat_report_base_url)

            while True:
                try:
                    wait = WebDriverWait(driver, 10)
                    show_more_button = wait.until(
                        EC.element_to_be_clickable((By.ID, "show-more-data"))
                    )
                    
                    driver.execute_script("arguments[0].click();", show_more_button)
                    self.logger.info("Clicked 'Show More' button. Waiting for new content...")
                    
                    time.sleep(2) 

                except TimeoutException:
                    self.logger.info("'Show More' button not found. All content is likely loaded.")
                    break
                except Exception as e:
                    self.logger.error(f"An unexpected error occurred while clicking 'Show More': {e}")
                    break
            
            self.logger.info("Parsing the fully loaded page source...")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            report_urls = []
            results_container = soup.find('div', id='mresults')
            if results_container:
                posts = results_container.find_all('div', class_='topiclisting')
                self.logger.info(f"Found {len(posts)} post entries in the HTML.")
                
                for post in posts:
                    link_tag = post.find('a')
                    if link_tag and link_tag.get('href'):
                        href = link_tag.get('href')
                        full_url = urljoin(self.base_url, href)
                        report_urls.append(full_url)
            
            self.logger.info(f"Finished fetching URLs. Total URLs found: {len(report_urls)}")
            return report_urls

        except Exception as e:
            self.logger.error("An error occurred during the Selenium process.")
            self.logger.exception(e)
            return [] 
        finally:
            self.logger.info("Closing the Selenium browser.")
            driver.quit()

        # self.api_session = requests.Session()
        # self.api_session.headers.update(HEADERS)
    # def get_report_urls(self):
    #     report_urls = []
    #     page_num = 0
    #     offset = 0

    #     self.logger.info("Starting to fetch report URLs from Trellix API.")
    #     while True:
    #         if page_num>2:
    #             break
    #         params = {'page': offset}
            
    #         self.logger.info(f"Crawling report URLs from API page {page_num} (offset={offset})")

    #         try:
    #             response = self.api_session.get(self.threat_report_base_url, params=params, timeout=90)
    #             response.raise_for_status()
                
    #             data = response.json()
                
    #             blogs = data.get('topics', [])
                
    #             if not blogs:
    #                 self.logger.info("No more blogs found. Stopping pagination.")
    #                 break

    #             for blog in blogs:
    #                 relative_url = blog.get('pagePath')
    #                 if relative_url:
    #                     full_url = urljoin(self.base_url, relative_url)
    #                     report_urls.append(full_url)

                

    #         except requests.exceptions.RequestException as e:
    #             self.logger.error(f"Failed to fetch API page {page_num}. Exception: {e}")
    #             break 
    #         except ValueError as e:
    #             self.logger.error(f"Failed to decode JSON from API response on page {page_num}. Exception: {e}")
    #             self.logger.info(f"Response text: {response.text}")
    #             break
    #         offset += 10
    #         page_num += 1
    #     self.logger.info(f"Finished fetching URLs. Total URLs found: {len(report_urls)}")
    #     return report_urls
    
    # def get_report_urls(self):
    #     page_number = 0  # Maximum 13 confirmed on 07/13/2020
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
    #             # Every page has 8 articles
    #             page_url = os.path.join(page_url, "?blog_entries_start=" + str((page_number-1)*8))

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "html.parser")
    #             title_list = soup.find_all(class_="c11v9")
    #             if len(title_list) == 0:
    #                 raise Exception("The page does not contain report URLs")

    #             if len(title_list) == 1:
    #                 if title_list[0].find("div", {"class": "btn btn-tertiary btn-44474D"}):  # "see more" page
    #                     raise Exception("The page does not contain report URLs")

    #             for title in title_list:
    #                 hrefs = title.find_all("a")
    #                 if len(hrefs) > 0:
    #                     report_url = self.base_url + hrefs[0]["href"]
    #                     report_urls.append(report_url)

    #         except Exception as e:
    #             page_failed_count += 1
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))

    #     return report_urls


if __name__ == "__main__":
    crawler = TrellixHTMLCrawler()
    crawler.run()
