@echo off
chcp 65001 >nul
cd /d "%~dp0"

:start
cls
echo.
echo  ============================================================
echo    🔬 Research Agent  v2.0.0
echo    Multi-Agent Research Automation System
echo  ============================================================
echo.
echo  경로: %~dp0
echo.

REM ── 이미 실행 중이면 바로 브라우저 열기 ──────────────────────
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] 이미 실행 중입니다.
    echo.
    echo  브라우저에서 http://localhost:8601 을 엽니다...
    start http://localhost:8601
    goto shortcut
)

REM ── 최신 코드 자동 업데이트 (git pull) ───────────────────────
echo  [INFO] 최신 코드 확인 중...
git pull --autostash >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] 코드 최신 상태
) else (
    echo  [INFO] git 업데이트 건너뜀 (네트워크/git 미설치)
)
echo.

REM ── 가상환경 자동 감지 및 활성화 ─────────────────────────────
if exist "%~dp0venv\Scripts\activate.bat" (
    echo  [INFO] 가상환경 활성화 중... (venv)
    call "%~dp0venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
    echo  [INFO] 가상환경 활성화 중... (.venv)
    call "%~dp0.venv\Scripts\activate.bat"
) else (
    echo  [INFO] 시스템 Python 사용 중...
)

REM ── Python 확인 ───────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [오류] Python 을 찾을 수 없습니다.
    echo         Python 설치 후 PATH 에 추가하세요.
    echo         https://python.org
    echo.
    pause
    exit /b 1
)
echo.

REM ── Streamlit 설치 확인 ───────────────────────────────────────
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [오류] Streamlit 이 설치되지 않았습니다.
    echo         아래 명령어를 실행하세요:
    echo.
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ── .env 파일 확인 ────────────────────────────────────────────
if not exist "%~dp0.env" (
    echo  [경고] .env 파일이 없습니다. Anthropic API 키가 필요합니다.
    echo         .env 파일을 생성하고 아래 내용을 입력하세요:
    echo.
    echo    ANTHROPIC_API_KEY=sk-ant-...
    echo.
    echo  계속하려면 아무 키나 누르세요...
    pause >nul
)

REM ── Streamlit 앱 실행 ─────────────────────────────────────────
echo.
echo  [INFO] Research Agent 시작 중...
start "ResearchAgent" /D "%~dp0" /min cmd /k "chcp 65001 >nul && python -m streamlit run app.py --server.port 8601 --server.headless true --browser.gatherUsageStats false"

REM ── 서버 준비 대기 (최대 30초) ───────────────────────────────
echo  [INFO] 서버 준비 대기 중...
set /a tries=0
:wait_loop
timeout /t 1 >nul
set /a tries=%tries%+1
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 goto server_ready
if %tries% lss 40 goto wait_loop

echo.
echo  [오류] 30초 내에 서버가 시작되지 않았습니다.
echo         최소화된 터미널 창에서 오류 내용을 확인하세요.
echo.
pause
exit /b 1

:server_ready
echo  [OK] 서버 준비 완료!
echo.
echo  브라우저에서 http://localhost:8601 을 엽니다...
start http://localhost:8601

REM ── 바탕화면 바로가기 생성 (최초 1회) ───────────────────────
:shortcut
set "SHORTCUT=%USERPROFILE%\Desktop\연구자동화시스템.lnk"
if exist "%SHORTCUT%" goto done
echo.
echo  [INFO] 바탕화면 바로가기 생성 중...
powershell -NoProfile -Command ^
  "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath='%~f0';" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "$s.Description='Research Agent v2.0.0';" ^
  "$s.IconLocation='%SystemRoot%\System32\SHELL32.dll,13';" ^
  "$s.Save()"
if exist "%SHORTCUT%" echo  [OK] 바탕화면 바로가기 생성 완료!

:done
echo.
echo  ============================================================
echo    완료!   http://localhost:8601
echo  ============================================================
echo.
echo  이 창은 닫아도 됩니다. 아무 키나 누르세요...
pause >nul
exit /b 0
