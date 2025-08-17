# 🛠️ 다방크롤러 Windows 수동 빌드 가이드

## 📋 사전 요구사항

### 1. Python 환경
```bash
# Python 3.12 설치 확인
python --version

# 필요한 패키지 설치
pip install -r requirements.txt
pip install pyinstaller
```

### 2. GitHub CLI 설치 (릴리즈용)
```bash
# Windows에서 설치
winget install GitHub.cli

# 또는 직접 다운로드
# https://cli.github.com/
```

### 3. 로그인
```bash
# GitHub CLI 로그인
gh auth login
```

## 🚀 수동 빌드 방법

### 방법 1: 자동화 스크립트 사용 (권장)

#### 1단계: 패키징 실행
```bash
# Windows에서 실행
build_manual.bat
```

#### 2단계: GitHub 릴리즈 생성
```bash
# 릴리즈 생성
release_github.bat
```

### 방법 2: 수동 명령어 실행

#### 1단계: 코드 정리
```bash
git add .
git commit -m "build: release package for Windows"
git push origin main
```

#### 2단계: PyInstaller 빌드
```bash
# GUI 모드 빌드
pyinstaller --onefile --noconsole --name="다방크롤러" --icon="assets/icon.ico" app/gui.py

# CLI 모드 빌드
pyinstaller --onefile --name="다방크롤러_CLI" --icon="assets/icon.ico" app/cli_collect.py
```

#### 3단계: 패키지 폴더 생성
```bash
# 폴더 구조 생성
mkdir package
mkdir package\config
mkdir package\data
mkdir package\logs
mkdir package\output
mkdir package\scraper
mkdir package\app
mkdir package\storage
mkdir package\scripts
mkdir package\tools
mkdir package\tests
mkdir package\realestate_dabang
mkdir package\assets
```

#### 4단계: 파일 복사
```bash
# 실행 파일 복사
copy dist\다방크롤러.exe package\
copy dist\다방크롤러_CLI.exe package\

# 설정 파일 복사
copy config\settings.toml package\config\
copy data\regions_kr.json package\data\

# 스크래퍼 파일 복사
copy scraper\*.json package\scraper\
copy scraper\*.py package\scraper\
xcopy scraper\utils package\scraper\utils\ /E /I /Y

# 앱 파일 복사
xcopy app package\app\ /E /I /Y
xcopy storage package\storage\ /E /I /Y
xcopy scripts package\scripts\ /E /I /Y
xcopy tools package\tools\ /E /I /Y
xcopy tests package\tests\ /E /I /Y
xcopy realestate_dabang package\realestate_dabang\ /E /I /Y

# 루트 파일 복사
copy README.md package\
copy LICENSE package\
copy requirements.txt package\
copy package.json package\
copy package-lock.json package\
copy tsconfig.json package\
copy *.py package\
copy *.bat package\
copy *.js package\
copy assets\icon.ico package\assets\
```

#### 5단계: ZIP 파일 생성
```bash
# PowerShell 사용
powershell -Command "Compress-Archive -Path 'package\*' -DestinationPath '다방크롤러_Windows_manual.zip' -Force"
```

#### 6단계: GitHub 릴리즈 생성
```bash
# 태그 생성
git tag -a v2.0.0 -m "Windows build v2.0.0"
git push origin v2.0.0

# 릴리즈 생성
gh release create v2.0.0 다방크롤러_Windows_manual.zip \
  --title "다방크롤러 Windows v2.0.0" \
  --notes "Windows 실행 파일 배포 버전"
```

## 🔧 빌드 옵션 설명

### PyInstaller 옵션
- `--onefile`: 단일 실행 파일 생성
- `--noconsole`: GUI 모드에서 콘솔창 숨김
- `--name`: 실행 파일 이름 지정
- `--icon`: 아이콘 파일 지정

### 추가 옵션 (필요시)
- `--debug`: 디버그 정보 포함
- `--strip`: 디버그 심볼 제거
- `--upx-dir`: UPX 압축 사용 (바이러스 백신 오탐 가능성)

## 🛡️ 보안 고려사항

### 바이러스 백신 오탐 방지
1. **UPX 압축 비활성화**: `--upx-dir` 옵션 사용하지 않음
2. **불필요한 모듈 제외**: 최소한의 필수 모듈만 포함
3. **Windows 네이티브 DLL 사용**: 안정성 향상

### 파일 무결성 검증
```bash
# SHA256 해시 생성
powershell -Command "Get-FileHash '다방크롤러_Windows_manual.zip' -Algorithm SHA256"
```

## 📦 패키지 구조

```
다방크롤러_Windows_manual.zip
├── 다방크롤러.exe (GUI 모드)
├── 다방크롤러_CLI.exe (CLI 모드)
├── 다방크롤러_실행.bat (실행 스크립트)
├── SECURITY_INFO.txt (보안 정보)
├── ANTIVIRUS_GUIDE.txt (바이러스 백신 가이드)
├── README_Windows.txt (사용법 가이드)
├── config/ (설정 파일)
├── data/ (데이터 파일)
├── scraper/ (스크래퍼 모듈)
├── app/ (앱 모듈)
├── storage/ (저장 모듈)
├── scripts/ (TypeScript 파일)
├── tools/ (도구 파일)
├── tests/ (테스트 파일)
├── realestate_dabang/ (실제 부동산 모듈)
└── assets/ (아이콘 등)
```

## 🚨 문제 해결

### 빌드 실패
1. **Python 버전 확인**: Python 3.12 권장
2. **의존성 설치**: `pip install -r requirements.txt`
3. **PyInstaller 재설치**: `pip install --upgrade pyinstaller`

### 실행 파일 오류
1. **파일 경로 확인**: 모든 필요한 파일이 포함되었는지 확인
2. **권한 문제**: 관리자 권한으로 실행
3. **바이러스 백신**: 예외 목록에 추가

### GitHub CLI 오류
1. **로그인 확인**: `gh auth status`
2. **토큰 설정**: GitHub Personal Access Token 필요
3. **권한 확인**: 저장소에 대한 쓰기 권한 필요

## 📝 릴리즈 노트 템플릿

```markdown
## 🚀 다방크롤러 Windows v2.0.0 릴리즈

### 📦 다운로드
- GUI 모드: `다방크롤러.exe`
- CLI 모드: `다방크롤러_CLI.exe`

### ✨ 주요 기능
- 다방 부동산 매물 자동 수집
- Excel 파일로 데이터 저장
- GUI 및 CLI 모드 지원
- 지역별, 매물 타입별 필터링
- **개선된 CSS 선택자로 정확한 데이터 파싱**
- **중복 제거 비활성화 (모든 데이터 수집)**

### 🔧 설치 방법
1. ZIP 파일 다운로드 및 압축 해제
2. `다방크롤러_실행.bat` 실행
3. GUI 또는 CLI 모드 선택

### 📋 지원하는 매물 타입
- 원룸, 투룸, 아파트, 주택/빌라, 오피스텔

### 💻 CLI 사용법
```bash
다방크롤러_CLI.exe --region "서울 강남" --type "원룸" --limit 10
다방크롤러_CLI.exe --region "부산 해운대" --type "아파트" --limit 20
```

### 🔧 시스템 요구사항
- Windows 10/11 (64비트)
- 인터넷 연결
- 최소 4GB RAM
- Python 3.12 (자동 설치됨)

### 📝 변경사항
- v2.0.0: TypeScript 파일 참고로 CSS 선택자 개선
- v2.0.0: 상세 페이지 기반 정확한 정보 추출
- v2.0.0: 중복 제거 비활성화로 모든 데이터 수집
- v2.0.0: 주소, 부동산, 관리비, 등록일 필드 파싱 개선
- v2.0.0: 바이러스 백신 오탐 방지 최적화
- v2.0.0: Google Drive 친화적 패키징

### 🛡️ 보안 정보
- UPX 압축 비활성화로 바이러스 백신 오탐 방지
- SHA256 해시로 파일 무결성 검증
- 완전한 소스 코드 공개 (GitHub)
- 투명한 빌드 프로세스

### 📄 라이선스
이 소프트웨어는 교육 및 개인 사용 목적으로만 사용하세요.
상업적 사용 시 다방의 이용약관을 확인하세요.
```

## 🎯 최적화 팁

### 빌드 시간 단축
1. **캐시 활용**: `--workpath` 옵션으로 작업 디렉토리 지정
2. **병렬 처리**: `--jobs` 옵션으로 병렬 빌드
3. **불필요한 파일 제외**: `--exclude-module` 옵션 사용

### 파일 크기 최적화
1. **UPX 압축**: 바이러스 백신 오탐 가능성 있음
2. **불필요한 모듈 제외**: 최소한의 필수 모듈만 포함
3. **디버그 정보 제거**: `--strip` 옵션 사용

### 안정성 향상
1. **Windows 호환성**: `--win-private-assemblies` 옵션
2. **에러 처리**: 적절한 예외 처리 추가
3. **로깅**: 상세한 로그 파일 생성
