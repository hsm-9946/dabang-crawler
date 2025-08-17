import { createHash } from 'crypto';

// 텍스트 정규화 함수들
export interface ParsedPrice {
  type: string;
  deposit?: number;
  rent?: number;
  price?: number;
  raw: string;
}

export function parsePrice(text: string): ParsedPrice {
  const raw = text.trim();
  
  // 월세 패턴: "월세 500/43" 또는 "월세 500만/43만"
  const monthlyMatch = raw.match(/월세\s*(\d+(?:\.\d+)?)(?:만)?\/(\d+(?:\.\d+)?)(?:만)?/);
  if (monthlyMatch) {
    const deposit = parseFloat(monthlyMatch[1]) * 10000; // 만원 단위
    const rent = parseFloat(monthlyMatch[2]) * 10000;
    return {
      type: '월세',
      deposit: Math.round(deposit),
      rent: Math.round(rent),
      raw
    };
  }
  
  // 전세 패턴: "전세 1억" 또는 "전세 1억 5000"
  const jeonseMatch = raw.match(/전세\s*(\d+)억(?:\s*(\d+))?/);
  if (jeonseMatch) {
    const deposit = parseInt(jeonseMatch[1]) * 100000000;
    const additional = jeonseMatch[2] ? parseInt(jeonseMatch[2]) * 10000 : 0;
    return {
      type: '전세',
      deposit: deposit + additional,
      raw
    };
  }
  
  // 매매 패턴: "매매 5억" 또는 "매매 5억 5000"
  const saleMatch = raw.match(/매매\s*(\d+)억(?:\s*(\d+))?/);
  if (saleMatch) {
    const price = parseInt(saleMatch[1]) * 100000000;
    const additional = saleMatch[2] ? parseInt(saleMatch[2]) * 10000 : 0;
    return {
      type: '매매',
      price: price + additional,
      raw
    };
  }
  
  // 기본 반환
  return {
    type: '기타',
    raw
  };
}

export function parseMaintenance(text: string): number | null {
  const raw = text.trim();
  
  // "매월 7만원" 패턴
  const monthlyMatch = raw.match(/매월\s*(\d+(?:\.\d+)?)(?:만)?원?/);
  if (monthlyMatch) {
    const amount = parseFloat(monthlyMatch[1]);
    return amount >= 1000 ? amount : amount * 10000; // 만원 단위 처리
  }
  
  // "관리비 7만원" 패턴
  const maintMatch = raw.match(/관리비\s*(\d+(?:\.\d+)?)(?:만)?원?/);
  if (maintMatch) {
    const amount = parseFloat(maintMatch[1]);
    return amount >= 1000 ? amount : amount * 10000;
  }
  
  // 숫자만 추출
  const numMatch = raw.match(/(\d+(?:\.\d+)?)(?:만)?원?/);
  if (numMatch) {
    const amount = parseFloat(numMatch[1]);
    return amount >= 1000 ? amount : amount * 10000;
  }
  
  return null;
}

export function parseDate(text: string): string | null {
  const raw = text.trim();
  
  // "2025.07.04" 패턴
  const dateMatch = raw.match(/(\d{4})\.(\d{1,2})\.(\d{1,2})/);
  if (dateMatch) {
    const year = dateMatch[1];
    const month = dateMatch[2].padStart(2, '0');
    const day = dateMatch[3].padStart(2, '0');
    return `${year}-${month}-${day}`;
  }
  
  // "2025-07-04" 패턴
  const isoMatch = raw.match(/(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (isoMatch) {
    return raw;
  }
  
  return null;
}

// 중복 방지를 위한 해시 생성
export function generateHash(text: string): string {
  return createHash('md5').update(text).digest('hex');
}

// URL 정규화
export function normalizeUrl(url: string, baseUrl: string = 'https://dabangapp.com'): string {
  if (url.startsWith('http')) {
    return url;
  }
  if (url.startsWith('/')) {
    return `${baseUrl}${url}`;
  }
  return `${baseUrl}/${url}`;
}

// 안전한 텍스트 추출
export async function safeTextExtract(element: any, selectors: string[]): Promise<string | null> {
  for (const selector of selectors) {
    try {
      const el = await element.locator(selector).first();
      const text = await el.textContent();
      if (text && text.trim()) {
        return text.trim();
      }
    } catch (error) {
      // 다음 선택자 시도
      continue;
    }
  }
  return null;
}

// 안전한 속성 추출
export async function safeAttrExtract(element: any, selector: string, attr: string): Promise<string | null> {
  try {
    const el = await element.locator(selector).first();
    const value = await el.getAttribute(attr);
    return value || null;
  } catch (error) {
    return null;
  }
}

// 타임스탬프 생성
export function getCurrentTimestamp(): string {
  return new Date().toISOString();
}

// 파일명 생성
export function generateFilename(prefix: string = 'dabang_자동수집'): string {
  const now = new Date();
  const dateStr = now.getFullYear().toString() +
    (now.getMonth() + 1).toString().padStart(2, '0') +
    now.getDate().toString().padStart(2, '0');
  const timeStr = now.getHours().toString().padStart(2, '0') +
    now.getMinutes().toString().padStart(2, '0');
  
  return `${prefix}_${dateStr}_${timeStr}`;
}
