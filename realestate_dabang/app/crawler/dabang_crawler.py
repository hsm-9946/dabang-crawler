from __future__ import annotations

import threading
import time
from typing import Callable, List, Optional

from bs4 import BeautifulSoup
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from ..core.browser import create_chrome_driver, try_select_all, try_select_first, safe_quit
from ..core.models import CrawlerInput, Record
from ..core.throttling import random_sleep
from ..utils.text import extract_lot_address, parse_maintenance_fee_to_won, parse_price_to_won
from .. import config
from . import selectors as S


class PauseSignal:
    """CAPTCHA 대응을 위한 일시정지/재개 제어 신호."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

    def request_stop(self) -> None:
        self._stop_event.set()

    def request_pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def wait_if_paused(self) -> None:
        while self._pause_event.is_set() and not self._stop_event.is_set():
            time.sleep(0.3)


def detect_captcha(driver: WebDriver) -> bool:
    """캡차/차단 감지: 힌트 요소 또는 페이지 소스 텍스트 검사."""
    try:
        hints = try_select_all(driver, S.CAPTCHA_HINTS)
        if hints:
            return True
    except Exception:
        pass
    html = driver.page_source.lower()
    for kw in ["captcha", "자동입력", "보안문자"]:
        if kw in html:
            return True
    return False


def absolute_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return "https://www.dabangapp.com" + href


class DabangCrawler:
    """다방 사이트 크롤러.

    - 지역 키워드 검색 → 결과 스크롤 → 카드 파싱
    - 캡차 감지 시 pause_signal을 set 하여 상위(UI)에 통지
    """

    def __init__(
        self,
        user_input: CrawlerInput,
        pause_signal: Optional[PauseSignal] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.user_input = user_input
        self.pause_signal = pause_signal or PauseSignal()
        self.progress_callback = progress_callback

    def _emit(self, msg: str) -> None:
        logger.info(msg)
        if self.progress_callback:
            try:
                self.progress_callback(msg)
            except Exception:
                pass

    def _search_region(self, driver: WebDriver) -> None:
        driver.get("https://www.dabangapp.com/")
        random_sleep()
        input_el = None
        for sel in S.SEARCH_INPUT:
            input_el = try_select_first(driver, [sel])
            if input_el:
                break
        if not input_el:
            raise RuntimeError("검색 입력창을 찾을 수 없습니다. 셀렉터를 업데이트 해주세요.")

        input_el.click()
        random_sleep(0.2, 0.6)
        input_el.clear()
        input_el.send_keys(self.user_input.region_keyword)
        random_sleep(0.2, 0.6)
        # 1차: ENTER
        input_el.send_keys(Keys.ENTER)

        # 2차: 자동완성 첫 항목 클릭 시도
        time.sleep(0.8)
        ac = try_select_first(driver, S.AUTOCOMPLETE_FIRST)
        if ac:
            try:
                ac.click()
            except Exception:
                pass

        # 결과 컨테이너/카드 등장 대기 (soft wait)
        time.sleep(2.5)

        # 원룸 필터 적용(가능한 경우)
        try:
            if any("원룸" in t for t in (self.user_input.property_types or [])):
                self._emit("UI 필터 적용: 추가필터 > 방구조 > 원룸")
                more_btn = try_select_first(driver, S.FILTER_TOGGLE_MORE)
                if more_btn:
                    try:
                        more_btn.click()
                        time.sleep(0.6)
                    except Exception:
                        pass
                # 방구조 섹션 내 원룸 버튼
                one_btn = try_select_first(driver, S.STRUCTURE_ONE_ROOM)
                if one_btn:
                    try:
                        one_btn.click()
                        time.sleep(0.8)
                    except Exception:
                        pass
            # 아파트 탭 전환(요청 시)
            if any("아파트" in t for t in (self.user_input.property_types or [])):
                self._emit("카테고리 탭 전환: 아파트")
                apt_tab = try_select_first(driver, S.PROPERTY_TAB_APARTMENT)
                if apt_tab:
                    try:
                        apt_tab.click()
                        time.sleep(1.2)
                    except Exception:
                        pass
            # 오피스텔 탭 전환(요청 시)
            if any("오피스텔" in t for t in (self.user_input.property_types or [])):
                self._emit("카테고리 탭 전환: 오피스텔")
                ofc_tab = try_select_first(driver, S.PROPERTY_TAB_OFFICETEL)
                if ofc_tab:
                    try:
                        ofc_tab.click()
                        time.sleep(1.2)
                    except Exception:
                        pass
            # 주택/빌라 탭 전환(요청 시)
            if any((("주택" in t) or ("빌라" in t)) for t in (self.user_input.property_types or [])):
                self._emit("카테고리 탭 전환: 주택/빌라")
                hv_tab = try_select_first(driver, S.PROPERTY_TAB_HOUSE_VILLA)
                if hv_tab:
                    try:
                        hv_tab.click()
                        time.sleep(1.2)
                    except Exception:
                        pass
            # 분양 관련 필터(옵션) 적용
            self._apply_sale_filters(driver)
        except Exception as e:
            logger.debug("유형/원룸 필터 적용 실패(무시): {}", e)

    def _click_candidates(self, driver: WebDriver, selectors: list[str]) -> bool:
        for sel in selectors:
            try:
                el = try_select_first(driver, [sel])
                if el:
                    el.click()
                    time.sleep(0.5)
                    return True
            except Exception:
                continue
        return False

    def _apply_sale_filters(self, driver: WebDriver) -> None:
        """분양 관련 필터(UI 기반). 각 토글을 열고 선택 항목을 클릭.
        실패해도 예외를 올리지 않는다.
        """
        ui = self.user_input
        # 건물유형
        if ui.sale_building_types:
            self._click_candidates(driver, S.SALE_BUILDING_TOGGLE)
            for label in ui.sale_building_types:
                opts = S.SALE_BUILDING_OPTIONS.get(label, [])
                if opts:
                    self._click_candidates(driver, opts)
            time.sleep(0.4)
        # 분양단계
        if ui.sale_stages:
            self._click_candidates(driver, S.SALE_STAGE_TOGGLE)
            for label in ui.sale_stages:
                opts = S.SALE_STAGE_OPTIONS.get(label, [])
                if opts:
                    self._click_candidates(driver, opts)
            time.sleep(0.4)
        # 분양일정
        if ui.sale_schedules:
            self._click_candidates(driver, S.SALE_SCHEDULE_TOGGLE)
            for label in ui.sale_schedules:
                opts = S.SALE_SCHEDULE_OPTIONS.get(label, [])
                if opts:
                    self._click_candidates(driver, opts)
            time.sleep(0.4)
        # 공급유형
        if ui.sale_supply_types:
            self._click_candidates(driver, S.SALE_SUPPLY_TOGGLE)
            for label in ui.sale_supply_types:
                opts = S.SALE_SUPPLY_OPTIONS.get(label, [])
                if opts:
                    self._click_candidates(driver, opts)
            time.sleep(0.4)

    def _try_load_more_or_next(self, driver: WebDriver) -> bool:
        """더보기/다음 페이지 시도. 성공 시 True."""
        for sel in S.LOAD_MORE:
            try:
                btn = try_select_first(driver, [sel])
                if btn:
                    btn.click()
                    time.sleep(config.SCROLL_PAUSE_SECONDS)
                    return True
            except Exception:
                continue
        for sel in S.PAGINATION_NEXT:
            try:
                btn = try_select_first(driver, [sel])
                if btn:
                    btn.click()
                    time.sleep(config.SCROLL_PAUSE_SECONDS)
                    return True
            except Exception:
                continue
        return False

    def _scroll_collect_cards(self, driver: WebDriver) -> List:
        last_count = 0
        stable_rounds = 0
        max_scrolls = 50
        scrolls = 0
        collected = []
        while True:
            if self.pause_signal.should_stop():
                break
            if detect_captcha(driver):
                self._emit("CAPTCHA 감지됨: 인증 후 재개 버튼을 눌러주세요.")
                self.pause_signal.request_pause()
                self.pause_signal.wait_if_paused()
                self._emit("재개됨. 계속 진행합니다.")

            # 현재 카드 수집
            cards = try_select_all(driver, S.CARD)
            if cards:
                collected = cards
            
            # 스크롤 다운
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(config.SCROLL_PAUSE_SECONDS)
            scrolls += 1

            # 증가 확인
            current_count = len(cards)
            if current_count <= last_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                last_count = current_count

            if stable_rounds >= 4:
                # 추가 대기
                time.sleep(2.0)
                # 더보기/다음 시도 후 다시 스크롤 루프 이어감
                if not self._try_load_more_or_next(driver):
                    break
                stable_rounds = 0
            if scrolls >= max_scrolls:
                break

        self._emit(f"카드 수집 완료: {len(collected)}개")
        return collected

    def _parse_card(self, driver: WebDriver, card) -> Optional[Record]:
        try:
            html = card.get_attribute("innerHTML")
            soup = BeautifulSoup(html, "lxml")

            # 주소
            lot_address_text = None
            for sel in S.ADDRESS:
                try:
                    if sel.startswith("xpath:"):
                        # XPATH은 card 기준이 아닌 driver 기준이라 어려움 → soup 폴백 우선
                        continue
                    el = card.find_element(By.CSS_SELECTOR, sel)
                    if el and el.text.strip():
                        lot_address_text = el.text.strip()
                        break
                except Exception:
                    continue
            if not lot_address_text:
                lot_address_text = soup.get_text(" ", strip=True)
            lot_address = extract_lot_address(lot_address_text)
            if not lot_address:
                logger.warning("지번 미노출 카드 스킵")
                return None

            # 가격
            price_text = None
            for sel in S.PRICE:
                try:
                    if sel.startswith("xpath:"):
                        continue
                    el = card.find_element(By.CSS_SELECTOR, sel)
                    if el and el.text.strip():
                        price_text = el.text.strip()
                        break
                except Exception:
                    continue
            if not price_text:
                price_text = soup.get_text(" ", strip=True)
            price = parse_price_to_won(price_text)

            # 관리비
            maint_text = None
            for sel in S.MAINT_FEE:
                try:
                    if sel.startswith("xpath:"):
                        continue
                    el = card.find_element(By.CSS_SELECTOR, sel)
                    if el and el.text.strip():
                        maint_text = el.text.strip()
                        break
                except Exception:
                    continue
            if not maint_text:
                maint_text = soup.get_text(" ", strip=True)
            maintenance_fee = parse_maintenance_fee_to_won(maint_text)

            # 유형
            prop_type = ""
            for sel in S.TYPE:
                try:
                    if sel.startswith("xpath:"):
                        continue
                    el = card.find_element(By.CSS_SELECTOR, sel)
                    if el and el.text.strip():
                        prop_type = el.text.strip()
                        break
                except Exception:
                    continue
            if not prop_type:
                prop_type = soup.get_text(" ", strip=True)

            # URL
            url = ""
            for sel in S.DETAIL_LINK:
                try:
                    if sel.startswith("xpath:"):
                        continue
                    a = card.find_element(By.CSS_SELECTOR, sel)
                    href = a.get_attribute("href")
                    if href:
                        url = absolute_url(href)
                        break
                except Exception:
                    continue

            rec = Record(
                lot_address=lot_address,
                price=price,
                property_type=prop_type,
                maintenance_fee=maintenance_fee,
                url=url,
                collected_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
            return rec
        except Exception as e:  # noqa: BLE001
            logger.warning("카드 파싱 실패: {}", e)
            return None

    def _dump_diagnostics(self, driver: WebDriver, tag: str) -> None:
        if not self.user_input.diagnostics:
            return
        try:
            ts = time.strftime("%Y%m%d_%H%M%S")
            png = config.DEBUG_DIR / f"empty_list_{tag}_{ts}.png"
            html = config.DEBUG_DIR / f"empty_list_{tag}_{ts}.html"
            url = driver.current_url
            ua = driver.execute_script("return navigator.userAgent")
            cookies = driver.get_cookies() or []
            driver.save_screenshot(str(png))
            html.write_text(driver.page_source, encoding="utf-8")
            logger.warning("진단 덤프 저장: {} / {} (url={}, ua_len={}, cookies={})", png, html, url, len(ua or ""), len(cookies))
        except Exception as e:
            logger.warning("진단 덤프 실패: {}", e)

    def run(self) -> tuple[List[Record], int]:
        records: List[Record] = []
        with safe_quit(create_chrome_driver(self.user_input.headless)) as driver:
            self._emit(f"다방 메인 진입 및 검색: {self.user_input.region_keyword}")
            self._search_region(driver)
            self._emit("결과 페이지 로딩. 스크롤 시작")
            cards = self._scroll_collect_cards(driver)
            for idx, card in enumerate(cards, start=1):
                if self.pause_signal.should_stop():
                    break
                self.pause_signal.wait_if_paused()
                rec = self._parse_card(driver, card)
                if rec:
                    records.append(rec)
                if idx % 20 == 0:
                    self._emit(f"파싱 진행: {idx}/{len(cards)}")
                random_sleep()
        total_cards = len(cards)
        if total_cards == 0:
            self._dump_diagnostics(driver, "headless" if self.user_input.headless else "nonheadless")
        
        # 헤드리스에서 0건일 때 비헤드리스 재시도
        if total_cards == 0 and self.user_input.headless:
            self._emit("헤드리스에서 0건 감지 → non-headless로 1회 재시도")
            try:
                with safe_quit(create_chrome_driver(False)) as driver2:
                    self._search_region(driver2)
                    cards2 = self._scroll_collect_cards(driver2)
                    for idx, card in enumerate(cards2, start=1):
                        if self.pause_signal.should_stop():
                            break
                        self.pause_signal.wait_if_paused()
                        rec2 = self._parse_card(driver2, card)
                        if rec2:
                            records.append(rec2)
                        if idx % 20 == 0:
                            self._emit(f"비헤드리스 파싱 진행: {idx}/{len(cards2)}")
                        random_sleep()
                    total_cards = len(cards2)
                    if total_cards == 0:
                        self._dump_diagnostics(driver2, "nonheadless")
            except Exception as e:
                logger.warning("non-headless 재시도 중 오류: {}", e)

        return records, total_cards


