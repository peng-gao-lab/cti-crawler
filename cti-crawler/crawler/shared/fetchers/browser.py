import logging
import threading
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrowserResponse:
    url: str
    text: str
    headers: dict = field(default_factory=lambda: {"Content-Type": "text/html"})
    status_code: int | None = None  # Selenium does not expose the HTTP status.
    history: tuple = ()

    @property
    def content(self) -> bytes:
        return self.text.encode("utf-8")


class BrowserFetcher:
    def __init__(self, settings: dict, stop_event: threading.Event):
        self.settings = settings
        self.stop_event = stop_event
        self.max_navigation_steps = settings["max_navigation_steps"]
        self._local = threading.local()
        self._drivers = []
        self._lock = threading.Lock()

    def _driver(self):
        if not hasattr(self._local, "driver"):
            options = webdriver.ChromeOptions()
            if self.settings.get("headless", True):
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            if user_agent := self.settings.get("user_agent"):
                options.add_argument(f"user-agent={user_agent}")

            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.settings["page_load_timeout_seconds"])
            self._local.driver = driver
            with self._lock:
                self._drivers.append(driver)
        return self._local.driver

    def get(self, url: str, wait_for: str | None = None) -> BrowserResponse:
        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")

        driver = self._driver()
        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")
        driver.get(url)
        if wait_for:
            self.wait_for(wait_for)

        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")
        return self.current_response()

    def wait_for(self, selector: str, timeout_seconds: int | None = None) -> None:
        WebDriverWait(
            self._driver(),
            timeout_seconds or self.settings["wait_timeout_seconds"],
        ).until(lambda current: self._elements_ready(current, selector))

    def current_response(self) -> BrowserResponse:
        driver = self._driver()
        return BrowserResponse(driver.current_url, driver.page_source)

    def _elements_ready(self, driver, selector: str):
        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")
        return driver.find_elements(By.CSS_SELECTOR, selector)

    def current_html(self) -> str:
        return self._driver().page_source

    def element_count(self, selector: str) -> int:
        return len(self._driver().find_elements(By.CSS_SELECTOR, selector))

    def element_attribute(self, selector: str, name: str) -> str | None:
        elements = self._driver().find_elements(By.CSS_SELECTOR, selector)
        return elements[0].get_attribute(name) if elements else None

    def can_click(self, selector: str, text_contains: str | None = None) -> bool:
        return bool(self._clickable_element(self._driver(), selector, text_contains))

    def click(
        self,
        selector: str,
        text_contains: str | None = None,
        timeout_seconds: int | None = None,
    ) -> bool:
        try:
            element = WebDriverWait(
                self._driver(),
                timeout_seconds or self.settings["wait_timeout_seconds"],
            ).until(
                lambda current: self._clickable_element(
                    current,
                    selector,
                    text_contains,
                )
            )
        except TimeoutException:
            return False

        driver = self._driver()
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            element,
        )
        driver.execute_script("arguments[0].click();", element)
        return True

    def _clickable_element(
        self,
        driver,
        selector: str,
        text_contains: str | None,
    ):
        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            text_matches = text_contains is None or text_contains in element.text
            if text_matches and element.is_displayed() and element.is_enabled():
                return element
        return False

    def wait_for_more(self, selector: str, previous_count: int) -> bool:
        try:
            WebDriverWait(
                self._driver(),
                self.settings["wait_timeout_seconds"],
            ).until(
                lambda current: len(self._elements_ready(current, selector))
                > previous_count
            )
        except TimeoutException:
            return False
        return True

    def wait_for_change(self, selector: str, previous_value: str | None) -> bool:
        try:
            WebDriverWait(
                self._driver(),
                self.settings["wait_timeout_seconds"],
            ).until(
                lambda current: self._attribute_changed(
                    current,
                    selector,
                    previous_value,
                )
            )
        except TimeoutException:
            return False
        return True

    def _attribute_changed(self, driver, selector: str, previous_value: str | None):
        value = self._first_attribute(driver, selector, "outerHTML")
        return value is not None and value != previous_value

    def _first_attribute(self, driver, selector: str, name: str) -> str | None:
        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        return elements[0].get_attribute(name) if elements else None

    def close(self) -> None:
        with self._lock:
            drivers = self._drivers
            self._drivers = []
            self._local = threading.local()
        for driver in drivers:
            try:
                driver.quit()
            except WebDriverException:
                LOGGER.warning("Browser did not close cleanly", exc_info=True)
