@echo off
cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo    Research Agent - Launcher
echo  ============================================================
echo.
echo  폴더: %~dp0
echo.
REM -- 이미 실행 중이면 브라우저만 열기 --
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] 이미 실행 중입니다.
    echo.
    echo  브라우저에서 http://localhost:8601 을 엽니다...
    start http://localhost:8601
    goto shortcut
)
REM -- 가상환경 자동 감지 및 활성화 --
if exist "%~dp0venv\Scripts\activate.bat" (
    echo  [INFO] 가상환경 활성화 중... (venv)
    call "%~dp0venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
    echo  [INFO] 가상환경 활성화 중... (.venv)
    call "%~dp0.venv\Scripts\activate.bat"
) else (
    echo  [INFO] 시스템 Python 사용 중...
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [오류] Python 을 찾을 수 없습니다.
    pause
    exit
)
REM -- Streamlit 백그라운드 실행 --
echo  [INFO] Streamlit 앱 시작 중...
start "ResearchAgent" /D "%~dp0" /min cmd /k "chcp 65001 >nul && python -m streamlit run app.py --server.port 8601 --server.headless true --browser.gatherUsageStats false"
REM -- 서버 준비 대기 (최대 30초) --
echo  [INFO] 서버 준비 대기 중...
set /a tries=0
:wait_loop
timeout /t 1 >nul
set /a tries=%tries%+1
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 goto server_ready
if %tries% lss 30 goto wait_loop
echo.
echo  [오류] 서버가 30초 내에 시작되지 않았습니다.
pause
exit
:server_ready
echo  [OK] 서버 준비 완료!
echo.
echo  브라우저에서 http://localhost:8601 을 엽니다...
start http://localhost:8601
:shortcut
set SHORTCUT=%USERPROFILE%\Desktop\연구자동화시스템.lnk
if exist "%SHORTCUT%" goto done
echo  [INFO] 바탕화면 바로가기 생성 중...
powershell -NoProfile -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%');$s.TargetPath='%~f0';$s.WorkingDirectory='%~dp0';$s.Description='연구 자동화 시스템';$s.IconLocation='%SystemRoot%\System32\SHELL32.dll,13';$s.Save()"
if exist "%SHORTCUT%" echo  [OK] 바탕화면 바로가기 생성 완료!
:done
echo.
echo  ============================================================
echo    완료!  http://localhost:8601
echo  ============================================================
echo.
echo  이 창을 닫으려면 아무 키나 누르세요...
pause >nul
exit