import json
import os
import threading
from utils.logger import create_logger
from abc import abstractmethod, ABC
from utils.scraper import Scraper
from utils.multithreaded_task_scheduler import MultiThreadedTaskScheduler
from config.root_settings import NUM_THREADS_DOWNLOAD_HTML

with_proxy_pool = bool(os.environ.get('WITH_PROXY', False))


class BaseCrawler(ABC):
    def __init__(self, base_url, threat_report_base_url, threat_report_dir, urls_to_filename_map_path, crawler_name,
                 with_proxy=with_proxy_pool, use_headers=False):
        self.base_url = base_url
        self.threat_report_base_url = threat_report_base_url
        self.threat_report_dir = threat_report_dir
        self.logger = create_logger(crawler_name)
        self.crawler_name = crawler_name
        self.lock = threading.Lock()
        self.urls_to_filename_map_path = urls_to_filename_map_path
        self.scraper = Scraper(self.logger, with_proxy, use_headers)
        self.report_urls = []

    @abstractmethod
    def get_report_urls(self):
        pass

    def get_report_html(self, report_url):
        response = self.scraper.scrape(report_url)
        if response:
            return response.text

    def get_report_name(self, report_url):
        report_name = report_url.replace(self.threat_report_base_url, "").strip("/").replace("/", ":")
        return report_name

    def get_file_path(self, report_name):
        if not report_name.endswith(".html"):
            report_name += ".html"
        return os.path.join(self.threat_report_dir, report_name)

    def run(self):
        self.logger.info("Crawling report HTML files --- start")
        try:
            if not os.path.exists(self.threat_report_dir):
                os.makedirs(self.threat_report_dir)

            self.logger.info("Crawling all report URLs --- start")
            for report_url in self.get_report_urls():
                self.report_urls.append(report_url)
            self.logger.info("Crawling all report URLs --- done")

            urls_to_filename_map_parent_dir = os.path.dirname(self.urls_to_filename_map_path)
            if not os.path.exists(urls_to_filename_map_parent_dir):
                os.makedirs(urls_to_filename_map_parent_dir)

            urls_to_filename_map = {}
            if os.path.exists(self.urls_to_filename_map_path):
                with open(self.urls_to_filename_map_path, "r") as read_file:
                    urls_to_filename_map = json.load(read_file)

            def report_urls_handler(url):
                report_name = self.get_report_name(url)
                report_file_path = self.get_file_path(report_name)
                if url in urls_to_filename_map or os.path.exists(report_file_path):
                    self.logger.info("{} exists".format(report_file_path))
                else:
                    try:
                        report_html = self.get_report_html(url)
                        if report_html:
                            with open(report_file_path, "w") as f:
                                f.write(report_html)
                                self.logger.info("Finished crawling: {}".format(report_file_path))

                        try:
                            self.lock.acquire()
                            urls_to_filename_map[url] = report_name

                            # Update urls_to_filename_mappings here after an html download
                            with open(self.urls_to_filename_map_path, "w+") as write_file:
                                json.dump(urls_to_filename_map, write_file)
                        except Exception as e:
                            raise Exception(f"Error adding url {url} to urls_to_filename_map")
                        finally:
                            self.lock.release()

                    except Exception as e:
                        self.logger.info("Encountered exception in report_urls_handler function")
                        self.logger.exception(e)


            mtts = MultiThreadedTaskScheduler(NUM_THREADS_DOWNLOAD_HTML, report_urls_handler, self.crawler_name, thread_join_timeout=10,
                                              tasks=self.report_urls, exception_count_limit=5)
            mtts.start()
            mtts.wait()

        except Exception as e:
            self.logger.info("Encountered exception in base crawler run function")
            self.logger.exception(e)

        self.logger.info("Crawling report HTML files --- done")
