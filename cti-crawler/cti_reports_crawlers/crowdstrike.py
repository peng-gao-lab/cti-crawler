import os
import re
from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
from config.cti_reports_crawlers_settings import CROWDSTRIKE_BASE_URL, CROWDSTRIKE_THREAT_REPORT_BASE_URL, CROWDSTRIKE_THREAT_REPORT_DIR,\
    CROWDSTRIKE_URL_TO_FILENAME_MAP_PATH
from urllib.parse import urljoin

class CrowdStrikeHTMLCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(CROWDSTRIKE_BASE_URL, CROWDSTRIKE_THREAT_REPORT_BASE_URL, CROWDSTRIKE_THREAT_REPORT_DIR,
                         CROWDSTRIKE_URL_TO_FILENAME_MAP_PATH, "crowdstrike_report_crawler")

    # def get_report_urls(self):
    #     page_number = 0  # Maximum 63 confirmed on 07/12/2020
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
    #             title_list = soup.find_all(class_="vcex-post-type-entry-title entry-title")
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

    #     return report_urls
    def get_category_urls(self):
        self.logger.info(f"crawling cotegory URL: {self.threat_report_base_url}")
        response = self.scraper.scrape(self.threat_report_base_url)
        soup = BeautifulSoup(response.text, "html.parser")

        category_urls = []
        category_list_container = soup.find('div', class_='blog_featured_category_list')
        if not category_list_container:
            self.logger.error("There is no category container")
            return []
            
        category_links = category_list_container.find_all('a', class_='category-sidebar-link')
        for link in category_links:
            if link.has_attr('href'):
                relative_url = link['href']
                full_url = urljoin(self.base_url, relative_url)
                category_urls.append(full_url)
        
        self.logger.info(f"Found {len(category_urls)} categories.")
        return category_urls
    
    def get_urls_from_category_page(self, category_url):
        report_urls = []
        try:
            response = self.scraper.scrape(category_url)
            soup = BeautifulSoup(response.text, "html.parser")
            article_container = soup.find("div", id="blogAutoGenerationDiv")
            if not article_container:
                raise Exception("The page does not have article_container. There might be structure change.")
            title_list = article_container.find_all("h3")
            if not title_list:
                raise Exception("The page does not contain report URLs")
            for title in title_list:
                link_tag = title.find('a')
                if link_tag and link_tag.has_attr('href'):
                    relative_url = link_tag['href']
                    report_url = urljoin(self.base_url, relative_url)
                    if report_url not in report_urls:
                        report_urls.append(report_url)
       
        except Exception as e:
            self.logger.exception(e)
            self.logger.warning("category {} failed".format(category_url))

        return report_urls
    
    def get_report_urls(self):
        all_blog_urls = []
        category_urls = self.get_category_urls()

        if not category_urls:
            self.logger.error("No category found.")
            return []

        for category in category_urls:
            urls_in_category = self.get_urls_from_category_page(category)
            for url in urls_in_category:
                if url not in all_blog_urls:
                    all_blog_urls.append(url)
        return all_blog_urls

    def get_report_name(self, report_url):
        return report_url.replace(os.path.join(self.base_url, "en-us/blog"), "").strip("/").replace("/", ":") + ".html"
    
    def get_file_path(self, report_name):
        # Overload parent method
        return os.path.join(self.threat_report_dir, report_name)


if __name__ == "__main__":
    crawler = CrowdStrikeHTMLCrawler()
    crawler.run()
