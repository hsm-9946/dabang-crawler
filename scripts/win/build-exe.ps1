$ErrorActionPreference = "Stop"
Write-Host "🛠️ PyInstaller 빌드 시작..." -ForegroundColor Green

# 깨끗이
Write-Host "🧹 이전 빌드 파일 정리 중..." -ForegroundColor Yellow
Remove-Item -Recurse -Force build, dist, *.spec -ErrorAction SilentlyContinue

# 가상환경(있다면) 활성화는 생략. pip 의존성 보장 가정.
Write-Host "🔨 PyInstaller 빌드 중..." -ForegroundColor Yellow
pyinstaller `
  --noconfirm `
  --onefile `
  --windowed `
  --name "다방크롤러" `
  --paths . `
  --add-data "config;config" `
  --add-data "app/widgets;app/widgets" `
  --add-data "storage;storage" `
  --add-data "scraper;scraper" `
  --add-data "data;data" `
  --add-data "assets;assets" `
  --add-data "scripts;scripts" `
  --add-data "tools;tools" `
  --add-data "tests;tests" `
  --add-data "realestate_dabang;realestate_dabang" `
  --icon "assets/icon.ico" `
  app/gui.py

if (-not (Test-Path ".\\dist\\다방크롤러.exe")) {
  Write-Host "❌ 빌드 산출물을 찾지 못했습니다. hook/hiddenimports 또는 경로를 점검하세요." -ForegroundColor Red
  exit 1
}

$exePath = ".\\dist\\다방크롤러.exe"
$fileSize = [math]::Round((Get-Item $exePath).Length / 1MB, 2)
$fileHash = (Get-FileHash -Algorithm SHA256 $exePath).Hash

Write-Host "✅ 빌드 완료!" -ForegroundColor Green
Write-Host "📄 파일: $exePath" -ForegroundColor Cyan
Write-Host "📏 크기: $fileSize MB" -ForegroundColor Cyan
Write-Host "🔐 SHA256: $fileHash" -ForegroundColor Cyan
Write-Host ""
Write-Host "ℹ️ 처음 실행 전 Playwright 브라우저 설치가 필요할 수 있습니다:" -ForegroundColor Yellow
Write-Host "   python -m playwright install chromium" -ForegroundColor White
Write-Host ""
Write-Host "ℹ️ Windows 차단 해제가 필요할 수 있습니다:" -ForegroundColor Yellow
Write-Host "   Unblock-File -Path '$exePath'" -ForegroundColor White
