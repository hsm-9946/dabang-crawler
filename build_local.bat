@echo off
echo 다방 부동산 크롤러 Windows 빌드 스크립트
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
pip install pyinstaller

REM 빌드 디렉토리 생성
echo 빌드 디렉토리를 생성합니다...
if not exist "build" mkdir build
if not exist "dist" mkdir dist

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
copy "dist\다방크롤러.exe" "package\"
copy "dist\다방크롤러_CLI.exe" "package\"
copy "config\settings.toml" "package\config\"
copy "data\regions_kr.json" "package\data\"
copy "README.md" "package\"

REM 실행 배치 파일 생성
echo 실행 배치 파일을 생성합니다...
(
echo @echo off
echo echo 다방 부동산 크롤러를 시작합니다...
echo echo.
echo echo 1. GUI 모드 ^(그래픽 인터페이스^)
echo echo 2. CLI 모드 ^(명령줄 인터페이스^)
echo echo.
echo set /p choice="선택하세요 ^(1 또는 2^): "
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
echo ^) else ^(
echo     echo 잘못된 선택입니다.
echo     pause
echo ^)
) > package\다방크롤러_실행.bat

REM ZIP 파일 생성
echo ZIP 파일을 생성합니다...
powershell -Command "Compress-Archive -Path 'package\*' -DestinationPath '다방크롤러_Windows_local.zip' -Force"

echo.
echo ======================================
echo 빌드 완료!
echo.
echo 생성된 파일들:
echo - dist\다방크롤러.exe ^(GUI 모드^)
echo - dist\다방크롤러_CLI.exe ^(CLI 모드^)
echo - package\ ^(패키지 폴더^)
echo - 다방크롤러_Windows_local.zip ^(배포용 ZIP^)
echo.
echo 테스트하려면 package 폴더의 다방크롤러_실행.bat를 실행하세요.
echo.
pause
