#!/usr/bin/env python3
"""
실제 검색 테스트 스크립트
"""

import asyncio
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 다방 지도 페이지로 이동
            await page.goto("https://www.dabangapp.com/map/onetwo", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            logger.info(f"현재 URL: {page.url}")
            
            # 검색창 찾기 및 검색
            search_input = page.locator("input[placeholder*='검색'], input[placeholder*='지역'], input[type='search']").first
            if await search_input.count() > 0:
                await search_input.click()
                await search_input.fill("부산 기장")
                await page.wait_for_timeout(1000)
                
                # 검색 결과 클릭
                search_result = page.get_by_text("부산 기장", exact=True).first
                if await search_result.count() > 0:
                    await search_result.click()
                    await page.wait_for_timeout(3000)
                    logger.info("검색 완료")
                else:
                    logger.info("검색 결과를 찾을 수 없음")
            else:
                logger.info("검색창을 찾을 수 없음")
            
            # 현재 페이지 구조 분석
            structure = await page.evaluate("""
                () => {
                    const result = {
                        url: window.location.href,
                        onetwoList: document.querySelector('#onetwo-list'),
                        roomLinks: document.querySelectorAll('a[href*="/room/"]').length,
                        listItems: document.querySelectorAll('li').length,
                        roleListItems: document.querySelectorAll('[role="listitem"]').length,
                        scrollableElements: []
                    };
                    
                    // 스크롤 가능한 요소들 찾기
                    const allElements = document.querySelectorAll('*');
                    allElements.forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (/(auto|scroll)/.test(style.overflowY) || el.scrollHeight > el.clientHeight) {
                            result.scrollableElements.push({
                                tag: el.tagName,
                                id: el.id,
                                className: el.className,
                                children: el.children.length,
                                roomLinks: el.querySelectorAll('a[href*="/room/"]').length
                            });
                        }
                    });
                    
                    return result;
                }
            """)
            
            logger.info("=== 검색 후 페이지 구조 ===")
            logger.info(f"URL: {structure['url']}")
            logger.info(f"#onetwo-list 존재: {structure['onetwoList'] is not None}")
            logger.info(f"방 링크: {structure['roomLinks']}개")
            logger.info(f"li 요소: {structure['listItems']}개")
            logger.info(f"role='listitem' 요소: {structure['roleListItems']}개")
            
            logger.info("=== 스크롤 가능한 요소들 ===")
            for i, elem in enumerate(structure['scrollableElements'][:10]):
                logger.info(f"{i+1}. {elem['tag']} (id: {elem['id']}, class: {elem['className']}, 자식: {elem['children']}개, 방링크: {elem['roomLinks']}개)")
            
            # 스크린샷 저장
            await page.screenshot(path="test_search.png", full_page=True)
            logger.info("스크린샷이 test_search.png에 저장되었습니다.")
            
            # 사용자 입력 대기
            input("테스트 완료. 브라우저를 닫으려면 Enter를 누르세요...")
            
        except Exception as e:
            logger.error(f"테스트 중 오류: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_search())
