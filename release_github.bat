@echo off
chcp 65001 >nul
echo ========================================
echo    GitHub 릴리즈 생성 스크립트
echo ========================================
echo.

echo 1. 버전 태그 입력...
set /p version="릴리즈 버전을 입력하세요 (예: v2.0.0): "
echo.

echo 2. Git 태그 생성...
git tag -a %version% -m "Windows build %version%"
echo.

echo 3. 태그 푸시...
git push origin %version%
echo.

echo 4. GitHub CLI 릴리즈 생성...
gh release create %version% 다방크롤러_Windows_manual.zip ^
  --title "다방크롤러 Windows %version%" ^
  --notes "## 🚀 다방크롤러 Windows %version% 릴리즈

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
- **TypeScript 파일 참고로 최적화된 선택자**

### 🔧 설치 방법
1. ZIP 파일 다운로드 및 압축 해제
2. `다방크롤러_실행.bat` 실행
3. GUI 또는 CLI 모드 선택

### 📋 지원하는 매물 타입
- 원룸, 투룸, 아파트, 주택/빌라, 오피스텔

### 💻 CLI 사용법
```bash
다방크롤러_CLI.exe --region \"서울 강남\" --type \"원룸\" --limit 10
다방크롤러_CLI.exe --region \"부산 해운대\" --type \"아파트\" --limit 20
```

### 🔧 시스템 요구사항
- Windows 10/11 (64비트)
- 인터넷 연결
- 최소 4GB RAM
- Python 3.12 (자동 설치됨)

### 📝 변경사항
- %version%: TypeScript 파일 참고로 CSS 선택자 개선
- %version%: 상세 페이지 기반 정확한 정보 추출
- %version%: 중복 제거 비활성화로 모든 데이터 수집
- %version%: 주소, 부동산, 관리비, 등록일 필드 파싱 개선
- %version%: 바이러스 백신 오탐 방지 최적화
- %version%: Google Drive 친화적 패키징

### 🛡️ 보안 정보
- UPX 압축 비활성화로 바이러스 백신 오탐 방지
- SHA256 해시로 파일 무결성 검증
- 완전한 소스 코드 공개 (GitHub)
- 투명한 빌드 프로세스

### 📄 라이선스
이 소프트웨어는 교육 및 개인 사용 목적으로만 사용하세요.
상업적 사용 시 다방의 이용약관을 확인하세요."
echo.

echo 5. 릴리즈 완료!
echo.
echo 생성된 릴리즈:
echo - 버전: %version%
echo - 파일: 다방크롤러_Windows_manual.zip
echo - GitHub: https://github.com/hsm-9946/dabang-crawler/releases
echo.
pause
