import os
import random
import requests
import time
from config.root_settings import HEADERS

PROXY_HOST = os.environ.get('PROXY_HOST', '127.0.0.1')
NUMBER_RETRIES = 5 #10
TIMEOUT = 20


class Scraper:
    def __init__(self, logger=None, with_proxy=False, use_headers=True): #use_headers=False
        self.logger = logger
        self.with_proxy = with_proxy
        self.use_headers = use_headers

    @staticmethod
    def get_proxy():
        return requests.get("http://{}:5010/get/".format(PROXY_HOST), timeout=TIMEOUT).json()

    @staticmethod
    def delete_proxy(proxy):
        requests.get("http://{}:5010/delete/?proxy={}".format(PROXY_HOST, proxy), timeout=TIMEOUT)

    @staticmethod
    def get_headers():
        return HEADERS

    def scrape(self, url, proxy=None, retry=0, proxy_count=0):
        if retry > 0:
            if self.with_proxy:
                logger_str = "Retry number {} for proxy {} getting url {} with proxy_count {}".format(retry, proxy, url, proxy_count)
            else:
                logger_str = "Retry number {} for url {}".format(retry, url)

            self.logger.info(logger_str)

        if retry == NUMBER_RETRIES:
            if self.with_proxy:
                if proxy_count < NUMBER_RETRIES:  # Swich to a new proxy
                    self.delete_proxy(proxy)
                    new_proxy = None
                    while new_proxy is None:
                        new_proxy = self.get_proxy().get('proxy')
                    return self.scrape(url, new_proxy, 0, proxy_count + 1)
                else:
                    self.logger.warning("Retry number {} reaches maximum for proxy count {}. Exit."
                                        .format(retry, proxy_count))
                    return None
            else:
                self.logger.warning("Retry number {} reaches maximum. Exit.".format(retry))
                return None
        try:
            if self.with_proxy:
                proxy = None
                while proxy is None:
                    proxy = self.get_proxy().get("proxy")
                if self.use_headers:
                    response = requests.get(url, proxies={"https": "https://{}".format(proxy)},
                                            headers=self.get_headers(), timeout=TIMEOUT)
                else:
                    response = requests.get(url, proxies={"https": "https://{}".format(proxy)}, timeout=TIMEOUT)
            else:
                if self.use_headers:
                    response = requests.get(url, headers=self.get_headers(), timeout=TIMEOUT)
                else:
                    response = requests.get(url, timeout=TIMEOUT)

            if not response:
                # Delay before retrying
                time.sleep(random.randint(3, 5))
                return self.scrape(url, proxy, retry + 1, proxy_count)

            return response
        except Exception as e:
            self.logger.info(e)
            self.logger.exception(e)
            return self.scrape(url, proxy, retry + 1, proxy_count)
