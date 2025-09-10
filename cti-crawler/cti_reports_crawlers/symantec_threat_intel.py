import time
from selenium import webdriver
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import SYMANTECTHREATINTELLIGENCE_BASE_URL, SYMANTECTHREATINTELLIGENCE_THREAT_REPORT_BASE_URL, \
    SYMANTECTHREATINTELLIGENCE_THREAT_REPORT_DIR, SYMANTECTHREATINTELLIGENCE_URL_TO_FILENAME_MAP_PATH
from config.root_settings import CHROME_DRIVER_PATH

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
class SymantecThreatIntelligenceHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SYMANTECTHREATINTELLIGENCE_BASE_URL, SYMANTECTHREATINTELLIGENCE_THREAT_REPORT_BASE_URL, SYMANTECTHREATINTELLIGENCE_THREAT_REPORT_DIR,
                         SYMANTECTHREATINTELLIGENCE_URL_TO_FILENAME_MAP_PATH, "symantecthreatintelligence_report_crawler")

    @staticmethod
    def get_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')        
        driver = webdriver.Chrome(CHROME_DRIVER_PATH, options=chrome_options)
        return driver
    
    def get_report_urls(self):
        report_urls_set = set() 
        driver = self.get_driver()
        driver.get(self.threat_report_base_url)
        time.sleep(3) 
        wait = WebDriverWait(driver, 10)
        count = 0
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.blog-post-feed__inner")))
        while True:
            try:
                link_elements = driver.find_elements(By.CSS_SELECTOR, "a.blog-post-teaser__link-wrapper")
                num_links_before_click = len(link_elements)
                if not link_elements:
                    self.logger.warning("Waited for elements, but find_elements returned empty. This shouldn't happen.")
                    break

                new_links_found = 0
                for link in link_elements:
                    href = link.get_attribute('href')
                    if href:
                        if href not in report_urls_set:
                            report_urls_set.add(href)
                            new_links_found += 1
                
                self.logger.info(f"Found {len(link_elements)} links on this page. Added {new_links_found} new URLs. Total unique URLs: {len(report_urls_set)}")
                if count > 1000:
                    self.logger.warning("Clicked 'LOAD MORE' over 100 times. Stopping to prevent infinite loop.")
                    break
                load_more_button = driver.find_element(By.CSS_SELECTOR, ".blog-post-feed__load-more--button")
                driver.execute_script("arguments[0].click();", load_more_button)
                self.logger.info("Clicked 'LOAD MORE' button.")
                #time.sleep(3) 
                wait.until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "a.blog-post-teaser__link-wrapper")) > num_links_before_click
                )

                count += 1
            except NoSuchElementException:
                self.logger.info("No more 'LOAD MORE' button found. All articles have been loaded.")
                break
            except Exception as e:
                self.logger.exception("An error occurred during scraping.")
                self.logger.exception(e)
                break
        driver.quit()

        return list(report_urls_set)
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
    #             count += 1
    #             self.logger.info("Clicking 'See more' button for {} times".format(count))
    #             see_more_button = driver.find_elements_by_css_selector("main.main > a.btn.btn--more")[0]
    #             driver.execute_script("arguments[0].click();", see_more_button)

    #             # Need to sleep because of loading delay after clicking on 'See more' button
    #             # So new blog posts won't load until we wait a little bit
    #             time.sleep(10)

    #             # Get current hrefs
    #             hrefs = []
    #             for title in driver.find_elements_by_xpath("//a[@class='blog-teaser__link']"):
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
    #     title_list = driver.find_elements_by_xpath("//a[@class='blog-teaser__link']")
    #     self.logger.info("Crawled {} articles".format(len(title_list)))
    #     for title in title_list:
    #         report_urls.append(title.get_property('href'))

    #     driver.close()

    #     return report_urls


if __name__ == "__main__":
    crawler = SymantecThreatIntelligenceHTMLCrawler()
    crawler.run()
