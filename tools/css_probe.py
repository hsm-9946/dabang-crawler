#!/usr/bin/env python3
"""
다방 페이지 CSS 선택자 자동 추출 도구
"""

import json
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 대상 URL
LIST_URL = "https://www.dabangapp.com/map/onetwo?m_lat=35.2485565&m_lng=129.23992&m_zoom=13&search_type=region&search_id=5639"
DETAIL_URL = "https://www.dabangapp.com/map/onetwo?m_lat=35.2485565&m_lng=129.23992&m_zoom=13&search_type=region&search_id=5639&detail_type=room&detail_id=68998bc315abcc1f59113fc5"

# 텍스트 패턴 정의
PATTERNS = {
    "price": re.compile(r"(월세|전세|매매)\s?\d"),
    "maint": re.compile(r"관리비"),
    "realtor": re.compile(r"(공인중개|부동산|중개)"),
    "posted": re.compile(r"(\d+\s*(분|시간|일)\s*전|어제|20\d{2}-\d{2}-\d{2})"),
    "address": re.compile(r"(로|길|동|지번|구|군|읍)"),
}

class CSSProbe:
    def __init__(self):
        self.results = {}
    
    async def probe_list(self, page: Page) -> Dict:
        """리스트 페이지에서 선택자 추출"""
        logger.info("리스트 페이지 프로브 시작")
        
        # 페이지 로딩 대기
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # 스크롤 부모 탐지
        scroll_container = await self._find_scroll_container(page)
        if scroll_container:
            self.results["list_scroll_container"] = scroll_container
            logger.info(f"[SEL] list_scroll_container: {scroll_container}")
        
        # 카드 루트 탐지
        card_root = await self._find_card_root(page)
        if card_root:
            self.results["card_root"] = card_root
            logger.info(f"[SEL] card_root: {card_root}")
        
        # 카드 링크 탐지
        card_link = await self._find_card_link(page)
        if card_link:
            self.results["card_link"] = card_link
            logger.info(f"[SEL] card_link: {card_link}")
        
        # 스크롤하여 카드 샘플링
        await self._scroll_and_sample_cards(page)
        
        # 카드 내부 필드 탐지
        fields = ["list_address", "list_price", "list_maint", "list_realtor", "list_posted"]
        for field in fields:
            selector = await self._find_field_selector(page, field)
            if selector:
                self.results[field] = selector
                logger.info(f"[SEL] {field}: {selector}")
        
        return self.results
    
    async def probe_detail(self, page: Page) -> Dict:
        """상세 페이지에서 선택자 추출"""
        logger.info("상세 페이지 프로브 시작")
        
        # 페이지 로딩 대기
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # 상세 페이지 필드 탐지
        fields = ["detail_address", "detail_maint", "detail_realtor", "detail_posted"]
        for field in fields:
            selector = await self._find_field_selector(page, field)
            if selector:
                self.results[field] = selector
                logger.info(f"[SEL] {field}: {selector}")
        
        return self.results
    
    async def _find_scroll_container(self, page: Page) -> Optional[str]:
        """스크롤 가능한 컨테이너 찾기"""
        container = await page.evaluate("""
            () => {
                const canScroll = el => {
                    const s = getComputedStyle(el);
                    return /(auto|scroll)/.test(s.overflowY) || el.scrollHeight > el.clientHeight;
                };
                
                const candidates = Array.from(document.querySelectorAll('div'));
                const scored = candidates.map(el => {
                    const id = el.id || "";
                    const score = 
                        (id.startsWith('map-list-') ? 3 : 0) +
                        (id.startsWith('dock-content-') ? 2 : 0) +
                        (canScroll(el) ? 2 : 0) +
                        Math.min(el.querySelectorAll('[role="listitem"]').length, 10) +
                        Math.min(el.querySelectorAll('a[href^="/room/"]').length, 10);
                    return {el, score, id};
                }).filter(x => x.score >= 3).sort((a, b) => b.score - a.score);
                
                return candidates.length > 0 ? {
                    id: candidates[0].id,
                    selector: candidates[0].id ? `#${candidates[0].id}` : null,
                    score: candidates[0].score
                } : null;
            }
        """)
        
        if container and container.get("selector"):
            return container["selector"]
        
        # 폴백: 일반적인 스크롤 컨테이너
        fallback = await page.evaluate("""
            () => {
                const canScroll = el => {
                    const s = getComputedStyle(el);
                    return /(auto|scroll)/.test(s.overflowY) || el.scrollHeight > el.clientHeight;
                };
                
                const candidates = Array.from(document.querySelectorAll('div')).filter(canScroll);
                if (candidates.length > 0) {
                    const el = candidates[0];
                    return el.id ? `#${el.id}` : null;
                }
                return null;
            }
        """)
        
        return fallback
    
    async def _find_card_root(self, page: Page) -> Optional[str]:
        """카드 루트 요소 찾기"""
        card_root = await page.evaluate("""
            () => {
                const selectors = [
                    '[role="listitem"]',
                    'a[href^="/room/"][class*="Card"]',
                    'article[class*="Card"]',
                    'a[href^="/room/"]',
                    'li[class*="Card"]',
                    'div[class*="Card"]'
                ];
                
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        return selector;
                    }
                }
                return null;
            }
        """)
        
        return card_root
    
    async def _find_card_link(self, page: Page) -> Optional[str]:
        """카드 링크 요소 찾기"""
        card_link = await page.evaluate("""
            () => {
                const selectors = [
                    'a[href^="/room/"]',
                    'a[href*="/room/"]'
                ];
                
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        return selector;
                    }
                }
                return null;
            }
        """)
        
        return card_link
    
    async def _scroll_and_sample_cards(self, page: Page):
        """스크롤하여 카드 샘플링"""
        await page.evaluate("""
            () => {
                const scrollContainer = document.querySelector('#map-list-tab-container') || 
                                      document.querySelector('[id^="map-list-"]') ||
                                      document.querySelector('[id^="dock-content-"]');
                
                if (scrollContainer) {
                    // 스크롤하여 더 많은 카드 로드
                    for (let i = 0; i < 5; i++) {
                        scrollContainer.scrollTo(0, scrollContainer.scrollHeight);
                        // 잠시 대기
                        const start = Date.now();
                        while (Date.now() - start < 1000) {}
                    }
                }
            }
        """)
        await page.wait_for_timeout(2000)
    
    async def _find_field_selector(self, page: Page, field_name: str) -> Optional[str]:
        """특정 필드의 선택자 찾기"""
        field_type = field_name.replace("list_", "").replace("detail_", "")
        pattern = PATTERNS.get(field_type)
        
        if not pattern:
            return None
        
        # 더 구체적인 선택자 찾기
        candidates = await page.evaluate(f"""
            () => {{
                const pattern = /{pattern.pattern}/;
                const candidates = [];
                
                // 1. data-testid 기반 검색
                const testIdElements = document.querySelectorAll('[data-testid*="{field_type}"]');
                testIdElements.forEach(el => {{
                    const text = el.textContent || '';
                    if (pattern.test(text)) {{
                        candidates.push({{
                            selector: `[data-testid*="{field_type}"]`,
                            text: text.trim().substring(0, 100),
                            depth: 1,
                            score: 10
                        }});
                    }}
                }});
                
                // 2. 클래스명 기반 검색
                const classElements = document.querySelectorAll('[class*="{field_type}"]');
                classElements.forEach(el => {{
                    const text = el.textContent || '';
                    if (pattern.test(text)) {{
                        const className = el.className.split(' ').find(c => c.includes('{field_type}'));
                        candidates.push({{
                            selector: `[class*="{field_type}"]`,
                            text: text.trim().substring(0, 100),
                            depth: 1,
                            score: 8
                        }});
                    }}
                }});
                
                // 3. 특정 태그 기반 검색
                const tagSelectors = ['span', 'p', 'div', 'strong', 'em'];
                tagSelectors.forEach(tag => {{
                    const elements = document.querySelectorAll(tag);
                    elements.forEach(el => {{
                        const text = el.textContent || '';
                        if (pattern.test(text)) {{
                            let selector = tag;
                            if (el.className) {{
                                const classes = el.className.split(' ').filter(c => c && !c.startsWith('sc-'));
                                if (classes.length > 0) {{
                                    selector += '.' + classes.join('.');
                                }}
                            }}
                            candidates.push({{
                                selector: selector,
                                text: text.trim().substring(0, 100),
                                depth: 1,
                                score: 6
                            }});
                        }}
                    }});
                }});
                
                // 4. 텍스트 기반 검색 (더 구체적인 패턴)
                const textPatterns = [
                    `*:contains("{field_type}")`,
                    `span:contains("{field_type}")`,
                    `p:contains("{field_type}")`,
                    `div:contains("{field_type}")`
                ];
                
                textPatterns.forEach(textPattern => {{
                    try {{
                        const elements = document.querySelectorAll('*');
                        elements.forEach(el => {{
                            const text = el.textContent || '';
                            if (text.includes('{field_type}') && pattern.test(text)) {{
                                let selector = el.tagName.toLowerCase();
                                if (el.id) {{
                                    selector = '#' + el.id;
                                }} else if (el.className) {{
                                    const classes = el.className.split(' ').filter(c => c && !c.startsWith('sc-'));
                                    if (classes.length > 0) {{
                                        selector += '.' + classes.join('.');
                                    }}
                                }}
                                
                                candidates.push({{
                                    selector: selector,
                                    text: text.trim().substring(0, 100),
                                    depth: 2,
                                    score: 5
                                }});
                            }}
                        }});
                    }} catch (e) {{
                        // 오류 무시
                    }}
                }});
                
                // 5. 일반적인 텍스트 검색 (마지막 폴백)
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {{
                    const text = el.textContent || '';
                    if (pattern.test(text) && text.trim().length < 200) {{
                        let selector = el.tagName.toLowerCase();
                        if (el.id) {{
                            selector = '#' + el.id;
                        }} else if (el.className) {{
                            const classes = el.className.split(' ').filter(c => c && !c.startsWith('sc-'));
                            if (classes.length > 0) {{
                                selector += '.' + classes.join('.');
                            }}
                        }}
                        
                        candidates.push({{
                            selector: selector,
                            text: text.trim().substring(0, 100),
                            depth: 3,
                            score: 3
                        }});
                    }}
                }});
                
                // 중복 제거 및 정렬
                const unique = [];
                const seen = new Set();
                candidates.forEach(c => {{
                    const key = c.selector + '|' + c.text.substring(0, 50);
                    if (!seen.has(key)) {{
                        seen.add(key);
                        unique.push(c);
                    }}
                }});
                
                return unique
                    .sort((a, b) => b.score - a.score || a.depth - b.depth)
                    .slice(0, 3);
            }}
        """)
        
        if candidates:
            # 가장 높은 점수의 선택자 반환
            best_candidate = candidates[0]
            logger.info(f"  샘플 텍스트: {best_candidate['text']}")
            return best_candidate["selector"]
        
        return None

async def main():
    """메인 실행 함수"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        probe = CSSProbe()
        
        try:
            # 1. 리스트 페이지 프로브
            logger.info("=== 리스트 페이지 프로브 ===")
            await page.goto(LIST_URL, wait_until="domcontentloaded")
            await probe.probe_list(page)
            
            # 2. 상세 페이지 프로브
            logger.info("=== 상세 페이지 프로브 ===")
            await page.goto(DETAIL_URL, wait_until="domcontentloaded")
            await probe.probe_detail(page)
            
            # 3. 결과 저장
            output_path = Path("scraper/selectors.json")
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(probe.results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"선택자 결과가 {output_path}에 저장되었습니다.")
            
            # 4. 결과 출력
            logger.info("=== 최종 선택자 결과 ===")
            for key, value in probe.results.items():
                logger.info(f"[SEL] {key}: {value}")
                
        except Exception as e:
            logger.error(f"프로브 실행 중 오류: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
