from unittest.mock import patch

from scrapers.config.selenium_driver import SeleniumClient


def test_chrome_binary_defaults_to_selenium_manager(monkeypatch):
    monkeypatch.delenv("CHROME_BIN", raising=False)
    assert SeleniumClient().chrome_binary is None


def test_chrome_binary_from_env(monkeypatch):
    monkeypatch.setenv("CHROME_BIN", "/opt/chrome/chrome")
    assert SeleniumClient().chrome_binary == "/opt/chrome/chrome"


def test_explicit_chrome_binary_wins_over_env(monkeypatch):
    monkeypatch.setenv("CHROME_BIN", "/opt/chrome/chrome")
    assert SeleniumClient(chrome_binary="/custom/chrome").chrome_binary == "/custom/chrome"


@patch("scrapers.config.selenium_driver.webdriver.Chrome")
def test_connect_leaves_binary_location_empty_when_unset(mock_chrome, monkeypatch):
    monkeypatch.delenv("CHROME_BIN", raising=False)
    driver = SeleniumClient().connect()
    options = mock_chrome.call_args.kwargs["options"]
    assert options.binary_location == ""  # -> Selenium Manager resolves Chrome
    assert driver is mock_chrome.return_value


@patch("scrapers.config.selenium_driver.webdriver.Chrome")
def test_connect_sets_binary_location_when_given(mock_chrome):
    SeleniumClient(chrome_binary="/custom/chrome").connect()
    options = mock_chrome.call_args.kwargs["options"]
    assert options.binary_location == "/custom/chrome"
