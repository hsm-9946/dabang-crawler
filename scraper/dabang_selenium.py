from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin
import hashlib
import time

from loguru import logger
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver
import os
import subprocess
import re

from scraper.parsers import (
    extract_address,
    extract_price_text,
    extract_area_m2,
    extract_floor,
    normalize_price_text,
    normalize_maintenance_fee,
    to_absolute_time,
    to_ymd,
)


@dataclass
class SelOptions:
    region: str
    property_type: str
    max_items: int = 100
    headless: bool = True


@dataclass
class Row:
    address: str
    price_text: str
    maintenance_fee: Optional[int]
    realtor: str
    posted_at: str
    property_type: str
    url: str
    item_id: str
    area_m2: Optional[float] = None
    floor: Optional[str] = None


LIST_SELECTORS = [
    'article',
    'li[role="listitem"]',
]


def _detect_chrome_version_main() -> Optional[int]:
    env = os.getenv("CHROME_VERSION_MAIN")
    if env:
        try:
            return int(env)
        except Exception:
            return None
    # macOS Chrome path
    try:
        out = subprocess.check_output([
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "--version",
        ], stderr=subprocess.STDOUT).decode("utf-8", "ignore")
        m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
        if m:
            return int(m.group(1))
    except Exception:
        return None
    return None


def create_driver(headless: bool) -> WebDriver:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--lang=ko-KR")
    ver = _detect_chrome_version_main()
    if ver:
        driver = uc.Chrome(options=opts, version_main=ver)
    else:
        driver = uc.Chrome(options=opts)
    driver.maximize_window()
    driver.implicitly_wait(2)
    return driver


class DabangSelenium:
    def __init__(self, opts: SelOptions) -> None:
        self.opts = opts

    def run(self) -> List[Row]:
        rows: List[Row] = []
        driver = create_driver(self.opts.headless)
        try:
            logger.info("접속: 다방")
            driver.get("https://www.dabangapp.com/")
            time.sleep(1.5)
            # 검색
            box = None
            for css in [
                'input[placeholder*="검색"]',
                'input[placeholder*="지역"]',
                'input[type="search"]',
            ]:
                try:
                    box = driver.find_element(By.CSS_SELECTOR, css)
                    break
                except Exception:
                    continue
            if not box:
                raise RuntimeError("검색창을 찾지 못했습니다")
            box.click()
            box.clear()
            box.send_keys(self.opts.region)
            time.sleep(0.5)
            box.send_keys(Keys.ENTER)
            time.sleep(2.0)

            # 왼쪽 목록 패널 끝까지 스크롤
            self._scroll_list(driver)

            # 카드 수집
            cards = self._find_cards(driver)
            logger.info("카드: {}개", len(cards))
            for card in cards[: self.opts.max_items]:
                try:
                    html = card.get_attribute("innerText") or ""
                    addr = extract_address(html) or ""
                    price = extract_price_text(html) or ""
                    realtor = ""
                    try:
                        realtor = card.find_element(By.XPATH, './/*[contains(text(),"공인중개사") or contains(text(),"부동산")]').text
                    except Exception:
                        pass
                    posted = to_absolute_time(html) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ymd = to_ymd(posted)
                    link = ""
                    try:
                        a = card.find_element(By.CSS_SELECTOR, 'a[href]')
                        link = a.get_attribute('href') or ""
                    except Exception:
                        pass
                    url_abs = urljoin("https://www.dabangapp.com/", link) if link else ""
                    if not (addr and price):
                        continue
                    item_id = hashlib.sha1((url_abs or addr + price).encode('utf-8')).hexdigest()
                    rows.append(
                        Row(
                            address=addr,
                            price_text=normalize_price_text(price),
                            maintenance_fee=normalize_maintenance_fee(html),
                            realtor=realtor,
                            posted_at=ymd,
                            property_type=self.opts.property_type,
                            url=url_abs,
                            item_id=item_id,
                            area_m2=extract_area_m2(html),
                            floor=extract_floor(html),
                        )
                    )
                except Exception:
                    continue
        finally:
            try:
                driver.quit()
            except Exception:
                pass
        logger.info("수집 완료: {}건", len(rows))
        return rows

    def _scroll_list(self, driver: WebDriver) -> None:
        # 페이지 전체 스크롤과 목록 패널 스크롤 병행
        for _ in range(40):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.6)
        # 목록 패널 추정 요소들 내부 스크롤
        for sel in [
            'div[role="list"]',
            'div[class*="list"]',
            'section:has(article)',
        ]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, sel)
                for _ in range(60):
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", el)
                    time.sleep(0.4)
            except Exception:
                continue

    def _find_cards(self, driver: WebDriver):
        cards = []
        for sel in LIST_SELECTORS:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, sel)
                if cards:
                    break
            except Exception:
                continue
        return cards


