from bs4 import BeautifulSoup
from utils.base_crawler import BaseCrawler
import string
from config.threat_encyclopedia_crawlers_settings import SYMANTEC_REPORT_BASE_URL, SYMANTEC_THREAT_REPORT_DIR, \
    SYMANTEC_THREAT_REPORT_URL, SYMANTEC_THREATS_URL_TO_FILENAME_MAP_PATH


class SymantecHTMLThreatCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(SYMANTEC_REPORT_BASE_URL, SYMANTEC_THREAT_REPORT_URL,
                         SYMANTEC_THREAT_REPORT_DIR, SYMANTEC_THREATS_URL_TO_FILENAME_MAP_PATH,
                         "threat_encyclopedia_symantec_threats")

    def get_report_urls(self):
        urls = []
        threat_categories = list(string.ascii_uppercase) + ['_1234567890']

        for letter in threat_categories:
            self.logger.info("Crawling report URLs for letter {}".format(letter))

            url = self.threat_report_base_url + '?azid=' + letter
            req = self.scraper.scrape(url)
            soup = BeautifulSoup(req.text, "lxml")

            table = soup.findAll('table')[1]

            for tr in table.findAll('tr'):
                a = tr.findAll('a')
                if a:
                    a = a[0]
                    href = a['href']

                    report_url = self.base_url + href
                    technical_details_url = report_url + '&tabid=2'

                    urls.append(report_url)
                    urls.append(technical_details_url)

        return urls


if __name__ == "__main__":
    crawler = SymantecHTMLThreatCrawler()
    crawler.run()
