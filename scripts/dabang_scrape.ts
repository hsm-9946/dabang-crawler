#!/usr/bin/env tsx

// 수집 루틴 중복 실행 하드가드 추가
declare global { var __DABANG_RUNNING__: boolean | undefined; }

import { chromium, Browser, Page, Locator, BrowserContext } from 'playwright';
import * as XLSX from 'xlsx';
import * as fs from 'fs';
import * as path from 'path';
import { 
  LIST_CONTAINER, 
  CARD_ROOT, 
  FIELD_PRICE, 
  FIELD_MAINT, 
  FIELD_REALTOR, 
  FIELD_ADDR, 
  FIELD_LINK,
  PAGINATION_CONTAINER,
  NEXT_PAGE,
  SEARCH_INPUT,
  PROPERTY_BUTTON,
  DETAIL_ADDR,
  DETAIL_REALTOR,
  DETAIL_POSTED_DATE
} from './selectors';
import {
  parsePrice,
  parseMaintenance,
  parseDate,
  generateHash,
  normalizeUrl,
  safeTextExtract,
  safeAttrExtract,
  getCurrentTimestamp,
  generateFilename
} from './utils';

// 모든 매물 유형 카드 선택자
const CARD_CANDIDATES = [
  // 원투룸
  '#onetwo-list li.sc-bNShyZ',
  '#onetwo-list li[role="listitem"]',
  '#onetwo-list li',
  // 아파트
  '#apt-list ul.sc-0ItdJ li',
  '#apt-list li.sc-enXOiP',
  '#apt-list li[role="listitem"]',
  '#apt-list li',
  // 주택/빌라
  '#house-list li.sc-enXOiP',
  '#house-list li[role="listitem"]',
  '#house-list li',
  // 오피스텔
  '#officetel-list li.sc-enXOiP',
  '#officetel-list li[role="listitem"]',
  '#officetel-list li'
];

async function waitForOnetwoCards(page: Page) {
  // 모든 매물 유형 지원하는 컨테이너 대기
  await page.waitForSelector('#onetwo-list, #apt-list, #house-list, #officetel-list', { timeout: 10000 }); // 15s → 10s

  // '매물' 칩을 반드시 활성화 (아파트 페이지 대응)
  const chip = page.locator('button:has-text("매물"), button.sc-kMImeu.ifwrvU').first();
  if (await chip.count()) {
    const pressed = await chip.getAttribute('aria-pressed');
    if (!pressed || pressed === 'false') {
      try {
        await chip.click({ force: true });
        await page.waitForTimeout(200);
      } catch (error) {
        // 클릭 실패 시 JavaScript로 직접 클릭
        await page.evaluate(() => {
          const chip = (globalThis as any).document?.querySelector('button:has-text("매물"), button.sc-kMImeu.ifwrvU') as any;
          if (chip) chip.click();
        });
        await page.waitForTimeout(200);
      }
    }
  } else {
    // 아파트 페이지에서는 매물 버튼이 없을 수 있으므로 스킵
    console.log('매물 버튼을 찾을 수 없습니다. 아파트 페이지에서는 기본적으로 매물이 표시됩니다.');
  }

  // 내부 UL/role=list 등장 대기
  await page.locator('#onetwo-list ul, #onetwo-list [role="list"], #apt-list ul, #apt-list [role="list"], #house-list ul, #house-list [role="list"], #officetel-list ul, #officetel-list [role="list"]').first()
    .waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
      console.log('UL 요소를 찾을 수 없습니다. 직접 카드 찾기를 시도합니다.');
    }); // 8s → 5s

  // 렌더 트리거(스크롤+지도 패닝) - 더욱 단축
  const list = page.locator('#onetwo-list, #apt-list, #house-list, #officetel-list');
  for (let i = 0; i < 2; i++) { // 3회 → 2회로 단축
    await list.evaluate(el => { el.scrollTo({ top: 0 }); });
    await page.waitForTimeout(30); // 50ms → 30ms
    await list.evaluate(el => { el.scrollTo({ top: el.scrollHeight }); });
    await page.waitForTimeout(50); // 100ms → 50ms
  }
  
  // 지도 패닝 제거 (불필요한 지연 제거)
  
  // 카드 폴링(최대 8s)
  const deadline = Date.now() + 8000; // 12s → 8s
  while (Date.now() < deadline) {
    for (const sel of CARD_CANDIDATES) {
      const n = await page.locator(sel).count();
      if (n > 0) return { selector: sel, count: n };
    }
    await page.waitForTimeout(50); // 100ms → 50ms
  }
  throw new Error('property list present but no cards rendered');
}

async function ensureCardsAlive(page: Page, lastSelector: string | null): Promise<string> {
  let count = 0;
  if (lastSelector) count = await page.locator(lastSelector).count();
  if (count > 0) return lastSelector!;

  // 칩 재토글 + 컨테이너 리플로우
  const chip = page.locator('button:has-text("매물")').first();
  if (await chip.count()) { await chip.click({ force: true }); await page.waitForTimeout(500); }
  await page.evaluate(() => {
    const el = (globalThis as any).document?.querySelector('#onetwo-list, #apt-list, #house-list, #officetel-list') as any;
    if (el) { const d = el.style.display; el.style.display = 'none'; void el.offsetHeight; el.style.display = d || 'block'; }
  });
  const res = await waitForOnetwoCards(page);
  return res.selector;
}

async function getCards(page: Page, sel: string) {
  let cards = page.locator(sel);
  let n = await cards.count();
  if (n === 0) {
    sel = await ensureCardsAlive(page, sel);
    cards = page.locator(sel);
    n = await cards.count();
  }
  if (n === 0) throw new Error('카드를 끝내 찾지 못함');
  return { sel, cards, n };
}

interface PropertyData {
  source: string;
  type: string;
  title: string;
  deposit?: number;
  rent?: number;
  maintenance?: number | null;
  realtor: string;
  address: string;
  posted_at?: string;
  detail_url: string;
  scraped_at: string;
}

interface ScrapeOptions {
  type: string;
  region: string;
  limit: number;
  headless?: boolean;
  skipDetailPage?: boolean; // 상세페이지 진입 건너뛰기 옵션
}

// 상세 정보 추출용 인터페이스 및 헬퍼 타입
interface DetailInfo {
  priceRaw?: string;
  maintenanceRaw?: string;
  address?: string;
  realtor?: string;
  postedAt?: string;
  itemId?: string;
  extraData?: Partial<PropertyData>; // 상세페이지 추가 정보
}

class DabangScraper {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private context: BrowserContext | null = null;
  private collectedData: PropertyData[] = [];
  private seenHashes = new Set<string>();

  constructor(private options: ScrapeOptions) {}

  async initialize(): Promise<void> {
    console.log('브라우저 초기화 중...');
    this.browser = await chromium.launch({
      headless: this.options.headless ?? true,
      args: [
        '--disable-blink-features=AutomationControlled',
        '--lang=ko-KR',
        '--window-size=1440,900',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-images',
        '--disable-javascript-harmony-shipping',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-field-trial-config',
        '--disable-ipc-flooding-protection',
        '--memory-pressure-off',
        '--max_old_space_size=4096',
        '--aggressive-cache-discard',
        '--disable-cache',
        '--disable-application-cache',
        '--disable-offline-load-stale-cache',
        '--disk-cache-size=0',
        '--media-cache-size=0'
      ],
    });
    this.context = await this.browser.newContext({
      locale: 'ko-KR',
      timezoneId: 'Asia/Seoul',
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
      isMobile: false,
      hasTouch: false,
      javaScriptEnabled: true,
      bypassCSP: true,
      ignoreHTTPSErrors: true,
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
      extraHTTPHeaders: {
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
    this.page = await this.context.newPage();
    
    // 타임아웃 설정 더욱 단축
    this.page.setDefaultTimeout(6000); // 10s → 6s
    this.page.setDefaultNavigationTimeout(10000); // 15s → 10s
    
    // 페이지 성능 최적화 스크립트 주입
    await this.page.addInitScript(() => {
      // 불필요한 리소스 차단
      const originalFetch = (globalThis as any).fetch;
      (globalThis as any).fetch = function(...args: any[]) {
        const url = args[0] as string;
        if (url.includes('analytics') || url.includes('tracking') || url.includes('ads') || 
            url.includes('google-analytics') || url.includes('facebook') || url.includes('doubleclick')) {
          return Promise.resolve(new Response('', { status: 200 }));
        }
        return originalFetch.apply(this, args);
      };
      
      // 스크롤 성능 최적화
      Object.defineProperty((globalThis as any).document.body.style, 'scrollBehavior', {
        value: 'auto',
        writable: false
      });
      
      // 이미지 로딩 비활성화
      const originalCreateElement = (globalThis as any).document.createElement;
      (globalThis as any).document.createElement = function(tagName: string) {
        const element = originalCreateElement.call(this, tagName);
        if (tagName.toLowerCase() === 'img') {
          element.setAttribute('loading', 'lazy');
        }
        return element;
      };
    });
  }

  private getInitialUrl(): string {
    const typeMap: { [key: string]: string } = {
      '아파트': 'https://dabangapp.com/map/apt',
      '주택/빌라': 'https://dabangapp.com/map/house',
      '오피스텔': 'https://dabangapp.com/map/officetel',
      '원룸': 'https://dabangapp.com/map/onetwo'
    };
    
    return typeMap[this.options.type] || typeMap['아파트'];
  }

  async navigateToInitialPage(): Promise<void> {
    if (!this.page) throw new Error('페이지가 초기화되지 않았습니다.');
    
    const url = this.getInitialUrl();
    console.log(`초기 페이지로 이동: ${url}`);
    await this.page.goto(url);
    await this.page.waitForLoadState('domcontentloaded');
  }

  async searchRegion(): Promise<void> {
    if (!this.page || !this.options.region) return;
    
    console.log(`지역 검색: ${this.options.region}`);
    
    try {
      // 검색 입력창 찾기
      for (const selector of SEARCH_INPUT) {
        try {
          const input = await this.page.locator(selector).first();
          await input.click();
          await input.fill(this.options.region);
          await this.page.waitForTimeout(500); // 1s → 500ms
          
          // a태그(왼쪽 제안 리스트) 정확/부분 일치 우선
          try {
            const aExact = await this.page.locator(`a:has-text('${this.options.region}')`).first();
            if (await aExact.count() > 0) {
              await aExact.click();
              await this.page.waitForTimeout(500); // 1s → 500ms
              console.log("지역 a태그(정확일치) 클릭");
              return;
            }
          } catch (error) {
            // 다음 시도
          }
          
          try {
            const head = this.options.region.split(' ')[0];
            const aPartial = await this.page.locator("a[role='link'], a[href*='/map/']").filter({ hasText: head }).first();
            if (await aPartial.count() > 0) {
              await aPartial.click();
              await this.page.waitForTimeout(500); // 1s → 500ms
              console.log("지역 a태그(부분일치) 클릭");
              return;
            }
          } catch (error) {
            // 다음 시도
          }
          
          // 버튼/기존 후보들(폴백)
          try {
            const exactButton = await this.page.locator(`button:has-text('${this.options.region}')`).first();
            if (await exactButton.count() > 0) {
              await exactButton.click();
              await this.page.waitForTimeout(400); // 800ms → 400ms
              console.log("지역 button(정확일치) 클릭");
              return;
            }
          } catch (error) {
            // 다음 시도
          }
          
          // 최후: 텍스트/엔터
          try {
            await this.page.getByText(this.options.region, { exact: true }).first().click();
            await this.page.waitForTimeout(400); // 800ms → 400ms
            return;
          } catch (error) {
            // 다음 시도
          }
          
          try {
            await this.page.keyboard.press("Enter");
            await this.page.waitForTimeout(400); // 800ms → 400ms
            return;
          } catch (error) {
            // 다음 시도
          }
          
        } catch (error) {
          continue;
        }
      }
    } catch (error) {
      console.log('지역 검색 실패, 계속 진행:', error);
    }
  }

  async openPropertyList(): Promise<void> {
    if (!this.page) return;
    
    console.log('리스트 패널을 열려고 시도합니다...');
    
    // 1) '매물' 칩/버튼 직격 (클릭 방해 요소 제거 후 클릭)
    try {
      // 클릭 방해 요소 제거 시도
      await this.page!.evaluate(() => {
        const marks = (globalThis as any).document.querySelectorAll('mark');
        marks.forEach((mark: any) => mark.remove());
      });
      
      const mm = await this.page.locator("button:has-text('매물'), [role='button']:has-text('매물')");
      if (await mm.count() > 0) {
        await mm.first().click();
        await this.page.waitForTimeout(600); // 1.2s → 600ms
        console.log("매물 칩 클릭 성공");
      }
    } catch (error) {
      console.log(`매물 칩 클릭 실패: ${error}`);
    }
    
    // 2) 기존 후보들도 시도
    try {
      for (const selector of PROPERTY_BUTTON) {
        try {
          const button = await this.page.locator(selector).first();
          if (await button.isVisible()) {
            await button.click();
            await this.page.waitForTimeout(500); // 1s → 500ms
            break;
          }
        } catch (error) {
          continue;
        }
      }
    } catch (error) {
      console.log('기존 매물 버튼 클릭 실패:', error);
    }
    
    // 3) 수집 흐름 상 항상 "칩 활성 → 컨테이너 스크롤 → 카드 탐지" 순서를 지키도록 리팩터
    await waitForOnetwoCards(this.page);
  }



  async extractCardData(container: Locator): Promise<PropertyData[]> {
    const newData: PropertyData[] = [];
    
    // 카드 찾기
    let cards: Locator | null = null;
    for (const selector of CARD_ROOT) {
      try {
        cards = container.locator(selector);
        const count = await cards.count();
        if (count > 0) {
          console.log(`카드 선택자 사용: ${selector}, 개수: ${count}`);
          break;
        }
      } catch (error) {
        continue;
      }
    }
    
    if (!cards) {
      console.log('카드를 찾을 수 없습니다.');
      return newData;
    }
    
    const cardCount = await cards.count();
    console.log(`카드 데이터 추출 시작: ${cardCount}개`);
    
    for (let i = 0; i < cardCount; i++) {
      try {
        const card = cards.nth(i);
        const data = await this.extractSingleCard(card);
        
        if (data && !this.isDuplicate(data)) {
          newData.push(data);
          this.seenHashes.add(generateHash(data.detail_url));
        }
      } catch (error) {
        console.log(`카드 ${i} 추출 실패:`, error);
        continue;
      }
    }
    
    return newData;
  }

  // 모든 매물 유형 지원 컨테이너/카드/페이지네이션 셀렉터
  private readonly SEL = {
    LIST: '#onetwo-list, #apt-list, #house-list, #officetel-list',
    ULs: ['ul.sc-lqDIzo', 'ul[class*=sc-][class*=lqDIzo]'],
    CARD: 'li.sc-bNShyZ', // 카드 li
    PAGINATION: [
      '#onetwo-list >> .. >> .. >> div.pagination',
      'div.pagination',
      '[data-testid="pagination"]',
      '[class*="pagination"]',
      'nav[aria-label*="페이지"]',
      'nav[aria-label*="pagination"]'
    ],
    NEXTS: [
      'button[aria-label*=다음]',
      'button[aria-label*=next i]',
      'button:has-text(">")',
      'button:has-text("›")',
      'button[aria-label*="Next"]',
      'button[aria-label*="next"]',
      'a[aria-label*="다음"]',
      'a[aria-label*="next"]'
    ]
  };

  // 리스트 컨테이너 찾기
  private async resolveList(): Promise<Locator | null> {
    if (!this.page) return null;
    
    // onetwo-list가 뜨면 바로 사용
    const list = this.page.locator(this.SEL.LIST);
    await list.first().waitFor({ state: 'visible', timeout: 10_000 });
    // UL이 아직 렌더 중이어도 컨테이너 자체는 유효
    return list.first();
  }

  // 상세 패널/페이지 내 특정 탭을 열도록 보장
  private async ensureDetailTab(page: Page, tabText: string): Promise<void> {
    const scope = page.locator('#container-room-root');
    const tabBtn = scope.locator(`button:has-text("${tabText}")`).first();
    if (await tabBtn.count()) {
      const sel = await tabBtn.getAttribute('aria-pressed');
      if (!sel || sel === 'false') {
        await tabBtn.click({ force: true });
        await page.waitForTimeout(100); // 200ms → 100ms
      }
    }
  }

  // 상세 패널/팝업에서 정보 추출 (패널/팝업 모두 지원, 클래스명 변화에 강인)
  private async extractDetailInfo(detailPage: Page): Promise<DetailInfo> {
    const info: DetailInfo = {};
    const scope = detailPage.locator('#container-room-root');

    // 가끔 패널이 늦게 뜨므로 잠깐 대기
    await scope.first().waitFor({ state: 'visible', timeout: 3000 }).catch(() => {}); // 5s → 3s

    // 매물 번호
    try {
      const idLabel = scope.getByRole('heading', { name: /매물\s*번호|매물\s*번호\s*|매물\s*번호\s*:?/ });
      if (await idLabel.count()) {
        const container = idLabel.first().locator('..');
        const text = (await container.textContent()) || '';
        const m = text.match(/매물\s*번호\s*([0-9]+)/) || text.match(/매물번호\s*([0-9]+)/);
        if (m) info.itemId = m[1];
      } else {
        const raw = await scope.locator('text=매물번호').first().locator('..').textContent().catch(() => '');
        const m = raw ? raw.match(/매물번호\s*([0-9]+)/) : null;
        if (m) info.itemId = m[1];
      }
    } catch {}

    // 가격정보 탭
    try {
      await this.ensureDetailTab(detailPage, '가격정보');

      // 가격(예: "월세 500/40" 또는 "매매 5억5000")
      const priceCand = scope.locator('h1:has-text("월세"), h1:has-text("전세"), h1:has-text("매매"), p:has-text("/"), p:has-text("억")').first();
      if (await priceCand.count()) {
        info.priceRaw = (await priceCand.textContent())?.trim();
      }

      // 관리비 (li 항목 또는 p)
      const maintCand = scope.locator('li:has-text("관리비"), p:has-text("관리비")').first();
      if (await maintCand.count()) {
        const t = await maintCand.textContent();
        if (t) info.maintenanceRaw = t.trim();
      } else {
        // 사용자가 제공한 상세 li 클래스 폴백
        const liFallback = scope.locator('li.sc-kYLqRS');
        if (await liFallback.count()) {
          for (let i = 0; i < Math.min(10, await liFallback.count()); i++) {
            const txt = (await liFallback.nth(i).textContent()) || '';
            if (/관리비/.test(txt)) { info.maintenanceRaw = txt.trim(); break; }
            if (!info.priceRaw && /(월세|전세|매매)/.test(txt)) info.priceRaw = txt.trim();
          }
        }
      }
    } catch {}

    // === 주소 추출 (탭 전환 없이 직접 검색) ===
    try {
      for (const sel of DETAIL_ADDR) {
        const el = detailPage.locator(sel).first();
        if (await el.count()) {
          const t = (await el.textContent())?.trim();
          console.log(`    🔍 주소 셀렉터 "${sel}": "${t?.substring(0, 100)}"`);
          if (t && t.length >= 8) {  // "부산시" 같은 너무 짧은 값 방지
            // 주소 형식 검증 (시/군/구/동/읍/리 포함)
            if (/시|군|구|동|읍|리/.test(t)) {
              info.address = t;
              console.log(`    ✅ 주소 추출 성공: "${t}"`);
              break;
            }
          }
        }
      }
    } catch (error) {
      console.log(`    ❌ 주소 추출 오류: ${error}`);
    }

    // === 중개사 추출 (탭 전환 없이 직접 검색) ===
    try {
      for (const sel of DETAIL_REALTOR) {
        const el = detailPage.locator(sel).first();
        if (await el.count()) {
          // 앵커면 텍스트 또는 title 사용
          const tag = await el.evaluate((n: any) => n.tagName.toLowerCase()).catch(()=>'');
          let t = (await el.textContent())?.trim() || '';
          if (!t && tag === 'a') {
            t = (await el.getAttribute('title')) || '';
          }
          
          console.log(`    🔍 중개사 셀렉터 "${sel}": "${t?.substring(0, 100)}"`);
          
          // 불필요 접두사 제거 및 정리
          const originalT = t;
          t = t.replace(/\s*(공인중개사|중개사무소|중개사)\s*/g, '').trim();
          // 접두사가 제거되지 않았으면 원본 텍스트 사용
          if (!t) {
            t = originalT;
          }
          
          if (t && t.length >= 3) { // 최소 3자 이상
            info.realtor = t;
            console.log(`    ✅ 중개사 추출 성공: "${t}"`);
            break;
          }
        }
      }
    } catch (error) {
      console.log(`    ❌ 중개사 추출 오류: ${error}`);
    }

    // 상세정보 탭 → 최초등록일 (올린날짜)
    try {
      await this.ensureDetailTab(detailPage, '상세정보');
      for (const sel of DETAIL_POSTED_DATE) {
        const el = detailPage.locator(sel).first();
        if (await el.count()) {
          const t = (await el.textContent())?.trim();
          if (t) {
            // 날짜 형식 검증 (YYYY.MM.DD 또는 YYYY-MM-DD)
            const m = t.match(/(20\d{2}[.-]\d{2}[.-]\d{2})/);
            if (m) {
              info.postedAt = m[1];
              break;
            }
          }
        }
      }
    } catch {}

    // 상세페이지 추가 정보 추출
    try {
      const extraData = await this.extractDetailData(detailPage);
      info.extraData = extraData;
      
      // extraData에서 주소와 중개사 정보를 info 객체에 병합
      if (extraData.address && !info.address) {
        info.address = extraData.address;
      }
      if (extraData.realtor && !info.realtor) {
        info.realtor = extraData.realtor;
      }
      if (extraData.posted_at && !info.postedAt) {
        info.postedAt = extraData.posted_at;
      }
    } catch (error) {
      console.log('상세페이지 추가 정보 추출 실패:', error);
    }

    return info;
  }

  // 상세페이지에서 추가 데이터 추출하는 함수
  private async extractDetailData(detailPage: Page): Promise<Partial<PropertyData>> {
    const detailData: any = {};
    
    try {
      // 0. 관리비 정보 추출 (상세페이지에서 더 정확할 수 있음)
      const maintSelectors = [
        '[data-testid="maintenance"]',
        'span:has-text("관리비")',
        'div:has-text("관리비")',
        '[class*="maintenance"]'
      ];
      for (const selector of maintSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          if (text && text.trim()) {
            const maint = parseMaintenance(text.trim());
            if (maint) {
              detailData.maintenance = maint;
              break;
            }
          }
        }
      }

      // 0-1. 중개사무소 정보 추출 (상세페이지에서 더 정확할 수 있음)
      const realtorSelectors = [
        'div.sc-gVrasc.ktkEIH h1',                        // 스크린샷에서 확인된 정확한 중개사 셀렉터
        '[data-testid="realtor"]',
        'span:has-text("공인중개")',
        'div:has-text("공인중개")',
        '[class*="realtor"]',
        'section[data-scroll-spy-element="agent-info"] h1'
      ];
      for (const selector of realtorSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          if (text && text.trim()) {
            detailData.realtor = text.trim();
            break;
          }
        }
      }

      // 0-2. 주소 정보 추출 (상세페이지에서 더 정확할 수 있음)
      const addressSelectors = [
        'div.sc-hbxBMb.efnhT > p',                        // 스크린샷에서 확인된 정확한 주소 셀렉터
        '[data-testid="address"]',
        'span:has-text("시")',
        'div:has-text("시")',
        '[class*="address"]'
      ];
      for (const selector of addressSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          if (text && text.trim() && text.length >= 8) {
            // 주소 형식 검증 (시/군/구/동/읍/리 포함)
            if (/시|군|구|동|읍|리/.test(text.trim())) {
              detailData.address = text.trim();
              break;
            }
          }
        }
      }

      // 0-3. 올린날짜(최초등록일) 추출 (상세페이지에서 더 정확할 수 있음)
      const postedDateSelectors = [
        'p.sc-dPDzVR.iYQyEM',                             // 스크린샷에서 확인된 정확한 날짜 셀렉터
        'p:has-text("2025.")', 'p:has-text("2024.")', 'p:has-text("2023.")',
        'li:has-text("최초등록일")', 'p:has-text("최초등록일")',
        '[data-testid="posted-date"]', '[class*="date"]'
      ];
      for (const selector of postedDateSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          if (text && text.trim()) {
            // 날짜 형식 검증 (YYYY.MM.DD 또는 YYYY-MM-DD)
            const m = text.trim().match(/(20\d{2}[.-]\d{2}[.-]\d{2})/);
            if (m) {
              detailData.posted_at = m[1];
              break;
            }
          }
        }
      }

      // 1. 방 개수 추출
      const roomCountSelectors = [
        '[data-testid="room-count"]',
        'span:has-text("방")',
        'div:has-text("방")'
      ];
      for (const selector of roomCountSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          const match = text?.match(/(\d+)개?방|(\d+)룸/);
          if (match) {
            detailData.room_count = parseInt(match[1] || match[2]);
            break;
          }
        }
      }

      // 2. 면적 추출
      const areaSelectors = [
        '[data-testid="area"]',
        'span:has-text("㎡")',
        'div:has-text("㎡")'
      ];
      for (const selector of areaSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          const match = text?.match(/(\d+(?:\.\d+)?)㎡/);
          if (match) {
            detailData.area = parseFloat(match[1]);
            break;
          }
        }
      }

      // 3. 층수 추출
      const floorSelectors = [
        '[data-testid="floor"]',
        'span:has-text("층")',
        'div:has-text("층")',
        '[class*="floor"]'
      ];
      for (const selector of floorSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          const match = text?.match(/(\d+)층/);
          if (match) {
            detailData.floor = parseInt(match[1]);
            break;
          }
        }
      }

      // 4. 건물 연식 추출
      const yearSelectors = [
        '[data-testid="building-year"]',
        'span:has-text("년")',
        'div:has-text("년")',
        '[class*="year"]'
      ];
      for (const selector of yearSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          const match = text?.match(/(\d{4})년/);
          if (match) {
            detailData.building_year = parseInt(match[1]);
            break;
          }
        }
      }

      // 5. 상세 설명 추출
      const descSelectors = [
        '[data-testid="description"]',
        '[class*="description"]',
        '[class*="detail"]',
        'p:has-text("설명")',
        'div:has-text("설명")'
      ];
      for (const selector of descSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          if (text && text.trim().length > 10) {
            detailData.description = text.trim();
            break;
          }
        }
      }

      // 6. 이미지 URL 추출
      const imageSelectors = [
        '[data-testid="images"] img',
        '[class*="image"] img',
        '[class*="photo"] img',
        'img[src*="dabang"]'
      ];
      const images: string[] = [];
      for (const selector of imageSelectors) {
        const elements = detailPage.locator(selector);
        const count = await elements.count();
        for (let i = 0; i < Math.min(count, 10); i++) { // 최대 10개 이미지
          const src = await elements.nth(i).getAttribute('src');
          if (src && !images.includes(src)) {
            images.push(src);
          }
        }
        if (images.length > 0) break;
      }
      if (images.length > 0) {
        detailData.images = images;
      }

      // 7. 연락처 추출
      const phoneSelectors = [
        '[data-testid="phone"]',
        '[class*="phone"]',
        'span:has-text("010"), span:has-text("02-"), span:has-text("031")',
        'a[href^="tel:"]'
      ];
      for (const selector of phoneSelectors) {
        const element = detailPage.locator(selector).first();
        if (await element.count()) {
          const text = await element.textContent();
          const href = await element.getAttribute('href');
          const phone = text?.match(/(\d{2,3}-\d{3,4}-\d{4}|\d{10,11})/)?.[1] || 
                       href?.replace('tel:', '');
          if (phone) {
            detailData.phone = phone;
            break;
          }
        }
      }

      // 8. 편의시설 추출
      const facilitySelectors = [
        '[data-testid="facilities"]',
        '[class*="facility"]',
        '[class*="amenity"]',
        'span:has-text("주차"), span:has-text("엘리베이터"), span:has-text("에어컨"), span:has-text("난방")'
      ];
      const facilities: string[] = [];
      for (const selector of facilitySelectors) {
        const elements = detailPage.locator(selector);
        const count = await elements.count();
        for (let i = 0; i < count; i++) {
          const text = await elements.nth(i).textContent();
          if (text && text.trim()) {
            facilities.push(text.trim());
          }
        }
        if (facilities.length > 0) break;
      }
      if (facilities.length > 0) {
        detailData.facilities = facilities;
        // 개별 편의시설 플래그 설정
        detailData.parking = facilities.some(f => f.includes('주차'));
        detailData.elevator = facilities.some(f => f.includes('엘리베이터'));
        detailData.aircon = facilities.some(f => f.includes('에어컨'));
        detailData.heating = facilities.some(f => f.includes('난방'));
      }

    } catch (error) {
      console.log('상세페이지 데이터 추출 중 오류:', error);
    }

    return detailData;
  }



  // 다음 페이지로 이동
  private async goNext(listEl: Locator): Promise<boolean> {
    if (!this.page) return false;
    
    console.log('🔄 다음 페이지 이동 시도 중...');
    
    // 현재 첫 카드 id (detail_id) 스냅샷
    const firstId = async () => {
      const a = listEl.locator("a[href^='/room/']").first();
      if (await a.count() === 0) return '';
      const href = await a.getAttribute('href') || '';
      const m = href.match(/detail_id=([^&]+)/);
      return m?.[1] ?? href;
    };
    const prev = await firstId();
    console.log(`   📍 현재 첫 카드 ID: ${prev}`);

    // 컨테이너 맨 아래까지 스크롤 (페이지네이션 노출)
    try {
      const handle = await listEl.elementHandle();
      if (handle) await this.page.evaluate(el => { (el as any).scrollTop = el.scrollHeight; }, handle);
      console.log('   📜 리스트 컨테이너 맨 아래로 스크롤 완료');
    } catch {}
    await this.page.waitForTimeout(500);

    // 페이지네이션 찾기
    let pag: Locator | null = null;
    for (const sel of this.SEL.PAGINATION) {
      const cand = this.page.locator(sel).first();
      if (await cand.count()) { 
        pag = cand; 
        console.log(`   🔍 페이지네이션 컨테이너 발견: ${sel}`);
        break; 
      }
    }
    if (!pag) {
      console.log('   ❌ 페이지네이션 컨테이너를 찾을 수 없습니다.');
      return false;
    }

    // 다음 버튼 클릭 → 실패 시 현재 선택된 숫자 다음 클릭
    let clicked = false;
    console.log('   🔘 다음 버튼 찾기 시도...');
    
    for (const s of this.SEL.NEXTS) {
      const btn = pag.locator(s).first();
      if (await btn.count()) {
        const disabled = await btn.getAttribute('disabled');
        const btnText = await btn.textContent();
        console.log(`   🔍 다음 버튼 발견: ${s}, 텍스트: "${btnText}", 비활성화: ${disabled}`);
        
        if (!disabled) {
          await btn.scrollIntoViewIfNeeded();
          await btn.click();
          clicked = true;
          console.log(`   ✅ 다음 버튼 클릭 성공: ${s}`);
          break;
        } else {
          console.log(`   ⚠️ 다음 버튼이 비활성화됨: ${s}`);
        }
      }
    }
    
    if (!clicked) {
      console.log('   🔢 숫자 버튼으로 다음 페이지 찾기 시도...');
      const nums = await pag.locator('button').all();
      console.log(`   📊 총 ${nums.length}개의 버튼 발견`);
      
      let cur = -1;
      for (let i = 0; i < nums.length; i++) {
        const cls = (await nums[i].getAttribute('class')) || '';
        const aria = (await nums[i].getAttribute('aria-current')) || '';
        const btnText = await nums[i].textContent();
        console.log(`   🔍 버튼 ${i}: 텍스트="${btnText}", 클래스="${cls}", aria="${aria}"`);
        
        if (cls.includes('active') || cls.includes('selected') || aria === 'page') { 
          cur = i; 
          console.log(`   📍 현재 페이지 버튼: ${i}번`);
          break; 
        }
      }
      if (cur !== -1 && cur + 1 < nums.length) {
        const nextBtnText = await nums[cur + 1].textContent();
        console.log(`   🔘 다음 페이지 버튼 클릭: ${cur + 1}번 (${nextBtnText})`);
        await nums[cur + 1].scrollIntoViewIfNeeded();
        await nums[cur + 1].click();
        clicked = true;
      } else {
        console.log(`   ❌ 다음 페이지 버튼을 찾을 수 없음 (현재: ${cur}, 총 버튼: ${nums.length})`);
      }
    }
    
    if (!clicked) {
      console.log('   ❌ 다음 페이지로 이동할 수 없습니다.');
      return false;
    }

    // 내용 변경 대기: networkidle + 첫 카드 변경
    console.log('   ⏳ 페이지 변경 대기 중...');
    try { 
      await this.page.waitForLoadState('networkidle', { timeout: 3000 }); 
      console.log('   ✅ 네트워크 로딩 완료');
    } catch {
      console.log('   ⚠️ 네트워크 로딩 타임아웃');
    }
    
    for (let i = 0; i < 15; i++) { // 20회 → 15회
      const now = await firstId();
      console.log(`   🔍 변경 확인 ${i+1}/15: 이전="${prev}", 현재="${now}"`);
      if (now && now !== prev) {
        console.log('   ✅ 페이지 변경 확인됨!');
        return true;
      }
      await this.page.waitForTimeout(150); // 250ms → 150ms
    }
    console.log('   ⚠️ 페이지 변경을 확인할 수 없지만 계속 진행');
    return true; // 일부 환경에선 id가 같게 보일 수 있으니 관대하게 true
  }



  // "전체 페이지 끝까지" 수집 루프
  private async collectAllPages(limit: number = 9999): Promise<PropertyData[]> {
    if (!this.page || !this.context) return [];
    
    const out: PropertyData[] = [];
    let pageNo = 1;

    // "=== 전체 페이지 수집 시작 ===" 로그가 두 번 나오지 않도록, 해당 로그를 한 군데로 통합하고, 바로 waitForOnetwoCards 호출
    console.log('=== 전체 페이지 수집 시작 (목표: %d개) ===', limit);
    let cardSelector: string | null = null;
    try {
      const res = await waitForOnetwoCards(this.page);
      cardSelector = res.selector;
      console.log(`카드 선택자 확정: ${res.selector}, 초기 감지: ${res.count}개`);
    } catch (e) {
      console.log('카드 초기 감지 실패, 폴백 시도:', (e as Error).message);
      cardSelector = await ensureCardsAlive(this.page, null);
      const c = await this.page.locator(cardSelector).count();
      console.log(`카드 선택자 확정(폴백): ${cardSelector}, 초기 감지: ${c}개`);
    }

    // 리스트 패널이 열린 상태라고 가정 (이미 열었음)
    while (true) {
      const listEl = await this.resolveList();
      if (!listEl) {
        console.log('리스트 컨테이너를 찾을 수 없습니다.');
        break;
      }

      // 페이지네이션/무한스크롤 처리 전, 항상 "칩 활성 → 리스트 스크롤 → 카드 보장" 순서 유지
      await this.page.waitForTimeout(100); // 200ms → 100ms로 단축
      cardSelector = await ensureCardsAlive(this.page, cardSelector);

      // onetwo(원/투룸) 사이드 패널 전용 처리
      const sidePanel = this.page.locator('#onetwo-list');

      // 수집 루프에서 "카드를 찾을 수 없습니다." 발생 경로 교체(즉시 회복 시도)
      const { sel, cards, n } = await getCards(this.page, cardSelector || '');
      cardSelector = sel;

      console.log(`=== 페이지 ${pageNo} 수집 시작 (${n}개 카드) ===`);

      // 현재 페이지 카드 파싱
      for (let i = 0; i < n; i++) {
        console.log(`시도: 카드 ${i + 1}/${n}`);
        try {
          const c = cards.nth(i);
          // 기본 정보 추출
          const price = await c.locator('strong, b, [class*=price]').first().textContent().catch(()=> '');
          const addr = await c.locator('p:has-text("동"), p:has-text("읍"), [class*=address]').first().textContent().catch(()=> '');

          // 상세 정보 추출
          const priceText = await safeTextExtract(c, FIELD_PRICE) || (price || '').trim();
          const addressText = await safeTextExtract(c, FIELD_ADDR) || (addr || '').trim();
          const realtorText = await safeTextExtract(c, FIELD_REALTOR) || '정보없음';
          const maintText = await safeTextExtract(c, FIELD_MAINT);
          const maintenance = maintText ? parseMaintenance(maintText) : null;

          // href 후보(두 가지 모두 시도)
          let href = await c.locator("a[href^='/room/']").first().getAttribute('href').catch(()=> null);
          if (!href) {
            href = await c.locator("a[href*='detail_id=']").first().getAttribute('href').catch(()=> null);
          }
          let normalizedUrl = href ? normalizeUrl(href) : '';

                    // === 상세 열기 시도 (옵션에 따라 선택적 실행) ===
          let detailPage: Page | null = null;
          let panelOpened = false;
          
          // 현재 매물 처리 중 표시
          console.log(`📋 [${i+1}/${n}] 매물 처리 중...`);
          
          if (!this.options.skipDetailPage) {
            try {
              // 1) 우선 카드 내부 링크가 있으면 그것을 클릭, 없으면 카드 루트 클릭
              const cardSel = `${cardSelector} >> nth=${i}`; // 현재 반복의 카드 셀렉터
              const linkInCard = c.locator("a[href^='/room/'], a[href*='detail_id=']").first();
              const clickable = (await linkInCard.count()) ? linkInCard : c;

              const popupPromise: Promise<Page | null> = this.page!
                .waitForEvent('popup', { timeout: 1500 }) // 2.5s → 1.5s
                .then(p => p as Page)
                .catch(() => null);
              await clickable.click({ force: true });
              await this.page!.waitForTimeout(100); // 150ms → 100ms

              // 패널형 대기
              const panel = this.page.locator('#container-room-root');
              panelOpened = await panel.waitFor({ state: 'visible', timeout: 2000 }).then(() => true).catch(() => false); // 3s → 2s

              // 팝업형 대기 (타임아웃 보장)
              const maybePopup: Page | null = await Promise.race<Page | null>([
                popupPromise,
                new Promise<Page | null>(resolve => setTimeout(() => resolve(null), 1600)), // 2.6s → 1.6s
              ]);
              if (maybePopup) {
                detailPage = maybePopup;
                await detailPage.waitForLoadState('domcontentloaded').catch(() => {});
              }

              // 추가 폴백: 1.6초 내 반응 없으면 href로 강제 이동 시도
              if (!panelOpened && !detailPage && href) {
                const absHref = href.startsWith('http') ? href : new URL(href, 'https://dabangapp.com').toString();
                console.log('  팝업/패널 미감지 → href로 이동:', absHref);
                const p = await this.context!.newPage();
                await p.goto(absHref, { waitUntil: 'domcontentloaded' });
                detailPage = p;
              }

              // 상세 URL 확정: 팝업이면 팝업 url, 패널이면 현재 탭 url
              if (!normalizedUrl) {
                if (detailPage) normalizedUrl = normalizeUrl(detailPage.url());
                else if (panelOpened) normalizedUrl = normalizeUrl(this.page.url());
              }
            } catch (e) {
              console.log(`상세 열기 예외 (카드 ${i}):`, e);
            }
          }

            // 상세 페이지에서 심화 정보 수집 (가능한 경우)
  let detailInfo: DetailInfo | null = null;
  if (!this.options.skipDetailPage) {
    try {
      const activeDetailPage = detailPage || (panelOpened ? this.page! : null);
      if (activeDetailPage) {
        detailInfo = await this.extractDetailInfo(activeDetailPage);
      } else {
        console.log('  ⚠️ 상세페이지를 찾을 수 없음');
      }
    } catch (error) {
      console.log('  ❌ 상세페이지 정보 추출 실패:', error);
    }
  }

          // 중복 체크(가능하면 URL로, 없으면 내용 해시로)
          const dedupKey = normalizedUrl || generateHash([priceText, realtorText, addressText].join('|'));
          if (this.seenHashes.has(dedupKey)) {
            console.log(`⏭️  [${i+1}/${n}] 중복 매물 건너뛰기`);
            console.log(`   📍 ${addressText}`);
            console.log(`   💰 ${priceText}`);
            console.log(`   ─────────────────────────────────────────`);
            continue;
          }

          // === 상세 정보 우선 병합 규칙 ===
          // detailInfo > detailInfo.extraData > 카드 텍스트 순서로 최종값 결정
          const finalAddressRaw =
            (detailInfo?.address && detailInfo.address.trim()) ||
            ((detailInfo?.extraData as any)?.address && String((detailInfo?.extraData as any).address).trim()) ||
            addressText;

          const finalRealtorRaw =
            (detailInfo?.realtor && detailInfo.realtor.trim()) ||
            ((detailInfo?.extraData as any)?.realtor && String((detailInfo?.extraData as any).realtor).trim()) ||
            realtorText;

          const finalPostedAt: string | undefined =
            detailInfo?.postedAt ||
            ((detailInfo?.extraData as any)?.posted_at as string | undefined);

          // 텍스트 정제
          const finalAddress = this.cleanAddress(finalAddressRaw || '');
          const finalRealtor = this.cleanRealtor(finalRealtorRaw || '');

          // data 생성: extraData를 먼저 병합한 뒤, 명시 필드를 뒤에 둬서 항상 우선 적용
          const data: PropertyData = {
            source: '다방',
            type: this.options.type,
            title: (detailInfo?.priceRaw || priceText),
            maintenance: detailInfo?.maintenanceRaw ? parseMaintenance(detailInfo.maintenanceRaw) : maintenance,
            ...(detailInfo?.extraData || {}),
            realtor: finalRealtor,
            address: finalAddress,
            posted_at: finalPostedAt,
            detail_url: normalizedUrl || '',
            scraped_at: getCurrentTimestamp()
          };

          // 디버깅: 실제 저장되는 데이터 확인
          console.log(`    🔍 저장될 데이터:`, {
            address: data.address,
            realtor: data.realtor,
            posted_at: data.posted_at
          });

          out.push(data);
          this.seenHashes.add(dedupKey);
          // 패널 모드일 때 UI 안정화를 위해 잠깐 대기
          if (panelOpened && !detailPage) { await this.page!.keyboard.press('Escape').catch(() => {}); }
          try { if (detailPage && detailPage !== this.page) await (detailPage as Page).close(); } catch {}

          // 수집 완료 로그 (간소화)
          console.log(`✅ [${out.length}] 수집 완료!`);
          console.log(`   📍 주소: ${data.address}`);
          console.log(`   💰 금액: ${data.title}`);
          console.log(`   💸 관리비: ${data.maintenance || 0}`);
          console.log(`   🏢 부동산: ${data.realtor}`);
          console.log(`   📅 최종등록일: ${data.posted_at || ''}`);
          console.log(`   ─────────────────────────────────────────`);

          // 대기 시간 제거 (120ms → 0ms)
          // await this.page!.waitForTimeout(120);
          if (out.length >= limit) {
            console.log(`목표 수(${limit}) 도달`);
            return out;
          }
        } catch (error) {
          console.log(`❌ [${i+1}/${n}] 카드 파싱 실패`);
          console.log(`   🔍 오류: ${error}`);
          console.log(`   ─────────────────────────────────────────`);
          continue;
        }
      }

      // 다음 페이지로 이동 시도
      console.log(`=== 페이지 ${pageNo} 수집 완료 (${n}개 카드) ===`);
      
      // 다음 페이지로 이동
      const nextPageSuccess = await this.goNext(listEl);
      if (!nextPageSuccess) {
        console.log('다음 페이지가 없거나 이동 실패 - 수집 종료');
        break;
      }
      
      pageNo++;
      console.log(`=== 페이지 ${pageNo}로 이동 완료 ===`);
      
      // 페이지 로딩 대기
      await this.page!.waitForTimeout(1000);
    }
    
    console.log(`\n🎉 수집 완료!`);
    console.log(`📊 총 수집된 매물: ${out.length}개`);
    console.log(`📍 대상 지역: ${this.options.region}`);
    console.log(`🏠 매물 유형: ${this.options.type}`);
    console.log(`⏰ 수집 시간: ${new Date().toLocaleString('ko-KR')}`);
    console.log(`┌────────────────────────────────────────────────────────┐`);
    console.log(`│                    수집 완료!                          │`);
    console.log(`└────────────────────────────────────────────────────────┘`);
    return out;
  }

  // 주소 텍스트 정리
  private cleanAddress(address: string): string {
    if (!address) return '';
    // 상세페이지에서 추출된 정확한 주소인지 확인
    if (address.includes('부산시') || address.includes('서울시') || address.includes('경기도')) {
      return address;
    }
    // 첫 번째 줄만 추출 (개행 문자로 분리)
    const lines = address.split('\n');
    const firstLine = lines[0].trim();
    // 너무 길면 50자로 제한
    return firstLine.length > 50 ? firstLine.substring(0, 50) + '...' : firstLine;
  }

  // 중개사 텍스트 정리
  private cleanRealtor(realtor: string): string {
    if (!realtor) return '';
    // 상세페이지에서 추출된 정확한 중개사인지 확인
    if (realtor.includes('부동산') || realtor.includes('공인중개사') || realtor.includes('중개사무소')) {
      return realtor;
    }
    // 첫 번째 줄만 추출
    const lines = realtor.split('\n');
    const firstLine = lines[0].trim();
    // 너무 길면 30자로 제한
    return firstLine.length > 30 ? firstLine.substring(0, 30) + '...' : firstLine;
  }

  private async extractSingleCard(card: Locator): Promise<PropertyData | null> {
    try {
      // 가격 추출
      const priceText = await safeTextExtract(card, FIELD_PRICE);
      if (!priceText) return null;
      
      const priceData = parsePrice(priceText);
      
      // 관리비 추출
      const maintText = await safeTextExtract(card, FIELD_MAINT);
      const maintenance = maintText ? parseMaintenance(maintText) : undefined;
      
      // 중개사 추출
      const realtorText = await safeTextExtract(card, FIELD_REALTOR) || '정보없음';
      
      // 주소 추출
      let addressText = await safeTextExtract(card, FIELD_ADDR);
      if (!addressText) {
        // 상세 페이지에서 주소 추출 시도
        addressText = await this.extractAddressFromDetail(card);
      }
      const address = addressText || '주소정보없음';
      
      // 상세 링크 추출
      const detailUrl = await safeAttrExtract(card, FIELD_LINK[0], 'href') ||
                       await safeAttrExtract(card, FIELD_LINK[1], 'href');
      
      if (!detailUrl) return null;
      
      const normalizedUrl = normalizeUrl(detailUrl);
      
      // 기본 데이터 생성
      const propertyData: PropertyData = {
        source: '다방',
        type: this.options.type,
        title: priceData.raw,
        deposit: priceData.deposit,
        rent: priceData.rent,
        maintenance,
        realtor: realtorText,
        address,
        detail_url: normalizedUrl,
        scraped_at: getCurrentTimestamp()
      };
      
      // 상세페이지 정보는 collectAllPages에서 별도로 처리됨
      // 여기서는 기본 정보만 반환
      
      return propertyData;
      
    } catch (error) {
      console.log('카드 데이터 추출 실패:', error);
      return null;
    }
  }

  private async extractAddressFromDetail(card: Locator): Promise<string | null> {
    if (!this.page) return null;
    
    try {
      // 상세 링크 찾기
      const detailUrl = await safeAttrExtract(card, FIELD_LINK[0], 'href') ||
                       await safeAttrExtract(card, FIELD_LINK[1], 'href');
      
      if (!detailUrl) return null;
      
      const normalizedUrl = normalizeUrl(detailUrl);
      
      // 새 탭에서 열기
      const detailPage = await this.browser!.newPage();
      await detailPage.goto(normalizedUrl);
      await detailPage.waitForLoadState('domcontentloaded');
      
      // 주소 추출 시도
      const addressSelectors = [
        '[data-testid="address"]',
        '.address',
        'p:has-text("시"), p:has-text("구"), p:has-text("동")',
        'section[data-scroll-spy-element="near"] p'
      ];
      
      let address = null;
      for (const selector of addressSelectors) {
        try {
          const el = await detailPage.locator(selector).first();
          const text = await el.textContent();
          if (text && text.trim()) {
            address = text.trim();
            break;
          }
        } catch (error) {
          continue;
        }
      }
      
      await detailPage.close();
      return address;
      
    } catch (error) {
      console.log('상세 페이지 주소 추출 실패:', error);
      return null;
    }
  }

  private isDuplicate(data: PropertyData): boolean {
    const hash = generateHash(data.detail_url);
    return this.seenHashes.has(hash);
  }



  async scrape(): Promise<void> {
    // 진입 함수(메인 run 또는 scrape 함수) 맨 앞에 삽입
    if (globalThis.__DABANG_RUNNING__) {
      console.log('[guard] collector is already running, skip second start');
      process.exit(0);
    }
    globalThis.__DABANG_RUNNING__ = true;
    
    try {
      await this.initialize();
      await this.navigateToInitialPage();
      await this.searchRegion();
      await this.openPropertyList();
      
      // 새로운 collectAllPages 함수 사용
      this.collectedData = await this.collectAllPages(this.options.limit);
      
      console.log(`\n수집 완료: 총 ${this.collectedData.length}개 데이터`);
      
    } catch (error) {
      console.error('수집 중 오류 발생:', error);
      // 디버깅 스크린샷 저장
      await this.dumpContainerDiagnostics();
    } finally {
      await this.cleanup();
    }
  }

  private async dumpContainerDiagnostics(): Promise<void> {
    if (!this.page) return;
    
    try {
      console.log('컨테이너 디버깅 정보 저장 중...');
      
      // 스크린샷 저장
      const screenshotPath = 'debug/container_debug.png';
      await this.page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`스크린샷 저장: ${screenshotPath}`);
      
      // HTML 저장
      const htmlPath = 'debug/container_debug.html';
      const html = await this.page.content();
      const fs = require('fs');
      const path = require('path');
      
      // debug 디렉토리 생성
      if (!fs.existsSync('debug')) {
        fs.mkdirSync('debug', { recursive: true });
      }
      
      fs.writeFileSync(htmlPath, html, 'utf8');
      console.log(`HTML 저장: ${htmlPath}`);
      
    } catch (error) {
      console.log('디버깅 정보 저장 실패:', error);
    }
  }

  async saveResults(): Promise<void> {
    if (this.collectedData.length === 0) {
      console.log('저장할 데이터가 없습니다.');
      return;
    }
    
    const filename = generateFilename();
    const outputDir = 'output';
    
    // output 디렉토리 생성
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    // CSV 저장
    const csvPath = path.join(outputDir, `${filename}.csv`);
    const csvContent = this.generateCSV();
    fs.writeFileSync(csvPath, csvContent, 'utf8');
    console.log(`CSV 저장 완료: ${csvPath}`);
    
    // XLSX 저장
    const xlsxPath = path.join(outputDir, `${filename}.xlsx`);
    this.generateXLSX(xlsxPath);
    console.log(`XLSX 저장 완료: ${xlsxPath}`);
  }

  private generateCSV(): string {
    // 엑셀 시트 구조에 맞게 헤더 수정
    const headers = [
      '주소', '금액', '관리비', '부동산', '올린날짜'
    ];
    
    const csvRows = [headers.join(',')];
    
    for (const data of this.collectedData) {
      // 주소와 가격을 별도로 분리
      const address = this.formatAddressOnly(data);
      const price = this.formatPriceOnly(data);
      
      // 관리비 정제 (숫자만 추출)
      const maintenance = data.maintenance ? String(data.maintenance) : '';
      
      // 중개사 정보 정제
      const realtor = data.realtor || '';
      
      // 올린날짜 정제 (YYYY.MM.DD 형식)
      const postedDate = data.posted_at || '';
      
      const row = [
        `"${address}"`,
        `"${price}"`, // 금액을 별도 컬럼으로 분리
        `"${maintenance}"`,
        `"${realtor}"`,
        `"${postedDate}"`
      ];
      
      csvRows.push(row.join(','));
    }
    
    return csvRows.join('\n');
  }

  // 주소만 반환 (가격 제외)
  private formatAddressOnly(data: PropertyData): string {
    const address = data.address || '';
    return address.trim();
  }

  // 가격만 반환
  private formatPriceOnly(data: PropertyData): string {
    const priceText = data.title || '';
    return priceText.trim();
  }

  private generateXLSX(filepath: string): void {
    // 엑셀 시트 구조에 맞게 데이터 변환
    const excelData = this.collectedData.map(data => {
      // 주소와 가격을 별도로 분리
      const address = this.formatAddressOnly(data);
      const price = this.formatPriceOnly(data);
      
      // 관리비 정제 (숫자만 추출)
      const maintenance = data.maintenance ? String(data.maintenance) : '';
      
      // 중개사 정보 정제
      const realtor = data.realtor || '';
      
      // 올린날짜 정제 (YYYY.MM.DD 형식)
      const postedDate = data.posted_at || '';
      
      return {
        '주소': address,
        '금액': price, // 금액을 별도 컬럼으로 분리
        '관리비': maintenance,
        '부동산': realtor,
        '올린날짜': postedDate
      };
    });
    
    // 워크시트 생성
    const worksheet = XLSX.utils.json_to_sheet(excelData);
    
    // 컬럼 너비 자동 조정
    const columnWidths = [
      { wch: 50 }, // 주소 (넓게)
      { wch: 15 }, // 금액
      { wch: 12 }, // 관리비
      { wch: 20 }, // 부동산
      { wch: 15 }  // 올린날짜
    ];
    worksheet['!cols'] = columnWidths;
    
    // 워크북 생성 및 시트 추가
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, '다방매물');
    
    // 엑셀 파일 저장
    XLSX.writeFile(workbook, filepath);
  }

  async cleanup(): Promise<void> {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

// 헬퍼 함수 추가: 상세 오픈(클릭→팝업→수동이동) 3단계 폴백
async function openDetailFromCard(page: Page, cardSelector: string, context: BrowserContext) {
  // 1) 카드 내부의 실제 링크를 우선 찾는다
  const link = page.locator(`${cardSelector} a[href^="/room/"], ${cardSelector} a[href*="detail_id="]`).first();

  // href 확보 시 절대 URL로 변환
  let href: string | null = null;
  try {
    if (await link.count()) {
      href = await link.evaluate((el: any) => el.href || el.getAttribute('href'));
    }
  } catch {}

  // 2) 새 탭(popup) 케이스 대기 + 클릭 시도
  //    - 링크가 있으면 링크에 클릭, 없으면 카드 루트에 클릭
  const clickable = (await link.count()) ? link : page.locator(cardSelector).first();
  const popupPromise = page.waitForEvent('popup').catch(() => null);
  const navPromise = page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 5000 }).catch(() => null);

  try {
    await clickable.click({ button: 'left', delay: 30, force: true });
  } catch {
    // 오버레이 차단 대비 중간 클릭 시도
    try {
      const box = await clickable.boundingBox();
      if (box) {
        await page.mouse.click(box.x + Math.min(16, box.width / 3), box.y + Math.min(16, box.height / 2));
      }
    } catch {}
  }

  const popup = await popupPromise;
  const nav = await navPromise;

  if (popup) {
    // popup으로 열렸다면 그 페이지를 사용
    const detail = await popup;
    await detail.waitForLoadState('domcontentloaded', { timeout: 10000 }).catch(() => {});
    // onetwo 사이드 패널형이 아닌, 개별 상세 컨테이너 존재 확인
    await detail.waitForSelector('#container-room-root, [data-testid="room-detail"]', { timeout: 8000 }).catch(() => {});
    return detail;
  }

  if (nav) {
    // 같은 탭 내 네비게이션 성공 (아파트/주택 상세)
    await page.waitForSelector('#container-room-root, [data-testid="room-detail"]', { timeout: 8000 }).catch(() => {});
    return page;
  }

  // 3) 마지막 폴백: href 직접 이동
  if (href) {
    const abs = href.startsWith('http') ? href : new URL(href, page.url()).toString();
    await page.goto(abs, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#container-room-root, [data-testid="room-detail"]', { timeout: 8000 }).catch(() => {});
    return page;
  }

  // 그래도 실패면 카드 내부에서 텍스트 기반 링크를 찾아 강제 이동
  const textLink = page.locator(`${cardSelector} >> text=/^(월세|전세|매매)/`).first();
  if (await textLink.count()) {
    const href2 = await textLink.evaluate((el: any) => {
      let a = el.closest('a') as any;
      return a?.href || a?.getAttribute('href') || null;
    }).catch(() => null);
    if (href2) {
      const abs2 = href2.startsWith('http') ? href2 : new URL(href2, page.url()).toString();
      await page.goto(abs2, { waitUntil: 'domcontentloaded' });
      await page.waitForSelector('#container-room-root, [data-testid="room-detail"]', { timeout: 8000 }).catch(() => {});
      return page;
    }
  }

  throw new Error('상세페이지 오픈 실패: 클릭/팝업/직접이동 모두 불가');
}

// CLI 인자 파싱
function parseArguments(): ScrapeOptions {
  const args = process.argv.slice(2);
  const options: ScrapeOptions = {
    type: '아파트',
    region: '',
    limit: 1000,
    headless: true,
    skipDetailPage: false
  };
  
  for (let i = 0; i < args.length; i += 2) {
    const flag = args[i];
    const value = args[i + 1];
    
    switch (flag) {
      case '--type':
        options.type = value;
        break;
      case '--region':
        options.region = value;
        break;
      case '--limit':
        options.limit = parseInt(value) || 1000;
        break;
      case '--headless':
        options.headless = value === 'true';
        break;
      case '--skip-detail':
        options.skipDetailPage = value === 'true';
        break;
    }
  }
  
  return options;
}

// 메인 실행 함수
async function main() {
  const options = parseArguments();
  
  console.log('다방 부동산 매물 수집기 시작');
  console.log('옵션:', options);
  
  const scraper = new DabangScraper(options);
  
  try {
    await scraper.scrape();
    await scraper.saveResults();
    console.log('수집 완료!');
  } catch (error) {
    console.error('수집 실패:', error);
    process.exit(1);
  }
}

// 스크립트 직접 실행 시
if (require.main === module) {
  main().catch(console.error);
}



