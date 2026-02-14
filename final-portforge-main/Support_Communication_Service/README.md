# Template-Repo
백엔드 개발 템플릿입니다.

필수 프로그램 설치
아래 4가지 프로그램이 설치되어 있어야 합니다.

Git: https://git-scm.com/downloads

Python (3.10 이상): https://www.python.org/downloads/ (설치 시 "Add Python to PATH" 옵션 체크 필수)

Poetry: (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

Docker Desktop: https://www.docker.com/products/docker-desktop/ (설치 후 Docker Desktop 실행 필수)

git clone 하시고

Step 1. 라이브러리 설치
poetry install --no-root
pyproject.toml에 정의된 FastAPI, SQLAlchemy, aioboto3 등을 설치합니다.

Step 2. 환경 변수 설정 (.env 생성)
poetry run poe copy-env
역할: .env.example을 복사하여 개인용 .env 파일을 생성합니다.
코그니토 구현완료시: 생성된 .env를 열어 공유받은 AWS Cognito 정보(User Pool ID, Client ID)를 입력하세요.

Step 3. 로컬 인프라 실행 (Docker)
poetry run poe db-up
현재 로컬용 ddb, s3, mysql 컨테이너로 올라오게 함

Step 4. DB 테이블 생성 (Migration)
poetry run poe migrate
Alembic을 통해 작성된 모델 스키마를 로컬 MySQL에 배포합니다.
근데 필요한 db는 직접 코드로 구현해서 써야합니다.

Step 5. 애플리케이션 실행
poetry run poe run



개발 규칙 (Best Practices)

인증: 유저 정보가 필요한 API는 반드시 Depends(get_current_user)를 사용하세요. 

데이터베이스: 신규 테이블을 만들면 반드시 poe makemigrations 후 생성된 파일을 커밋하세요.

코드 품질: 커밋 전 poe lint를 실행하여 팀의 코드 스타일을 일치시키세요.

보안: 실제 AWS 키나 비밀번호가 적힌 .env는 절대 Git에 올리지 않습니다.


