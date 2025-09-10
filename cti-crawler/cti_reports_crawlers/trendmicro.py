import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import TRENDMICRO_BASE_URL, TRENDMICRO_THREAT_REPORT_BASE_URL, \
    TRENDMICRO_THREAT_REPORT_DIR, TRENDMICRO_URL_TO_FILENAME_MAP_PATH

import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from config.root_settings import HEADERS, CHROME_DRIVER_PATH

class TrendMicroHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(TRENDMICRO_BASE_URL, TRENDMICRO_THREAT_REPORT_BASE_URL, TRENDMICRO_THREAT_REPORT_DIR,
                         TRENDMICRO_URL_TO_FILENAME_MAP_PATH, "trendmicro_report_crawler", use_headers=True)
    def get_report_urls(self):
        self.logger.info("Starting to fetch report URLs using Selenium browser automation.")
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")

        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)
        driver.set_page_load_timeout(60)
        report_urls = []

        try:
            self.logger.info(f"Navigating to page: {self.threat_report_base_url}")
            driver.get(self.threat_report_base_url)

            while True:
                try:
                    wait = WebDriverWait(driver, 10)
                    load_more_button = wait.until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "load-more-btn"))
                    )
                    driver.execute_script("arguments[0].click();", load_more_button)
                    self.logger.info("Clicked 'Load More' button. Waiting for new content...")
                    time.sleep(2)
                except TimeoutException:
                    self.logger.info("'Load More' button not found. All content is likely loaded.")
                    break
                except Exception as e:
                    self.logger.error(f"An unexpected error occurred while clicking 'Load More': {e}")
                    break
                
            self.logger.info("Parsing the fully loaded page source...")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            
            article_items = soup.find_all('article', class_='grid-item')
            self.logger.info(f"Found {len(article_items)} post entries in the HTML.")

            featured_article_div = soup.find('div', class_='promotional-content')
            if featured_article_div:
                featured_link_tag = featured_article_div.find('h2', class_='article-title').find('a')
                if featured_link_tag and featured_link_tag.get('href'):
                    href = featured_link_tag.get('href')
                    full_url = urljoin(self.base_url, href)
                    if full_url not in report_urls:
                        report_urls.append(full_url)
                        self.logger.info(f"Found featured article URL: {full_url}")

            for item in article_items:
                heading = item.find('h3', class_='heading')
                if heading:
                    link_tag = heading.find('a')
                    if link_tag and link_tag.get('href'):
                        href = link_tag.get('href')
                        full_url = urljoin(self.base_url, href)
                        if full_url not in report_urls:
                            report_urls.append(full_url)

        except Exception as e:
            self.logger.error("An error occurred during the Selenium process.")
            self.logger.exception(e)
            return report_urls
        finally:
            self.logger.info("Closing the Selenium browser.")
            driver.quit()

        self.logger.info(f"Finished fetching URLs. Total unique URLs found: {len(report_urls)}")
        return report_urls
    
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-1][:-5]
        return report_name
    
    # def get_report_urls(self):
    #     page_number = 0  # Maximum 238 confirmed on 07/11/2020
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
    #             # Every page has 10 articles
    #             page_url = os.path.join(page_url, "page", str(page_number))

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "html.parser")
    #             title_list = soup.find_all(class_="post-title")
    #             if len(title_list) == 0:
    #                 raise Exception("The page does not contain report URLs")

    #             report_url_pattern = re.compile(
    #                 r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    #             for title in title_list:
    #                 report_url = re.findall(report_url_pattern, str(title))[0]
    #                 report_urls.append(report_url)

    #         except Exception as e:
    #             page_failed_count += 1
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))
    #         if page_number>1:
    #             break
    #     return report_urls


if __name__ == "__main__":
    crawler = TrendMicroHTMLCrawler()
    crawler.run()
