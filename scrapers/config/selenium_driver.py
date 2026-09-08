"""Headless Chrome connector used to render JS-heavy career pages.

Imported lazily (only when an ``html_sources`` entry sets ``render: true``) so
that ``selenium`` stays an optional dependency for the rest of the pipeline.
"""

import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

load_dotenv()
load_dotenv("./scrapers/.env")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/152.0.0.0 Safari/537.36"
)


class SeleniumClient:
    """Infra-level Selenium/Chrome connector."""

    def __init__(
        self,
        chrome_binary=None,
        headless=True,
        user_agent=DEFAULT_USER_AGENT,
        page_load_timeout=30,
        settle_delay=3.0,
        window_size="1500,3000",
    ):
        self.chrome_binary = chrome_binary or os.environ.get("CHROME_BIN") or None
        self.headless = headless
        self.user_agent = user_agent
        self.page_load_timeout = page_load_timeout
        self.settle_delay = settle_delay
        self.window_size = window_size
        self.driver = None

    def connect(self):
        options = webdriver.ChromeOptions()
        if self.chrome_binary:
            options.binary_location = self.chrome_binary
        if self.headless:
            options.add_argument("--headless=new")
        for arg in ("--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"):
            options.add_argument(arg)
        options.add_argument(f"--window-size={self.window_size}")
        options.add_argument("--lang=en-US")
        if self.user_agent:
            options.add_argument(f"user-agent={self.user_agent}")

        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(self.page_load_timeout)
        return self.driver

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def render(self, url, wait_selector=None, scroll=False, next_selector=None, max_pages=1):
        """Load ``url``, wait for it to settle, return the rendered page HTML.

        When ``next_selector`` is given, click that "next page" control up to
        ``max_pages`` times and return every page snapshot joined together.
        """
        self.driver.get(url)
        pages = [self._settle(wait_selector, scroll)]

        for _ in range(max(max_pages - 1, 0) if next_selector else 0):
            elements = self.driver.find_elements(By.CSS_SELECTOR, next_selector)
            clickable = next(
                (el for el in elements if el.is_displayed() and el.is_enabled()), None
            )
            if clickable is None or clickable.get_attribute("aria-disabled") == "true":
                break
            self.driver.execute_script("arguments[0].click();", clickable)
            pages.append(self._settle(wait_selector, scroll))

        return "\n".join(pages)

    def _settle(self, wait_selector, scroll):
        if wait_selector:
            try:
                WebDriverWait(self.driver, self.page_load_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except Exception:  # noqa: BLE001 - fall back to the settle delay
                pass
        time.sleep(self.settle_delay)
        if scroll:
            for fraction in (0.4, 0.75, 1.0):
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight * arguments[0]);", fraction
                )
                time.sleep(1.5)
        return self.driver.page_source
