-- =================================================================
-- Portforge MSA Database Schema Initialization
-- 물리적으로 1개의 MySQL 인스턴스, 논리적으로 서비스별 스키마 분리
-- =================================================================

-- 1. Auth Service Database
CREATE DATABASE IF NOT EXISTS portforge_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. Project Service Database  
CREATE DATABASE IF NOT EXISTS portforge_project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 3. Team Service Database
CREATE DATABASE IF NOT EXISTS portforge_team CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 4. AI Service Database
CREATE DATABASE IF NOT EXISTS portforge_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 5. Support & Communication Service Database
CREATE DATABASE IF NOT EXISTS portforge_support CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- =================================================================
-- 서비스별 사용자 생성 및 권한 부여 (보안 강화)
-- =================================================================

-- Auth Service User
CREATE USER IF NOT EXISTS 'auth_user'@'%' IDENTIFIED BY 'auth_password';
GRANT ALL PRIVILEGES ON portforge_auth.* TO 'auth_user'@'%';

-- Project Service User
CREATE USER IF NOT EXISTS 'project_user'@'%' IDENTIFIED BY 'project_password';
GRANT ALL PRIVILEGES ON portforge_project.* TO 'project_user'@'%';

-- Team Service User
CREATE USER IF NOT EXISTS 'team_user'@'%' IDENTIFIED BY 'team_password';
GRANT ALL PRIVILEGES ON portforge_team.* TO 'team_user'@'%';

-- AI Service User
CREATE USER IF NOT EXISTS 'ai_user'@'%' IDENTIFIED BY 'ai_password';
GRANT ALL PRIVILEGES ON portforge_ai.* TO 'ai_user'@'%';

-- Support Service User
CREATE USER IF NOT EXISTS 'support_user'@'%' IDENTIFIED BY 'support_password';
GRANT ALL PRIVILEGES ON portforge_support.* TO 'support_user'@'%';

-- 권한 적용
FLUSH PRIVILEGES;

-- =================================================================
-- 개발용 공통 사용자 (모든 스키마 접근 가능)
-- =================================================================
CREATE USER IF NOT EXISTS 'dev_user'@'%' IDENTIFIED BY 'dev_password';
GRANT ALL PRIVILEGES ON portforge_auth.* TO 'dev_user'@'%';
GRANT ALL PRIVILEGES ON portforge_project.* TO 'dev_user'@'%';
GRANT ALL PRIVILEGES ON portforge_team.* TO 'dev_user'@'%';
GRANT ALL PRIVILEGES ON portforge_ai.* TO 'dev_user'@'%';
GRANT ALL PRIVILEGES ON portforge_support.* TO 'dev_user'@'%';

-- =================================================================
-- Root 사용자 외부 접근 허용 (로컬 개발용)
-- Docker 네트워크에서 접속 시 필요
-- =================================================================
-- root 사용자가 모든 호스트에서 접근 가능하도록 설정
CREATE USER IF NOT EXISTS 'root'@'%' IDENTIFIED BY 'rootpassword';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

FLUSH PRIVILEGES;