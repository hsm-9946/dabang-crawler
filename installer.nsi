; 다방 부동산 크롤러 설치 프로그램
; NSIS 스크립트

!define APP_NAME "다방 부동산 크롤러"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "다방 크롤러 개발팀"
!define APP_EXE "다방크롤러.exe"
!define APP_CLI_EXE "다방크롤러_CLI.exe"

; MUI 2.0 포함
!include "MUI2.nsh"

; 기본 설정
Name "${APP_NAME}"
OutFile "다방크롤러_Setup_v${APP_VERSION}.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" ""

; 요청된 권한 레벨
RequestExecutionLevel admin

; MUI 설정
!define MUI_ABORTWARNING
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"

; 페이지
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 언인스톨 페이지
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; 언어
!insertmacro MUI_LANGUAGE "Korean"

; 설치 섹션
Section "MainApplication" SecMain
    SetOutPath "$INSTDIR"
    
    ; 메인 실행 파일들
    File "dist\${APP_EXE}"
    File "dist\${APP_CLI_EXE}"
    
    ; 설정 파일들
    SetOutPath "$INSTDIR\config"
    File "config\settings.toml"
    
    ; 데이터 파일들
    SetOutPath "$INSTDIR\data"
    File "data\regions_kr.json"
    
    ; 문서
    File "README.md"
    File "LICENSE"
    
    ; 시작 메뉴 바로가기
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME} CLI.lnk" "$INSTDIR\${APP_CLI_EXE}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\언인스톨.lnk" "$INSTDIR\uninstall.exe"
    
    ; 바탕화면 바로가기
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
    
    ; 레지스트리 정보
    WriteRegStr HKCU "Software\${APP_NAME}" "" $INSTDIR
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
    
    ; 언인스톨러 생성
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; 언인스톨 섹션
Section "Uninstall"
    ; 실행 파일들 제거
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\${APP_CLI_EXE}"
    
    ; 설정 파일들 제거
    Delete "$INSTDIR\config\settings.toml"
    RMDir "$INSTDIR\config"
    
    ; 데이터 파일들 제거
    Delete "$INSTDIR\data\regions_kr.json"
    RMDir "$INSTDIR\data"
    
    ; 문서 제거
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\LICENSE"
    
    ; 바로가기 제거
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME} CLI.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\언인스톨.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; 언인스톨러 제거
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"
    
    ; 레지스트리 제거
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
