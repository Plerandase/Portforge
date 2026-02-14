# app/models/enums.py - 공통 Enum 정의
from enum import Enum

# 모든 Enum에 str을 함께 상속받아 API 통신 시 자동으로 문자열 변환

# 사용자 역할
class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

# 팀 역할
class TeamRole(str, Enum):
    LEADER = "LEADER"
    MEMBER = "MEMBER"

# 프로젝트 타입
class ProjectType(str, Enum):
    PROJECT = "PROJECT"
    STUDY = "STUDY"

# 프로젝트 방식
class ProjectMethod(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MIXED = "MIXED"

# 프로젝트 상태
class ProjectStatus(str, Enum):
    RECRUITING = "RECRUITING"
    PROCEEDING = "PROCEEDING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"

# 지원 상태
class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

# 스택 카테고리
class StackCategory(str, Enum):
    FRONTEND = "FRONTEND"
    BACKEND = "BACKEND"
    DB = "DB"
    INFRA = "INFRA"
    DESIGN = "DESIGN"
    ETC = "ETC"

# 기술 스택 (ERD 반영)
class TechStack(str, Enum):
    # Frontend
    React = "React"
    Vue = "Vue"
    Nextjs = "Nextjs"
    Svelte = "Svelte"
    Angular = "Angular"
    TypeScript = "TypeScript"
    JavaScript = "JavaScript"
    TailwindCSS = "TailwindCSS"
    StyledComponents = "StyledComponents"
    Redux = "Redux"
    Recoil = "Recoil"
    Vite = "Vite"
    Webpack = "Webpack"
    
    # Backend
    Java = "Java"
    Spring = "Spring"
    Nodejs = "Nodejs"
    Nestjs = "Nestjs"
    Go = "Go"
    Python = "Python"
    Django = "Django"
    Flask = "Flask"
    Express = "Express"
    php = "php"
    Laravel = "Laravel"
    GraphQL = "GraphQL"
    RubyOnRails = "RubyOnRails"
    CSharp = "CSharp"
    DotNET = "DotNET"
    
    # Database
    MySQL = "MySQL"
    PostgreSQL = "PostgreSQL"
    MongoDB = "MongoDB"
    Redis = "Redis"
    Oracle = "Oracle"
    SQLite = "SQLite"
    MariaDB = "MariaDB"
    Cassandra = "Cassandra"
    DynamoDB = "DynamoDB"
    FirebaseFirestore = "FirebaseFirestore"
    Prisma = "Prisma"
    
    # Infrastructure
    AWS = "AWS"
    Docker = "Docker"
    Kubernetes = "Kubernetes"
    GCP = "GCP"
    Azure = "Azure"
    Terraform = "Terraform"
    Jenkins = "Jenkins"
    GithubActions = "GithubActions"
    Nginx = "Nginx"
    Linux = "Linux"
    Vercel = "Vercel"
    Netlify = "Netlify"
    
    # Design
    Figma = "Figma"
    AdobeXD = "AdobeXD"
    Sketch = "Sketch"
    Canva = "Canva"
    Photoshop = "Photoshop"
    Illustrator = "Illustrator"
    Blender = "Blender"
    UIUX_Design = "UIUX_Design"
    Branding = "Branding"
    
    # ETC
    Git = "Git"
    Slack = "Slack"
    Jira = "Jira"
    Notion = "Notion"
    Discord = "Discord"
    Postman = "Postman"
    Swagger = "Swagger"
    Zeplin = "Zeplin"

# 회의 상태
class MeetingStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# 리포트 타입
class ReportType(str, Enum):
    MEETING_MINUTES = "MEETING_MINUTES"
    PROJECT_PLAN = "PROJECT_PLAN"
    WEEKLY_REPORT = "WEEKLY_REPORT"
    PORTFOLIO = "PORTFOLIO"

# 테스트 타입
class TestType(str, Enum):
    PRACTICE = "PRACTICE"
    APPLICATION = "APPLICATION"
