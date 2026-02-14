from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.repositories.project_recruitment_repository import ProjectRecruitmentRepository
from app.schemas.project_recruitment import (
    ProjectFilters, ProjectCreate, ProjectUpdate, ProjectStatusUpdate,
    ProjectDetail, ProjectListResponse, ProjectSummary
)
from app.models.project_recruitment import ProjectStatus
from datetime import datetime
import json

router = APIRouter(prefix="/recruitment-projects", tags=["Project Recruitment"])

# 메모리 기반 프로젝트 저장소 (DB 연결 실패 시 사용)
memory_projects = []
next_project_id = 1000

# DB 연결 상태 확인 함수
async def is_db_available() -> bool:
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # SQLite의 경우 간단한 쿼리로 연결 확인
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return False

@router.post("", 
    status_code=status.HTTP_201_CREATED, 
    response_model=ProjectDetail,
    summary="프로젝트 생성",
    description="새로운 프로젝트를 생성하고 팀원 모집 포지션을 설정합니다.",
    responses={
        201: {"description": "프로젝트가 성공적으로 생성됨"},
        400: {"description": "잘못된 요청 데이터"},
        500: {"description": "서버 내부 오류"}
    }
)
async def create_project(project_data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """
    ## 프로젝트 생성
    
    새로운 프로젝트를 생성하고 팀원 모집을 시작합니다.
    
    ### 요청 데이터:
    - **title**: 프로젝트 제목 (최대 100자)
    - **description**: 프로젝트 상세 설명
    - **type**: 프로젝트 타입 (PROJECT/STUDY)
    - **method**: 진행 방식 (ONLINE/OFFLINE/MIXED)
    - **start_date**: 프로젝트 시작일
    - **end_date**: 프로젝트 종료일
    - **test_required**: AI 역량 테스트 필수 여부
    - **recruitment_positions**: 모집 포지션 목록
    
    ### 반환값:
    생성된 프로젝트의 상세 정보
    """
    print(f"🔍 받은 프로젝트 데이터: {project_data}")
    print(f"🔍 프로젝트 데이터 dict: {project_data.dict()}")
    try:
        # DB 연결 확인
        if await is_db_available():
            repo = ProjectRecruitmentRepository(db)
            project_dict = project_data.dict()
            # user_id를 임시로 설정 (실제로는 인증에서 가져와야 함)
            project = await repo.create_project(project_dict, "1")
            
            return ProjectDetail(
                id=project.project_id,
                title=project.title,
                description=project.description,
                type=project.type,
                status=project.status,
                method=project.method,
                views=project.views,
                user_id=project.user_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                start_date=project.start_date,
                end_date=project.end_date,
                test_required=project.test_required,
                recruitment_positions=[
                    {
                        "project_id": pos.project_id,
                        "position_type": pos.position_type,
                        "required_stacks": pos.required_stacks,
                        "target_count": pos.target_count,
                        "current_count": pos.current_count,
                        "employment_type": pos.employment_type,
                        "recruitment_deadline": pos.recruitment_deadline,
                        "created_at": pos.created_at,
                        "updated_at": pos.updated_at
                    }
                    for pos in project.recruitment_positions
                ]
            )
        else:
            # 메모리 기반 저장소에 프로젝트 추가
            global next_project_id
            print(f"🔍 메모리 저장소 사용 - 받은 데이터: {project_data.dict()}")
            new_project = {
                "id": next_project_id,
                "title": project_data.title,
                "description": project_data.description,
                "type": project_data.type.value,
                "status": "RECRUITING",
                "method": project_data.method.value,
                "views": 0,
                "user_id": "1",  # Convert to string
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "start_date": project_data.start_date.strftime("%Y-%m-%d"),
                "end_date": project_data.end_date.strftime("%Y-%m-%d"),
                "test_required": project_data.test_required,
                "recruitment_positions": [
                    {
                        "project_id": next_project_id,
                        "position_type": pos.position_type.value,
                        "required_stacks": pos.required_stacks,
                        "target_count": pos.target_count,
                        "current_count": 0,
                        "employment_type": pos.employment_type,
                        "recruitment_deadline": pos.recruitment_deadline.strftime("%Y-%m-%d") if pos.recruitment_deadline else None,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": None
                    }
                    for pos in project_data.recruitment_positions
                ]
            }
            
            # 메모리에 저장
            memory_projects.append(new_project)
            next_project_id += 1
            
            print(f"✅ 메모리에 저장된 프로젝트: {new_project}")
            
            # ProjectDetail 형식으로 반환
            return ProjectDetail(
                id=new_project["id"],
                title=new_project["title"],
                description=new_project["description"],
                type=project_data.type,
                status="RECRUITING",
                method=project_data.method,
                views=new_project["views"],
                user_id=new_project["user_id"],
                created_at=datetime.fromisoformat(new_project["created_at"]),
                updated_at=datetime.fromisoformat(new_project["updated_at"]) if new_project["updated_at"] else None,
                start_date=project_data.start_date,
                end_date=project_data.end_date,
                test_required=new_project["test_required"],
                recruitment_positions=new_project["recruitment_positions"]
            )
    except Exception as e:
        print(f"❌ 프로젝트 생성 오류: {e}")
        print(f"❌ 오류 타입: {type(e)}")
        import traceback
        print(f"❌ 스택 트레이스: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"프로젝트 생성 중 오류 발생: {str(e)}")


@router.get("", 
    response_model=ProjectListResponse,
    summary="프로젝트 목록 조회",
    description="필터링과 페이지네이션을 지원하는 프로젝트 목록을 조회합니다.",
    responses={
        200: {"description": "프로젝트 목록 조회 성공"},
        500: {"description": "서버 내부 오류"}
    }
)
async def get_project_list(
    type: Optional[str] = Query(None, description="프로젝트 타입 필터 (PROJECT/STUDY)"),
    status: Optional[str] = Query(None, description="프로젝트 상태 필터 (RECRUITING/PROCEEDING/COMPLETED/CLOSED)"),
    tech_stack: Optional[str] = Query(None, description="기술 스택 필터"),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    size: int = Query(10, ge=1, le=100, description="페이지 크기 (1-100)"),
    db: AsyncSession = Depends(get_db)
):
    """
    ## 프로젝트 목록 조회
    
    다양한 필터 조건으로 프로젝트 목록을 조회할 수 있습니다.
    
    ### 쿼리 파라미터:
    - **type**: 프로젝트 타입으로 필터링
    - **status**: 프로젝트 상태로 필터링  
    - **tech_stack**: 기술 스택으로 필터링
    - **page**: 페이지 번호
    - **size**: 페이지당 항목 수
    
    ### 반환값:
    - 프로젝트 목록과 페이지네이션 정보
    """
    print(f"🔍 API 호출됨: GET /recruitment-projects (page={page}, size={size})")
    try:
        # DB 연결 확인
        if await is_db_available():
            repo = ProjectRecruitmentRepository(db)
            filters = ProjectFilters(
                type=type,
                status=status,
                tech_stack=tech_stack,
                page=page,
                size=size
            )
            
            projects, total = await repo.get_projects_with_filters(filters)
            
            project_list = []
            for project in projects:
                project_list.append({
                    "id": project.project_id,  # Updated field name
                    "title": project.title,
                    "description": project.description,
                    "type": project.type.value,
                    "status": project.status.value,
                    "method": project.method.value,
                    "views": project.views,
                    "user_id": project.user_id,
                    "created_at": project.created_at.isoformat(),
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                    "start_date": project.start_date.strftime("%Y-%m-%d"),
                    "end_date": project.end_date.strftime("%Y-%m-%d"),
                    "test_required": project.test_required,
                    "recruitment_positions": [
                        {
                            "project_id": pos.project_id,  # Updated field name
                            "position_type": pos.position_type.value,  # Updated field name
                            "required_stacks": pos.required_stacks,  # Updated field name
                            "target_count": pos.target_count,  # Updated field name
                            "current_count": pos.current_count
                        }
                        for pos in project.recruitment_positions
                    ]
                })
            
            return ProjectListResponse(
                projects=[
                    ProjectSummary(
                        id=project.project_id,
                        title=project.title,
                        description=project.description,
                        type=project.type,
                        status=project.status,
                        method=project.method,
                        views=project.views,
                        user_id=project.user_id,
                        created_at=project.created_at,
                        updated_at=project.updated_at,
                        start_date=project.start_date,
                        end_date=project.end_date,
                        test_required=project.test_required
                    )
                    for project in projects
                ],
                total=total,
                page=page,
                size=size,
                total_pages=(total + size - 1) // size
            )
        else:
            # Fallback to sample data + memory projects if DB is not available
            print("DB 연결 실패, 샘플 데이터 + 메모리 프로젝트 사용")
            sample_projects = [
                {
                    "id": 1,
                    "title": "🚀 팀으로 기획부터 배포까지 완주하는 사이드 프로젝트 멤버 구함",
                    "description": "실제 서비스를 목표로 기획부터 디자인, 개발, 배포까지 함께하실 열정적인 분들을 찾습니다.",
                    "type": "PROJECT",
                    "status": "RECRUITING",
                    "method": "ONLINE",
                    "views": 2451,
                    "user_id": "admin_id",  # 현재 사용자와 매칭되도록 설정
                    "author_name": "김개발자",  # 작성자 이름 추가
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2026-01-06T11:22:14.740919",
                    "start_date": "2024-06-01",
                    "end_date": "2024-08-30",
                    "test_required": True,
                    "recruitment_positions": [
                        {
                            "id": 1,
                            "position_name": "프론트엔드 개발자",
                            "position_type": "FRONTEND",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 2,
                            "target_count": 2,
                            "current_count": 0
                        },
                        {
                            "id": 2,
                            "position_name": "백엔드 개발자", 
                            "position_type": "BACKEND",
                            "tech_stack": "Node.js",
                            "required_stacks": "Node.js",
                            "required_count": 1,
                            "target_count": 1,
                            "current_count": 1
                        }
                    ]
                },
                {
                    "id": 2,
                    "title": "AI 기반 공동구매 플랫폼 프론트엔드 개발자 긴급 모집합니다",
                    "description": "현재 백엔드 2명, 디자이너 1명이 있습니다. React와 TypeScript를 활용한 모던 웹 개발에 관심있는 분들을 찾고 있습니다.",
                    "type": "PROJECT",
                    "status": "RECRUITING",
                    "method": "OFFLINE",
                    "views": 1880,
                    "user_id": "2",  # Convert to string for UUID compatibility
                    "author_name": "이프론트엔드매니저",  # 작성자 이름 추가
                    "created_at": "2024-01-02T00:00:00",
                    "updated_at": "2024-01-02T00:00:00",
                    "start_date": "2024-07-15",
                    "end_date": "2024-10-15",
                    "test_required": False,
                    "recruitment_positions": [
                        {
                            "id": 3,
                            "position_name": "프론트엔드 개발자",
                            "position_type": "FRONTEND",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 2,
                            "target_count": 2,
                            "current_count": 0
                        }
                    ]
                },
                {
                    "id": 3,
                    "title": "📚 React 심화 스터디 - 실무 프로젝트로 배우는 고급 패턴",
                    "description": "React의 고급 패턴과 최신 기능들을 실무 프로젝트를 통해 학습합니다. 함께 성장해요!",
                    "type": "STUDY",
                    "status": "RECRUITING",
                    "method": "ONLINE",
                    "views": 1250,
                    "user_id": "3",  # Convert to string for UUID compatibility
                    "author_name": "박백엔드아키텍트",  # 작성자 이름 추가
                    "created_at": "2024-01-03T00:00:00",
                    "updated_at": "2024-01-03T00:00:00",
                    "start_date": "2024-06-15",
                    "end_date": "2024-08-15",
                    "test_required": False,
                    "recruitment_positions": [
                        {
                            "id": 4,
                            "position_name": "스터디원",
                            "position_type": "ETC",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 6,
                            "target_count": 6,
                            "current_count": 2
                        }
                    ]
                },
                {
                    "id": 4,
                    "title": "🔥 풀스택 개발자 양성 프로젝트 - AI 기반 추천 시스템 구축",
                    "description": "머신러닝과 웹 개발을 결합한 실무 프로젝트입니다. AI 역량 테스트를 통해 실력을 검증하고 함께 성장해요!",
                    "type": "PROJECT",
                    "status": "RECRUITING",
                    "method": "MIXED",
                    "views": 3200,
                    "user_id": "4",  # Convert to string for UUID compatibility
                    "author_name": "최풀스택개발자",  # 작성자 이름 추가
                    "created_at": "2024-01-04T00:00:00",
                    "updated_at": "2024-01-04T00:00:00",
                    "start_date": "2024-07-01",
                    "end_date": "2024-12-31",
                    "test_required": True,
                    "recruitment_positions": [
                        {
                            "id": 5,
                            "position_name": "AI/ML 엔지니어",
                            "position_type": "ETC",
                            "tech_stack": "Python",
                            "required_stacks": "Python",
                            "required_count": 2,
                            "target_count": 2,
                            "current_count": 0
                        },
                        {
                            "id": 6,
                            "position_name": "풀스택 개발자",
                            "position_type": "FRONTEND",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 3,
                            "target_count": 3,
                            "current_count": 1
                        }
                    ]
                }
            ]
            
            # 메모리에 저장된 프로젝트들과 합치기
            all_projects = sample_projects + memory_projects
            
            return {
                "projects": all_projects,
                "total": len(all_projects),
                "page": page,
                "size": size,
                "total_pages": 1
            }
    except Exception as e:
        print(f"프로젝트 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", 
    response_model=ProjectDetail,
    summary="프로젝트 상세 조회",
    description="특정 프로젝트의 상세 정보를 조회하고 조회수를 증가시킵니다.",
    responses={
        200: {"description": "프로젝트 상세 정보 조회 성공"},
        404: {"description": "프로젝트를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def get_project_detail(
    project_id: int = Path(..., description="조회할 프로젝트 ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    ## 프로젝트 상세 조회
    
    특정 프로젝트의 상세 정보를 조회합니다.
    조회 시 해당 프로젝트의 조회수가 1 증가합니다.
    
    ### 경로 파라미터:
    - **project_id**: 조회할 프로젝트의 고유 ID
    
    ### 반환값:
    - 프로젝트 상세 정보 (모집 포지션 포함)
    """
    try:
        # DB 연결 확인
        if await is_db_available():
            repo = ProjectRecruitmentRepository(db)
            project = await repo.get_project_by_id(project_id)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            await repo.increment_views(project_id)
            
            return ProjectDetail(
                id=project.project_id,
                title=project.title,
                description=project.description,
                type=project.type,
                status=project.status,
                method=project.method,
                views=project.views + 1,
                user_id=project.user_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                start_date=project.start_date,
                end_date=project.end_date,
                test_required=project.test_required,
                recruitment_positions=[
                    {
                        "project_id": pos.project_id,
                        "position_type": pos.position_type,
                        "required_stacks": pos.required_stacks,
                        "target_count": pos.target_count,
                        "current_count": pos.current_count,
                        "employment_type": pos.employment_type,
                        "recruitment_deadline": pos.recruitment_deadline,
                        "created_at": pos.created_at,
                        "updated_at": pos.updated_at
                    }
                    for pos in project.recruitment_positions
                ]
            )
        else:
            # Fallback to sample data + memory projects if DB is not available
            print("DB 연결 실패, 샘플 데이터 사용")
            
            # 메모리에서 해당 ID의 프로젝트 찾기
            for project in memory_projects:
                if project["id"] == project_id:
                    # 조회수 증가
                    project["views"] = project.get("views", 0) + 1
                    return project
            
            # 기본 샘플 데이터에서 찾기
            if project_id == 1:
                return {
                    "id": 1,
                    "title": "🚀 팀으로 기획부터 배포까지 완주하는 사이드 프로젝트 멤버 구함",
                    "description": "실제 서비스를 목표로 기획부터 디자인, 개발, 배포까지 함께하실 열정적인 분들을 찾습니다.",
                    "type": "PROJECT",
                    "status": "RECRUITING",
                    "method": "ONLINE",
                    "views": 2452,
                    "user_id": "admin_id",  # 현재 사용자와 매칭되도록 설정
                    "author_name": "김개발자",  # 작성자 이름 추가
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2026-01-06T11:22:14.740919",
                    "start_date": "2024-06-01",
                    "end_date": "2024-08-30",
                    "test_required": True,
                    "recruitment_positions": [
                        {
                            "id": 1,
                            "position_name": "프론트엔드 개발자",
                            "position_type": "FRONTEND",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 2,
                            "target_count": 2,
                            "current_count": 0
                        },
                        {
                            "id": 2,
                            "position_name": "백엔드 개발자",
                            "position_type": "BACKEND", 
                            "tech_stack": "Node.js",
                            "required_stacks": "Node.js",
                            "required_count": 1,
                            "target_count": 1,
                            "current_count": 1
                        }
                    ]
                }
            elif project_id == 2:
                return {
                    "id": 2,
                    "title": "AI 기반 공동구매 플랫폼 프론트엔드 개발자 긴급 모집합니다",
                    "description": "현재 백엔드 2명, 디자이너 1명이 있습니다. React와 TypeScript를 활용한 모던 웹 개발에 관심있는 분들을 찾고 있습니다.",
                    "type": "PROJECT",
                    "status": "RECRUITING",
                    "method": "OFFLINE",
                    "views": 1881,
                    "user_id": "2",  # Convert to string for UUID compatibility
                    "author_name": "이프론트엔드매니저",  # 작성자 이름 추가
                    "created_at": "2024-01-02T00:00:00",
                    "updated_at": "2024-01-02T00:00:00",
                    "start_date": "2024-07-15",
                    "end_date": "2024-10-15",
                    "test_required": False,
                    "recruitment_positions": [
                        {
                            "id": 3,
                            "position_name": "프론트엔드 개발자",
                            "position_type": "FRONTEND",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 2,
                            "target_count": 2,
                            "current_count": 0
                        }
                    ]
                }
            elif project_id == 3:
                return {
                    "id": 3,
                    "title": "📚 React 심화 스터디 - 실무 프로젝트로 배우는 고급 패턴",
                    "description": "React의 고급 패턴과 최신 기능들을 실무 프로젝트를 통해 학습합니다. 함께 성장해요!",
                    "type": "STUDY",
                    "status": "RECRUITING",
                    "method": "ONLINE",
                    "views": 1251,
                    "user_id": "3",  # Convert to string for UUID compatibility
                    "author_name": "박백엔드아키텍트",  # 작성자 이름 추가
                    "created_at": "2024-01-03T00:00:00",
                    "updated_at": "2024-01-03T00:00:00",
                    "start_date": "2024-06-15",
                    "end_date": "2024-08-15",
                    "test_required": False,
                    "recruitment_positions": [
                        {
                            "id": 4,
                            "position_name": "스터디원",
                            "position_type": "ETC",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 6,
                            "target_count": 6,
                            "current_count": 2
                        }
                    ]
                }
            elif project_id == 4:
                return {
                    "id": 4,
                    "title": "🔥 풀스택 개발자 양성 프로젝트 - AI 기반 추천 시스템 구축",
                    "description": "머신러닝과 웹 개발을 결합한 실무 프로젝트입니다. AI 역량 테스트를 통해 실력을 검증하고 함께 성장해요!",
                    "type": "PROJECT",
                    "status": "RECRUITING",
                    "method": "MIXED",
                    "views": 3201,
                    "user_id": "4",  # Convert to string for UUID compatibility
                    "author_name": "최풀스택개발자",  # 작성자 이름 추가
                    "created_at": "2024-01-04T00:00:00",
                    "updated_at": "2024-01-04T00:00:00",
                    "start_date": "2024-07-01",
                    "end_date": "2024-12-31",
                    "test_required": True,
                    "recruitment_positions": [
                        {
                            "id": 5,
                            "position_name": "AI/ML 엔지니어",
                            "position_type": "ETC",
                            "tech_stack": "Python",
                            "required_stacks": "Python",
                            "required_count": 2,
                            "target_count": 2,
                            "current_count": 0
                        },
                        {
                            "id": 6,
                            "position_name": "풀스택 개발자",
                            "position_type": "FRONTEND",
                            "tech_stack": "React",
                            "required_stacks": "React",
                            "required_count": 3,
                            "target_count": 3,
                            "current_count": 1
                        }
                    ]
                }
            else:
                raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"프로젝트 상세 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}", response_model=ProjectDetail)
async def update_project(project_id: int, project_data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    """Update project (only by project owner)"""
    try:
        if await is_db_available():
            repo = ProjectRecruitmentRepository(db)
            project_dict = project_data.dict(exclude_unset=True)
            project = await repo.update_project(project_id, project_dict)
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            return ProjectDetail.from_orm(project)
        else:
            raise HTTPException(status_code=503, detail="Database not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}/status")
async def update_project_status(project_id: int, status_data: ProjectStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Update project status (only by project owner)"""
    try:
        if await is_db_available():
            repo = ProjectRecruitmentRepository(db)
            status_value = ProjectStatus(status_data.status)
            success = await repo.update_project_status(project_id, status_value)
            if not success:
                raise HTTPException(status_code=404, detail="Project not found")
            return {"message": "Status updated successfully"}
        else:
            raise HTTPException(status_code=503, detail="Database not available")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status value")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}",
    summary="프로젝트 삭제",
    description="프로젝트를 영구적으로 삭제합니다. 관련된 모든 데이터도 함께 삭제됩니다.",
    responses={
        200: {"description": "프로젝트 삭제 성공"},
        404: {"description": "프로젝트를 찾을 수 없음"},
        500: {"description": "서버 내부 오류"}
    }
)
async def delete_project(
    project_id: int = Path(..., description="삭제할 프로젝트 ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    ## 프로젝트 삭제
    
    프로젝트를 영구적으로 삭제합니다.
    
    ⚠️ **주의**: 이 작업은 되돌릴 수 없으며, 관련된 모든 데이터가 삭제됩니다.
    
    ### 경로 파라미터:
    - **project_id**: 삭제할 프로젝트의 고유 ID
    
    ### 반환값:
    - 삭제 성공 메시지
    """
    print(f"🗑️ 프로젝트 삭제 요청: ID {project_id}")
    try:
        if await is_db_available():
            repo = ProjectRecruitmentRepository(db)
            success = await repo.delete_project(project_id)
            if not success:
                raise HTTPException(status_code=404, detail="Project not found")
            print(f"✅ 프로젝트 {project_id} 삭제 완료")
            return {"message": "Project deleted successfully"}
        else:
            # 메모리에서 프로젝트 삭제
            global memory_projects
            memory_projects = [p for p in memory_projects if p["id"] != project_id]
            print(f"✅ 메모리에서 프로젝트 {project_id} 삭제 완료")
            return {"message": "Project deleted successfully"}
    except Exception as e:
        print(f"❌ 프로젝트 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))