@echo off
chcp 65001 >nul
cd /d "%~dp0"

cls
echo.
echo  ============================================================
echo    Research Agent - 연구자동화시스템 런처
echo    Python 3.12 / 시스템 Python
echo  ============================================================
echo.

REM ── [STEP 1] 이미 실행 중이면 바로 열기 ─────────────────────
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] 이미 실행 중입니다.
    echo  브라우저에서 http://localhost:8601 을 엽니다...
    start http://localhost:8601
    goto shortcut
)

REM ── [STEP 2] Python 3.12 확인 ────────────────────────────────
echo  [1/4] Python 3.12 확인 중...
py -3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [오류] Python 3.12 를 찾을 수 없습니다.
    echo         python.org 에서 Python 3.12 를 설치하세요.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('py -3.12 --version 2^>^&1') do echo  [OK] %%v
echo.

REM ── [STEP 3] git pull ────────────────────────────────────────
echo  [2/4] 최신 코드 확인 중...
git pull --autostash >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] 코드 최신 상태
) else (
    echo  [INFO] git pull 실패 — 현재 코드로 계속 진행
)
echo.

REM ── [STEP 4] 패키지 확인 (import 체크 → 실패 시만 설치) ─────
echo  [3/4] 패키지 확인 중...
py -3.12 -c "import streamlit, anthropic, dotenv, docx, fpdf" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] 모든 패키지 설치 확인됨
) else (
    echo  [INFO] 누락 패키지 설치 중... (최초 실행 시 수분 소요)
    py -3.12 -m pip install -r "%~dp0requirements.txt" -q >nul 2>&1
    py -3.12 -m pip install streamlit python-docx fpdf2 -q >nul 2>&1
    py -3.12 -c "import streamlit, anthropic, dotenv, docx, fpdf" >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [오류] 패키지 설치 실패. 인터넷 연결을 확인하세요.
        pause
        exit /b 1
    )
    echo  [OK] 패키지 설치 완료
)
echo.

REM ── [STEP 5] .env 확인 ───────────────────────────────────────
if not exist "%~dp0.env" (
    echo  [경고] .env 파일 없음 — ANTHROPIC_API_KEY 를 .env 에 입력하세요.
    echo.
)

REM ── [STEP 6] Streamlit 실행 ──────────────────────────────────
echo  [4/4] Streamlit 앱 시작 중...
start "ResearchAgent" /D "%~dp0" /min cmd /k "chcp 65001 >nul && py -3.12 -m streamlit run app.py --server.port 8601 --server.headless true --browser.gatherUsageStats false"

REM ── 서버 준비 대기 (최대 40초) ──────────────────────────────
set /a tries=0
:wait_loop
timeout /t 1 >nul
set /a tries=%tries%+1
netstat -ano | findstr ":8601" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 goto server_ready
if %tries% lss 40 goto wait_loop

echo  [오류] 40초 내에 서버가 시작되지 않았습니다.
echo         최소화된 Streamlit 창에서 오류를 확인하세요.
pause
exit /b 1

:server_ready
echo  [OK] 서버 준비 완료! (%tries%초 소요)
echo.
echo  브라우저에서 http://localhost:8601 을 엽니다...
start http://localhost:8601

REM ── 바탕화면 바로가기 생성 (최초 1회) ──────────────────────
:shortcut
set "SHORTCUT=%USERPROFILE%\Desktop\연구자동화시스템.lnk"
if exist "%SHORTCUT%" goto done
echo.
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
exit /b 0
