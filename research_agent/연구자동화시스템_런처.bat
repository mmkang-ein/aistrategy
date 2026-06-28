@echo off
chcp 65001 >nul
cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo    🔬 연구 자동화 시스템 (Multi-Agent Research System)
echo  ============================================================
echo.

REM ── 이미 실행 중이면 브라우저만 열기 ──────────────────────────
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo  [INFO] 이미 실행 중입니다. 브라우저를 엽니다...
    timeout /t 1 >nul
    start http://localhost:8601
    goto shortcut
)

REM ── 가상환경 자동 감지 및 활성화 ──────────────────────────────
if exist "%~dp0venv\Scripts\activate.bat" (
    echo  [INFO] 가상환경 활성화 중... (venv)
    call "%~dp0venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
    echo  [INFO] 가상환경 활성화 중... (.venv)
    call "%~dp0.venv\Scripts\activate.bat"
) else (
    echo  [INFO] 시스템 Python 사용 중...
)

REM ── Streamlit 백그라운드 실행 (최소화) ────────────────────────
echo  [INFO] 앱 시작 중... (포트 8601)
start "연구자동화시스템" /D "%~dp0" /min cmd /k ^
  "chcp 65001 >nul && python -m streamlit run app.py --server.port 8601 --server.headless true --browser.gatherUsageStats false"

REM ── 서버 준비 대기 후 브라우저 오픈 ──────────────────────────
echo  [INFO] 서버 준비 중...
:wait_loop
timeout /t 1 >nul
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if not %errorlevel%==0 goto wait_loop

echo  [INFO] 브라우저 오픈 중...
start http://localhost:8601

REM ── 바탕화면 바로가기 생성 (최초 1회) ────────────────────────
:shortcut
set SHORTCUT=%USERPROFILE%\Desktop\연구자동화시스템.lnk
if exist "%SHORTCUT%" goto done

echo  [INFO] 바탕화면 바로가기 생성 중...
powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%');$s.TargetPath='%~f0';$s.WorkingDirectory='%~dp0';$s.Description='연구 자동화 시스템 런처';$s.IconLocation='%SystemRoot%\System32\SHELL32.dll,13';$s.Save()"
if exist "%SHORTCUT%" (
    echo  [완료] 바탕화면 바로가기가 생성됐습니다.
) else (
    echo  [참고] 바로가기 생성 실패 (권한 문제일 수 있습니다)
)

:done
echo.
echo  ============================================================
echo    ✅ http://localhost:8601 에서 실행 중
echo    이 창은 닫아도 됩니다.
echo  ============================================================
echo.
timeout /t 4 >nul
exit
