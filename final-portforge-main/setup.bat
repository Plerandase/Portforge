@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ================================================
echo   Portforge - One-Click Setup
echo ================================================
echo.

:: ========================================
:: 1. 사전 요구사항 체크
:: ========================================
echo [1/7] 사전 요구사항 확인 중...

:: Python 체크
python --version >nul 2>&1
if errorlevel 1 (
    echo     [X] Python이 설치되어 있지 않습니다.
    echo         https://www.python.org/downloads/ 에서 Python 3.11+ 설치
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo     [OK] Python %PYTHON_VER%

:: Poetry 체크
poetry --version >nul 2>&1
if errorlevel 1 (
    echo     [!] Poetry 설치 중...
    powershell -Command "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"
    if errorlevel 1 (
        echo     [X] Poetry 설치 실패. 수동 설치 필요.
        pause
        exit /b 1
    )
    echo     [OK] Poetry 설치 완료
) else (
    for /f "tokens=3" %%i in ('poetry --version 2^>^&1') do set POETRY_VER=%%i
    echo     [OK] Poetry %POETRY_VER%
)

:: Node.js 체크
node --version >nul 2>&1
if errorlevel 1 (
    echo     [X] Node.js가 설치되어 있지 않습니다.
    echo         https://nodejs.org/ 에서 Node.js 18+ 설치
    pause
    exit /b 1
)
for /f %%i in ('node --version 2^>^&1') do set NODE_VER=%%i
echo     [OK] Node.js %NODE_VER%

:: Docker 체크
docker --version >nul 2>&1
if errorlevel 1 (
    echo     [X] Docker가 설치되어 있지 않습니다.
    echo         https://www.docker.com/products/docker-desktop/ 에서 설치
    pause
    exit /b 1
)
echo     [OK] Docker 확인

:: Docker 실행 중인지 체크
docker info >nul 2>&1
if errorlevel 1 (
    echo     [X] Docker Desktop이 실행 중이 아닙니다.
    echo         Docker Desktop을 실행한 후 다시 시도하세요.
    pause
    exit /b 1
)
echo     [OK] Docker 실행 중

echo.

:: ========================================
:: 2. 환경 변수 파일 복사
:: ========================================
echo [2/7] 환경 변수 파일 설정 중...

if not exist "Auth\.env" (
    if exist "Auth\.env.example" (
        copy "Auth\.env.example" "Auth\.env" >nul
        echo     [OK] Auth/.env 생성
    )
) else (
    echo     [--] Auth/.env 이미 존재
)

if not exist "Project_Service\.env" (
    if exist "Project_Service\.env.example" (
        copy "Project_Service\.env.example" "Project_Service\.env" >nul
        echo     [OK] Project_Service/.env 생성
    )
) else (
    echo     [--] Project_Service/.env 이미 존재
)

if not exist "Team-BE\.env" (
    if exist "Team-BE\.env.example" (
        copy "Team-BE\.env.example" "Team-BE\.env" >nul
        echo     [OK] Team-BE/.env 생성
    )
) else (
    echo     [--] Team-BE/.env 이미 존재
)

if not exist "Ai\.env" (
    if exist "Ai\.env.example" (
        copy "Ai\.env.example" "Ai\.env" >nul
        echo     [OK] Ai/.env 생성
    )
) else (
    echo     [--] Ai/.env 이미 존재
)

if not exist "Support_Communication_Service\.env" (
    if exist "Support_Communication_Service\.env.example" (
        copy "Support_Communication_Service\.env.example" "Support_Communication_Service\.env" >nul
        echo     [OK] Support_Communication_Service/.env 생성
    )
) else (
    echo     [--] Support_Communication_Service/.env 이미 존재
)

echo.

:: ========================================
:: 3. Python 의존성 설치
:: ========================================
echo [3/7] Python 의존성 설치 중...

call :install_service "Auth"
call :install_service "Project_Service"
call :install_service "Team-BE"
call :install_service "Ai"
call :install_service "Support_Communication_Service"

echo     [OK] Python 의존성 설치 완료
echo.

:: ========================================
:: 4. Frontend 의존성 설치
:: ========================================
echo [4/7] Frontend 의존성 설치 중...

if not exist "FE\package.json" (
    echo     [!] FE/package.json 없음
    goto :skip_frontend
)

cd FE
if exist "node_modules" (
    echo     [--] node_modules 존재, 업데이트 확인...
) else (
    echo     [..] npm install 실행 중 ^(시간이 걸릴 수 있습니다^)...
)
call npm install --silent
cd ..
echo     [OK] Frontend 의존성 설치 완료

:skip_frontend

echo.

:: ========================================
:: 5. Docker 컨테이너 시작
:: ========================================
echo [5/7] Docker 컨테이너 시작 중...

:: 기존 컨테이너와 충돌 방지: 강제 삭제 후 재생성
docker rm -f portforge-mysql portforge-dynamodb portforge-dynamodb-admin portforge-dynamodb-admin >nul 2>&1

docker compose up -d
if errorlevel 1 (
    echo     [X] Docker 컨테이너 시작 실패
    pause
    exit /b 1
)
echo     [OK] Docker 컨테이너 시작 완료

:: MySQL이 준비될 때까지 대기 (Python으로 체크)
echo     [..] MySQL 준비 대기 중 (최대 60초)...
set /a count=0
:wait_mysql
timeout /t 2 /nobreak >nul
set /a count+=2

:: Python으로 MySQL 연결 테스트
python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost',3306)); s.close(); print('ok')" >nul 2>&1
if errorlevel 1 (
    if !count! geq 60 (
        echo     [X] MySQL 시작 시간 초과
        pause
        exit /b 1
    )
    goto wait_mysql
)
:: 추가 대기 (MySQL 초기화 완료 대기)
timeout /t 5 /nobreak >nul
echo     [OK] MySQL 준비 완료

echo.

:: ========================================
:: 6. 데이터베이스 초기화 (리셋 + 테이블 생성)
:: ========================================
echo [6/7] 데이터베이스 초기화 중...

:: db_manager.py로 DB 리셋 및 테이블 생성
echo     [..] 데이터베이스 리셋 중...
python db_manager.py reset --no-confirm >nul 2>&1
if errorlevel 1 (
    echo     [!] DB 리셋 실패, 테이블 생성만 진행...
)

echo     [..] 테이블 생성 중...

cd Auth
call poetry run python create_tables.py >nul 2>&1
if errorlevel 1 (
    echo     [!] Auth 테이블 생성 실패
) else (
    echo     [OK] Auth 테이블
)
cd ..

cd Project_Service
call poetry run python create_tables.py >nul 2>&1
if errorlevel 1 (
    echo     [!] Project 테이블 생성 실패
) else (
    echo     [OK] Project 테이블
)
cd ..

cd Team-BE
call poetry run python create_tables.py >nul 2>&1
if errorlevel 1 (
    echo     [!] Team 테이블 생성 실패
) else (
    echo     [OK] Team 테이블
)
cd ..

cd Ai
call poetry run python create_tables.py >nul 2>&1
if errorlevel 1 (
    echo     [!] AI 테이블 생성 실패
) else (
    echo     [OK] AI 테이블
)
cd ..

cd Support_Communication_Service
call poetry run python create_tables.py >nul 2>&1
if errorlevel 1 (
    echo     [!] Support 테이블 생성 실패
) else (
    echo     [OK] Support 테이블
)
cd ..

:: DynamoDB 테이블 생성
echo     [..] DynamoDB 테이블 생성 중...
python create_dynamodb_tables.py >nul 2>&1
if errorlevel 1 (
    echo     [!] DynamoDB 테이블 생성 실패 (무시 가능)
) else (
    echo     [OK] DynamoDB 테이블
)

echo     [OK] 데이터베이스 초기화 완료

echo.

:: ========================================
:: 7. 완료
:: ========================================
echo [7/7] 설정 완료!
echo.
echo ================================================
echo   Setup Complete!
echo ================================================
echo.
echo   [!] Cognito 설정 필요 (회원가입/로그인용)
echo       Auth/.env 파일에 팀장에게 받은 값 입력:
echo       - COGNITO_USERPOOL_ID
echo       - COGNITO_APP_CLIENT_ID
echo.
echo   서비스 시작: start_services.bat
echo   접속 주소:   http://localhost:3000
echo.
echo ================================================
echo.

set /p start_now="지금 서비스를 시작하시겠습니까? (Y/N): "
if /i "%start_now%"=="Y" (
    call start_services.bat
)

endlocal
exit /b 0

:: ========================================
:: 서비스별 설치 함수
:: ========================================
:install_service
set "service=%~1"

if not exist "%service%\pyproject.toml" (
    goto :eof
)

cd %service%

if exist ".venv\Scripts\python.exe" (
    echo     [--] %service% venv 존재, 동기화 중...
    call poetry install --no-root --quiet 2>nul
) else (
    echo     [..] %service% venv 생성 중...
    call poetry install --no-root --quiet 2>nul
)

cd ..
goto :eof
