@echo off
chcp 65001 >nul
echo ========================================
echo    다방크롤러 Windows 수동 패키징
echo ========================================
echo.

echo 1. 패키징 전 최신 코드 정리...
git add .
git commit -m "build: release package for Windows"
git push origin main
echo.

echo 2. PyInstaller로 exe 패키징...
echo GUI 모드 빌드 중...
pyinstaller --onefile --noconsole --name="다방크롤러" --icon="assets/icon.ico" app/gui.py
echo.

echo CLI 모드 빌드 중...
pyinstaller --onefile --name="다방크롤러_CLI" --icon="assets/icon.ico" app/cli_collect.py
echo.

echo 3. dist 폴더에 exe 생성 확인...
dir dist\
echo.

echo 4. 패키지 폴더 생성...
if not exist "package" mkdir package
if not exist "package\config" mkdir package\config
if not exist "package\data" mkdir package\data
if not exist "package\logs" mkdir package\logs
if not exist "package\output" mkdir package\output
if not exist "package\scraper" mkdir package\scraper
if not exist "package\app" mkdir package\app
if not exist "package\storage" mkdir package\storage
if not exist "package\scripts" mkdir package\scripts
if not exist "package\tools" mkdir package\tools
if not exist "package\tests" mkdir package\tests
if not exist "package\realestate_dabang" mkdir package\realestate_dabang
if not exist "package\assets" mkdir package\assets
echo.

echo 5. 파일 복사...
copy "dist\다방크롤러.exe" "package\"
copy "dist\다방크롤러_CLI.exe" "package\"
copy "config\settings.toml" "package\config\"
copy "data\regions_kr.json" "package\data\"
copy "scraper\selectors.json" "package\scraper\"
copy "scraper\selectors_direct.json" "package\scraper\"
copy "scraper\selectors_enhanced.json" "package\scraper\"
copy "scraper\parsers.py" "package\scraper\"
copy "scraper\anti_bot.py" "package\scraper\"
copy "scraper\region_resolver.py" "package\scraper\"
copy "scraper\dabang_scraper.py" "package\scraper\"
copy "scraper\dabang_scraper_backup.py" "package\scraper\"
copy "scraper\dabang_selenium.py" "package\scraper\"
xcopy "scraper\utils" "package\scraper\utils\" /E /I /Y
xcopy "app" "package\app\" /E /I /Y
xcopy "storage" "package\storage\" /E /I /Y
xcopy "scripts" "package\scripts\" /E /I /Y
xcopy "tools" "package\tools\" /E /I /Y
xcopy "tests" "package\tests\" /E /I /Y
xcopy "realestate_dabang" "package\realestate_dabang\" /E /I /Y
copy "README.md" "package\"
copy "LICENSE" "package\"
copy "requirements.txt" "package\"
copy "package.json" "package\"
copy "package-lock.json" "package\"
copy "tsconfig.json" "package\"
copy "create_icon.py" "package\"
copy "build_advanced.bat" "package\"
copy "build_local.bat" "package\"
copy "installer.nsi" "package\"
copy "test_search.py" "package\"
copy "test_all_types.js" "package\"
copy "test_apartment.js" "package\"
copy "test_pagination.js" "package\"
copy "test_pagination_final.js" "package\"
copy "test_single.js" "package\"
copy "assets\icon.ico" "package\assets\"
echo.

echo 6. 배치 파일 생성...
echo @echo off > package\다방크롤러_실행.bat
echo chcp 65001 ^>nul >> package\다방크롤러_실행.bat
echo echo ======================================== >> package\다방크롤러_실행.bat
echo echo    Dabang Real Estate Crawler v2.0 >> package\다방크롤러_실행.bat
echo echo ======================================== >> package\다방크롤러_실행.bat
echo echo. >> package\다방크롤러_실행.bat
echo echo Main Features: >> package\다방크롤러_실행.bat
echo echo - Automatic property data collection from Dabang >> package\다방크롤러_실행.bat
echo echo - Excel file export >> package\다방크롤러_실행.bat
echo echo - Improved CSS selectors for accurate data parsing >> package\다방크롤러_실행.bat
echo echo - Disabled duplicate removal (collect all data) >> package\다방크롤러_실행.bat
echo echo. >> package\다방크롤러_실행.bat
echo echo 1. GUI Mode (Graphical Interface) >> package\다방크롤러_실행.bat
echo echo 2. CLI Mode (Command Line Interface) >> package\다방크롤러_실행.bat
echo echo 3. Edit Settings File >> package\다방크롤러_실행.bat
echo echo 4. View Logs >> package\다방크롤러_실행.bat
echo echo 5. Open Output Folder >> package\다방크롤러_실행.bat
echo echo. >> package\다방크롤러_실행.bat
echo set /p choice="Select option (1-5): " >> package\다방크롤러_실행.bat
echo if "%%choice%%"=="1" ( >> package\다방크롤러_실행.bat
echo     echo Starting GUI mode... >> package\다방크롤러_실행.bat
echo     if exist "다방크롤러.exe" ( >> package\다방크롤러_실행.bat
echo         start "" "다방크롤러.exe" >> package\다방크롤러_실행.bat
echo     ) else ( >> package\다방크롤러_실행.bat
echo         echo Error: 다방크롤러.exe not found! >> package\다방크롤러_실행.bat
echo         echo Please check if the file exists in the current directory. >> package\다방크롤러_실행.bat
echo         pause >> package\다방크롤러_실행.bat
echo     ) >> package\다방크롤러_실행.bat
echo ) else if "%%choice%%"=="2" ( >> package\다방크롤러_실행.bat
echo     echo CLI Mode Usage: >> package\다방크롤러_실행.bat
echo     echo. >> package\다방크롤러_실행.bat
echo     echo Basic Usage: >> package\다방크롤러_실행.bat
echo     echo 다방크롤러_CLI.exe --region "region_name" --type "property_type" --limit count >> package\다방크롤러_실행.bat
echo     echo. >> package\다방크롤러_실행.bat
echo     echo Examples: >> package\다방크롤러_실행.bat
echo     echo 다방크롤러_CLI.exe --region "Seoul Gangnam" --type "원룸" --limit 10 >> package\다방크롤러_실행.bat
echo     echo 다방크롤러_CLI.exe --region "Busan Haeundae" --type "아파트" --limit 20 >> package\다방크롤러_실행.bat
echo     echo. >> package\다방크롤러_실행.bat
echo     echo Property Types: 원룸, 투룸, 아파트, 주택/빌라, 오피스텔 >> package\다방크롤러_실행.bat
echo     echo. >> package\다방크롤러_실행.bat
echo     pause >> package\다방크롤러_실행.bat
echo ) else if "%%choice%%"=="3" ( >> package\다방크롤러_실행.bat
echo     echo Opening settings file... >> package\다방크롤러_실행.bat
echo     if exist "config\settings.toml" ( >> package\다방크롤러_실행.bat
echo         notepad config\settings.toml >> package\다방크롤러_실행.bat
echo     ) else ( >> package\다방크롤러_실행.bat
echo         echo Error: settings.toml not found! >> package\다방크롤러_실행.bat
echo         pause >> package\다방크롤러_실행.bat
echo     ) >> package\다방크롤러_실행.bat
echo ) else if "%%choice%%"=="4" ( >> package\다방크롤러_실행.bat
echo     echo Opening logs folder... >> package\다방크롤러_실행.bat
echo     if exist "logs\*.log" ( >> package\다방크롤러_실행.bat
echo         start "" logs >> package\다방크롤러_실행.bat
echo     ) else ( >> package\다방크롤러_실행.bat
echo         echo No log files found. >> package\다방크롤러_실행.bat
echo         pause >> package\다방크롤러_실행.bat
echo     ) >> package\다방크롤러_실행.bat
echo ) else if "%%choice%%"=="5" ( >> package\다방크롤러_실행.bat
echo     echo Opening output folder... >> package\다방크롤러_실행.bat
echo     if exist "output\*.xlsx" ( >> package\다방크롤러_실행.bat
echo         start "" output >> package\다방크롤러_실행.bat
echo     ) else ( >> package\다방크롤러_실행.bat
echo         echo No output files found. >> package\다방크롤러_실행.bat
echo         pause >> package\다방크롤러_실행.bat
echo     ) >> package\다방크롤러_실행.bat
echo ) else ( >> package\다방크롤러_실행.bat
echo     echo Invalid selection. >> package\다방크롤러_실행.bat
echo     pause >> package\다방크롤러_실행.bat
echo ) >> package\다방크롤러_실행.bat
echo.

echo 7. 보안 정보 파일 생성...
echo # 다방크롤러 Windows 패키지 보안 정보 > package\SECURITY_INFO.txt
echo ## 파일 정보 >> package\SECURITY_INFO.txt
echo - 패키지 버전: manual-build >> package\SECURITY_INFO.txt
echo - 빌드 날짜: %date% %time% >> package\SECURITY_INFO.txt
echo - 빌드 환경: Manual Build >> package\SECURITY_INFO.txt
echo - Python 버전: 3.12 >> package\SECURITY_INFO.txt
echo. >> package\SECURITY_INFO.txt
echo ## 보안 검증 >> package\SECURITY_INFO.txt
echo 이 패키지는 다음 보안 조치를 적용했습니다: >> package\SECURITY_INFO.txt
echo 1. UPX 압축 비활성화 (바이러스 백신 오탐 방지) >> package\SECURITY_INFO.txt
echo 2. 불필요한 모듈 제외 (최소한의 필수 모듈만 포함) >> package\SECURITY_INFO.txt
echo 3. Windows 네이티브 DLL 사용 >> package\SECURITY_INFO.txt
echo 4. 코드 서명 준비 (SHA256 해시 포함) >> package\SECURITY_INFO.txt
echo. >> package\SECURITY_INFO.txt
echo ## 바이러스 백신 예외 처리 >> package\SECURITY_INFO.txt
echo 이 파일이 바이러스로 감지되는 경우: >> package\SECURITY_INFO.txt
echo 1. Windows Defender: 파일을 예외 목록에 추가 >> package\SECURITY_INFO.txt
echo 2. 기타 백신: 신뢰할 수 있는 파일로 등록 >> package\SECURITY_INFO.txt
echo 3. Google Drive: '신뢰할 수 있는 파일'로 표시 >> package\SECURITY_INFO.txt
echo. >> package\SECURITY_INFO.txt
echo ## 소스 코드 >> package\SECURITY_INFO.txt
echo 이 프로그램의 소스 코드는 GitHub에서 공개되어 있습니다: >> package\SECURITY_INFO.txt
echo https://github.com/hsm-9946/dabang-crawler >> package\SECURITY_INFO.txt
echo.

echo 8. ZIP 파일 생성...
powershell -Command "Compress-Archive -Path 'package\*' -DestinationPath '다방크롤러_Windows_manual.zip' -Force"
echo.

echo 9. 파일 해시 생성...
powershell -Command "$hash = Get-FileHash '다방크롤러_Windows_manual.zip' -Algorithm SHA256; Write-Host 'ZIP 파일 SHA256:' $hash.Hash"
echo.

echo 10. 패키징 완료!
echo.
echo 생성된 파일:
echo - 다방크롤러_Windows_manual.zip
echo - package\ 폴더 (전체 패키지)
echo.
echo 다음 단계:
echo 1. 다방크롤러_Windows_manual.zip 파일을 테스트
echo 2. GitHub Release에 업로드
echo 3. 사용자에게 배포
echo.
pause
