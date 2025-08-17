## 다방 매물 수집기 (Playwright 버전)

### 요구 흐름
- 실행(.exe) → [수집 시작] → 자동 수집/저장 → 저장 파일 자동 열기

### 설치

#### Python 버전 (기존)
```
python -m venv .venv
. .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
playwright install chromium
```

#### Node.js 버전 (새로운 TypeScript 스크립트)
```
npm install
npx playwright install chromium
```

### 개발 실행

#### Python GUI 버전
```
python app/main.py
```

#### Node.js CLI 버전
```
npx tsx scripts/dabang_scrape.ts --type "오피스텔" --region "부산광역시 기장군 기장읍" --limit 200
```

### 옵션
- GUI에서 지역, 종류, 가격 범위, 최대건수/페이지수, 저장경로 선택 가능
- Headless 기본, 체크 해제 시 창 표시
- CLI 버전: --type (아파트|주택/빌라|오피스텔|원룸), --region, --limit 지원

### 빌드(Windows .exe)

#### 로컬 빌드
```bash
# Windows에서 실행
build_local.bat

# 또는 수동 빌드
pip install pyinstaller
pyinstaller build_config.spec
```

#### GitHub Actions 자동 빌드
1. GitHub에 코드 푸시
2. Actions 탭에서 "Build Windows Executable" 워크플로우 확인
3. 빌드 완료 후 Artifacts에서 다운로드
4. 태그 생성 시 자동 릴리즈 생성

#### 빌드 결과물
- `다방크롤러.exe` (GUI 모드)
- `다방크롤러_CLI.exe` (CLI 모드)
- `다방크롤러_실행.bat` (실행 스크립트)
- 설정 파일 및 데이터 파일 포함

### 출력
- 파일명: `dabang_자동수집_YYYYMMDD_HHMM.csv`, `.xlsx`
- 시트: "다방매물"
- 컬럼: source, type, title, deposit, rent, maintenance, realtor, address, posted_at, detail_url, scraped_at

### 문제 해결
- 0건 발생: 헤드리스 해제 후 재시도, 지역 키워드 구체화, 페이지 수/스크롤 증가
- SSL/인증서 오류: `playwright install chromium` 재실행
- 차단/캡차: 속도 늦추기, 시간차 두고 재실행

### 체크리스트
- [ ] GUI에서 [수집 시작]으로 N건 이상 수집되어 엑셀 생성
- [ ] CLI에서 --region, --type, --limit 옵션으로 수집 가능
- [ ] 필수 컬럼 채워짐(없으면 빈칸 허용)
- [ ] 중복 제거 동작
- [ ] 예외 시 GUI와 로그 파일에 메시지 출력
- [ ] settings.toml 값 수정 후 재실행 가능
- [ ] headless/on-off 정상 동작


