# import os
# import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import ZSCALER_BASE_URL, ZSCALER_THREAT_REPORT_BASE_URL, \
    ZSCALER_THREAT_REPORT_DIR, ZSCALER_URL_TO_FILENAME_MAP_PATH

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import urljoin
from config.root_settings import CHROME_DRIVER_PATH
class ZscalerHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(ZSCALER_BASE_URL, ZSCALER_THREAT_REPORT_BASE_URL, ZSCALER_THREAT_REPORT_DIR,
                         ZSCALER_URL_TO_FILENAME_MAP_PATH, "zscaler_report_crawler")
        
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-1]
        return report_name
    
    def get_report_urls(self):

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)
        driver.set_page_load_timeout(30)

        report_urls = []
        try:
            self.logger.info(f"Navigating to page: {self.threat_report_base_url}")
            driver.get(self.threat_report_base_url)
            while True:
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.blog_post_filter_module_teaserCard__a_4Yd")))

                first_card_on_page = driver.find_element(By.CSS_SELECTOR, "div.blog_post_filter_module_teaserCard__a_4Yd")

                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                blog_cards = soup.find_all('div', class_='blog_post_filter_module_teaserCard__a_4Yd')
                if not blog_cards:
                    self.logger.info("No blog cards found on the page.")
                    break

                for card in blog_cards:
                    link_tag = card.find('a')
                    if link_tag and link_tag.get('href'):
                        full_url = urljoin(self.base_url, link_tag['href'])
                        if full_url not in report_urls:
                            report_urls.append(full_url)

                try:
                    next_buttons = driver.find_elements(By.CSS_SELECTOR, "li.rc-pagination-next")

                    if not next_buttons or next_buttons[0].get_attribute('aria-disabled') == 'true':
                        self.logger.info("Reached the last page.")
                        break
                    
                    driver.execute_script("arguments[0].click();", next_buttons[0])

                    wait.until(EC.staleness_of(first_card_on_page))

                except Exception as e:
                    self.logger.error(f"An unexpected error occurred during pagination check: {e}")
                    break
        except Exception as e:
            self.logger.error("An error occurred during the Selenium process.")
            self.logger.exception(e)
        finally:
            self.logger.info(f"Closing the Selenium browser. Total URLs found: {len(report_urls)}")
            driver.quit()
            
        return report_urls
    
    # def get_report_urls(self):
    #     page_number = 0  # Maximum 78 confirmed on 03/20/2022
    #     page_failed_count = 0
    #     report_urls = []
    #     title_list_prev = None

    #     while True:  # For each page
    #         if page_failed_count > 5:
    #             self.logger.warning("Failed page URLs greater than 5. Exit.")
    #             break

    #         self.logger.info("Crawling report URLs for page {}".format(page_number))

    #         # Every page has 10 articles
    #         page_url = self.threat_report_base_url + "?page=" + str(page_number)
    #         page_number += 1

    #         try:
    #             response = self.scraper.scrape(page_url)
    #             soup = BeautifulSoup(response.text, "html.parser")
    #             title_list = soup.find_all(class_="text-darkBlue typography-h5") #text-darkBlue typography-h5 fw-400 fg-color-black
    #             if len(title_list) == 0:
    #                 raise Exception("The page does not contain report URLs")

    #             # Check if title_list for current page is different than previous page
    #             if title_list_prev is None:
    #                 title_list_prev = title_list
    #             else:
    #                 if title_list == title_list_prev:
    #                     raise Exception("Could not find anymore urls")
    #                 else:
    #                     title_list_prev = title_list

    #             for title_tag in title_list:
    #                 title = title_tag.text
    #                 url = soup.find("a", attrs={ 'title': title })
    #                 if not url is None:
    #                     report_url = url['href']
    #                     report_urls.append(report_url)

    #         except Exception as e:
    #             page_failed_count += 1
    #             self.logger.exception(e)
    #             self.logger.warning("Page {} failed".format(page_number))
    #         if page_number>1:
    #             break
    #     return report_urls


if __name__ == "__main__":
    crawler = ZscalerHTMLCrawler()
    crawler.run()
