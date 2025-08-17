from typing import Iterable, Optional, Union
from playwright.async_api import Page as AsyncPage, Locator as AsyncLocator
from playwright.sync_api import Page as SyncPage, Locator as SyncLocator

# Async versions
async def first_locator(page: AsyncPage, selectors: Iterable[str]) -> AsyncLocator:
    """
    selectors 순서대로 시도하여 count()>0 인 Locator를 반환.
    전부 실패하면 마지막 시도의 Locator를 반환(추가 디버깅 용이).
    """
    last: Optional[AsyncLocator] = None
    for s in selectors:
        loc = page.locator(s)
        last = loc
        try:
            if await loc.count() > 0:
                return loc
        except Exception:
            # 유효하지 않은 selector는 무시하고 다음으로
            continue
    return last if last is not None else page.locator("html")

async def click_first(page: AsyncPage, selectors: Iterable[str]) -> None:
    """첫 번째로 매칭되는 요소를 클릭합니다."""
    loc = await first_locator(page, selectors)
    await loc.first.click()

async def fill_first(page: AsyncPage, selectors: Iterable[str], text: str) -> None:
    """첫 번째로 매칭되는 요소에 텍스트를 입력합니다."""
    loc = await first_locator(page, selectors)
    await loc.first.fill(text)

async def text_first(page: AsyncPage, selectors: Iterable[str]) -> str:
    """첫 번째로 매칭되는 요소의 텍스트를 반환합니다."""
    loc = await first_locator(page, selectors)
    return (await loc.first.text_content() or "").strip()

async def first_locator_from_element(element: AsyncLocator, selectors: Iterable[str]) -> AsyncLocator:
    """
    요소 내에서 selectors 순서대로 시도하여 count()>0 인 Locator를 반환.
    """
    last: Optional[AsyncLocator] = None
    for s in selectors:
        loc = element.locator(s)
        last = loc
        try:
            if await loc.count() > 0:
                return loc
        except Exception:
            continue
    return last if last is not None else element.locator("div")

async def text_first_from_element(element: AsyncLocator, selectors: Iterable[str]) -> str:
    """요소 내에서 첫 번째로 매칭되는 요소의 텍스트를 반환합니다."""
    loc = await first_locator_from_element(element, selectors)
    return (await loc.first.text_content() or "").strip()

# Sync versions
def first_locator_sync(page: SyncPage, selectors: Iterable[str]) -> SyncLocator:
    """
    selectors 순서대로 시도하여 count()>0 인 Locator를 반환.
    전부 실패하면 마지막 시도의 Locator를 반환(추가 디버깅 용이).
    """
    last: Optional[SyncLocator] = None
    for s in selectors:
        loc = page.locator(s)
        last = loc
        try:
            if loc.count() > 0:
                return loc
        except Exception:
            # 유효하지 않은 selector는 무시하고 다음으로
            continue
    return last if last is not None else page.locator("html")

def click_first_sync(page: SyncPage, selectors: Iterable[str]) -> None:
    """첫 번째로 매칭되는 요소를 클릭합니다."""
    loc = first_locator_sync(page, selectors)
    loc.first.click()

def fill_first_sync(page: SyncPage, selectors: Iterable[str], text: str) -> None:
    """첫 번째로 매칭되는 요소에 텍스트를 입력합니다."""
    loc = first_locator_sync(page, selectors)
    loc.first.fill(text)

def text_first_sync(page: SyncPage, selectors: Iterable[str]) -> str:
    """첫 번째로 매칭되는 요소의 텍스트를 반환합니다."""
    loc = first_locator_sync(page, selectors)
    return (loc.first.text_content() or "").strip()

def first_locator_from_element_sync(element: SyncLocator, selectors: Iterable[str]) -> SyncLocator:
    """
    요소 내에서 selectors 순서대로 시도하여 count()>0 인 Locator를 반환.
    """
    last: Optional[SyncLocator] = None
    for s in selectors:
        loc = element.locator(s)
        last = loc
        try:
            if loc.count() > 0:
                return loc
        except Exception:
            continue
    return last if last is not None else element.locator("div")

def text_first_from_element_sync(element: SyncLocator, selectors: Iterable[str]) -> str:
    """요소 내에서 첫 번째로 매칭되는 요소의 텍스트를 반환합니다."""
    loc = first_locator_from_element_sync(element, selectors)
    return (loc.first.text_content() or "").strip()
