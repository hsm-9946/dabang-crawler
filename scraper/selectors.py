from __future__ import annotations
import json
from pathlib import Path

"""다방용 선택자 세트.

각 키는 의미 단위이며 값은 우선순위가 높은 순서의 CSS/XPath/has-text 후보 문자열 목록이다.
Playwright에서는 locator("text=..."), locator("css"), locator("xpath=...") 형태로 사용한다.
"""

# JSON 파일에서 선택자 로드
def load_selectors():
    """selectors.json에서 선택자를 로드합니다."""
    try:
        json_path = Path(__file__).parent / "selectors.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

# JSON 선택자 로드
JSON_SELECTORS = load_selectors()

# 지역 확정
REGION_INPUT = [
    "input[placeholder*='검색']",
    "input[placeholder*='지역']",
    "input[type='search']",
    "input#search-input",  # 다방 검색 입력창 (이미지에서 확인)
    "input[class*='sc-ezVCTI']",  # 다방 검색 입력창 클래스 (이미지에서 확인)
    "input[class*='hgqZzn']",  # 다방 검색 입력창 클래스 (이미지에서 확인)
]

# 지역 검색 결과 컨테이너 (이미지에서 확인된 실제 구조)
REGION_SEARCH_CONTAINER = [
    "div#search-region-subway-univ-list",  # 지역, 지하철, 대학교 리스트 컨테이너 (이미지에서 확인)
    "div[class*='sc-fkYqBV']",  # sc-fkYqBV 클래스 컨테이너 (이미지에서 확인)
    "div[class*='kxi0MM']",  # kxi0MM 클래스 컨테이너 (이미지에서 확인)
    "div[class*='sc-Pgsbw']",  # sc-Pgsbw 클래스 컨테이너 (이미지에서 확인)
    "div[class*='eIBNw0']",  # eIBNw0 클래스 컨테이너 (이미지에서 확인)
]

# 제안 리스트에서 항목(지역명 포함 텍스트) - 실제 클릭
REGION_SUGGEST_ITEM = [
    # 핵심 후보 (사용자 요청)
    "a[role='link']",
    "a[href*='/map/']",          # 스샷처럼 왼쪽 제안 컬럼의 링크들
    "li a",
    "button[role='option']",
    "ul[role='listbox'] button",
    # 이미지에서 확인된 실제 지역 선택 버튼 클래스
    "button.sc-fEETNT.cGRZls",  # 지역 선택 버튼 (이미지에서 확인)
    "button[class*='sc-fEETNT']",  # sc-fEETNT 클래스가 있는 버튼
    "button[class*='cGRZls']",  # cGRZls 클래스가 있는 버튼
    # 기존 셀렉터들 (폴백)
    "ul[role='listbox'] li",
    "div[class*='auto'] li",
    "button:has-text('부산'), button:has-text('서울'), button:has-text('경기')",  # 텍스트 기반
]

# 선택된 지역 칩/라벨 (텍스트 확인용)
REGION_CHIP = [
    "[class*='Chip']:has-text('{text}')",
    "button:has-text('{text}')",
    "[role='button']:has-text('{text}')",
]

# 네비게이션 탭 관련 셀렉터 추가
NAVIGATION_TABS = [
    # 다방 분석 결과 기반: 네비게이션 탭
    "nav[class*='sc-eYRUSB'] a",  # 다방 네비게이션 링크 (이미지에서 확인)
    "nav[class*='gnvA0'] a",  # 다방 네비게이션 클래스 (이미지에서 확인)
    "a[href='/map/onetwo']",  # 지도 탭
    "a[href*='/map/']",  # 지도 관련 탭
    "button:has-text('지도')",
    "button:has-text('분양')",
    "button:has-text('관심목록')",
    "button:has-text('방내놓기')",
    "button:has-text('개편중')",
]

# 필터 드롭다운 관련 셀렉터 추가
FILTER_DROPDOWNS = [
    # 다방 분석 결과 기반: 필터 드롭다운
    "select:has-text('월세, 전세')",
    "select:has-text('방크기')",
    "select:has-text('사용승인일')",
    "select:has-text('층수')",
    "select:has-text('추가필터')",
    "button:has-text('월세, 전세')",
    "button:has-text('방크기')",
    "button:has-text('사용승인일')",
    "button:has-text('층수')",
    "button:has-text('추가필터')",
]

# 매물 타입 사이드바 관련 셀렉터 추가
PROPERTY_TYPE_SIDEBAR = [
    # 이미지에서 확인된 실제 CSS 클래스들
    "a[class*='sc-evlKSw'][class*='gfXolk']",  # 아파트, 주택/빌라, 오피스텔, 분양 링크 클래스 (이미지에서 확인)
    "a[class*='sc-evlKSw']",  # sc-evlKSw 클래스가 있는 링크
    "a[class*='gfXolk']",  # gfXolk 클래스가 있는 링크
    "a.sc-evlKSw.gfXolk",  # 좌측 사이드바 실제 링크 클래스 (주택/빌라 등)
    "a.sc-erobCP.bsOpZZ",  # 좌측 사이드바 실제 링크 클래스 (오피스텔)
    "a[class*='sc-erobCP']",  # 오피스텔 링크 클래스 패턴
    "a[class*='bsOpZZ']",  # 오피스텔 링크 클래스 패턴
    # 기존 텍스트 기반 선택자들
    "a:has-text('원/투룸')",
    "a:has-text('아파트')",
    "a:has-text('주택/빌라')",
    "a:has-text('오피스텔')",
    "a:has-text('분양')",
    "button:has-text('원/투룸')",
    "button:has-text('아파트')",
    "button:has-text('주택/빌라')",
    "button:has-text('오피스텔')",
    "button:has-text('분양')",
]

# 카드 루트 (우선순위 1→3)
CARD_ROOT = [
    '#map-list-tab-container li.sc-ouVgf.cuFXAJ',
    '#map-list-tab-container li.sc-bNShyz.kdCXHE',
    '#map-list-tab-container li[class*="sc-ouVgf"][class*="cuFXAJ"]',
    '#map-list-tab-container li[class*="sc-bNShyz"][class*="kdCXHE"]',
    # 이미지에서 확인된 실제 카드 클래스들
    'li[class*="sc-czXwGc"][class*="jphyhy"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="sc-czXwGc"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="jphyhy"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="sc-ouVgf"][class*="lRqXV"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="sc-ouVgf"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="lRqXV"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="cuFXAJ"]',  # 다방 카드 클래스 (이미지에서 확인)
    'li[class*="gCbeGA"]',  # 다방 카드 클래스
    'li[class*="sc-gShICF"]',  # 다방 카드 스타일드 컴포넌트
    'li[class*="Card"]',  # 일반 카드 클래스
    # 최신 DOM(styled-components): a 카드 루트
    'a[href^="/room/"][class*="Card"][class*="sc-"]',
    'a[href^="/room/"][class*="sc-dVMXWE"]',  # 다방 링크 클래스
    'article[class*="Card"][class*="sc-"]',
    "li[role='listitem']",
    "[data-testid*='room'], [data-testid='room-card']",
    "article, div[class*='RoomCard']",
]

# 카드 하위 필드
CARD_PRICE = [
    # onetwo 전용 가격 선택자
    ":scope >> text=/^(전세|월세|매매)/",              # onetwo 카드 내 가격 텍스트
    # 기존 선택자들 (폴백)
    # JSON에서 로드한 선택자 (우선순위 1)
    JSON_SELECTORS.get("list_price", ""),
    "p[class*='sc-fLMXbb'][class*='jZjfUh']",  # 아파트/원투룸 공통 가격 p
    "p.sc-fLMXbb.jZjfUh",
    "p.sc-doIiHy.jtStDE",                  # 오피스텔 가격 p 클래스(스샷)
    "p[class*='sc-doIiHy'][class*='jtStDE']",  # 오피스텔 가격 p 패턴
    "p[class*='sc-fLMXbb']",
    "p[class*='jZjfUh']",
    # 이미지에서 확인된 실제 가격 클래스들
    "h1[class*='sc-gtGlis'][class*='islzsw']",  # 다방 가격 제목 클래스 (이미지에서 확인)
    "h1[class*='sc-gtGlis']",  # 다방 가격 제목 클래스 (이미지에서 확인)
    "h1[class*='islzsw']",  # 다방 가격 제목 클래스 (이미지에서 확인)
    "p[class*='sc-fLMXbb'][class*='jZjfUh']",  # 다방 가격 p 태그 클래스 (이미지에서 확인)
    "p[class*='sc-fLMXbb']",  # 다방 가격 p 태그 클래스 (이미지에서 확인)
    "p[class*='jZjfUh']",  # 다방 가격 p 태그 클래스 (이미지에서 확인)
    # 기존 클래스들
    "h1[class*='sc-hoq0XT'][class*='kiYwXU']",  # 다방 가격 제목 클래스 (이미지에서 확인)
    "h1[class*='sc-hoq0XT']",  # 다방 가격 제목 클래스 (이미지에서 확인)
    "h1[class*='kiYwXU']",  # 다방 가격 제목 클래스 (이미지에서 확인)
    "div[class*='sc-eisxGE'] p",  # 다방 제목 컨테이너 내 텍스트
    "div[class*='hIWJxN'] p",  # 다방 제목 클래스
    "p:has-text(/^(월세|전세|매매)/)",  # 가격 패턴이 포함된 p 태그
    ".price",
    "[data-testid='price']",
    ".room-price",
    "text=/^(월세|전세|매매)/",
    "xpath=.//*[contains(text(),'월세') or contains(text(),'전세') or contains(text(),'매매')][1]",
]

# 빈 문자열 제거
CARD_PRICE = [sel for sel in CARD_PRICE if sel]

CARD_REALTOR = [
    # onetwo 전용 중개사 선택자
    ":scope >> text=/공인중개|중개사무소/",              # onetwo 카드 내 중개사 텍스트
    # 기존 선택자들 (폴백)
    # JSON에서 로드한 선택자 (우선순위 1)
    JSON_SELECTORS.get("list_realtor", ""),
    # 다방 분석 결과 기반: 브랜드 표시
    "p[class*='sc-cBzQip']",  # 다방 브랜드 클래스
    "p[class*='gCbNoQ']",  # 다방 브랜드 클래스
    "text=/공인중개사|부동산/",
]

# 빈 문자열 제거
CARD_REALTOR = [sel for sel in CARD_REALTOR if sel]

CARD_TIME = [
    # onetwo 전용 시간 선택자
    ":scope >> text=/등록일|전|초|분|시간|일|월/",        # onetwo 카드 내 시간 텍스트
    # 기존 선택자들 (폴백)
    "text=/\d+\s*(분|시간|일)\s*전/",
    "text=/어제|오늘/",
]

# 관리비 필드 추가
CARD_MAINTENANCE = [
    # onetwo 전용 관리비 선택자
    ":scope >> text=/관리비/",                          # onetwo 카드 내 관리비 텍스트
    # 기존 선택자들 (폴백)
    # JSON에서 로드한 선택자 (우선순위 1)
    JSON_SELECTORS.get("list_maint", ""),
    # 기존 관리비 선택자
    "text=/관리비/ ~ *",
    "[class*='maintenance']",
    "xpath=.//*[contains(text(),'관리비')]/following-sibling::*[1]",
]

# 빈 문자열 제거
CARD_MAINTENANCE = [sel for sel in CARD_MAINTENANCE if sel]

CARD_LINK = [
    # 다방 분석 결과 기반: 링크 요소
    "a[class*='sc-dVMXWE']",  # 다방 링크 클래스
    "a[class*='eoBiHP']",  # 다방 링크 클래스
    "a[href^='/room/']",  # 방 상세 링크
    "a[href]",
]

# 주소 추출 관련 선택자 (통합)
CARD_ADDRESS = [
    # onetwo 전용 주소 선택자
    ":scope >> text=/[가-힣]+(시|도)\s+[가-힣]+(구|군)\s+[가-힣]+(동|읍|면)/",  # onetwo 카드 내 주소 패턴
    # 기존 선택자들 (폴백)
    "section[data-scroll-spy-element='near'] p",
    "section.sc-hMraNJ.bclnPG p",          # 오피스텔 위치 섹션 p(스샷)
    "section.sc-huGleg.iCNJqs p",          # 오피스텔 위치 섹션 p(스샷)
    "p.sc-dPDzVR.iYQyEM",                  # 오피스텔 주소 p 클래스(스샷)
    # 공통 주소 컴포넌트 클래스 패턴
    "p[class*='sc-hMraNJ']",
    "p[class*='cllwBM']",
    # 위치/주소 관련 컨테이너 내부 텍스트
    "div[class*='location'] p",
    "div[class*='address'] p",
    # 폴백: 주소 형태 단어 포함 텍스트
    "p:has-text('시'), p:has-text('구'), p:has-text('동')",
]

DETAIL_ADDRESS = [
    "section[data-scroll-spy-element='near'] p",
    "section[class*='sc-ktesqn'] p",
    "div[class*='address'] p",
    "section.sc-hMraNJ.bclnPG p",
    "section.sc-huGleg.iCNJqs p",
    "p.sc-dPDzVR.iYQyEM",
]

LOCATION_INFO = [
    "section[data-scroll-spy-element='near']",
    "section[class*='sc-ktesqn']",
    "div[class*='location']",
    "div[class*='address']",
    "section.sc-hMraNJ.bclnPG",
    "section.sc-huGleg.iCNJqs",
]

CARD_ADDRESS_HINT = [
    # onetwo 전용 주소 힌트
    ":scope >> p, :scope >> div",                    # onetwo 카드 내 텍스트 요소
    # 기존 선택자들 (폴백)
    JSON_SELECTORS.get("list_address", ""),
    "div[class*='sc-eisxGE']",
    "div[class*='hIWJxN']",
    "[data-testid='address']",
    ".address",
    ".addr",
]
# 빈 문자열 제거
CARD_ADDRESS_HINT = [sel for sel in CARD_ADDRESS_HINT if sel]

DETAIL_TAB_BUTTONS = [
    # onetwo 전용 상세 페이지 탭
    "button:has-text('가격정보')",
    "button:has-text('상세정보')",
    "button:has-text('옵션')",
    "button:has-text('보안')",          # 보안/안전시설
    "button:has-text('3D투어')",
    # 기존 선택자들 (폴백)
    "button.sc-kjFqil.kQHrWF",           # 활성/비활성 탭 버튼 공통
    "button.sc-cWILuG.koQcu",             # 오피스텔 탭 버튼 클래스
    "button.sc-cWILuG.koQcu.active",      # 오피스텔 탭 버튼 활성 클래스
    "button[data-scroll-spy-btn]",       # data-scroll-spy 버튼
    "button:has-text('상세설명')",
    "button:has-text('위치 및 주변시설')",
    "button:has-text('중개사무소 정보')",
]

# onetwo(원/투룸) 전용
LIST_CONTAINER_SELECTORS = [
    "#onetwo-list",                      # 좌측 리스트 패널 루트
    "#map-list-tab-container",           # (백업) 탭 컨테이너
    # 기존 선택자들 (폴백)
    '#onetwo-list',                    # 메인 컨테이너(원/투룸)
    '#map-list-tab-container',         # 공통: 왼쪽 리스트 탭 컨테이너
    '[id^="map-list-"]',
    '[id^="dock-content-"]',
    '#onetwo-list ul',                 # 내부 리스트(원/투룸)
    '#onetwo-list ul[role="list"]',
    '#onetwo-list ul[class*="grid"]',
    '#map-list-tab-container ul',      # 내부 리스트(아파트/기타)
    '#map-list-tab-container ul[class*="sc-"][class*="grid"]',
    '#map-list-tab-container ul.sc-fkQybV',
    '#map-list-tab-container [role="list"]',
    '#map-list-tab-container ul[class*="grid"]',
    '#map-list-tab-container',
    ".hLRDng",                                  # 오피스텔: 리스트/패널 공통 grid 컨테이너
    "div.officetel-list",                      # 오피스텔: 리스트 컨테이너 식별자(일반)
    "#map-list-tab-container div.officetel-list",  # 오피스텔: 좌측 패널 내부 컨테이너
    "#officetel-list",                         # 오피스텔: 아이디 컨테이너(폴백)
    "#officetel-list [role='list']",
    "#officetel-list [role='listitem']",
]

# 리스트 UL과 카드
ONETWO_LIST_UL = [
    "ul.sc-lqDIzo.besNwT",            # 정확 클래스 (소문자 o)
    'ul[class^="sc-lqDIz"].besNwT',   # 패턴 폴백
    '#onetwo-list ul'                 # 컨테이너 폴백
]

# 빈 문자열 제거
LIST_CONTAINER_SELECTORS = [sel for sel in LIST_CONTAINER_SELECTORS if sel]

# 매물 카드 루트 셀렉터 (디버깅 결과 반영)
CARD_ROOT_SELECTORS = [
    # onetwo 전용 카드 선택자
    "li.sc-bNShyZ",                      # onetwo 목록 카드 li
    "li[class^='sc-bNShyZ']",            # 클래스 변경 대비
    # 기존 선택자들 (폴백)
    "#onetwo-list li",
    "li[role='listitem']",
    "a[href^='/room/']",                         # 앵커 자체도 카드 단서
    '#map-list-tab-container li.sc-ouVgf.cuFXAJ',
    '#map-list-tab-container li.sc-bNShyz.kdCXHE',
    '#map-list-tab-container li[class*="sc-ouVgf"][class*="cuFXAJ"]',
    '#map-list-tab-container li[class*="sc-bNShyz"][class*="kdCXHE"]',
    '#map-list-tab-container li.sc-ouVgf.cuFXAJ',                 # 아파트 카드 li (정확 일치)
    '#map-list-tab-container li[class*="sc-ouVgf"][class*="cuFXAJ"]',
    '#map-list-tab-container li.sc-bNShyz.kdCXHE',                # 스샷: 아파트 li 패턴
    '#map-list-tab-container li[class*="sc-bNShyz"][class*="kdCXHE"]',
    'li.sc-ouVgf.cuFXAJ',
    'li.sc-bNShyz.kdCXHE',
    '#onetwo-list li[class*="sc-czXwGc"][class*="jphyhy"]',    # 원/투룸 구역
    '#onetwo-list li[class*="sc-czXwGc"]',
    '#onetwo-list li[class*="jphyhy"]',
    '#onetwo-list li[role="listitem"]',                          # 1순위(구형)
    '#onetwo-list ul > li',                                       # 2순위
    '#map-list-tab-container li[class*="sc-"]',                  # 2.5순위(아파트 패널의 모든 sc-* li)
    '#onetwo-list li:has(a[href*="detail_type=room"])',         # 7순위(앵커 포함 li)
    'li[role="listitem"]',                                      # 전역 폴백
    'div:has(a[href*="detail_type=room"])',                     # div 폴백
    'li:has-text("월세"), li:has-text("전세"), li:has-text("매매")', # 텍스트 폴백
    "#officetel-list li",
    "#map-list-tab-container li.sc-bNShyz.kdCXHE",   # 오피스텔/공통 리스트 아이템
    "#map-list-tab-container li[class*='sc-bNShyz'][class*='kdCXHE']",
]

# 빈 문자열 제거
CARD_ROOT_SELECTORS = [sel for sel in CARD_ROOT_SELECTORS if sel]

# 방 링크 셀렉터 (이미지에서 확인된 실제 구조)
CARD_LINK_SELECTORS = [
    # onetwo 전용 링크
    "a[href^='/room/']",                                # onetwo 상세 링크
    # 기존 선택자들 (폴백)
    'a[href*="detail_type=room"][href*="detail_id="]',  # onetwo 상세 링크(최신)
    'a[href*="/map/onetwo"]',
    'a[href*="detail"]',
]


# 빈 문자열 제거
CARD_LINK_SELECTORS = [sel for sel in CARD_LINK_SELECTORS if sel]

# --- 매물번호 추출 선택자들 ---
# 상세 패널/페이지 텍스트에서 매물번호를 읽기 위한 후보들
LISTING_ID_SELECTORS = [
    "h1:has-text(/^\s*매물\s*\d+/)",              # 예: "매물 52201976"
    "text=/^\s*매물번호\s*\d+/",                  # 예: "매물번호 52201976"
    "#container-room-root :text('매물번호')",        # onetwo 사이드 패널 내부
    "#container-room-root :text('매물')",            # 예비 폴백
]

# 리스트 카드의 링크 href에서 id를 파싱하기 위한 후보들
LISTING_LINK_SELECTORS = [
    "a[href^='/room/']",            # /room/12345678 형태
    "a[href*='detail_id=']",        # ?detail_id=12345678 형태
]

# 매물 유형 필터 선택자
PROPERTY_TYPE_SELECTORS = {
    '원룸': 'a[href="/map/onetwo"]',
    '아파트': 'a[href="/map/apt"]',
    '주택/빌라': 'a[href="/map/house"]',
    '주택': 'a[href="/map/house"]',
    '오피스텔': 'a[href="/map/officetel"]',
    '분양': 'a[href="/map/sale-in-lots"]',
}

# 검색 및 필터 선택자
SEARCH_INPUT_SELECTORS = [
    'input#search-input',             # 검색 입력 필드
    'input[placeholder*="지역"]',     # 지역 검색 입력 필드
    'input[placeholder*="매물번호"]', # 매물번호 검색 입력 필드
]

REGION_SELECTION_SELECTORS = [
    # 이미지에서 확인된 실제 지역 선택 버튼 클래스
    'button.sc-fEETNT.cGRZls',        # 지역 선택 버튼 (이미지에서 확인)
    'button[class*="sc-fEETNT"]',     # sc-fEETNT 클래스가 있는 버튼
    'button[class*="cGRZls"]',        # cGRZls 클래스가 있는 버튼
    # 텍스트 기반 선택자들
    'button:has-text("부산"), button:has-text("서울"), button:has-text("경기")', # 텍스트 기반
    'button:has-text("기장"), button:has-text("종로"), button:has-text("분당")', # 구체적 지역명
]

# 매물 버튼 선택자
LIST_OPEN_BUTTON = [
    # 이미지에서 확인된 실제 매물 버튼 클래스
    'button:has-text("매물")',        # 매물 버튼
    'button.sc-hGqmkL.kOEMcC',       # 매물 버튼 클래스 (이미지에서 확인)
    'button[class*="sc-hGqmkL"]',    # sc-hGqmkL 클래스가 있는 버튼
    'button[class*="kOEMcC"]',       # kOEMcC 클래스가 있는 버튼
    # 추가 매물 관련 버튼들
    'button:has-text("목록")',        # 목록 버튼
    'button:has-text("리스트")',      # 리스트 버튼
    'div[role="button"]:has-text("매물")',  # div 버튼
]

# 페이지네이션 선택자
PAGINATION_CONTAINER = [
    # onetwo 전용 페이지네이션
    "div.sc-efUvXT.fvodgZ.pagination",                    # onetwo 페이지네이션 컨테이너
    "div[class*='pagination']",                           # 일반 페이지네이션
    # 기존 선택자들 (폴백)
    'div.sc-iEWboB.lolndx.pagination',   # 다방: 좌측 리스트 하단 페이지네이션 컨테이너(스샷)
    '#map-list-tab-container div.sc-iEWboB.lolndx.pagination',
    '#map-list-tab-container div[class*="pagination"]',
    'nav[class*="pagination"]',
    'ul[class*="pagination"]',
    '#map-list-tab-container nav[aria-label*="Pagination"]',
]

PAGE_NUMBER_BUTTONS = [
    "div.sc-efUvXT.fvodgZ.pagination button",  # onetwo 전용
    "div[class*='pagination'] button",         # 일반
    'div.sc-iEWboB.lolndx.pagination button',  # 구형/다른 탭
    'nav[aria-label*="Pagination"] button',
    '#map-list-tab-container .pagination button',
]

NEXT_PAGE_BUTTON = [
    # onetwo 전용 다음 페이지 버튼
    "div.sc-efUvXT.fvodgZ.pagination button:last-child:not([disabled])",  # onetwo 다음 버튼
    "div[class*='pagination'] button:last-child:not([disabled])",         # 일반 다음 버튼
    # 기존 선택자들 (폴백)
    'div.sc-iEWboB.lolndx.pagination button[aria-label="다음"]',
    'div.sc-iEWboB.lolndx.pagination button:has-text("다음")',
    'div.sc-iEWboB.lolndx.pagination button[aria-label*="next"]',
    '#map-list-tab-container .pagination button:has-text("다음")',
    '#map-list-tab-container .pagination a:has-text("다음")',
    '#map-list-tab-container button:has-text("›"), #map-list-tab-container button:has-text(">")',
    'button[aria-label*="다음"]',
    'a[aria-label*="다음"]',
    'nav[aria-label*="Pagination"] button[aria-label*="다음"]',
    'nav[aria-label*="Pagination"] button:has-text("›")',
]

    

# --- normalize newly added lists ---
for _name in ['PAGE_NUMBER_BUTTONS', 'LISTING_ID_SELECTORS', 'LISTING_LINK_SELECTORS']:
    _lst = globals().get(_name)
    if isinstance(_lst, list):
        # drop empties and keep order while removing dups
        seen = set()
        cleaned = []
        for s in _lst:
            if s and s not in seen:
                seen.add(s)
                cleaned.append(s)
        globals()[_name] = cleaned
