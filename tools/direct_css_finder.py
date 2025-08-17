#!/usr/bin/env python3
"""
다방 웹사이트 직접 CSS 선택자 찾기 도구
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

class DirectCSSFinder:
    def __init__(self):
        self.results = {}
        self.page = None
    
    async def find_css_selectors(self, page: Page) -> Dict:
        """페이지에서 직접 CSS 선택자 찾기"""
        self.page = page
        
        logger.info("=== 직접 CSS 선택자 찾기 시작 ===")
        
        # 1. 페이지 로딩 대기
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(5000)
        
        # 2. 스크롤하여 매물 로드
        await self._scroll_to_load_items()
        
        # 3. 각 필드별 선택자 찾기
        await self._find_container_selectors()
        await self._find_card_selectors()
        await self._find_field_selectors()
        
        return self.results
    
    async def _scroll_to_load_items(self):
        """스크롤하여 매물 아이템 로드"""
        logger.info("매물 로딩을 위한 스크롤 시작...")
        
        # 스크롤 컨테이너 찾기
        scroll_containers = await self.page.evaluate("""
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
                            roomLinks: el.querySelectorAll('a[href*="/room/"]').length
                        });
                    }
                });
                
                return containers.sort((a, b) => b.roomLinks - a.roomLinks);
            }
        """)
        
        logger.info(f"스크롤 가능한 컨테이너 {len(scroll_containers)}개 발견")
        for i, container in enumerate(scroll_containers[:5]):
            logger.info(f"  {i+1}. {container['tagName']} (id: {container['id']}, 방링크: {container['roomLinks']}개)")
        
        # 가장 많은 방 링크를 가진 컨테이너에서 스크롤
        if scroll_containers:
            best_container = scroll_containers[0]
            if best_container['roomLinks'] > 0:
                logger.info(f"최적 컨테이너에서 스크롤: {best_container['tagName']} (id: {best_container['id']})")
                
                # 스크롤 실행
                await self.page.evaluate("""
                    (containerInfo) => {
                        const container = document.getElementById(containerInfo.id) || 
                                        document.querySelector(containerInfo.tagName + (containerInfo.className ? '.' + containerInfo.className.split(' ').join('.') : ''));
                        
                        if (container) {
                            // 여러 번 스크롤하여 더 많은 아이템 로드
                            for (let i = 0; i < 10; i++) {
                                container.scrollTo(0, container.scrollHeight);
                                // 잠시 대기
                                const start = Date.now();
                                while (Date.now() - start < 500) {}
                            }
                        }
                    }
                """, best_container)
                
                await self.page.wait_for_timeout(3000)
    
    async def _find_container_selectors(self):
        """컨테이너 선택자 찾기"""
        logger.info("컨테이너 선택자 찾기...")
        
        containers = await self.page.evaluate("""
            () => {
                const candidates = [];
                
                // 1. ID 기반 컨테이너
                const idContainers = ['onetwo-list', 'map-list-tab-container', 'dock-content'];
                idContainers.forEach(id => {
                    const el = document.getElementById(id);
                    if (el) {
                        candidates.push({
                            type: 'id',
                            selector: '#' + id,
                            roomLinks: el.querySelectorAll('a[href*="/room/"]').length,
                            scrollable: /(auto|scroll)/.test(getComputedStyle(el).overflowY)
                        });
                    }
                });
                
                // 2. 클래스 기반 컨테이너
                const classPatterns = ['list', 'container', 'scroll', 'dock'];
                classPatterns.forEach(pattern => {
                    const elements = document.querySelectorAll('[class*="' + pattern + '"]');
                    elements.forEach(el => {
                        const roomLinks = el.querySelectorAll('a[href*="/room/"]').length;
                        if (roomLinks > 0) {
                            candidates.push({
                                type: 'class',
                                selector: '[class*="' + pattern + '"]',
                                roomLinks: roomLinks,
                                scrollable: /(auto|scroll)/.test(getComputedStyle(el).overflowY)
                            });
                        }
                    });
                });
                
                return candidates.sort((a, b) => b.roomLinks - a.roomLinks);
            }
        """)
        
        if containers:
            best_container = containers[0]
            self.results['list_scroll_container'] = best_container['selector']
            logger.info(f"최적 컨테이너: {best_container['selector']} (방링크: {best_container['roomLinks']}개)")
    
    async def _find_card_selectors(self):
        """카드 선택자 찾기"""
        logger.info("카드 선택자 찾기...")
        
        cards = await self.page.evaluate("""
            () => {
                const candidates = [];
                const roomLinks = document.querySelectorAll('a[href*="/room/"]');
                
                roomLinks.forEach(link => {
                    // 카드의 루트 요소 찾기
                    let cardRoot = link;
                    let depth = 0;
                    
                    // 최대 5단계까지 부모로 올라가며 카드 루트 찾기
                    while (cardRoot.parentElement && depth < 5) {
                        const siblings = cardRoot.parentElement.children;
                        let hasMultipleCards = false;
                        
                        // 같은 부모 아래에 다른 방 링크가 있는지 확인
                        for (let i = 0; i < siblings.length; i++) {
                            if (siblings[i].querySelector('a[href*="/room/"]')) {
                                hasMultipleCards = true;
                                break;
                            }
                        }
                        
                        if (hasMultipleCards) {
                            cardRoot = cardRoot.parentElement;
                            break;
                        }
                        
                        cardRoot = cardRoot.parentElement;
                        depth++;
                    }
                    
                    // 선택자 생성
                    let selector = cardRoot.tagName.toLowerCase();
                    if (cardRoot.id) {
                        selector = '#' + cardRoot.id;
                    } else if (cardRoot.className) {
                        const classes = cardRoot.className.split(' ').filter(c => c && !c.startsWith('sc-'));
                        if (classes.length > 0) {
                            selector += '.' + classes.join('.');
                        }
                    }
                    
                    candidates.push({
                        selector: selector,
                        tagName: cardRoot.tagName,
                        className: cardRoot.className,
                        id: cardRoot.id,
                        depth: depth
                    });
                });
                
                // 중복 제거 및 정렬
                const unique = [];
                const seen = new Set();
                candidates.forEach(c => {
                    if (!seen.has(c.selector)) {
                        seen.add(c.selector);
                        unique.push(c);
                    }
                });
                
                return unique.slice(0, 5);
            }
        """)
        
        if cards:
            best_card = cards[0]
            self.results['card_root'] = best_card['selector']
            logger.info(f"최적 카드 선택자: {best_card['selector']}")
    
    async def _find_field_selectors(self):
        """필드별 선택자 찾기"""
        logger.info("필드별 선택자 찾기...")
        
        # 가격 선택자 찾기
        await self._find_price_selectors()
        
        # 주소 선택자 찾기
        await self._find_address_selectors()
        
        # 관리비 선택자 찾기
        await self._find_maintenance_selectors()
        
        # 부동산 선택자 찾기
        await self._find_realtor_selectors()
        
        # 게시일 선택자 찾기
        await self._find_posted_selectors()
    
    async def _find_price_selectors(self):
        """가격 선택자 찾기"""
        price_selectors = await self.page.evaluate("""
            () => {
                const candidates = [];
                const pricePattern = /(월세|전세|매매)\\s*\\d+/;
                
                // 모든 텍스트 노드 검사
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (pricePattern.test(node.textContent)) {
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
                            
                            candidates.push({
                                selector: selector,
                                text: node.textContent.trim().substring(0, 50),
                                tagName: parent.tagName,
                                className: parent.className
                            });
                        }
                    }
                }
                
                return candidates.slice(0, 5);
            }
        """)
        
        if price_selectors:
            best_price = price_selectors[0]
            self.results['list_price'] = best_price['selector']
            logger.info(f"가격 선택자: {best_price['selector']} (샘플: {best_price['text']})")
    
    async def _find_address_selectors(self):
        """주소 선택자 찾기"""
        address_selectors = await self.page.evaluate("""
            () => {
                const candidates = [];
                const addressPattern = /(로|길|동|지번|구|군|읍)/;
                
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (addressPattern.test(node.textContent)) {
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
                            
                            candidates.push({
                                selector: selector,
                                text: node.textContent.trim().substring(0, 50),
                                tagName: parent.tagName,
                                className: parent.className
                            });
                        }
                    }
                }
                
                return candidates.slice(0, 5);
            }
        """)
        
        if address_selectors:
            best_address = address_selectors[0]
            self.results['list_address'] = best_address['selector']
            logger.info(f"주소 선택자: {best_address['selector']} (샘플: {best_address['text']})")
    
    async def _find_maintenance_selectors(self):
        """관리비 선택자 찾기"""
        maintenance_selectors = await self.page.evaluate("""
            () => {
                const candidates = [];
                const maintPattern = /관리비/;
                
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (maintPattern.test(node.textContent)) {
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
                            
                            candidates.push({
                                selector: selector,
                                text: node.textContent.trim().substring(0, 50),
                                tagName: parent.tagName,
                                className: parent.className
                            });
                        }
                    }
                }
                
                return candidates.slice(0, 5);
            }
        """)
        
        if maintenance_selectors:
            best_maint = maintenance_selectors[0]
            self.results['list_maint'] = best_maint['selector']
            logger.info(f"관리비 선택자: {best_maint['selector']} (샘플: {best_maint['text']})")
    
    async def _find_realtor_selectors(self):
        """부동산 선택자 찾기"""
        realtor_selectors = await self.page.evaluate("""
            () => {
                const candidates = [];
                const realtorPattern = /(공인중개|부동산|중개)/;
                
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (realtorPattern.test(node.textContent)) {
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
                            
                            candidates.push({
                                selector: selector,
                                text: node.textContent.trim().substring(0, 50),
                                tagName: parent.tagName,
                                className: parent.className
                            });
                        }
                    }
                }
                
                return candidates.slice(0, 5);
            }
        """)
        
        if realtor_selectors:
            best_realtor = realtor_selectors[0]
            self.results['list_realtor'] = best_realtor['selector']
            logger.info(f"부동산 선택자: {best_realtor['selector']} (샘플: {best_realtor['text']})")
    
    async def _find_posted_selectors(self):
        """게시일 선택자 찾기"""
        posted_selectors = await self.page.evaluate("""
            () => {
                const candidates = [];
                const postedPattern = /(\\d+\\s*(분|시간|일)\\s*전|어제|20\\d{2}-\\d{2}-\\d{2})/;
                
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (postedPattern.test(node.textContent)) {
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
                            
                            candidates.push({
                                selector: selector,
                                text: node.textContent.trim().substring(0, 50),
                                tagName: parent.tagName,
                                className: parent.className
                            });
                        }
                    }
                }
                
                return candidates.slice(0, 5);
            }
        """)
        
        if posted_selectors:
            best_posted = posted_selectors[0]
            self.results['list_posted'] = best_posted['selector']
            logger.info(f"게시일 선택자: {best_posted['selector']} (샘플: {best_posted['text']})")

async def main():
    """메인 실행 함수"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        finder = DirectCSSFinder()
        
        try:
            # 다방 페이지로 이동
            logger.info(f"다방 페이지로 이동: {TARGET_URL}")
            await page.goto(TARGET_URL, wait_until="domcontentloaded")
            
            # CSS 선택자 찾기
            results = await finder.find_css_selectors(page)
            
            # 결과 저장
            output_path = Path("scraper/selectors_direct.json")
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"직접 찾은 선택자가 {output_path}에 저장되었습니다.")
            
            # 결과 출력
            logger.info("=== 직접 찾은 CSS 선택자 결과 ===")
            for key, value in results.items():
                logger.info(f"[SEL] {key}: {value}")
            
            # 스크린샷 저장
            await page.screenshot(path="direct_css_finder.png", full_page=True)
            logger.info("스크린샷이 direct_css_finder.png에 저장되었습니다.")
            
            # 사용자 입력 대기
            input("분석 완료. 브라우저를 닫으려면 Enter를 누르세요...")
            
        except Exception as e:
            logger.error(f"직접 CSS 찾기 중 오류: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
