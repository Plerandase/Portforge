import json
import boto3
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ai_model import Portfolio, TestResult
from app.core.exceptions import BusinessException, ErrorCode
from app.adapters.internal_adapters import project_adapter
from app.services.ai_service import ai_service
from app.core.config import settings
import logging
import httpx

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self):
        # AWS S3 직접 연결 (MinIO 제거됨)
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_TEAM
        self.team_be_url = settings.TEAM_SERVICE_URL

    async def generate_portfolio(self, db: AsyncSession, user_id: str, project_id: int, is_team_leader: bool = False) -> dict:
        """
        포트폴리오 생성 및 저장
        """
        original_user_id = user_id
        
        # 실제 사용자 이름 가져오기
        user_name = "사용자"  # 기본값
        try:
            async with httpx.AsyncClient() as client:
                auth_url = settings.AUTH_SERVICE_URL
                response = await client.get(f"{auth_url}/auth/users/{original_user_id}")
                if response.status_code == 200:
                    user_data = response.json()
                    user_name = user_data.get('nickname') or user_data.get('name') or user_data.get('email', '').split('@')[0] or "사용자"
        except Exception as e:
            logger.warning(f"Failed to fetch user info: {e}")
        
        user_id = "dummy_user_1"  # 테스트용 더미 ID 유지

        # 역할 결정 (팀장 여부에 따라)
        role_description = "프로젝트 팀장" if is_team_leader else "프로젝트 참여자" 

        # 1. 프로젝트 정보 조회
        try:
            project_info = await project_adapter.get_project_details(project_id)
        except Exception:
            raise BusinessException(ErrorCode.INVALID_INPUT, "프로젝트 정보를 불러올 수 없습니다.")

        # 2. 회의록 수집 (Team-BE API 호출)
        team_id = 1 
        meeting_data_list = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.team_be_url}/teams/{team_id}/reports?report_type=MEETING_MINUTES")
                if response.status_code == 200:
                    reports = response.json()
                    for report in reports:
                        if report.get('s3_key'):
                            try:
                                obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=report['s3_key'])
                                file_content = obj['Body'].read().decode('utf-8')
                                meeting_json = json.loads(file_content)
                                meeting_data_list.append(meeting_json)
                            except Exception as e:
                                logger.warning(f"Failed to read S3 file {report['s3_key']}: {e}")
        except Exception as e:
            logger.warning(f"Failed to fetch meeting reports from Team-BE: {e}")

        # 3. 역량 테스트 결과 수집
        tests_res = await db.execute(select(TestResult).where(TestResult.user_id == user_id))
        test_results = tests_res.scalars().all()
        verified_skills = [f"{t.feedback} (Score: {t.score})" for t in test_results if t.score and t.score >= 70] # 70점 이상만 인증

        # 4. 프롬프트 구성
        system_prompt = "You are a professional IT career consultant. Analyze the provided meeting logs and project info to generate a structured portfolio summary."
        
        user_prompt = f"""
        Analyze the following data and generate a portfolio summary for the user '{user_name}'.
        
        [Project Info]
        Title: {project_info['title']}
        Period: {project_info.get('period', '기간 미정')}
        Stack: {', '.join(project_info['tech_stacks'])}
        
        [User Role]
        {role_description}
        
        [Verified Skills (AI Test)]
        {json.dumps(verified_skills, ensure_ascii=False)}
        
        [Meeting Logs (Activity Evidence)]
        {json.dumps(meeting_data_list, ensure_ascii=False, default=str)}
        
        [Task]
        Generate a JSON output with the following fields (Korean):
        1. "role": Use "{role_description}" as the role.
        2. "period": Project period string.
        3. "stack": Tech stack used (highlight verified skills).
        4. "contributions": Array of objects {{ "category": "String", "text": "String" }}. Extract 3 key achievements using STAR method.
        5. "aiAnalysis": A professional one-paragraph evaluation of {user_name}'s performance and soft skills based on meeting behaviors.
        
        Output valid JSON only. No markdown.
        """

        # 5. Bedrock 호출
        try:
            ai_response = await ai_service._invoke_bedrock(system_prompt, user_prompt)
            cleaned = ai_response.strip().replace("```json", "").replace("```", "").strip()
            result_data = json.loads(cleaned)
        except Exception as e:
            logger.error(f"AI Generation Failed: {e}")
            # Fallback Mock Data
            result_data = {
                "role": role_description,
                "period": "2024.06 ~ 2024.08",
                "stack": "React, Node.js",
                "contributions": [{"category": "일반", "text": "AI 서비스 연결 오류로 기본 데이터만 표시됩니다."}],
                "aiAnalysis": "분석 실패"
            }

        # 6. DB 저장/업데이트
        # 기존 데이터 확인 (Upsert)
        existing_res = await db.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .where(Portfolio.project_id == project_id)
        )
        existing_portfolio = existing_res.scalar_one_or_none()
        
        if existing_portfolio:
            existing_portfolio.summary = json.dumps(result_data, ensure_ascii=False)
            # 기존 객체 업데이트
            portfolio = existing_portfolio
        else:
            new_portfolio = Portfolio(
                user_id=user_id,
                project_id=project_id,
                title=f"{project_info['title']} - 포트폴리오",
                summary=json.dumps(result_data, ensure_ascii=False)
            )
            db.add(new_portfolio)
            portfolio = new_portfolio
            
        await db.commit()
        await db.refresh(portfolio)
        
        # portfolio_id를 포함한 결과 반환
        result_data['portfolio_id'] = portfolio.portfolio_id
        
        return result_data

portfolio_service = PortfolioService()
