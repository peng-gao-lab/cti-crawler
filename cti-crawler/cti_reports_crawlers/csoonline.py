import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import CSOONLINE_BASE_URL, CSOONLINE_SECURITY_THREAT_REPORT_BASE_URL, \
    CSOONLINE_VULERNABILITIES_THREAT_REPORT_BASE_URL, CSOONLINE_CYBERWARFARE_THREAT_REPORT_BASE_URL, \
    CSOONLINE_CYBERCRIME_THREAT_REPORT_BASE_URL, CSOONLINE_THREAT_REPORT_DIR, CSOONLINE_URL_TO_FILENAME_MAP_PATH
from config.root_settings import CHROME_DRIVER_PATH


class CSOOnlineHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(CSOONLINE_BASE_URL, '', CSOONLINE_THREAT_REPORT_DIR,
                         CSOONLINE_URL_TO_FILENAME_MAP_PATH, "csoonline_report_crawler")

    @staticmethod
    def get_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)
        return driver
    
    def get_report_name(self, report_url):
        report_name = report_url.split('/')[-1][:-5] #report_url.replace(self.base_url, "").strip("/").replace("/", ":")
        return report_name
    
    def get_report_urls(self, max_pages_per_category=max(1,400)): 
            report_urls = set()
            threat_report_base_urls_map = {
                #"security": CSOONLINE_SECURITY_THREAT_REPORT_BASE_URL, 
                #"vulnerabilities": CSOONLINE_VULERNABILITIES_THREAT_REPORT_BASE_URL,
                #"cyberwarfare": CSOONLINE_CYBERWARFARE_THREAT_REPORT_BASE_URL,
                "cybercrime": CSOONLINE_CYBERCRIME_THREAT_REPORT_BASE_URL
            }

            for threat_report_type, base_url in threat_report_base_urls_map.items():
                self.logger.info(f"--- Starting category: {threat_report_type} ---")
                driver = self.get_driver()
                wait = WebDriverWait(driver, 10)

                try:
                    self.logger.info(f"[{threat_report_type}] Scraping main landing page: {base_url}")
                    driver.get(base_url)
                    article_selector = (By.CSS_SELECTOR, "a.grid.content-row-article, section.latest-content a.card")
                    try:
                        article_count_before_click = len(driver.find_elements(*article_selector))
                        show_more_button = wait.until(EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, ".content-listing-articles__button-show button[data-toggle='expand']")
                        ))
                        driver.execute_script("arguments[0].click();", show_more_button)
                        #time.sleep(2)
                        wait.until(
                            lambda d: len(d.find_elements(*article_selector)) > article_count_before_click
                        )
                    except TimeoutException:
                        self.logger.info(f"[{threat_report_type}] 'Show more' button not found or not clickable. Proceeding without clicking.")

                    initial_urls = set()
                    article_links = driver.find_elements(*article_selector)
                    for link in article_links:
                        href = link.get_attribute('href')
                        if href and 'csoonline.com/article/' in href:
                            initial_urls.add(href)
                    
                    self.logger.info(f"[{threat_report_type}] Found {len(initial_urls)} URLs on the landing page.")
                    report_urls.update(initial_urls)

                    for page_num in range(2, max_pages_per_category + 1):
                        page_url = f"{base_url.rstrip('/')}/page/{page_num}/"
                        self.logger.info(f"[{threat_report_type}] Scraping page {page_num}: {page_url}")
                        driver.get(page_url)
                        
                        try:
                            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section.content-listing-various")))
                        except TimeoutException:
                            self.logger.warning(f"[{threat_report_type}] Content container not found on page {page_num}. Assuming end of category.")
                            break

                        paginated_links = driver.find_elements(By.CSS_SELECTOR, ".content-listing-various__row a.grid.content-row-article")

                        if not paginated_links:
                            self.logger.info(f"[{threat_report_type}] No more articles found on page {page_num}. Ending crawl for this category.")
                            break
                        
                        page_urls = set()
                        for link in paginated_links:
                            href = link.get_attribute('href')
                            if href and 'csoonline.com/article/' in href:
                                page_urls.add(href)
                        
                        report_urls.update(page_urls)

                except Exception as e:
                    self.logger.error(f"An error occurred while crawling category '{threat_report_type}': {e}", exc_info=True)
                finally:
                    self.logger.info(f"--- Finished category: {threat_report_type}. Total URLs found so far: {len(report_urls)} ---")
                    driver.quit()

            return report_urls
    
    # def get_report_urls(self):
    #     # Use Selenium
    #     report_urls = set()
    #     threat_report_base_urls_map = {
    #         "security": CSOONLINE_SECURITY_THREAT_REPORT_BASE_URL, 
    #         "vulnerabilities": CSOONLINE_VULERNABILITIES_THREAT_REPORT_BASE_URL,
    #         "cyberwarfare": CSOONLINE_CYBERWARFARE_THREAT_REPORT_BASE_URL,
    #         "cybercrime": CSOONLINE_CYBERCRIME_THREAT_REPORT_BASE_URL
    #     }

    #     for threat_report_type in threat_report_base_urls_map.keys():
    #         threat_report_base_url = threat_report_base_urls_map[threat_report_type]
    #         driver = self.get_driver()
    #         driver.get(threat_report_base_url)
    #         count = 0
    #         hrefs_prev = None

    #         while True:
    #             # Keep clicking the "See more" button until the end
    #             try:
    #                 count += 1 
    #                 self.logger.info("{} category - Clicking 'See more' button for {} times".format(threat_report_type, count))
    #                 see_more_button = driver.find_elements_by_css_selector("#load-more-index")[0]
    #                 driver.execute_script("arguments[0].click();", see_more_button)

    #                 # Get current hrefs
    #                 hrefs = []
    #                 for title in driver.find_elements_by_css_selector("div.river-well.article > div > h3 > a"):
    #                     hrefs.append(title.get_property('href'))

    #                 self.logger.info("{} category - Current number of hrefs: {}".format(threat_report_type, len(hrefs)))

    #                 if hrefs_prev is None:
    #                     hrefs_prev = hrefs
    #                 else:
    #                     if hrefs_prev == hrefs:
    #                         self.logger.info("{} category - No new hrefs. Exit loop.".format(threat_report_type))
    #                         break
    #                     else:
    #                         hrefs_prev = hrefs

    #                 if count > 3: #1000:
    #                     # Only crawl the latest 1000 pages
    #                     self.logger.info("{} category - Clicking 'See more' for more than {} times. Exit loop.".format(threat_report_type, 1000))
    #                     break
    #             except Exception as e:
    #                 self.logger.exception(e)
    #                 break

    #             time.sleep(3)

    #         # Get all hrefs
    #         title_list = driver.find_elements_by_css_selector("div.river-well.article > div > h3 > a")
    #         self.logger.info("{} category - Crawled {} articles".format(threat_report_type, len(title_list)))
    #         for title in title_list:
    #             report_urls.add(title.get_property('href'))

    #         driver.close()

    #     return report_urls


if __name__ == "__main__":
    crawler = CSOOnlineHTMLCrawler()
    crawler.run()
