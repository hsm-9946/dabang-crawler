## 다방(Dabang) 전용 부동산 매물 수집기

이 프로젝트는 다방 웹사이트에서 지번이 화면에 노출된 매물만을 대상으로 조건 필터를 적용하여 수집하고, Excel(.xlsx)로 저장하는 자동화 도구입니다. GUI(customtkinter)와 CLI를 모두 제공하며, 헤드리스 모드 on/off, 로그 저장, CAPTCHA 발생 시 일시정지/재개를 지원합니다.

### 주요 기능
- 지번 노출 매물만 수집: 주소 텍스트에서 지번 패턴만 추출하여 저장
- 수집 항목: lot_address, price, property_type, maintenance_fee, url, source='dabang', collected_at
- 조건 필터: 지역 키워드, 가격 최소/최대, 유형 리스트(원룸/투룸/오피스텔/아파트 등)
- 저장: Excel(.xlsx, UTF-8), 열 순서 고정, 중복 제거 옵션(url, lot_address+price)
- GUI(customtkinter): 입력 필드, 진행 로그, 남은/완료 건수, 저장 경로 선택, 헤드리스/중복제거 토글, CAPTCHA 재개 버튼
- CLI: 같은 매개변수로 무인 실행 가능
- 브라우저: Selenium + undetected-chromedriver, ko-KR, 성능 최적화 옵션
- 로깅: loguru, 콘솔+파일 동시 로깅(logs/ 일자별 파일)
- 안정화: 랜덤 지연, 명시적 wait, 재시도 데코레이터, 무한스크롤/페이지네이션 대응

### 폴더 구조

```
realestate_dabang/
 ├─ app/
 │   ├─ gui_app.py                 # GUI 메인(실행 진입점)
 │   ├─ main_runner.py             # GUI 없이 CLI로도 동작 가능
 │   ├─ crawler/
 │   │   ├─ dabang_crawler.py      # 핵심 크롤러
 │   │   └─ selectors.py           # 선택자/텍스트 패턴 상수
 │   ├─ core/
 │   │   ├─ models.py              # Pydantic 모델(Inputs, Record)
 │   │   ├─ filters.py             # 조건 필터 로직
 │   │   ├─ exporter.py            # DataFrame → Excel 저장
+ │   │   ├─ browser.py             # 드라이버 초기화/Wait 유틸
 │   │   └─ throttling.py          # 랜덤 슬립, 재시도
 │   ├─ utils/
 │   │   ├─ text.py                # 지번/가격/관리비 파싱
 │   │   └─ time.py                # 타임스탬프/파일명
 │   └─ config.py                  # 기본 설정
 ├─ tests/
 │   ├─ test_filters.py
 │   ├─ test_text_parse.py
 │   └─ test_exporter.py
 ├─ output/
 ├─ logs/
 ├─ requirements.txt
 ├─ README.md
 └─ LICENSE (MIT)
```

### 설치
1) Python 3.10 이상 설치
2) 가상환경 생성 및 활성화
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```
3) 의존성 설치
```
pip install -r requirements.txt
```

선택: `.env` 파일로 기본 설정을 조정할 수 있습니다.

```
# .env 예시
HEADLESS=true
TIMEOUT_SECONDS=20
OUTPUT_DIR=output
LOG_DIR=logs
```

### 실행

#### GUI 실행
```
python -m realestate_dabang.app.gui_app
```

필드에 지역/가격/유형을 입력 후 [수집 시작]을 누르면 진행 로그와 함께 작업이 시작됩니다. 진행 중 CAPTCHA 감지 시 일시정지되며, 브라우저에서 직접 인증 후 [재개] 버튼을 눌러 계속합니다.

#### CLI 실행
```
python -m realestate_dabang.app.main_runner \
  --region "부산 기장" \
  --price-min 0 \
  --price-max 2000000 \
  --types 원룸 \
  --headless true \
  --dedupe true
```

복수 유형은 `--types 원룸 --types 투룸` 처럼 여러 번 지정합니다.

### 빌드(.exe)
PyInstaller로 단일 실행 파일을 만들 수 있습니다.

```
pip install pyinstaller
pyinstaller -F -w -n dabang_crawler_gui realestate_dabang/app/gui_app.py
```

- `-w`: 콘솔 창 숨김(Windows)
- 드라이버(Chrome) 존재가 필요합니다. 첫 실행 시 `undetected-chromedriver`가 자동 관리합니다.

### 자주 묻는 질문(FAQ)
- CAPTCHA가 자주 뜨는 경우: 속도를 더 늦추고(설정의 랜덤 지연 상향), 헤드리스 off, 작업 중간에 충분한 대기 시간을 주세요. GUI에서는 CAPTCHA 감지 시 자동 일시정지되며 인증 후 [재개]가 가능합니다.
- 요소를 못 찾습니다: 셀렉터가 변경되었을 수 있습니다. `app/crawler/selectors.py`의 후보 셀렉터를 추가/수정하고, 실패 시 BS4 폴백이 동작하도록 되어 있습니다.
- 수집 결과가 비어 있습니다: 지역 키워드가 모호하거나 결과가 적을 수 있습니다. 키워드를 더 구체화해보세요.

### 문제 해결 가이드(Driver/Headless/Diagnostics)

- Chrome/Driver 자동 동기화: 로컬 Chrome 메이저 버전을 감지해 `undetected_chromedriver.Chrome(version_main=LOCAL_MAJOR)`로 맞춥니다. 실패 시 환경변수 `CHROME_VERSION_MAIN=138` 처럼 설정해 재시도하세요.
- Headless에서 0건: 헤드리스에서 카드가 0개면 자동으로 non-headless로 1회 재시도합니다. 또한 진단 모드를 켜면 `debug/`에 화면 스크린샷(`empty_list_*.png`)과 HTML(`empty_list_*.html`)을 저장합니다.
- 진단 모드 사용: GUI 체크박스 또는 CLI `--diagnostics true`로 켜며, 0건/이상 징후 시 자동 덤프를 남깁니다.

### 샘플 실행 로그 (요약)
```
2025-01-01 10:00:00 | INFO | 브라우저 초기화(headless=True)
2025-01-01 10:00:02 | INFO | 다방 메인 진입 및 검색: 부산 기장
2025-01-01 10:00:06 | INFO | 결과 페이지 로딩 완료. 스크롤 시작
2025-01-01 10:00:30 | INFO | 카드 120개 수집됨. 세부 파싱 시작
2025-01-01 10:00:45 | WARNING | 일부 카드에서 주소 파싱 실패 → BS4 폴백 사용
2025-01-01 10:01:10 | INFO | 필터 적용 후 64건 유지
2025-01-01 10:01:11 | INFO | 중복 제거 후 58건 → Excel 저장(output/dabang_부산_기장_20250101_100111.xlsx)
2025-01-01 10:01:11 | SUCCESS | 완료
```

### 수용 기준 체크리스트
- GUI에서 지역="부산 기장", 가격 0~200만, 유형=원룸 선택 후 수집 시작 시 페이지 탐색/스크롤과 엑셀 저장이 정상 동작
- CAPTCHA 감지 시 GUI가 정지/안내 후 재개
- CLI 모드에서도 동일 매개변수로 xlsx 생성
- 주요 함수에 타입힌트/주석/에러 메시지 포함

### 라이선스
MIT License. 자세한 내용은 `LICENSE` 참조.


