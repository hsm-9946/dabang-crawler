#!/usr/bin/env python3
"""
향상된 다방 CSS 선택자 찾기 도구
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 대상 URL
TARGET_URL = "https://www.dabangapp.com/map/onetwo?m_lat=35.2862584&m_lng=129.3581947&m_zoom=10"

class EnhancedCSSFinder:
    def __init__(self):
        self.results = {}
        self.page = None
    
    async def find_css_selectors(self, page: Page) -> Dict:
        """향상된 CSS 선택자 찾기"""
        self.page = page
        
        logger.info("=== 향상된 CSS 선택자 찾기 시작 ===")
        
        # 1. 페이지 로딩 대기
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # 2. 지도 영역 클릭하여 매물 로드
        await self._click_map_to_load_items()
        
        # 3. 스크롤하여 더 많은 매물 로드
        await self._enhanced_scroll_to_load_items()
        
        # 4. 매물이 로드될 때까지 대기
        await self._wait_for_items_to_load()
        
        # 5. 각 필드별 선택자 찾기
        await self._find_enhanced_selectors()
        
        return self.results
    
    async def _click_map_to_load_items(self):
        """지도 영역 클릭하여 매물 로드"""
        logger.info("지도 영역 클릭하여 매물 로드...")
        
        try:
            # 지도 영역 찾기 및 클릭
            map_area = await self.page.evaluate("""
                () => {
                    // 지도 캔버스나 지도 컨테이너 찾기
                    const mapSelectors = [
                        'canvas',
                        '[class*="map"]',
                        '[class*="Map"]',
                        '[data-testid*="map"]',
                        'div[style*="position: absolute"]'
                    ];
                    
                    for (const selector of mapSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            return {
                                selector: selector,
                                rect: element.getBoundingClientRect()
                            };
                        }
                    }
                    return null;
                }
            """)
            
            if map_area:
                # 지도 중앙 클릭
                await self.page.mouse.click(
                    map_area['rect']['x'] + map_area['rect']['width'] / 2,
                    map_area['rect']['y'] + map_area['rect']['height'] / 2
                )
                logger.info("지도 영역 클릭 완료")
                await self.page.wait_for_timeout(2000)
            else:
                logger.info("지도 영역을 찾을 수 없음")
                
        except Exception as e:
            logger.info(f"지도 클릭 실패: {e}")
    
    async def _enhanced_scroll_to_load_items(self):
        """향상된 스크롤로 매물 로드"""
        logger.info("향상된 스크롤로 매물 로드...")
        
        # 스크롤 컨테이너 찾기 및 스크롤
        scroll_result = await self.page.evaluate("""
            () => {
                const containers = [];
                const allElements = document.querySelectorAll('*');
                
                allElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (/(auto|scroll)/.test(style.overflowY) || el.scrollHeight > el.clientHeight) {
                        containers.push({
                            id: el.id,
                            className: el.className,
                            tagName: el.tagName,
                            roomLinks: el.querySelectorAll('a[href*="/room/"]').length,
                            scrollHeight: el.scrollHeight,
                            clientHeight: el.clientHeight
                        });
                    }
                });
                
                // 가장 많은 방 링크를 가진 컨테이너 찾기
                const bestContainer = containers.sort((a, b) => b.roomLinks - a.roomLinks)[0];
                
                if (bestContainer) {
                    const container = document.getElementById(bestContainer.id) || 
                                    document.querySelector(bestContainer.tagName + (bestContainer.className ? '.' + bestContainer.className.split(' ').join('.') : ''));
                    
                    if (container) {
                        // 여러 번 스크롤하여 더 많은 아이템 로드
                        for (let i = 0; i < 15; i++) {
                            container.scrollTo(0, container.scrollHeight);
                            // 잠시 대기
                            const start = Date.now();
                            while (Date.now() - start < 300) {}
                        }
                        
                        return {
                            success: true,
                            container: bestContainer,
                            finalRoomLinks: container.querySelectorAll('a[href*="/room/"]').length
                        };
                    }
                }
                
                return { success: false };
            }
        """)
        
        if scroll_result.get('success'):
            logger.info(f"스크롤 완료: {scroll_result['container']['tagName']} (id: {scroll_result['container']['id']})")
            logger.info(f"최종 방 링크 수: {scroll_result['finalRoomLinks']}개")
        else:
            logger.info("스크롤 컨테이너를 찾을 수 없음")
        
        await self.page.wait_for_timeout(3000)
    
    async def _wait_for_items_to_load(self):
        """매물이 로드될 때까지 대기"""
        logger.info("매물 로드 대기...")
        
        for attempt in range(10):
            room_count = await self.page.evaluate("""
                () => document.querySelectorAll('a[href*="/room/"]').length
            """)
            
            logger.info(f"시도 {attempt + 1}: 방 링크 {room_count}개")
            
            if room_count > 0:
                logger.info(f"매물 로드 완료: {room_count}개")
                break
            
            await self.page.wait_for_timeout(1000)
        else:
            logger.info("매물 로드 실패")
    
    async def _find_enhanced_selectors(self):
        """향상된 선택자 찾기"""
        logger.info("향상된 선택자 찾기...")
        
        # 전체 페이지에서 매물 관련 요소 찾기
        selectors = await self.page.evaluate("""
            () => {
                const results = {};
                
                // 1. 컨테이너 선택자
                const containers = ['onetwo-list', 'map-list-tab-container', 'dock-content'];
                for (const id of containers) {
                    const el = document.getElementById(id);
                    if (el && el.querySelectorAll('a[href*="/room/"]').length > 0) {
                        results.list_scroll_container = '#' + id;
                        break;
                    }
                }
                
                // 2. 카드 선택자
                const roomLinks = document.querySelectorAll('a[href*="/room/"]');
                if (roomLinks.length > 0) {
                    const firstLink = roomLinks[0];
                    let cardRoot = firstLink;
                    
                    // 카드 루트 찾기
                    for (let i = 0; i < 5; i++) {
                        if (cardRoot.parentElement) {
                            const siblings = cardRoot.parentElement.children;
                            let hasMultipleCards = false;
                            
                            for (let j = 0; j < siblings.length; j++) {
                                if (siblings[j].querySelector('a[href*="/room/"]')) {
                                    hasMultipleCards = true;
                                    break;
                                }
                            }
                            
                            if (hasMultipleCards) {
                                cardRoot = cardRoot.parentElement;
                                break;
                            }
                            
                            cardRoot = cardRoot.parentElement;
                        }
                    }
                    
                    // 카드 선택자 생성
                    let selector = cardRoot.tagName.toLowerCase();
                    if (cardRoot.id) {
                        selector = '#' + cardRoot.id;
                    } else if (cardRoot.className) {
                        const classes = cardRoot.className.split(' ').filter(c => c && !c.startsWith('sc-'));
                        if (classes.length > 0) {
                            selector += '.' + classes.join('.');
                        }
                    }
                    results.card_root = selector;
                }
                
                // 3. 필드별 선택자 찾기
                const patterns = {
                    price: /(월세|전세|매매)\\s*\\d+/,
                    address: /(로|길|동|지번|구|군|읍)/,
                    maintenance: /관리비/,
                    realtor: /(공인중개|부동산|중개)/,
                    posted: /(\\d+\\s*(분|시간|일)\\s*전|어제|20\\d{2}-\\d{2}-\\d{2})/
                };
                
                const fieldNames = {
                    price: 'list_price',
                    address: 'list_address', 
                    maintenance: 'list_maint',
                    realtor: 'list_realtor',
                    posted: 'list_posted'
                };
                
                // 각 패턴에 대해 선택자 찾기
                Object.entries(patterns).forEach(([key, pattern]) => {
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        if (pattern.test(node.textContent)) {
                            const parent = node.parentElement;
                            if (parent) {
                                let selector = parent.tagName.toLowerCase();
                                if (parent.id) {
                                    selector = '#' + parent.id;
                                } else if (parent.className) {
                                    const classes = parent.className.split(' ').filter(c => c && !c.startsWith('sc-'));
                                    if (classes.length > 0) {
                                        selector += '.' + classes.join('.');
                                    }
                                }
                                
                                results[fieldNames[key]] = selector;
                                break;
                            }
                        }
                    }
                });
                
                return results;
            }
        """)
        
        self.results.update(selectors)
        
        # 결과 출력
        for key, value in selectors.items():
            if value:
                logger.info(f"선택자 발견: {key} = {value}")

async def main():
    """메인 실행 함수"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        finder = EnhancedCSSFinder()
        
        try:
            # 다방 페이지로 이동
            logger.info(f"다방 페이지로 이동: {TARGET_URL}")
            await page.goto(TARGET_URL, wait_until="domcontentloaded")
            
            # CSS 선택자 찾기
            results = await finder.find_css_selectors(page)
            
            # 결과 저장
            output_path = Path("scraper/selectors_enhanced.json")
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"향상된 선택자가 {output_path}에 저장되었습니다.")
            
            # 결과 출력
            logger.info("=== 향상된 CSS 선택자 결과 ===")
            for key, value in results.items():
                logger.info(f"[SEL] {key}: {value}")
            
            # 스크린샷 저장
            await page.screenshot(path="enhanced_css_finder.png", full_page=True)
            logger.info("스크린샷이 enhanced_css_finder.png에 저장되었습니다.")
            
            # 사용자 입력 대기
            input("분석 완료. 브라우저를 닫으려면 Enter를 누르세요...")
            
        except Exception as e:
            logger.error(f"향상된 CSS 찾기 중 오류: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

