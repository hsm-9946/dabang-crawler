$ErrorActionPreference = "Stop"
Write-Host "🔎 EXE 진단 시작..." -ForegroundColor Green

$roots = @(
  (Resolve-Path ".\").Path,
  (Join-Path (Resolve-Path ".\").Path "dist"),
  (Join-Path (Resolve-Path ".\").Path "release"),
  (Join-Path (Resolve-Path ".\").Path "downloads")
) | Get-Unique

$patterns = @("다방크롤러.exe","다방 크롤러.exe","dabang*.exe","*dabang*crawler*.exe","*.exe")

$found = @()
foreach ($r in $roots) {
  if (Test-Path $r) {
    Write-Host "📁 검색 중: $r" -ForegroundColor Yellow
    foreach ($p in $patterns) {
      $found += Get-ChildItem -Path $r -Filter $p -Recurse -ErrorAction SilentlyContinue
    }
  }
}
$found = $found | Sort-Object FullName -Unique

if (-not $found) {
  Write-Host "❌ exe를 찾지 못했습니다. 다음을 확인하세요:" -ForegroundColor Red
  Write-Host "  1) GitHub Release에서 ZIP이 아닌 단일 .exe를 받았는지" -ForegroundColor Yellow
  Write-Host "  2) ZIP이면 압축을 완전히 풀었는지 (경로에 부동산-xxxxx/부동산/... 구조인지)" -ForegroundColor Yellow
  Write-Host "  3) 파일명이 '다방 크롤러.exe' 등 스페이스/한글 포함으로 저장되지 않았는지" -ForegroundColor Yellow
  Write-Host "  4) 현재 디렉토리에서 실행 중인지 확인" -ForegroundColor Yellow
  exit 1
}

Write-Host "✅ 발견된 exe 목록:" -ForegroundColor Green
foreach ($f in $found) {
  $hash = (Get-FileHash -Algorithm SHA256 $f.FullName).Hash
  $size = [math]::Round($f.Length / 1MB, 2)
  Write-Host "📄 $($f.Name)" -ForegroundColor Cyan
  Write-Host "  • 경로: $($f.FullName)" -ForegroundColor White
  Write-Host "  • 크기: $size MB ($($f.Length) bytes)" -ForegroundColor White
  Write-Host "  • SHA256: $hash" -ForegroundColor White
  Write-Host ""
}

Write-Host "ℹ️ Windows가 다운로드 차단했을 수 있습니다. 차단 해제:" -ForegroundColor Yellow
Write-Host "   Unblock-File -Path 'C:\\경로\\파일명.exe'" -ForegroundColor White
Write-Host "ℹ️ 경로 또는 파일명에 공백/한글이 있으면 반드시 큰따옴표로 실행:" -ForegroundColor Yellow
Write-Host "   & \"C:\\경로\\다방 크롤러.exe\"" -ForegroundColor White
Write-Host "ℹ️ 관리자 권한으로 실행이 필요할 수 있습니다." -ForegroundColor Yellow
