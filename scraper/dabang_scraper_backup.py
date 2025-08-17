from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import random
import time
from typing import Callable, List, Optional
from urllib.parse import urljoin
from pathlib import Path
import hashlib

from loguru import logger
from playwright.sync_api import sync_playwright, Page, Browser, expect  # type: ignore[reportMissingImports]
import re

from scraper.parsers import (
    normalize_price_text,
    normalize_maintenance_fee,
    to_absolute_time,
    extract_area_m2,
    extract_floor,
    extract_address,
    extract_price_text,
    to_ymd,
)
from scraper.anti_bot import build_context_kwargs, human_sleep, infinite_scroll, scroll_container
from scraper.selectors import *
import scraper.selectors as S
from scraper.utils.locators import first_locator_sync, click_first_sync, fill_first_sync, text_first_sync, first_locator_from_element_sync, text_first_from_element_sync
from config import settings


@dataclass
class ScrapeOptions:
    region: str
    property_type: str
    price_min: int
    price_max: int
    max_items: int
    max_pages: int
    headless: bool = True


@dataclass
class Item:
    address: str
    price_text: str
    maintenance_fee: Optional[int]
    realtor: str
    posted_at: str  # YYYY-MM-DD hh:mm:ss
    property_type: str
    url: str
    item_id: str
    area_m2: Optional[float] = None
    floor: Optional[str] = None
    property_number: Optional[str] = None
    options: Optional[str] = None
    security: Optional[str] = None
    tour_3d: Optional[str] = None
    details: Optional[str] = None


class DabangScraper:
    def __init__(self, opts: ScrapeOptions, stop_flag, log_cb: Optional[Callable[[str], None]] = None) -> None:
        self.opts = opts
        self.stop_flag = stop_flag
        self.log_cb = log_cb
        self._context = None

    def _log(self, msg: str) -> None:
        logger.info(msg)
        if self.log_cb:
            try:
                self.log_cb(msg)
            except Exception:
                pass

    def run(self) -> List[Item]:
        """크롤링 실행 - 모든 매물 종류 지원"""
        items: List[Item] = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.opts.headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                page = browser.new_page()
                try:
                    # 데스크톱 레이아웃 강제: 모바일/좁은 화면 분기 회피
                    page.set_viewport_size({"width": 1440, "height": 960})
                except Exception:
                    pass

                # 모든 매물 종류 크롤링
                if self.opts.property_type == "전체":
                    property_types = ["원룸", "투룸", "오피스텔", "아파트", "주택", "빌라"]
                    self._log(f"전체 매물 종류 크롤링 시작: {property_types}")

                    for prop_type in property_types:
                        self._log(f"=== {prop_type} 매물 크롤링 시작 ===")
                        self.opts.property_type = prop_type
                        try:
                            type_items = self._crawl_single_property_type(page, prop_type)
                            items.extend(type_items)
                            self._log(f"{prop_type} 매물 {len(type_items)}건 수집 완료")
                        except Exception as e:
                            self._log(f"{prop_type} 매물 크롤링 실패: {e}")
                            continue
                        # 매물 종류 간 대기
                        page.wait_for_timeout(2000)
                else:
                    # 단일 매물 종류 크롤링
                    items = self._crawl_single_property_type(page, self.opts.property_type)

                browser.close()
        except Exception as e:
            self._log(f"크롤링 실행 실패: {e}")

        # 중복 제거
        items = self._remove_duplicates(items)
        return items

    def _crawl_single_property_type(self, page: Page, property_type: str) -> List[Item]:
        """단일 매물 종류 크롤링"""
        items: List[Item] = []
        
        try:
            # 다방 메인 페이지로 이동
            page.goto("https://www.dabangapp.com/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            self._log(f"현재 URL: {page.url}")
            
            # 매물 종류별 페이지 이동
            if property_type in ["원룸", "투룸"]:
                # 원/투룸 페이지로 이동
                self._goto_onetwo_map(page)
            else:
                # 다른 매물 종류는 직접 해당 페이지로 이동
                self._switch_to_property_type(page, property_type)
            
            # 지역 검색 (지정된 경우)
            if self.opts.region:
                self._search_and_confirm_region(page, self.opts.region)
            
            # 지역 검색 후 추가 대기
            self._log("지역 검색 후 추가 대기 중...")
            page.wait_for_timeout(15000)  # 15초 대기
            
            # 매물 수집
            items = self._collect_items(page)
            
            # 매물 종류 정보 추가
            for item in items:
                item.property_type = property_type
            
        except Exception as e:
            self._log(f"{property_type} 매물 크롤링 실패: {e}")
        
        return items

    def _apply_property_type_filter(self, page: Page, property_type: str) -> None:
        """매물 종류 필터 적용"""
        try:
            self._log(f"매물 종류 필터 적용: {property_type}")
            
            # 매물 종류별 처리
            if property_type in ["원룸", "투룸"]:
                # 원/투룸은 이미 원/투룸 페이지에 있으므로 추가 필터만 적용
                self._apply_room_type_filter(page, property_type)
            elif property_type in ["오피스텔", "아파트", "주택", "빌라"]:
                # 다른 매물 종류로 전환
                self._switch_to_property_type(page, property_type)
            
        except Exception as e:
            self._log(f"매물 종류 필터 적용 실패: {e}")

    def _apply_room_type_filter(self, page: Page, room_type: str) -> None:
        """원룸/투룸 필터 적용"""
        try:
            # 추가필터에서 방구조 필터 시도
            self._log(f"방구조 필터 시도: {room_type}")
            
            # 추가필터 버튼 클릭
            filter_selectors = [
                "button:has-text('추가필터')",
                "div:has-text('추가필터')",
                "[class*='filter']:has-text('추가')"
            ]
            
            for selector in filter_selectors:
                try:
                    filter_btn = page.locator(selector).first
                    if filter_btn.count() > 0:
                        filter_btn.click()
                        page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
            
            # 방구조 선택
            try:
                room_structure_btn = page.locator(f"button:has-text('{room_type}')").first
                if room_structure_btn.count() > 0:
                    room_structure_btn.click()
                    page.wait_for_timeout(1000)
                    self._log(f"{room_type} 필터 적용 완료")
            except Exception as e:
                self._log(f"방구조 필터 적용 실패: {e}")
            
            # 필터 닫기
            try:
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
            except Exception:
                pass
                
        except Exception as e:
            self._log(f"방구조 필터 적용 실패: {e}")

    def _switch_to_property_type(self, page: Page, property_type: str) -> None:
        """다른 매물 종류로 전환 - 이미지에서 확인된 실제 구조 반영"""
        try:
            self._log(f"매물 종류 전환: {property_type}")
            
            # 이미지에서 확인된 실제 URL 구조 사용
            property_urls = {
                "오피스텔": "/map/officetel",
                "아파트": "/map/apt", 
                "주택": "/map/house",
                "빌라": "/map/house",
                "분양": "/map/sale"
            }
            
            if property_type in property_urls:
                target_url = property_urls[property_type]
                current_url = page.url
                
                # 현재 URL이 이미 해당 매물 종류인지 확인
                if target_url in current_url:
                    self._log(f"이미 {property_type} 페이지에 있습니다.")
                    return
                
                # 해당 매물 종류 페이지로 직접 이동
                full_url = f"https://www.dabangapp.com{target_url}"
                self._log(f"{property_type} 페이지로 이동: {full_url}")
                
                page.goto(full_url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                
                # 지도 탭 클릭 (필요한 경우)
                try:
                    map_tab = page.locator("a:has-text('지도')").first
                    if map_tab.count() > 0:
                        map_tab.click()
                        page.wait_for_timeout(2000)
                        self._log("지도 탭 클릭 완료")
                except Exception as e:
                    self._log(f"지도 탭 클릭 실패: {e}")
                
                # 매물 버튼 클릭 (필요한 경우)
                try:
                    self._open_list_panel(page)
                except Exception as e:
                    self._log(f"매물 버튼 클릭 실패: {e}")
                
                self._log(f"{property_type} 매물 종류로 전환 완료")
            else:
                self._log(f"지원하지 않는 매물 종류: {property_type}")
                
        except Exception as e:
            self._log(f"매물 종류 전환 실패: {e}")

    @staticmethod
    def _norm(s: str) -> str:
        return re.sub(r"\s+|[()·,]", "", (s or "").strip())

    def _search_and_confirm_region(self, page: Page, region_text: str) -> None:
        # uses selectors.py
        mode_all = len((region_text or "").strip()) == 0
        self._log(f"검색 시작: {'전지역' if mode_all else region_text}")
        # onetwo 지도 페이지가 아니라면 이동 보장
        try:
            if "/map/onetwo" not in (page.url or ""):
                self._goto_onetwo_map(page)
        except Exception:
            pass
        if mode_all:
            # 지역 입력 없이 기본 목록을 스크롤로 로딩
            page.wait_for_timeout(1500)
            self._open_list_panel(page)
            return
        # 이하: 특정 지역 검색 모드
        try:
            # selectors.py의 REGION_INPUT 사용
            fill_first_sync(page, REGION_INPUT, region_text)
            page.wait_for_timeout(900)
            
            # 개선된 지역 선택 로직 (이미지에서 확인된 실제 구조 반영)
            clicked = self._select_region_from_suggestions(page, region_text)
            
            page.wait_for_timeout(1200)
            # 좌측 리스트 패널 열기
            self._open_list_panel(page)
            # 매물 탭 클릭 이후 네트워크 안정 + 컨테이너/카드 텍스트까지 대기
            try:
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(400)
                page.wait_for_selector('#onetwo-list, #map-list-tab-container, [id^="map-list-"]', state='visible', timeout=10000)
                page.wait_for_selector(':text("월세"), :text("전세"), a[href*="detail_type=room"]', timeout=8000)
            except Exception:
                pass
            # 지역 검색 후 컨테이너가 다시 로드될 수 있으므로 추가 대기
            page.wait_for_timeout(3000)
            
            # 지역 검색 후 컨테이너 재확인 (대기 시간 증가)
            page.wait_for_timeout(10000)  # 10초 대기로 증가
            self._ensure_list_container_after_search(page)
        except Exception as e:
            self._log(f"지역 검색 실패: {e}")
            # 검색창을 못 찾으면 onetwo로 재진입 후 재탐색
            try:
                self._goto_onetwo_map(page)
                fill_first_sync(page, REGION_INPUT, region_text)
            except Exception:
                pass

    def _select_region_from_suggestions(self, page: Page, region_text: str) -> bool:
        # uses selectors.py
        """개선된 지역 선택 로직 - 이미지에서 확인된 실제 DOM 구조 반영"""
        self._log(f"지역 선택 시도: {region_text}")
        
        # 1. 정확한 텍스트 일치 버튼 클릭 (이미지에서 확인된 실제 구조)
        try:
            # 이미지에서 확인된 실제 지역 선택 버튼 클래스 사용
            exact_button = page.locator(f"button.sc-fEETNT.cGRZls:has-text('{region_text}')").first
            if exact_button.count() > 0:
                self._log(f"정확한 지역 버튼 발견: {region_text}")
                exact_button.click()
                page.wait_for_timeout(1000)
                return True
        except Exception as e:
            self._log(f"정확한 지역 버튼 클릭 실패: {e}")
        
        # 2. 부분 일치 버튼 클릭 - selectors.py 사용
        try:
            for button_sel in REGION_SUGGEST_ITEM:
                if "button" in button_sel:
                    buttons = page.locator(button_sel)
                    for i in range(buttons.count()):
                        try:
                            button = buttons.nth(i)
                            button_text = button.inner_text(timeout=1000).strip()
                            if region_text in button_text:
                                self._log(f"부분 일치 지역 버튼 발견: {button_text}")
                                button.click()
                                page.wait_for_timeout(1000)
                                return True
                        except Exception:
                            continue
        except Exception as e:
            self._log(f"부분 일치 지역 버튼 클릭 실패: {e}")
        
        # 3. 기존 로직 폴백
        clicked = False
        try:
            exact = page.get_by_text(region_text, exact=True).first
            if exact.count() > 0:
                exact.click()
                clicked = True
        except Exception:
            pass
        if not clicked:
            try:
                xp = f"xpath=//*[self::li or self::a or self::div][normalize-space()='{region_text}']"
                exact2 = page.locator(xp).first
                if exact2.count() > 0:
                    exact2.click()
                    clicked = True
            except Exception:
                pass
        if not clicked:
            # 마지막 폴백: 첫 제안 또는 Enter - selectors.py 사용
            try:
                click_first_sync(page, REGION_SUGGEST_ITEM)
            except Exception:
                # 검색창에서 Enter 키 입력
                try:
                    fill_first_sync(page, REGION_INPUT, "")
                    page.keyboard.press("Enter")
                except Exception:
                    pass
        
        return clicked

    def _open_list_panel(self, page: Page) -> None:
        # uses selectors.py
        """좌측 '매물' 리스트 패널이 보이도록 보장.

        최신 DOM에서 텍스트 칩/버튼을 클릭하여 목록이 열리게 한다.
        """
        self._log("리스트 패널을 열려고 시도합니다...")
        
        # selectors.py의 LIST_OPEN_BUTTON 사용
        try:
            click_first_sync(page, LIST_OPEN_BUTTON)
            page.wait_for_timeout(2000)
            self._log("매물 버튼 클릭 성공")
        except Exception as e:
            self._log(f"매물 버튼 클릭 실패: {e}")
            # 폴백: 다양한 클릭 방법 시도
            for sel in LIST_OPEN_BUTTON:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0:
                        self._log(f"매물 버튼을 찾았습니다: {sel}")
                        
                        # 방법 1: JavaScript 클릭 시도
                        try:
                            page.evaluate("(element) => element.click()", loc)
                            page.wait_for_timeout(2000)
                            self._log("JavaScript 클릭 성공")
                            break
                        except Exception as e:
                            self._log(f"JavaScript 클릭 실패: {e}")
                        
                        # 방법 2: 포커스 후 클릭 시도
                        try:
                            loc.focus()
                            page.wait_for_timeout(500)
                            loc.click(timeout=5000)
                            page.wait_for_timeout(2000)
                            self._log("포커스 후 클릭 성공")
                            break
                        except Exception as e:
                            self._log(f"포커스 후 클릭 실패: {e}")
                        
                        # 방법 3: 스크롤 후 클릭 시도
                        try:
                            loc.scroll_into_view_if_needed()
                            page.wait_for_timeout(500)
                            loc.click(timeout=5000)
                            page.wait_for_timeout(2000)
                            self._log("스크롤 후 클릭 성공")
                            break
                        except Exception as e:
                            self._log(f"스크롤 후 클릭 실패: {e}")
                        
                        # 방법 4: 키보드 엔터 시도
                        try:
                            loc.focus()
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(2000)
                            self._log("키보드 엔터 성공")
                            break
                        except Exception as e:
                            self._log(f"키보드 엔터 실패: {e}")
                        
                except Exception as e:
                    self._log(f"매물 버튼 클릭 실패: {sel} - {e}")
                    continue
        
        # 지도 화면에서 목록 펼침용 사이드 핸들 같은 요소도 시도
        try:
            # typical handle at left edge
            handle = page.locator('aside, [class*="panel"], [class*="Dock"], [class*="Sidebar"]').first
            if handle.count() > 0:
                # focus to ensure it's interactable
                handle.hover(timeout=1000)
                page.wait_for_timeout(500)
                self._log("사이드 핸들을 찾았습니다.")
        except Exception:
            pass
        
        # 컨테이너가 나타날 때까지 소프트 대기
        for i in range(20):  # 대기 시간 증가
            try:
                # 정의된 후보들을 순회하여 하나라도 보이면 성공
                found = False
                for sel in getattr(S, 'LIST_CONTAINER_SELECTORS', []):
                    if page.locator(sel).count() > 0:
                        self._log(f"리스트 컨테이너를 찾았습니다: {sel}")
                        found = True
                        break
                if found:
                    # 매물 버튼 클릭 후 추가 대기
                    self._log("매물 버튼 클릭 후 대기 중...")
                    page.wait_for_timeout(8000)  # 8초 대기
                    return
            except Exception:
                pass
            page.wait_for_timeout(500)  # 대기 시간 증가
            if i % 5 == 0:  # 5초마다 로그 출력
                self._log(f"리스트 컨테이너 대기 중... ({i+1}/20)")
        
        self._log("리스트 패널을 열지 못했습니다.")

    def _apply_filters(self, page: Page) -> None:
        # 매물 종류 탭/버튼 시도
        t = self.opts.property_type
        try:
            if t in {"아파트", "오피스텔", "주택", "빌라"}:
                self._log(f"카테고리 전환 시도: {t}")
                for sel in S.PROPERTY_TYPE_SIDEBAR:
                    if t in sel:
                        try:
                            page.locator(sel).first.click(timeout=2000)
                            page.wait_for_timeout(800)
                            break
                        except Exception:
                            continue
            elif t in {"원룸", "투룸"}:
                # 추가필터에서 방구조 → 원룸/투룸 시도 (실패해도 무시)
                self._log("방구조 필터 시도")
                for sel in S.FILTER_DROPDOWNS:
                    if "추가필터" in sel:
                        try:
                            page.locator(sel).first.click(timeout=2000)
                            page.locator(r"text=/방구조|방\s*구조/").first.click(timeout=2000)
                            page.get_by_text(t).first.click(timeout=2000)
                            page.keyboard.press("Escape")
                            break
                        except Exception:
                            continue
        except Exception:
            self._log("필터 적용을 건너뜀(요소 미발견)")
        # 가격 범위(가능 범위에서만) — DOM 변동이 잦아 보류

    def _collect_items(self, page: Page) -> List[Item]:
        """목록을 "끝까지 수집"하도록 페이지네이션 루프 추가"""
        self._log("매물 수집 시작...")
        items: List[Item] = []
        seen_ids = set()
        page_idx = 1

        while True:
            list_el = self._resolve_list_container_improved(page)

            # 카드 기다리기
            self._log(f"=== 페이지 {page_idx} 수집 시작 ===")
            cards = None
            # onetwo는 li.sc-bNShyZ
            for sel in CARD_ROOT_SELECTORS:
                loc = list_el.locator(sel)
                if loc.count() > 0:
                    cards = loc
                    self._log(f"카드 선택자 사용: {sel}, 개수: {loc.count()}")
                    break
            if cards is None:
                self._log("카드 없음 – selectors.py 점검 필요")
                break

            # 페이지 내 카드 파싱
            limit_this_page = cards.count()
            for i in range(limit_this_page):
                # 수집 개수 제한 도달 시 즉시 종료
                if self.opts.max_items and len(items) >= self.opts.max_items:
                    self._log(f"요청 수({self.opts.max_items}) 도달")
                    return items
                
                try:
                    card = cards.nth(i)
                    
                    # 디버깅: 카드의 실제 텍스트 내용 출력
                    card_text = card.inner_text()
                    self._log(f"카드 {i+1} 텍스트 내용: {card_text[:200]}...")
                    
                    link_el = card.locator("a[href^='/room/']").first
                    href = link_el.get_attribute("href") if link_el.count() else None
                    full = urljoin(page.url, href) if href else ""
                    pid = ""
                    if full:
                        m = re.search(r"detail_id=([^&]+)", full)
                        pid = m.group(1) if m else hashlib.md5(full.encode()).hexdigest()
                    if pid in seen_ids:
                        continue

                    # 기본 정보 파싱 (카드에서 직접)
                    try:
                        price = text_first_from_element_sync(card, CARD_PRICE) or ""
                    except Exception:
                        price = ""
                    
                    # 상세 정보는 카드 클릭하여 상세 페이지에서 가져오기
                    address = ""
                    realtor = ""
                    maintenance = ""
                    posted_date = ""
                    
                    try:
                        # 카드 클릭하여 상세 페이지로 이동
                        self._log(f"카드 {i+1} 클릭하여 상세 페이지로 이동...")
                        card.click()
                        page.wait_for_timeout(3000)  # 페이지 로딩 대기
                        
                        # 상세 페이지에서 정보 추출 - TypeScript 파일 참고하여 수정
                        # 주소 찾기
                        try:
                             # TypeScript의 DETAIL_ADDR 선택자들을 참고
                             address_selectors = [
                                 "section[data-scroll-spy-element='near'] p:has-text('시')",  # 위치 탭 내 주소
                                 "section[data-scroll-spy-element='near'] p:has-text('구')",  # 구 포함된 주소
                                 "section[data-scroll-spy-element='near'] p:has-text('동')",  # 동 포함된 주소
                                 "div.sc-hbxBMb.efnhT > p",  # 스크린샷에서 확인된 정확한 주소 wrapper
                                 "p:has-text('시')", "p:has-text('구')", "p:has-text('동')", "p:has-text('읍')",
                                 "p:has-text(/[가-힣]+(시|도)\s+[가-힣]+(구|군)\s+[가-힣]+(동|읍|면)/)",
                                 "div:has-text(/[가-힣]+(시|도)\s+[가-힣]+(구|군)\s+[가-힣]+(동|읍|면)/)",
                                 "span:has-text(/[가-힣]+(시|도)\s+[가-힣]+(구|군)\s+[가-힣]+(동|읍|면)/)",
                                 "text=/[가-힣]+(시|도)\s+[가-힣]+(구|군)\s+[가-힣]+(동|읍|면)/"
                             ]
                             
                             for selector in address_selectors:
                                 try:
                                     address_elements = page.locator(selector)
                                     if address_elements.count() > 0:
                                         address = address_elements.first.inner_text().strip()
                                         # 주소 형식 검증 (시/군/구/동/읍/리 포함)
                                         if len(address) >= 8 and re.search(r'시|군|구|동|읍|리', address):
                                             self._log(f"주소 찾음: {address}")
                                             break
                                 except Exception:
                                     continue
                         except Exception as e:
                             self._log(f"주소 추출 실패: {e}")
                         
                         # 부동산 정보 찾기
                         try:
                             # TypeScript의 DETAIL_REALTOR 선택자들을 참고
                             realtor_selectors = [
                                 "section[data-scroll-spy-element='agent-info'] h1:has-text('부동산')",  # 중개사무소 정보 섹션의 상호 h1
                                 "section[data-scroll-spy-element='agent-info'] h1:has-text('공인중개사')",  # 공인중개사 포함
                                 "section[data-scroll-spy-element='agent-info'] h1:has-text('중개사무소')",  # 중개사무소 포함
                                 "div.sc-gVrasc.ktkEIH h1",  # 스크린샷에서 확인된 정확한 중개사 h1 컨테이너
                                 "h1:has-text('공인중개사')", "h1:has-text('중개사무소')",  # 실제 작동하는 중개사 셀렉터
                                 "section[data-scroll-spy-element='agent-info'] a[href^='/agent/']",
                                 "[data-testid='realtor'] h1", "[data-testid='realtor']",  # 폴백
                                 "h1:has-text(/공인중개|중개사무소|부동산/)",
                                 "div:has-text(/공인중개|중개사무소|부동산/)",
                                 "p:has-text(/공인중개|중개사무소|부동산/)",
                                 "text=/공인중개|중개사무소|부동산/"
                             ]
                             
                             for selector in realtor_selectors:
                                 try:
                                     realtor_elements = page.locator(selector)
                                     if realtor_elements.count() > 0:
                                         realtor = realtor_elements.first.inner_text().strip()
                                         # 불필요 접두사 제거 및 정리
                                         realtor = re.sub(r'\s*(공인중개사|중개사무소|중개사)\s*', '', realtor).strip()
                                         if len(realtor) >= 3:  # 최소 3자 이상
                                             self._log(f"부동산 찾음: {realtor}")
                                             break
                                 except Exception:
                                     continue
                         except Exception as e:
                             self._log(f"부동산 추출 실패: {e}")
                         
                         # 관리비 정보 찾기
                         try:
                             # TypeScript의 관리비 선택자들을 참고
                             maintenance_selectors = [
                                 "li:has-text('관리비')",  # 상세정보 탭 내 관리비
                                 "p:has-text('관리비')",
                                 "span:has-text('관리비')",
                                 "div:has-text('관리비')",
                                 "text=/관리비/"
                             ]
                             
                             for selector in maintenance_selectors:
                                 try:
                                     maintenance_elements = page.locator(selector)
                                     if maintenance_elements.count() > 0:
                                         maintenance_text = maintenance_elements.first.inner_text()
                                         maintenance_match = re.search(r'관리비\s*(없음|\d+만?)', maintenance_text)
                                         if maintenance_match:
                                             maintenance = maintenance_match.group(0).strip()
                                             self._log(f"관리비 찾음: {maintenance}")
                                             break
                                 except Exception:
                                     continue
                         except Exception as e:
                             self._log(f"관리비 추출 실패: {e}")
                         
                         # 등록일 찾기
                         try:
                             # TypeScript의 DETAIL_POSTED_DATE 선택자들을 참고
                             date_selectors = [
                                 "p.sc-dPDzVR.iYQyEM",  # 스크린샷에서 확인된 정확한 날짜 셀렉터
                                 "p:has-text('2025.')", "p:has-text('2024.')", "p:has-text('2023.')",
                                 "li:has-text('최초등록일')", "p:has-text('최초등록일')",
                                 "[data-testid='posted-date']", "[class*='date']",
                                 "div:has-text('최초등록일')",
                                 "span:has-text('최초등록일')",
                                 "text=/최초등록일/"
                             ]
                             
                             for selector in date_selectors:
                                 try:
                                     date_elements = page.locator(selector)
                                     if date_elements.count() > 0:
                                         date_text = date_elements.first.inner_text()
                                         # 날짜 형식 검증 (YYYY.MM.DD 또는 YYYY-MM-DD)
                                         date_match = re.search(r'(\d{4}[.-]\d{2}[.-]\d{2})', date_text)
                                         if date_match:
                                             posted_date = date_match.group(1)
                                             self._log(f"등록일 찾음: {posted_date}")
                                             break
                                 except Exception:
                                     continue
                         except Exception as e:
                             self._log(f"등록일 추출 실패: {e}")
                        
                        # 뒤로 가기
                        self._log(f"상세 페이지에서 뒤로 가기...")
                        page.go_back()
                        page.wait_for_timeout(2000)  # 페이지 로딩 대기
                        
                    except Exception as e:
                        self._log(f"상세 페이지 정보 추출 실패: {e}")
                        # 뒤로 가기 시도
                        try:
                            page.go_back()
                            page.wait_for_timeout(2000)
                        except Exception:
                            pass

                    item = Item(
                        address=address,
                        price_text=price,
                        maintenance_fee=normalize_maintenance_fee(maintenance) if maintenance else None,
                        realtor=realtor,
                        posted_at=to_ymd(posted_date) if posted_date else datetime.now().strftime("%Y-%m-%d"),
                        property_type=self.opts.property_type,
                        url=full,
                        item_id=pid,
                        details=details,
                        area_m2=extract_area_m2(details),
                        floor=extract_floor(details),
                    )
                    items.append(item)
                    seen_ids.add(pid)
                    # 상세한 아이템 정보 로그 출력
                    maintenance_info = f"관리비: {item.maintenance_fee:,}원" if item.maintenance_fee else "관리비: 없음"
                    self._log(f"아이템 {len(items)} 수집 완료:")
                    self._log(f"  📍 주소: {item.address}")
                    self._log(f"  💰 가격: {item.price_text}")
                    self._log(f"  🏢 부동산: {item.realtor}")
                    self._log(f"  📅 등록일: {item.posted_at}")
                    self._log(f"  💸 {maintenance_info}")
                    self._log(f"  🔗 URL: {item.url}")
                    self._log("  " + "─" * 50)
                except Exception as e:
                    self._log(f"카드 파싱 실패: {e}")
                    continue

            # 페이지네이션 마운트 대기
            page.wait_for_timeout(400)  # 페이지네이션 마운트 대기
            # 다음 페이지가 없으면 종료
            if not self._go_next_page_onetwo(page, list_el):
                self._log("다음 페이지 없음 – 종료")
                break

            page_idx += 1
            page.wait_for_timeout(1500)

        self._log(f"수집 완료: {len(items)}건")
        return items

    def _go_next_page_onetwo(self, page: Page, list_el):
        """다음 페이지로 이동.
        - 리스트 컨테이너 바닥까지 스크롤
        - onetwo 리스트 주변의 페이지네이션을 찾아 '다음' 또는 숫자 버튼 클릭
        - 첫 카드가 바뀌는지(또는 페이지 번호가 바뀌는지)까지 대기
        """
        # 현재 첫 카드 id 스냅샷
        def _first_card_id():
            try:
                link = list_el.locator("a[href^='/room/']").first
                if link.count() == 0:
                    return ""
                href = link.get_attribute("href") or ""
                full = urljoin(page.url, href)
                m = re.search(r"detail_id=([^&]+)", full)
                return m.group(1) if m else hashlib.md5(full.encode()).hexdigest()
            except Exception:
                return ""

        prev_id = _first_card_id()

        # 1) 컨테이너 바닥까지 스크롤(페이지네이션 노출)
        try:
            page.evaluate("(el)=>{el.scrollTop = el.scrollHeight;}", list_el.element_handle())
        except Exception:
            try:
                list_el.evaluate('el => el.scrollTo(0, el.scrollHeight)')
            except Exception:
                page.mouse.wheel(0, 2500)
        page.wait_for_timeout(700)

        # 2) 페이지네이션 컨테이너 탐색 (컨테이너 기준 → 형제/조상 범위)
        pagination_candidates = [
            "xpath=//div[contains(@class,'pagination')][1]",
            "xpath=ancestor::div[contains(@id,'map-list-tab-container')]//div[contains(@class,'pagination')]",
        ]
        try:
            # onetwo-list 기준으로 우선 탐색
            base = page.locator("#onetwo-list").first if page.locator("#onetwo-list").count() else list_el
        except Exception:
            base = list_el

        pag = None
        for sel in getattr(S, 'PAGINATION_CONTAINER', []) + pagination_candidates:
            try:
                candidate = base.locator(sel).first if sel.startswith("xpath=") else page.locator(sel).first
                if candidate.count() > 0:
                    pag = candidate
                    break
            except Exception:
                continue
        if not pag or pag.count() == 0:
            return False

        # 3) 다음 버튼/숫자 버튼 클릭 시도
        # 우선: > / 다음 / › 버튼
        next_selectors = list(getattr(S, 'NEXT_PAGE_BUTTON', [])) + [
            "button[aria-label*='다음']",
            "button[aria-label*='next' i]",
            "button:has-text('>')",
            "button:has-text('›')",
            "a:has-text('>')",
        ]
        clicked = False
        for nx in next_selectors:
            try:
                btn = pag.locator(nx).first
                if btn.count() == 0:
                    continue
                # 비활성 확인
                dis = btn.get_attribute("disabled") is not None
                if dis:
                    continue
                btn.scroll_into_view_if_needed()
                btn.click()
                clicked = True
                break
            except Exception:
                continue

        # 대체: 현재 선택된 페이지 다음 숫자 클릭
        if not clicked:
            try:
                nums = pag.locator("button").all()
                cur_idx = -1
                for i, b in enumerate(nums):
                    cls = (b.get_attribute("class") or "")
                    aria = (b.get_attribute("aria-current") or "")
                    if "active" in cls or "selected" in cls or aria == "page":
                        cur_idx = i
                        break
                if cur_idx != -1 and cur_idx + 1 < len(nums):
                    nums[cur_idx + 1].scroll_into_view_if_needed()
                    nums[cur_idx + 1].click()
                    clicked = True
            except Exception:
                pass

        if not clicked:
            return False

        # 4) 변경 대기: 네트워크 idle + 첫 카드 변경 또는 페이지 번호 변경
        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        # 첫 카드 변경 대기
        for _ in range(20):
            cur = _first_card_id()
            if cur and cur != prev_id:
                break
            page.wait_for_timeout(250)
        return True

    def _open_all_detail_tabs(self, page: Page):
        """상세 페이지에서 5개 탭 강제 클릭 후 읽기"""
        for sel in DETAIL_TAB_BUTTONS:
            try:
                el = page.locator(sel).first
                if el.count():
                    el.click()
                    page.wait_for_timeout(300)
            except Exception:
                continue

    def _goto_onetwo_map(self, page: Page) -> None:
        try:
            page.goto("https://www.dabangapp.com", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            self._log(f"현재 URL: {page.url}")

            try:
                onetwo_link = page.locator("a:has-text('원/투룸')").first
                if onetwo_link.count() > 0:
                    self._log("원/투룸 링크를 찾았습니다. 클릭합니다.")
                    onetwo_link.click()
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(5000)
                    self._log(f"원/투룸 클릭 후 URL: {page.url}")
                else:
                    self._log("원/투룸 링크를 찾지 못했습니다. 직접 URL로 이동합니다.")
                    page.goto("https://www.dabangapp.com/map/onetwo", timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(5000)
                    self._log(f"직접 이동 후 URL: {page.url}")
            except Exception as e:
                self._log(f"원/투룸 클릭 실패: {e}. 직접 URL로 이동합니다.")
                page.goto("https://www.dabangapp.com/map/onetwo", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                self._log(f"직접 이동 후 URL: {page.url}")

            # 지도 탭 클릭 (안전) - selectors.py 사용
            try:
                click_first_sync(page, NAVIGATION_TABS)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
                self._log(f"지도 탭 클릭 후 URL: {page.url}")
            except Exception as e:
                self._log(f"지도 탭 클릭 실패: {e}")

            # 지도 요소 대기 (유연)
            try:
                page.wait_for_selector("canvas, [class*='map'], [data-testid*='map']", timeout=10000)
                self._log("지도 요소를 찾았습니다.")
            except Exception:
                self._log("지도 요소 대기 실패, 계속 진행")
        except Exception as e:
            self._log(f"지도 페이지 이동 실패: {e}")
        self._open_list_panel(page)

    def _check_pagination(self, page: Page) -> bool:
        # uses selectors.py
        """페이지네이션이 있는지 확인하고 다음 페이지로 이동할 수 있는지 확인합니다."""
        try:
            # 페이지네이션 컨테이너 확인 - selectors.py 사용
            for sel in PAGINATION_CONTAINER:
                if page.locator(sel).count() > 0:
                    self._log(f"페이지네이션 컨테이너 발견: {sel}")
                    
                    # 다음 페이지 버튼 확인 - selectors.py 사용
                    for next_sel in NEXT_PAGE_BUTTON:
                        next_btn = page.locator(next_sel).first
                        if next_btn.count() > 0:
                            # 버튼이 비활성화되어 있는지 확인
                            try:
                                is_disabled = next_btn.get_attribute("disabled") is not None
                                if not is_disabled:
                                    self._log(f"다음 페이지 버튼 발견: {next_sel}")
                                    return True
                                else:
                                    self._log("다음 페이지 버튼이 비활성화되어 있습니다.")
                                    return False
                            except Exception:
                                self._log(f"다음 페이지 버튼 확인 실패: {next_sel}")
                                continue
                    break
            return False
        except Exception as e:
            self._log(f"페이지네이션 확인 실패: {e}")
            return False

    def _click_next_page(self, page: Page) -> bool:
        # uses selectors.py
        """다음 페이지 버튼을 클릭합니다."""
        try:
            # selectors.py의 NEXT_PAGE_BUTTON 사용
            click_first_sync(page, NEXT_PAGE_BUTTON)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)
            return True
        except Exception as e:
            self._log(f"다음 페이지 클릭 실패: {e}")
            return False

    def _get_current_page_number(self, page: Page) -> int:
        # uses selectors.py
        """현재 페이지 번호를 가져옵니다."""
        try:
            for sel in PAGE_NUMBER_BUTTONS:
                buttons = page.locator(sel)
                for i in range(buttons.count()):
                    try:
                        btn = buttons.nth(i)
                        # 현재 페이지 버튼은 보통 다른 스타일을 가집니다
                        class_attr = btn.get_attribute("class") or ""
                        if "active" in class_attr or "selected" in class_attr:
                            text = btn.inner_text(timeout=1000)
                            if text.isdigit():
                                return int(text)
                    except Exception:
                        continue
            return 1  # 기본값
        except Exception as e:
            self._log(f"현재 페이지 번호 확인 실패: {e}")
            return 1

    def _resolve_list_container_by_anchor(self, page: Page):
        """목록 카드의 앵커(`/room/`)를 기준으로 가장 가까운 스크롤 가능한 조상을 자동 탐지한다.

        1) 앵커가 안 보이면 리스트 패널 열기 후보를 시도
        2) 첫 번째 앵커의 조상들을 타고 올라가며 overflowY/scrollHeight로 스크롤러 판정
        3) 후보에 data-picked="1"를 달아 Locator로 재획득 후 카드 존재성 검증
        """
        try:
            page.wait_for_timeout(600)
            anchors = page.locator("a[href^='/room/']")
            if anchors.count() == 0:
                # 리스트 패널 열기 후보 시도 - selectors.py 사용
                try:
                    click_first_sync(page, LIST_OPEN_BUTTON)
                    page.wait_for_timeout(500)
                except Exception:
                    pass
                page.wait_for_timeout(600)
            if anchors.count() == 0:
                return None

            handle = anchors.first.element_handle()
            if not handle:
                return None
            picked = page.evaluate_handle(
                """
                el => {
                  const canScroll = (n) => {
                    if (!n) return false;
                    const s = getComputedStyle(n);
                    return /(auto|scroll)/.test(s.overflowY) || n.scrollHeight > n.clientHeight;
                  };
                  let cur = el;
                  while (cur && cur.parentElement) {
                    cur = cur.parentElement;
                    if (canScroll(cur)) return cur;
                  }
                  return null;
                }
                """,
                handle,
            )
            if not picked:
                return None
            page.evaluate('(el)=>el.setAttribute("data-picked","1")', picked)
            loc = page.locator('[data-picked="1"]').first
            # 카드 후보 존재 확인
            for csel in S.CARD_ROOT_SELECTORS:
                if loc.locator(csel).count() > 0:
                    self._log("컨테이너(앵커기반) 확정: data-picked=1")
                    return loc
            return None
        except Exception:
            return None

    def _resolve_list_container(self, page: Page):
        # uses selectors.py
        # 0) 앵커→조상 스크롤러 자동 탐지(우선 시도)
        loc = self._resolve_list_container_by_anchor(page)
        if loc is not None:
            return loc

        # 1) 정적 후보 순회 - selectors.py 사용
        for sel in LIST_CONTAINER_SELECTORS:
            try:
                loc = page.locator(sel).first
                if loc.count() == 0:
                    continue
                loc.wait_for(state="visible", timeout=3000)
                self._log(f"컨테이너 후보 발견: {sel}")
                
                # 특별 처리: #onetwo-list는 카드 확인 없이 바로 반환
                if sel == "#onetwo-list":
                    self._log(f"onetwo-list 컨테이너 확정: {sel}")
                    return loc
                
                # 카드 존재 확인(성급탈락 방지) - selectors.py 사용
                has_cards = False
                for csel in CARD_ROOT_SELECTORS:
                    card_count = loc.locator(csel).count()
                    if card_count > 0:
                        has_cards = True
                        self._log(f"  카드 발견: {csel} - {card_count}개")
                        break
                if has_cards:
                    self._log(f"컨테이너 확정: {sel}")
                    return loc
                else:
                    self._log(f"  카드 없음, 다음 후보 시도")
            except Exception as e:
                self._log(f"컨테이너 후보 실패 ({sel}): {e}")
                continue
        # 2) 휴리스틱 자동 탐지
        try:
            handle = page.evaluate_handle(
                """
                () => {
                  const canScroll = el => {
                    const s = getComputedStyle(el);
                    return (/(auto|scroll)/.test(s.overflowY) || el.scrollHeight > el.clientHeight);
                  };
                  const candidates = Array.from(document.querySelectorAll('div'));
                  const scored = candidates.map(el => {
                    let score = 0;
                    if (canScroll(el)) score += 2;
                    if (el.id && el.id.startsWith('dock-content-')) score += 3;
                    const cardsA = el.querySelectorAll('a[href^="/room/"]').length;
                    const items = el.querySelectorAll('[role="listitem"]').length;
                    score += Math.min(cardsA + items, 10) / 5;
                    return {el, score, cardsA, items};
                  }).filter(x => x.score >= 3)
                    .sort((a,b) => b.score - a.score);
                  return scored.length ? scored[0].el : null;
                }
                """
            )
            if handle:
                page.evaluate('(el)=>el.setAttribute("data-picked","1")', handle)
                loc = page.locator('[data-picked="1"]').first
                # 검증 - selectors.py 사용
                for csel in CARD_ROOT_SELECTORS:
                    if loc.locator(csel).count() > 0:
                        self._log("컨테이너(휴리스틱) 확정: data-picked=1")
                        return loc
        except Exception:
            pass
        # 3) 더 유연한 탐지 시도
        try:
            # 전체 페이지에서 카드 요소 찾기 - selectors.py 사용
            for csel in CARD_ROOT_SELECTORS:
                cards = page.locator(csel)
                if cards.count() > 0:
                    self._log(f"카드 발견: {csel} - {card_count}개")
                    # 카드의 부모 컨테이너 찾기
                    first_card = cards.first
                    container = first_card.evaluate("""
                        (el) => {
                            const canScroll = (n) => {
                                if (!n) return false;
                                const s = getComputedStyle(n);
                                return /(auto|scroll)/.test(s.overflowY) || n.scrollHeight > n.clientHeight;
                            };
                            let cur = el.parentElement;
                            while (cur && cur.parentElement) {
                                if (canScroll(cur)) return cur;
                                cur = cur.parentElement;
                            }
                            return el.parentElement || document.body;
                        }
                    """)
                    if container:
                        page.evaluate('(el)=>el.setAttribute("data-picked","1")', container)
                        loc = page.locator('[data-picked="1"]').first
                        self._log("컨테이너(유연탐지) 확정: data-picked=1")
                        return loc
        except Exception as e:
            self._log(f"유연 탐지 실패: {e}")
        
        # 4) 최후의 수단: body를 컨테이너로 사용
        try:
            self._log("최후 수단: body를 컨테이너로 사용")
            return page.locator("body")
        except Exception as e:
            self._log(f"body 컨테이너 실패: {e}")
        
        # 4) 진단 덤프
        self._dump_container_diagnostics(page)
        raise RuntimeError("리스트 컨테이너를 찾지 못했습니다. selectors.py 업데이트 필요")

    def _dump_container_diagnostics(self, page: Page) -> None:
        try:
            htmls = page.evaluate(
                """
                () => {
                  const res = [];
                  const canScroll = el => {
                    const s = getComputedStyle(el);
                    return (/(auto|scroll)/.test(s.overflowY) || el.scrollHeight > el.clientHeight);
                  };
                  const candidates = Array.from(document.querySelectorAll('div')).map(el=>{
                    const cardsA = el.querySelectorAll('a[href^="/room/"]').length;
                    const items = el.querySelectorAll('[role="listitem"]').length;
                    const id = el.id || '';
                    const cls = el.className || '';
                    const sc = canScroll(el);
                    return {el, id, cls, sc, cardsA, items};
                  }).filter(x=> x.sc || x.cardsA>0 || x.items>0)
                    .sort((a,b)=>(b.cardsA+b.items)-(a.cardsA+a.items))
                    .slice(0,3);
                  return candidates.map(c=>({
                    id:c.id, cls:c.cls, sc:c.sc, cardsA:c.cardsA, items:c.items,
                    outer: c.el.outerHTML.slice(0, 2000)
                  }));
                }
                """
            )
            for i, h in enumerate(htmls or []):
                logger.info("[진단] 후보#{} id={} sc={} cardsA={} items={}", i+1, h.get('id'), h.get('sc'), h.get('cardsA'), h.get('items'))
            # 추가 진단 산출물 저장
            try:
                debug_dir = Path("debug")
                debug_dir.mkdir(exist_ok=True)
                page.screenshot(path=str(debug_dir / "container_debug.png"), full_page=True)
                (debug_dir / "container_debug.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
        except Exception as e:
            logger.warning("[진단] 덤프 실패: {}", e)

    def _extract_address(self, page: Page, card_element=None) -> str:
        """매물의 실제 주소를 추출합니다."""
        try:
            # 1. 먼저 카드 내에서 주소 정보 찾기 (타임아웃 단축)
            if card_element:
                for sel in getattr(S, 'CARD_ADDRESS', []):
                    try:
                        address_elements = card_element.locator(sel)
                        if address_elements.count() > 0:
                            for i in range(min(address_elements.count(), 3)):  # 최대 3개만 시도
                                try:
                                    text = address_elements.nth(i).inner_text(timeout=3000).strip()  # 타임아웃 단축
                                    if self._is_valid_address(text):
                                        self._log(f"카드에서 주소 발견: {text}")
                                        return text
                                except Exception as e:
                                    self._log(f"주소 요소 {i} 추출 실패: {e}")
                                    continue
                    except Exception as e:
                        self._log(f"카드 주소 추출 실패 {sel}: {e}")
                        continue
            
            # 2. 상세 페이지에서 주소 정보 찾기 (매물 링크 클릭)
            if card_element:
                try:
                    # 매물 링크 찾기
                    room_link = card_element.locator("a[href^='/room/']").first
                    if room_link.count() > 0:
                        href = room_link.get_attribute("href")
                        if href:
                            # 상대 URL을 절대 URL로 변환
                            if href.startswith('/'):
                                room_url = f"https://www.dabangapp.com{href}"
                            else:
                                room_url = href
                            
                            self._log(f"매물 상세 페이지로 이동하여 주소 추출 시도: {room_url}")
                            
                            # 새로운 상세 페이지 주소 추출 메서드 사용
                            address = self._extract_address_from_detail_page(page, room_url)
                            if address:
                                return address
                        
                except Exception as e:
                    self._log(f"상세 페이지 주소 추출 실패: {e}")
            
            # 3. 현재 페이지에서 주소 정보 찾기
            for sel in getattr(S, 'CARD_ADDRESS', []):
                try:
                    address_elements = page.locator(sel)
                    if address_elements.count() > 0:
                        for i in range(address_elements.count()):
                            text = address_elements.nth(i).inner_text(timeout=1000).strip()
                            if self._is_valid_address(text):
                                self._log(f"현재 페이지에서 주소 발견: {text}")
                                return text
                except Exception as e:
                    self._log(f"현재 페이지 주소 추출 실패 {sel}: {e}")
                    continue
            
            # 4. 폴백: 카드의 전체 텍스트에서 주소 패턴 찾기
            if card_element:
                try:
                    card_text = card_element.inner_text(timeout=1000)
                    address = self._extract_address_from_text(card_text)
                    if address:
                        self._log(f"카드 텍스트에서 주소 추출: {address}")
                        return address
                except Exception as e:
                    self._log(f"카드 텍스트 주소 추출 실패: {e}")
            
            return ""
            
        except Exception as e:
            self._log(f"주소 추출 실패: {e}")
            return ""

    def _is_valid_address(self, text: str) -> bool:
        """텍스트가 유효한 주소인지 확인합니다."""
        if not text or len(text) < 5:
            return False
        
        # 한국 주소 패턴 확인
        import re
        
        # 시/도 + 시/군/구 + 읍/면/동 패턴
        patterns = [
            r'^[가-힣]+시\s+[가-힣]+군\s+[가-힣]+읍',  # 부산광역시 기장군 기장읍
            r'^[가-힣]+시\s+[가-힣]+구\s+[가-힣]+동',  # 서울특별시 종로구 청운동
            r'^[가-힣]+도\s+[가-힣]+시\s+[가-힣]+구',  # 경기도 성남시 분당구
            r'^[가-힣]+시\s+[가-힣]+군\s+[가-힣]+읍\s+[가-힣]+리',  # 부산광역시 기장군 기장읍 대라리
            r'^[가-힣]+시\s+[가-힣]+구\s+[가-힣]+동\s+[0-9-]+',  # 서울특별시 종로구 청운동 123-45
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False

    def _extract_text(self, element, selectors: List[str]) -> str:
        # uses selectors.py - deprecated, use text_first_from_element_sync instead
        """요소에서 텍스트를 추출합니다. (deprecated - use text_first_from_element_sync)"""
        return text_first_from_element_sync(element, selectors)

    def _extract_address_from_text(self, text: str) -> str:
        """텍스트에서 주소 패턴을 추출합니다."""
        import re
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if self._is_valid_address(line):
                return line
        
        return ""

    def _extract_address_from_detail_page(self, page: Page, room_url: str) -> str:
        """상세 페이지에서 실제 주소를 추출합니다."""
        try:
            # 새 탭에서 상세 페이지 열기
            with page.context.expect_page() as new_page_info:
                page.goto(room_url)
            
            detail_page = new_page_info.value
            detail_page.wait_for_load_state("domcontentloaded")
            detail_page.wait_for_timeout(3000)
            
            # 페이지 로딩 확인
            try:
                detail_page.wait_for_selector("body", timeout=10000)
            except Exception:
                self._log("상세 페이지 로딩 실패")
                detail_page.close()
                return ""
            
            self._log(f"상세 페이지 접속: {detail_page.url}")
            
            # 1. 위치 및 주변시설 섹션에서 주소 추출
            address = self._extract_address_from_location_section(detail_page)
            if address:
                self._log(f"위치 섹션에서 주소 발견: {address}")
                detail_page.close()
                return address
            
            # 2. 상세정보 섹션에서 주소 추출
            address = self._extract_address_from_detail_section(detail_page)
            if address:
                self._log(f"상세정보 섹션에서 주소 발견: {address}")
                detail_page.close()
                return address
            
            # 3. 전체 페이지에서 주소 패턴 검색
            address = self._extract_address_from_entire_page(detail_page)
            if address:
                self._log(f"전체 페이지에서 주소 발견: {address}")
                detail_page.close()
                return address
            
            detail_page.close()
            return ""
            
        except Exception as e:
            self._log(f"상세 페이지 주소 추출 실패: {e}")
            return ""

    def _extract_address_from_location_section(self, page: Page) -> str:
        """위치 및 주변시설 섹션에서 주소를 추출합니다."""
        try:
            # 위치 섹션 찾기
            location_selectors = [
                "section[data-scroll-spy-element='near']",
                "section[class*='sc-ktesqn']",
                "div[class*='location']",
                "div:has-text('위치')",
                "div:has-text('주소')",
            ]
            
            for selector in location_selectors:
                try:
                    location_elements = page.locator(selector)
                    if location_elements.count() > 0:
                        for i in range(location_elements.count()):
                            element = location_elements.nth(i)
                            # 섹션 내의 모든 텍스트 확인
                            all_text = element.inner_text(timeout=2000).strip()
                            lines = all_text.split('\n')
                            
                            for line in lines:
                                line = line.strip()
                                if self._is_valid_detailed_address(line):
                                    return line
                except Exception:
                    continue
            
            return ""
            
        except Exception as e:
            self._log(f"위치 섹션 주소 추출 실패: {e}")
            return ""

    def _extract_address_from_detail_section(self, page: Page) -> str:
        """상세정보 섹션에서 주소를 추출합니다."""
        try:
            # 상세정보 섹션 찾기
            detail_selectors = [
                "section[data-scroll-spy-element='detail-info']",
                "section[class*='detail']",
                "div[class*='detail']",
                "div:has-text('상세정보')",
            ]
            
            for selector in detail_selectors:
                try:
                    detail_elements = page.locator(selector)
                    if detail_elements.count() > 0:
                        for i in range(detail_elements.count()):
                            element = detail_elements.nth(i)
                            all_text = element.inner_text(timeout=2000).strip()
                            lines = all_text.split('\n')
                            
                            for line in lines:
                                line = line.strip()
                                if self._is_valid_detailed_address(line):
                                    return line
                except Exception:
                    continue
            
            return ""
            
        except Exception as e:
            self._log(f"상세정보 섹션 주소 추출 실패: {e}")
            return ""

    def _extract_address_from_entire_page(self, page: Page) -> str:
        """전체 페이지에서 주소 패턴을 검색합니다."""
        try:
            # 페이지의 모든 텍스트 요소에서 주소 검색
            text_elements = page.locator("p, div, span, h1, h2, h3, h4, h5, h6")
            
            for i in range(min(text_elements.count(), 100)):  # 최대 100개 요소만 검색
                try:
                    element = text_elements.nth(i)
                    text = element.inner_text(timeout=1000).strip()
                    
                    if self._is_valid_detailed_address(text):
                        return text
                except Exception:
                    continue
            
            return ""
            
        except Exception as e:
            self._log(f"전체 페이지 주소 검색 실패: {e}")
            return ""

    def _is_valid_detailed_address(self, text: str) -> bool:
        """상세 주소가 유효한지 확인합니다."""
        if not text or len(text) < 10:
            return False
        
        # 한국 상세 주소 패턴 확인
        import re
        
        # 시/도 + 시/군/구 + 읍/면/동 + 리/번지 패턴
        patterns = [
            r'^[가-힣]+시\s+[가-힣]+군\s+[가-힣]+읍\s+[가-힣]+리\s*[0-9-]*',  # 부산광역시 기장군 기장읍 대라리 946
            r'^[가-힣]+시\s+[가-힣]+구\s+[가-힣]+동\s*[0-9-]*',  # 서울특별시 종로구 청운동 123-45
            r'^[가-힣]+도\s+[가-힣]+시\s+[가-힣]+구\s*[0-9-]*',  # 경기도 성남시 분당구 123-45
            r'^[가-힣]+시\s+[가-힣]+군\s+[가-힣]+면\s+[가-힣]+리\s*[0-9-]*',  # 시군면리 패턴
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False

    def _ensure_list_container_after_search(self, page: Page) -> None:
        """지역 검색 후 리스트 컨테이너가 제대로 로드되었는지 확인하고 필요시 재시도합니다."""
        self._log("지역 검색 후 컨테이너 재확인 중...")
        
        # 컨테이너 확인
        for i in range(30):  # 최대 30번 시도 (증가)
            try:
                # onetwo-list 컨테이너 확인
                onetwo_list = page.locator("#onetwo-list")
                if onetwo_list.count() > 0:
                    # 컨테이너 내부에 li 요소가 있는지 확인
                    li_elements = onetwo_list.locator("li")
                    if li_elements.count() > 0:
                        self._log(f"컨테이너 확인 완료: #onetwo-list에 {li_elements.count()}개의 li 요소 발견")
                        return
                    else:
                        self._log("onetwo-list는 있지만 li 요소가 없습니다. 대기 중...")
                else:
                    self._log("onetwo-list 컨테이너를 찾을 수 없습니다. 대기 중...")
                
                # 매물 버튼을 다시 클릭해보기
                if i == 15:  # 15번째 시도에서 매물 버튼 재클릭 (증가)
                    self._log("매물 버튼 재클릭 시도...")
                    try:
                        material_btn = page.locator("button:has-text('매물')").first
                        if material_btn.count() > 0:
                            material_btn.focus()
                            page.keyboard.press("Enter")
                            page.wait_for_timeout(2000)
                    except Exception as e:
                        self._log(f"매물 버튼 재클릭 실패: {e}")
                
                page.wait_for_timeout(3000)  # 대기 시간 증가 (2초 → 3초)
                
            except Exception as e:
                self._log(f"컨테이너 확인 중 오류: {e}")
                page.wait_for_timeout(3000)  # 대기 시간 증가 (2초 → 3초)
        
        self._log("지역 검색 후 컨테이너 확인 실패")

    def _resolve_list_container_improved(self, page: Page):
        """개선된 컨테이너 해결 로직 - onetwo 전용 UL 우선"""
        self._log("개선된 컨테이너 해결 로직 시작...")
        onetwo_list = page.locator("#onetwo-list")
        if onetwo_list.count() > 0:
            for ul_sel in ONETWO_LIST_UL:
                if onetwo_list.locator(ul_sel).count() > 0:
                    self._log("onetwo-list 컨테이너 확정")
                    return onetwo_list
            # UL이 아직 렌더 중인 경우라도 컨테이너 자체는 유효하므로 반환
            self._log("onetwo-list 존재(UL 미검출) → 컨테이너로 사용")
            return onetwo_list
        return self._resolve_list_container(page)

    def _remove_duplicates(self, items: List[Item]) -> List[Item]:
        """중복 제거 비활성화 - 모든 아이템을 그대로 반환"""
        if not items:
            return items

        self._log(f"중복 제거 비활성화: 총 {len(items)}건 모두 유지")

        # 중복 제거하지 않고 모든 아이템을 그대로 반환
        return items


