@echo off
echo 다방 부동산 크롤러 고급 빌드 스크립트
echo ======================================
echo.

REM Python 가상환경 활성화 (있는 경우)
if exist ".venv\Scripts\activate.bat" (
    echo 가상환경을 활성화합니다...
    call .venv\Scripts\activate.bat
)

REM 필요한 패키지 설치
echo 필요한 패키지를 설치합니다...
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium

REM 빌드 디렉토리 생성
echo 빌드 디렉토리를 생성합니다...
if not exist "build" mkdir build
if not exist "dist" mkdir dist
if not exist "output" mkdir output
if not exist "logs" mkdir logs
if not exist "assets" mkdir assets

REM PyInstaller로 실행 파일 빌드
echo 실행 파일을 빌드합니다...
echo.

echo 1. GUI 실행 파일 빌드 중...
pyinstaller build_config.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Spec 파일 빌드 실패, 기본 설정으로 재시도...
    pyinstaller --onefile --windowed --name "다방크롤러" app/gui.py
    pyinstaller --onefile --name "다방크롤러_CLI" app/cli_collect.py
)

REM 패키지 디렉토리 생성
echo.
echo 패키지 디렉토리를 생성합니다...
if not exist "package" mkdir package
if not exist "package\config" mkdir package\config
if not exist "package\data" mkdir package\data
if not exist "package\logs" mkdir package\logs
if not exist "package\output" mkdir package\output

REM 파일 복사
echo 파일을 복사합니다...
if exist "dist\다방크롤러.exe" copy "dist\다방크롤러.exe" "package\"
if exist "dist\다방크롤러_CLI.exe" copy "dist\다방크롤러_CLI.exe" "package\"
if exist "config\settings.toml" copy "config\settings.toml" "package\config\"
if exist "data\regions_kr.json" copy "data\regions_kr.json" "package\data\"
if exist "README.md" copy "README.md" "package\"
if exist "LICENSE" copy "LICENSE" "package\"

REM 실행 배치 파일 생성
echo 실행 배치 파일을 생성합니다...
(
echo @echo off
echo echo 다방 부동산 크롤러를 시작합니다...
echo echo.
echo echo 1. GUI 모드 ^(그래픽 인터페이스^)
echo echo 2. CLI 모드 ^(명령줄 인터페이스^)
echo echo 3. 설정 파일 편집
echo echo 4. 로그 확인
echo echo.
echo set /p choice="선택하세요 ^(1-4^): "
echo if "%%choice%%"=="1" ^(
echo     start "" "다방크롤러.exe"
echo ^) else if "%%choice%%"=="2" ^(
echo     echo CLI 모드 사용법:
echo     echo 다방크롤러_CLI.exe --region "지역명" --type "매물타입" --limit 개수
echo     echo.
echo     echo 예시:
echo     echo 다방크롤러_CLI.exe --region "서울 강남" --type "원룸" --limit 10
echo     echo.
echo     pause
echo ^) else if "%%choice%%"=="3" ^(
echo     notepad config\settings.toml
echo ^) else if "%%choice%%"=="4" ^(
echo     if exist "logs\*.log" ^(
echo         start "" logs
echo     ^) else ^(
echo         echo 로그 파일이 없습니다.
echo         pause
echo     ^)
echo ^) else ^(
echo     echo 잘못된 선택입니다.
echo     pause
echo ^)
) > package\다방크롤러_실행.bat

REM 고급 사용법 파일 생성
echo 고급 사용법 파일을 생성합니다...
(
echo 다방 부동산 크롤러 고급 사용법
echo ==============================
echo.
echo 1. GUI 모드
echo    - 다방크롤러.exe를 실행
echo    - 그래픽 인터페이스를 통해 설정
echo.
echo 2. CLI 모드
echo    - 다방크롤러_CLI.exe --region "지역명" --type "매물타입" --limit 개수
echo    - 예시: 다방크롤러_CLI.exe --region "부산 기장" --type "오피스텔" --limit 50
echo.
echo 3. 매물 타입 옵션
echo    - 원룸, 투룸, 오피스텔, 아파트, 주택/빌라
echo.
echo 4. 설정 파일 편집
echo    - config\settings.toml 파일을 텍스트 에디터로 편집
echo    - 기본값, 브라우저 설정, 경로 설정 등
echo.
echo 5. 로그 확인
echo    - logs 폴더의 로그 파일 확인
echo    - 오류 발생 시 디버깅에 활용
echo.
echo 6. 출력 파일
echo    - output 폴더에 Excel 파일로 저장
echo    - 자동으로 중복 제거 및 정렬
echo.
echo 7. 문제 해결
echo    - 인터넷 연결 확인
echo    - Windows Defender 예외 처리
echo    - 관리자 권한으로 실행
echo.
echo 8. 라이선스
echo    - MIT 라이선스 하에 배포
echo    - 교육 및 개인 사용 목적으로만 사용
echo    - 상업적 사용 시 다방 이용약관 확인
) > package\고급사용법.txt

REM ZIP 파일 생성
echo ZIP 파일을 생성합니다...
powershell -Command "Compress-Archive -Path 'package\*' -DestinationPath '다방크롤러_Windows_Advanced.zip' -Force"

REM 설치 프로그램 생성 (NSIS가 설치된 경우)
echo.
echo NSIS 설치 프로그램 생성을 시도합니다...
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    echo NSIS를 찾았습니다. 설치 프로그램을 생성합니다...
    "C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
    if %ERRORLEVEL% EQU 0 (
        echo 설치 프로그램 생성 완료: 다방크롤러_Setup_v1.0.0.exe
    ) else (
        echo NSIS 빌드 실패
    )
) else (
    echo NSIS가 설치되지 않았습니다. ZIP 파일만 생성됩니다.
    echo NSIS 설치: https://nsis.sourceforge.io/Download
)

echo.
echo ======================================
echo 고급 빌드 완료!
echo.
echo 생성된 파일들:
echo - dist\다방크롤러.exe ^(GUI 모드^)
echo - dist\다방크롤러_CLI.exe ^(CLI 모드^)
echo - package\ ^(고급 패키지 폴더^)
echo - 다방크롤러_Windows_Advanced.zip ^(고급 배포용 ZIP^)
echo - 고급사용법.txt ^(상세 사용법^)
echo.
echo 테스트하려면 package 폴더의 다방크롤러_실행.bat를 실행하세요.
echo.
pause
