import os
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
import string
from config.threat_encyclopedia_crawlers_settings import FSECURE_THREAT_REPORT_BASE_URL, FSECURE_THREAT_REPORT_DIR, \
    FSECURE_THREAT_REPORT_URL, FSECURE_URL_TO_FILENAME_MAP_PATH

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.root_settings import HEADERS, CHROME_DRIVER_PATH
class FSecureHTMLThreatCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(FSECURE_THREAT_REPORT_BASE_URL, FSECURE_THREAT_REPORT_URL,
                         FSECURE_THREAT_REPORT_DIR, FSECURE_URL_TO_FILENAME_MAP_PATH,
                         "threat_encyclopedia_fsecure_threats")
    def get_report_urls(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless') 
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument(f"user-agent={HEADERS['User-Agent']}")
        driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options)
        report_urls = []
        try:
            driver.get(self.threat_report_base_url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[class^="page_indexlist_"] li'))
            )
            
            html_content = driver.page_source
            
            soup = BeautifulSoup(html_content, "lxml")
            
            index_list = soup.select_one('ul[class^="page_indexlist_"]')
            
            if index_list:
                list_items = index_list.find_all("li")
                for item in list_items:
                    a_tag = item.find("a")
                    if a_tag and a_tag.has_attr('href'):
                        href = a_tag['href']
                        if href.startswith('..'):
                            
                            href = self.base_url + href[2:]
                        report_urls.append(href)
        finally:
            driver.quit() 
            
        return report_urls
    # def get_report_urls(self):
    #     report_urls = []
    #     url = self.threat_report_base_url
    #     req = self.scraper.scrape(url)
    #     soup = BeautifulSoup(req.text, "lxml")
    #     index_list = soup.find("ul", attrs={"id": "index"})
    #     if index_list:
    #         list_items = index_list.findAll("li", attrs={"class": "desc"})
    #         for item in list_items:
    #             a_tag = item.find("a")
    #             if a_tag and a_tag.has_attr('href'):
    #                 report_urls.append(a_tag['href'])
    #     return report_urls
    # def get_report_urls(self):
    #     report_urls = []
    #     threat_categories = list(string.ascii_uppercase) + ['0-9']

    #     url = self.threat_report_base_url
    #     req = self.scraper.scrape(url)
    #     soup = BeautifulSoup(req.text, "lxml")

    #     for letter in threat_categories:
    #         self.logger.info("Crawling report URLs for letter {}".format(letter))

    #         descriptions_pane = soup.find("div", attrs={"id": "descriptions-pane"})
    #         div_for_letter = descriptions_pane.find("div", attrs={"id": letter})
    #         p_tags = div_for_letter.findAll("p")
    #         for p_tag in p_tags:
    #             a = p_tag.find("a")
    #             if (a):
    #                 report_urls.append(a['href'])
    #         break
        
    #     return report_urls

    def get_report_name(self, report_url):
        return report_url.replace(self.base_url, "").strip("/").replace("/", ":") + ".html"

    def get_file_path(self, report_name):
        # Overload parent method
        return os.path.join(self.threat_report_dir, report_name)

if __name__ == "__main__":
    crawler = FSecureHTMLThreatCrawler()
    crawler.run()
