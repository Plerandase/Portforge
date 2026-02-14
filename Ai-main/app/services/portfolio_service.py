import json
import boto3
from datetime import datetime, timezone, timedelta
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

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

def now_kst() -> datetime:
    """현재 한국 시간 반환"""
    return datetime.now(KST)

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
        # 실제 사용자 이름 가져오기
        user_name = "사용자"  # 기본값
        try:
            async with httpx.AsyncClient() as client:
                auth_url = settings.AUTH_SERVICE_URL
                # /users/batch API 사용 (단일 사용자도 배열로 요청)
                response = await client.post(
                    f"{auth_url}/users/batch",
                    json={"user_ids": [user_id]}
                )
                if response.status_code == 200:
                    users = response.json()
                    if users and len(users) > 0:
                        user_data = users[0]
                        user_name = user_data.get('nickname') or user_data.get('name') or user_data.get('email', '').split('@')[0] or "사용자"
                        logger.info(f"User name fetched: {user_name}")
        except Exception as e:
            logger.warning(f"Failed to fetch user info: {e}")
        
        # 역할 결정 (팀장 여부에 따라)
        role_description = "프로젝트 팀장" if is_team_leader else "프로젝트 참여자" 

        # 1. 프로젝트 정보 조회
        try:
            project_info = await project_adapter.get_project_details(project_id)
        except Exception:
            raise BusinessException(ErrorCode.INVALID_INPUT, "프로젝트 정보를 불러올 수 없습니다.")

        # 2. 회의록 수집 (Team-BE API 호출)
        meeting_data_list = []
        try:
            # 프로젝트의 팀 ID 조회 - project_info에서 가져오거나 별도 조회
            team_id = project_info.get('team_id') or project_id  # team_id가 없으면 project_id 사용
            
            async with httpx.AsyncClient() as client:
                # Team-BE API 경로: /api/v1/teams/{project_id}/reports
                response = await client.get(f"{self.team_be_url}/api/v1/teams/{team_id}/reports?report_type=MEETING_MINUTES")
                logger.info(f"Team reports API response: {response.status_code}")
                if response.status_code == 200:
                    reports = response.json()
                    logger.info(f"Found {len(reports)} meeting reports")
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
        system_prompt = """You are a professional IT career consultant specializing in portfolio creation.
Your task is to create a portfolio summary based ONLY on the provided data.
IMPORTANT: 
- Focus ONLY on the specific user's contributions, not the entire team's work.
- Extract only what THIS USER said, did, or contributed from the meeting logs.
- Do NOT fabricate or assume any achievements, metrics, or specific actions that are not explicitly mentioned.
Always write in Korean."""
        
        # 회의록 유무에 따른 프롬프트 분기
        has_meetings = len(meeting_data_list) > 0
        has_skills = len(verified_skills) > 0
        
        user_prompt = f"""
'{user_name}' 사용자의 개인 포트폴리오를 생성해주세요.

[대상 사용자]
- 이름: {user_name}
- 역할: {role_description}

[프로젝트 정보]
- 프로젝트명: {project_info['title']}
- 진행 기간: {project_info.get('period', '기간 미정')}
- 기술 스택: {', '.join(project_info['tech_stacks']) if project_info['tech_stacks'] else '정보 없음'}
- 프로젝트 설명: {project_info.get('description', '설명 없음')}

[검증된 기술 역량 (AI 테스트 통과)]
{json.dumps(verified_skills, ensure_ascii=False) if has_skills else '테스트 결과 없음'}

[회의록 및 활동 기록]
{json.dumps(meeting_data_list, ensure_ascii=False, default=str) if has_meetings else '회의록 없음'}

[중요 지침]
1. 회의록에서 '{user_name}'이 직접 발언하거나 언급된 내용만 추출하세요.
2. 다른 팀원의 기여는 이 포트폴리오에 포함하지 마세요.
3. '{user_name}'이 회의록에서 언급되지 않았다면, 역할 기반으로 간단히 작성하되 구체적 성과는 지어내지 마세요.
4. 수치(%, 시간 단축 등)는 회의록에 명시된 경우에만 사용하세요.

다음 JSON 형식으로 출력해주세요:
{{
    "role": "{role_description}",
    "period": "프로젝트 기간",
    "stack": "사용한 기술 스택",
    "contributions": [
        {{"category": "카테고리명", "text": "{user_name}의 실제 기여 내용"}},
        {{"category": "카테고리명", "text": "기여 내용 2"}},
        {{"category": "카테고리명", "text": "기여 내용 3"}}
    ],
    "aiAnalysis": "{user_name}에 대한 평가 (회의록 기반, 없으면 정보 부족 명시)"
}}

JSON만 출력하세요. 마크다운 없이.
"""

        # 5. Bedrock 호출
        try:
            ai_response = await ai_service._invoke_bedrock(system_prompt, user_prompt)
            cleaned = ai_response.strip().replace("```json", "").replace("```", "").strip()
            result_data = json.loads(cleaned)
        except Exception as e:
            logger.error(f"AI Generation Failed: {e}")
            raise BusinessException(ErrorCode.AI_GENERATION_FAILED, "AI 포트폴리오 생성에 실패했습니다. 잠시 후 다시 시도해주세요.")

        # 6. S3에 포트폴리오 JSON 저장
        s3_key = f"{project_id}/portfolios/{user_id}.json"
        try:
            portfolio_json = json.dumps(result_data, ensure_ascii=False, indent=2)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=portfolio_json.encode('utf-8'),
                ContentType='application/json'
            )
            logger.info(f"Portfolio saved to S3: {s3_key}")
        except Exception as e:
            logger.error(f"Failed to save portfolio to S3: {e}")
            # S3 저장 실패해도 DB 저장은 진행

        # 7. DB 저장 (항상 새로 생성)
        logger.info(f"DB 저장 시작 - user_id: {user_id}, project_id: {project_id}")
        try:
            portfolio_title = f"{project_info['title']} - 포트폴리오"
            logger.info(f"새 포트폴리오 생성: {portfolio_title}")
            
            new_portfolio = Portfolio(
                user_id=user_id,
                project_id=project_id,
                title=portfolio_title,
                summary=result_data.get('aiAnalysis', ''),
                role_description=result_data.get('role', role_description),
                tech_stack_usage=result_data.get('stack', ''),
                problem_solving='\n\n'.join([f"[{c.get('category', '일반')}] {c.get('text', '')}" for c in result_data.get('contributions', [])]),
                growth_point=result_data.get('aiAnalysis', ''),
                s3_key=s3_key,
                created_at=now_kst(),
                updated_at=now_kst()
            )
            db.add(new_portfolio)
            portfolio = new_portfolio
            
            logger.info("DB commit 시작")
            await db.commit()
            logger.info("DB commit 완료")
            await db.refresh(portfolio)
            logger.info(f"DB 저장 완료 - portfolio_id: {portfolio.portfolio_id}")
        except Exception as db_error:
            logger.error(f"DB 저장 실패: {db_error}")
            await db.rollback()
            raise BusinessException(ErrorCode.AI_GENERATION_FAILED, f"포트폴리오 DB 저장 실패: {str(db_error)}")
        
        # portfolio_id와 title을 포함한 결과 반환
        result_data['portfolio_id'] = portfolio.portfolio_id
        result_data['title'] = portfolio.title
        
        return result_data

    async def delete_portfolio(self, db: AsyncSession, portfolio_id: int) -> dict:
        """
        포트폴리오 삭제 (S3 파일 포함)
        """
        from sqlalchemy import select
        
        # 포트폴리오 조회
        result = await db.execute(
            select(Portfolio).where(Portfolio.portfolio_id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise BusinessException(ErrorCode.INVALID_INPUT, "포트폴리오를 찾을 수 없습니다.")
        
        # S3에서 포트폴리오 JSON 파일 삭제
        if hasattr(portfolio, 's3_key') and portfolio.s3_key:
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=portfolio.s3_key)
                logger.info(f"S3 포트폴리오 파일 삭제 완료: {portfolio.s3_key}")
            except Exception as e:
                logger.warning(f"S3 포트폴리오 파일 삭제 실패 (무시): {e}")
        
        # S3에서 썸네일 파일 삭제
        if portfolio.thumbnail_url:
            try:
                if self.bucket_name in portfolio.thumbnail_url:
                    s3_key = portfolio.thumbnail_url.split(f"{self.bucket_name}/")[-1]
                    self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
                    logger.info(f"S3 썸네일 삭제 완료: {s3_key}")
            except Exception as e:
                logger.warning(f"S3 썸네일 삭제 실패 (무시): {e}")
        
        # DB에서 포트폴리오 삭제
        await db.delete(portfolio)
        await db.commit()
        
        return {
            "status": "success",
            "message": "Portfolio deleted successfully",
            "portfolio_id": portfolio_id
        }

portfolio_service = PortfolioService()
