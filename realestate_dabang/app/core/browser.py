from __future__ import annotations

import contextlib
from typing import Callable, List, Optional

from loguru import logger
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import undetected_chromedriver as uc
import subprocess
import re

from .. import config


def create_chrome_driver(headless: bool | None = None) -> WebDriver:
    """undetected-chromedriver 기반 Chrome 드라이버 생성."""

    headless = config.HEADLESS_DEFAULT if headless is None else headless
    logger.info("브라우저 초기화(headless={})", headless)

    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ko-KR")
    options.add_argument(f"--user-agent={config.USER_AGENT}")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 리소스 최소화 옵션
    prefs = {
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.images": 2,
        "webkit.webprefs.forceDarkMode": 0,
    }
    options.add_experimental_option("prefs", prefs)

    # 설치된 Chrome 메이저 버전 감지(맥)
    version_main: Optional[int] = None
    if config.CHROME_VERSION_MAIN:
        version_main = int(config.CHROME_VERSION_MAIN)  # type: ignore[arg-type]
    else:
        try:
            # macOS Chrome 버전 확인
            out = subprocess.check_output(
                [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "--version",
                ],
                stderr=subprocess.STDOUT,
            ).decode("utf-8", "ignore")
            m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
            if m:
                version_main = int(m.group(1))
        except Exception:
            version_main = None

    # undetected-chromedriver에 버전 힌트를 전달하면 맞는 드라이버를 받기 쉬움
    try:
        if version_main:
            driver = uc.Chrome(options=options, version_main=version_main)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:  # noqa: BLE001
        logger.error(
            "드라이버 생성 실패: {}. 설치된 Chrome 메이저 버전을 확인하고 환경변수 CHROME_VERSION_MAIN 설정 후 재시도하세요.",
            str(e),
        )
        raise
    driver.set_page_load_timeout(config.TIMEOUT_SECONDS)
    driver.implicitly_wait(2)
    return driver


def wait_for_visible(
    driver: WebDriver,
    by: By,
    value: str,
    timeout: Optional[int] = None,
):
    timeout = timeout or config.TIMEOUT_SECONDS
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, value)))


def wait_for_all_present(
    driver: WebDriver,
    by: By,
    value: str,
    timeout: Optional[int] = None,
):
    timeout = timeout or config.TIMEOUT_SECONDS
    return WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((by, value)))


def try_select_first(driver: WebDriver, selectors: List[str]):
    """복수 후보 셀렉터를 순차 시도하여 첫 번째로 발견되는 요소를 반환.

    셀렉터가 'xpath:' 접두사이면 XPATH로 처리, 아니면 CSS로 처리.
    실패 시 None 리턴.
    """

    for sel in selectors:
        try:
            if sel.startswith("xpath:"):
                xpath = sel.split("xpath:", 1)[1]
                el = driver.find_element(By.XPATH, xpath)
            else:
                el = driver.find_element(By.CSS_SELECTOR, sel)
            if el:
                return el
        except Exception:
            continue
    return None


def try_select_all(driver: WebDriver, selectors: List[str]):
    """복수 후보 셀렉터로 모든 요소를 모아 리스트로 반환."""

    elements = []
    for sel in selectors:
        try:
            if sel.startswith("xpath:"):
                xpath = sel.split("xpath:", 1)[1]
                elements.extend(driver.find_elements(By.XPATH, xpath))
            else:
                elements.extend(driver.find_elements(By.CSS_SELECTOR, sel))
        except Exception:
            continue
    return elements


@contextlib.contextmanager
def safe_quit(driver: WebDriver):
    try:
        yield driver
    finally:
        with contextlib.suppress(Exception):
            driver.quit()


