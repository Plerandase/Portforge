@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ================================================
echo   Portforge MSA Services Starting...
echo ================================================
echo.

:: Docker 실행 확인
docker info >nul 2>&1
if errorlevel 1 (
    echo [!] Docker Desktop이 실행 중이 아닙니다.
    echo     Docker Desktop을 실행한 후 다시 시도하세요.
    pause
    exit /b 1
)

:: Docker 컨테이너 시작
echo [1/7] Docker 컨테이너 확인 중...
docker compose up -d >nul 2>&1
echo     [OK] Docker 컨테이너 실행 중

REM MySQL 준비 대기
echo [2/7] MySQL 준비 대기 중...
set /a count=0
:wait_mysql
docker compose exec -T mysql mysqladmin ping -h localhost -u root -prootpassword >nul 2>&1
if errorlevel 1 (
    set /a count+=1
    if !count! geq 30 (
        echo     [!] MySQL 시작 시간 초과
        pause
        exit /b 1
    )
    timeout /t 1 /nobreak >nul
    goto wait_mysql
)
echo     [OK] MySQL 준비 완료

:: 백엔드 서비스 시작
echo [3/7] Auth Service 시작 중 (port 8000)...
start "Auth Service" cmd /c "cd Auth && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul

echo [4/7] Project Service 시작 중 (port 8001)...
start "Project Service" cmd /c "cd Project_Service && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
timeout /t 2 /nobreak >nul

echo [5/7] Team Service 시작 중 (port 8002)...
start "Team Service" cmd /c "cd Team-BE && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"
timeout /t 2 /nobreak >nul

echo [6/7] AI Service 시작 중 (port 8003)...
start "AI Service" cmd /c "cd Ai && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload"
timeout /t 2 /nobreak >nul

echo     Support Service 시작 중 (port 8004)...
start "Support Service" cmd /c "cd Support_Communication_Service && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload"
timeout /t 2 /nobreak >nul

:: 프론트엔드 시작
echo [7/7] Frontend 시작 중 (port 3000)...
start "Frontend" cmd /c "cd FE && npm run dev"
timeout /t 3 /nobreak >nul

:: 서비스 헬스체크 (간단히)
echo.
echo     서비스 시작 대기 중 (10초)...
timeout /t 10 /nobreak >nul

:: 브라우저 자동 열기
echo.
echo ================================================
echo   [OK] 모든 서비스 시작 완료!
echo ================================================
echo.
echo   Frontend:  http://localhost:3000
echo   Auth API:  http://localhost:8000/docs
echo   Project:   http://localhost:8001/docs
echo   Team:      http://localhost:8002/docs
echo   AI:        http://localhost:8003/docs
echo   Support:   http://localhost:8004/docs
echo.
echo   [!] 서비스 종료: 각 터미널 창을 닫으세요
echo.

:: 브라우저 열기
start http://localhost:3000

endlocal
pause