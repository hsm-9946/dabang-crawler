// 다방 부동산 매물 수집용 선택자 정의
// selectors.py와 의미를 맞추고 우선순위대로 나열

export const LIST_CONTAINER = [
  // 핵심 후보 (사용자 요청)
  "#onetwo-list",                              // 원/투룸 전용
  "#apt-list",                                 // 아파트 전용 (실제 ID)
  "#apartment-list",                           // 아파트 전용 (폴백)
  "aside ul[role='list']", "aside [role='list']",
  "div[id^='dock-content-'] ul",
  // 기존 선택자들
  '#onetwo-list',
  '#apt-list',
  '#apartment-list',
  '#map-list-tab-container',
  '[id^="map-list-"]',
  '[id^="dock-content-"]',
  '#onetwo-list ul',
  '#apt-list ul',
  '#apartment-list ul',
  '#map-list-tab-container ul',
  '#map-list-tab-container [role="list"]',
  '.hLRDng',
];

export const CARD_ROOT = [
  // onetwo 전용 카드 선택자
  "li.sc-bNShyZ",                              // onetwo 목록 카드 li
  "li[class^='sc-bNShyZ']",                    // 클래스 변경 대비
  // 아파트 전용 카드 선택자
  "li.sc-apartment-card",                      // 아파트 목록 카드 li
  "li[class^='sc-apartment']",                 // 아파트 클래스 변경 대비
  "div.apartment-item",                        // 아파트 아이템 div
  // 기존 선택자들 (폴백)
  "#onetwo-list li",
  "#apartment-list li",
  "li[role='listitem']",
  "a[href^='/room/']",                         // 앵커 자체도 카드 단서
  "a[href^='/apartment/']",                    // 아파트 앵커
  '#onetwo-list li.sc-bNShyZ.kdcXHE',
  '#onetwo-list li[class*="sc-bNShyZ"][class*="kdcXHE"]',
  '#apartment-list li.sc-apartment-card',
  '#apartment-list li[class*="sc-apartment"]',
  '#map-list-tab-container li.sc-bNShyZ.kdcXHE',
  '#map-list-tab-container li[class*="sc-bNShyZ"][class*="kdcXHE"]',
  '#onetwo-list li[role="listitem"]',
  '#apartment-list li[role="listitem"]',
  '#onetwo-list ul > li',
  '#apartment-list ul > li',
  '#map-list-tab-container li[class*="sc-"]',
  'li[role="listitem"]',
  'a[href^="/room/"]', // div 카드 대신 앵커 카드도 허용
  'a[href^="/apartment/"]', // 아파트 앵커도 허용
];

export const FIELD_PRICE = [
  // onetwo 전용 가격 선택자
  ':scope >> text=/^(전세|월세|매매)/',              // onetwo 카드 내 가격 텍스트
  // 기존 선택자들 (폴백)
  'text=/^(월세|전세|매매)/',
  'p[class*="sc-fLMXbb"]',
  'p[class*="doIiHy"]',
  'span:has-text(/^(월세|전세|매매)/)',
];

export const FIELD_MAINT = [
  // onetwo 전용 관리비 선택자
  ":scope >> text=/관리비/",                          // onetwo 카드 내 관리비 텍스트
  // 기존 선택자들 (폴백)
  'text=/관리비/ ~ *',
  "[class*='maintenance']",
];

export const FIELD_REALTOR = [
  // onetwo 전용 중개사 선택자
  ":scope >> text=/공인중개|중개사무소/",              // onetwo 카드 내 중개사 텍스트
  // 기존 선택자들 (폴백)
  "text=/공인중개사|부동산/",
  "p[class*='sc-cBzQip']",
  "p[class*='gCbNoQ']",
];

export const FIELD_ADDR = [
  // onetwo 전용 주소 선택자
  ":scope >> text=/[가-힣]+(시|도)\s+[가-힣]+(구|군)\s+[가-힣]+(동|읍|면)/",  // onetwo 카드 내 주소 패턴
  // 기존 선택자들 (폴백)
  "section[data-scroll-spy-element='near'] p",
  "p:has-text('시'), p:has-text('구'), p:has-text('동')",
];

export const FIELD_LINK = [
  'a[href*="detail_type=room"][href*="detail_id="]',
  'a[href*="detail_type=apartment"][href*="detail_id="]',
  'a[href^="/room/"]',
  'a[href^="/apartment/"]',
];

// 상세 패널(원/투룸) 주소/중개사 셀렉터
export const DETAIL_ADDR: string[] = [
  'section[data-scroll-spy-element="near"] p:has-text("부산")',  // 부산시 포함된 정확한 주소
  'section[data-scroll-spy-element="near"] p:has-text("시")',    // 시 포함된 주소
  'section[data-scroll-spy-element="near"] p:has-text("구")',    // 구 포함된 주소
  'section[data-scroll-spy-element="near"] p:has-text("동")',    // 동 포함된 주소
  'div.sc-hbxBMb.efnhT > p:has-text("부산")',                   // 스크린샷에서 확인된 정확한 주소 wrapper
  'p:has-text("부산")', 'p:has-text("시")', 'p:has-text("구")', 'p:has-text("동")', 'p:has-text("읍")'
];

export const DETAIL_REALTOR: string[] = [
  'section[data-scroll-spy-element="agent-info"] h1:has-text("부동산")',  // 중개사무소 정보 섹션의 상호 h1
  'section[data-scroll-spy-element="agent-info"] h1:has-text("공인중개사")',  // 공인중개사 포함
  'section[data-scroll-spy-element="agent-info"] h1:has-text("중개사무소")',  // 중개사무소 포함
  'h1:has-text("공인중개사")', 'h1:has-text("중개사무소")', // 실제 작동하는 중개사 셀렉터
  'div.sc-gVrasc.ktkEIH h1',                              // 스크린샷에서 확인된 정확한 중개사 h1 컨테이너
  'section[data-scroll-spy-element="agent-info"] a[href^="/agent/"]',
  '[data-testid="realtor"] h1, [data-testid="realtor"]'   // 폴백
];

// 아파트 전용 상세페이지 셀렉터 (필요시 추가)
export const APARTMENT_DETAIL_ADDR: string[] = [
  'section[data-scroll-spy-element="near"] p',            // 아파트 상세페이지 주소
  'div.apartment-address p',                              // 아파트 전용 주소 컨테이너
  'p:has-text("시")', 'p:has-text("구")', 'p:has-text("동")', 'p:has-text("읍")'
];

export const APARTMENT_DETAIL_REALTOR: string[] = [
  'h1:has-text("공인중개사")', 'h1:has-text("중개사무소")', // 아파트 상세페이지 중개사
  'div.apartment-realtor h1',                             // 아파트 전용 중개사 컨테이너
  'section[data-scroll-spy-element="agent-info"] h1',
  '[data-testid="realtor"] h1, [data-testid="realtor"]'
];

// 올린날짜(최초등록일) 셀렉터
export const DETAIL_POSTED_DATE: string[] = [
  'p.sc-dPDzVR.iYQyEM',                                   // 스크린샷에서 확인된 정확한 날짜 셀렉터
  'p:has-text("2025.")', 'p:has-text("2024.")', 'p:has-text("2023.")',
  'li:has-text("최초등록일")', 'p:has-text("최초등록일")',
  '[data-testid="posted-date"]', '[class*="date"]'
];

export const PAGINATION_CONTAINER = [
  // onetwo 전용 페이지네이션
  "div.sc-efUvXT.fvodgZ.pagination",                    // onetwo 페이지네이션 컨테이너
  // 아파트 전용 페이지네이션
  "div.apartment-pagination",                           // 아파트 페이지네이션 컨테이너
  "div[class*='pagination']",                           // 일반 페이지네이션
  // 기존 선택자들 (폴백)
  'div[class*="pagination"]',
  'nav[aria-label*="Pagination"]',
];

export const NEXT_PAGE = [
  // onetwo 전용 다음 페이지 버튼
  "div.sc-efUvXT.fvodgZ.pagination button:last-child:not([disabled])",  // onetwo 다음 버튼
  "div[class*='pagination'] button:last-child:not([disabled])",         // 일반 다음 버튼
  // 기존 선택자들 (폴백)
  'button[aria-label*="다음"]',
  'button:has-text("다음")',
  'button:has-text("›")',
];

export const SEARCH_INPUT = [
  '#search-input',
  'input[placeholder*="지역"]',
  'input[placeholder*="검색"]',
];

export const REGION_SUGGEST_ITEM = [
  // 핵심 후보 (사용자 요청)
  "a[role='link']",
  "a[href*='/map/']",          // 스샷처럼 왼쪽 제안 컬럼의 링크들
  "li a",
  "button[role='option']",
  "ul[role='listbox'] button",
  // 기존 선택자들
  "button:has-text('부산'), button:has-text('서울'), button:has-text('경기')",
];

export const PROPERTY_BUTTON = [
  'button:has-text("매물")',
  'button:has-text("리스트")',
  '[data-testid="property-list-button"]',
];
