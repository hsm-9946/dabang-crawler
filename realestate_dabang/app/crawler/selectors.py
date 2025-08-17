from __future__ import annotations

# 다중 후보 셀렉터 정의. 실제 DOM 변경에 대비하여 최소 3개 이상 후보 제공.


SEARCH_INPUT = [
    'input[placeholder*="검색"]',
    'input[placeholder*="지역"]',
    'input[type="search"]',
    'xpath://input[contains(@placeholder, "지역") or contains(@placeholder, "검색")]',
]

AUTOCOMPLETE_FIRST = [
    'ul[role="listbox"] li',
    'div[class*="auto"] li',
    'xpath://ul[contains(@class,"auto") or @role="listbox"]//li[1]',
]

SEARCH_RESULT_CONTAINER = [
    '[data-testid="search-results"]',
    'div[class*="result"]',
    'main',
]


CARD = [
    'div[class*="room-card"]',
    'li[data-id*="room"]',
    'article[data-testid*="item"]',
    'div[data-testid="room-card"]',
    'article[class*="RoomCard"]',
]

PRICE = [
    '.price',
    '.room-price',
    '[data-testid="price"]',
    'xpath://*[contains(text(),"만원") or contains(text(),"원")]',
]

MAINT_FEE = [
    '.maintenance',
    '.fee',
    'xpath://*[contains(text(),"관리비")]',
]

ADDRESS = [
    '.addr',
    '.address',
    '[data-testid="address"]',
    'xpath://*[contains(text(),"동") or contains(text(),"리") or contains(text(),"읍") or contains(text(),"면")]',
]

TYPE = [
    '.type',
    '.badge',
    '.category',
    '[data-testid="roomType"]',
]

DETAIL_LINK = [
    'a[href*="room"]',
    'a[href*="detail"]',
    'a[href^="/"]',
]

LOAD_MORE = [
    'button[aria-label*="더보기"]',
    'xpath://button[contains(text(),"더보기")]',
    'button.load-more',
]

PAGINATION_NEXT = [
    'a[rel="next"]',
    'button[aria-label*="다음"]',
    'xpath://a[contains(text(),"다음")] | //button[contains(text(),"다음")]',
]

CAPTCHA_HINTS = [
    'iframe[src*="captcha"]',
    '[id*="captcha"]',
    'xpath://*[contains(text(),"자동입력")] | //*[contains(text(),"보안문자")]',
]

# UI 필터 관련
FILTER_TOGGLE_MORE = [
    'button:has-text("추가필터")',
    'xpath://*[self::button or self::div][contains(text(),"추가필터")]',
    'div[role="button"][data-testid*="moreFilter"]',
]

FILTER_SECTION_STRUCTURE = [
    'xpath://*[(self::div or self::section) and contains(.,"방구조")]//..',
    'xpath://*[contains(text(),"방구조")]',
]

STRUCTURE_ONE_ROOM = [
    'xpath://*[(self::button or self::div) and contains(text(),"원룸")]',
    'button[data-value="원룸"]',
    'div[role="button"][aria-label*="원룸"]',
]

# 상단/카테고리 탭에서 매물유형 전환(원룸·투룸/오피스텔/아파트 등)
PROPERTY_TAB_ROOM = [
    'xpath://*[(self::a or self::button or self::div) and (contains(normalize-space(.),"원룸") or contains(normalize-space(.),"원룸·투룸") or contains(normalize-space(.),"원룸/투룸"))]',
    'a[href*="oneroom"]',
]

PROPERTY_TAB_OFFICETEL = [
    'xpath://*[(self::a or self::button or self::div) and contains(normalize-space(.),"오피스텔")]',
    'a[href*="officetel"]',
]

PROPERTY_TAB_APARTMENT = [
    'xpath://*[(self::a or self::button or self::div) and contains(normalize-space(.),"아파트")]',
    'a[href*="apartment"]',
    '[data-testid*="apartment"]',
]

PROPERTY_TAB_HOUSE_VILLA = [
    'xpath://*[(self::a or self::button or self::div) and (contains(normalize-space(.),"주택/빌라") or contains(normalize-space(.),"빌라/주택") or contains(normalize-space(.),"주택") or contains(normalize-space(.),"빌라") or contains(normalize-space(.),"연립") or contains(normalize-space(.),"다가구"))]',
    'a[href*="house"]',
    'a[href*="villa"]',
    '[data-testid*="house"], [data-testid*="villa"]',
]

# 분양 관련 탭/버튼(후보). 실제 분양 페이지/탭이 있는 경우에만 동작.
SALE_BUILDING_TOGGLE = [
    'xpath://*[(self::button or self::div) and contains(normalize-space(.),"건물유형")]',
    '[data-testid*="sale-building-type"]',
]
SALE_BUILDING_OPTIONS = {
    '아파트': [
        'xpath://*[(self::button or self::div) and contains(normalize-space(.),"아파트")]',
    ],
    '오피스텔': [
        'xpath://*[(self::button or self::div) and contains(normalize-space(.),"오피스텔")]',
    ],
    '도시형생활주택': [
        'xpath://*[(self::button or self::div) and contains(normalize-space(.),"도시형생활주택")]',
    ],
}

SALE_STAGE_TOGGLE = [
    'xpath://*[(self::button or self::div) and contains(normalize-space(.),"분양단계")]',
]
SALE_STAGE_OPTIONS = {
    '분양예정': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"분양예정")]'],
    '접수중': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"접수중")]'],
    '접수마감': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"접수마감")]'],
    '입주예정': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"입주예정")]'],
}

SALE_SCHEDULE_TOGGLE = [
    'xpath://*[(self::button or self::div) and contains(normalize-space(.),"분양일정")]',
]
SALE_SCHEDULE_OPTIONS = {
    '모집공고': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"모집공고")]'],
    '특별공급': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"특별공급")]'],
    '1순위청약': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"1순위청약")]'],
    '2순위청약': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"2순위청약")]'],
    '청약접수': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"청약접수")]'],
    '당첨자발표': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"당첨자발표")]'],
    '계약기간': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"계약기간")]'],
    '준공시기': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"준공시기")]'],
}

SALE_SUPPLY_TOGGLE = [
    'xpath://*[(self::button or self::div) and contains(normalize-space(.),"공급유형")]',
]
SALE_SUPPLY_OPTIONS = {
    '공공분양': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"공공분양")]'],
    '민간분양': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"민간분양")]'],
    '공공임대': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"공공임대")]'],
    '민간임대': ['xpath://*[(self::button or self::div) and contains(normalize-space(.),"민간임대")]'],
}


