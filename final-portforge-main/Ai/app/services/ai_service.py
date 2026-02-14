from datetime import datetime, timedelta
import json
import random
import logging
import aioboto3
from typing import Optional
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.exceptions import BusinessException, ErrorCode
from app.schemas.ai_schema import (
    QuestionRequest, QuestionResponse, AnalysisRequest, AnalysisResponse, 
    QuestionItem, AnalysisResponse
)
from app.repositories.ai_repository import TestRepository
from app.models.ai_model import Test, TestResult

logger = logging.getLogger(__name__)

class AiService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.model_id = settings.BEDROCK_MODEL_ID
        self.region = settings.BEDROCK_REGION
        
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.warning("AWS Credentials are missing. Bedrock calls may fail.")

    async def _invoke_bedrock(self, system_prompt: str, user_prompt: str) -> str:
        """
        Common method to invoke AWS Bedrock
        """
        async with self.session.client("bedrock-runtime", region_name=self.region) as client:
            try:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user", 
                            "content": [
                                {
                                    "type": "text",
                                    "text": user_prompt
                                }
                            ]
                        }
                    ],
                    "temperature": 0.7
                }
                response = await client.invoke_model(modelId=self.model_id, body=json.dumps(body))
                response_body = await response['body'].read()
                response_json = json.loads(response_body)
                
                if 'content' in response_json:
                    return response_json['content'][0]['text']
                else:
                    raise BusinessException(ErrorCode.AI_INVALID_RESPONSE, "Invalid response format from Bedrock")
            except ClientError as e:
                logger.error(f"Bedrock ClientError: {e}")
                raise BusinessException(ErrorCode.AI_GENERATION_FAILED, f"AWS Bedrock Error: {str(e)}")
            except Exception as e:
                logger.error(f"Bedrock invocation failed: {e}")
                if isinstance(e, BusinessException): raise e
                raise BusinessException(ErrorCode.AI_GENERATION_FAILED, str(e))

    async def generate_questions(self, request: QuestionRequest, repo: TestRepository, user_id: str) -> QuestionResponse:
        # 1. 주간 테스트 횟수 제한 체크 (DB 실패 시 무시하고 진행)
        try:
            weekly_count = await repo.count_weekly_tests(user_id)
            if weekly_count >= 5:
                raise BusinessException(ErrorCode.TEST_LIMIT_EXCEEDED, "이번 주 테스트 가능 횟수(5회)를 모두 소진했습니다.")
        except BusinessException:
            raise
        except Exception:
            logger.warning("Failed to check weekly count (DB Error). Proceeding without check.")

        target_count = request.count
        db_limit = 3

        # 2. MIXED 타입: DB 재사용 (객관식 1개 + 주관식 1개) + AI 생성 (나머지)
        if request.type == "MIXED":
            logger.info("MIXED request: DB 1+1, AI fills the rest")
            
            db_mc_questions: list[Test] = []
            db_sa_questions: list[Test] = []
            
            # DB에서 객관식 1개, 주관식 1개 조회 시도
            try:
                db_mc_questions = await repo.get_questions_by_type(request.stack, request.difficulty, "MULTIPLE_CHOICE", 1)
                db_sa_questions = await repo.get_questions_by_type(request.stack, request.difficulty, "SHORT_ANSWER", 1)
                logger.info(f"DB에서 조회: MC={len(db_mc_questions)}, SA={len(db_sa_questions)}")
            except Exception as e:
                logger.warning(f"DB 조회 실패: {e}. AI로 전체 생성.")
                db_mc_questions = []
                db_sa_questions = []
            
            # DB에서 가져온 문제들의 question 텍스트 (중복 방지용)
            existing_questions_text = set()
            for q in db_mc_questions + db_sa_questions:
                existing_questions_text.add(q.question_json.get('question', '').strip().lower())
            
            # AI로 생성할 개수 계산
            ai_mc_needed = 3 - len(db_mc_questions)  # 객관식: 총 3개 필요
            ai_sa_needed = 2 - len(db_sa_questions)  # 주관식: 총 2개 필요
            
            logger.info(f"AI 생성 필요: MC={ai_mc_needed}, SA={ai_sa_needed}")
            
            # AI로 문제 생성 (정확한 개수 지정)
            ai_questions = await self._generate_questions_from_ai(
                request.stack, request.difficulty, 
                ai_mc_needed + ai_sa_needed,
                "MIXED",
                target_mc=ai_mc_needed,
                target_sa=ai_sa_needed
            )
            
            # AI 생성 문제에서 중복 제거 및 타입별 분류
            ai_mc_list: list[QuestionItem] = []
            ai_sa_list: list[QuestionItem] = []
            
            for q in ai_questions:
                q_text = q.question.strip().lower()
                if q_text in existing_questions_text:
                    logger.info(f"중복 문제 제외: {q_text[:30]}...")
                    continue
                existing_questions_text.add(q_text)
                
                if q.type == 'MULTIPLE_CHOICE' and len(ai_mc_list) < ai_mc_needed:
                    ai_mc_list.append(q)
                elif q.type == 'SHORT_ANSWER' and len(ai_sa_list) < ai_sa_needed:
                    ai_sa_list.append(q)
            
            # 부족하면 해당 타입만 추가 생성
            if len(ai_mc_list) < ai_mc_needed:
                shortage = ai_mc_needed - len(ai_mc_list)
                logger.info(f"객관식 {shortage}개 부족, 추가 생성")
                extra_mc = await self._generate_questions_from_ai(
                    request.stack, request.difficulty, shortage + 1, "MULTIPLE_CHOICE"
                )
                for q in extra_mc:
                    q_text = q.question.strip().lower()
                    if q_text not in existing_questions_text and len(ai_mc_list) < ai_mc_needed:
                        existing_questions_text.add(q_text)
                        ai_mc_list.append(q)
            
            if len(ai_sa_list) < ai_sa_needed:
                shortage = ai_sa_needed - len(ai_sa_list)
                logger.info(f"주관식 {shortage}개 부족, 추가 생성")
                extra_sa = await self._generate_questions_from_ai(
                    request.stack, request.difficulty, shortage + 1, "SHORT_ANSWER"
                )
                for q in extra_sa:
                    q_text = q.question.strip().lower()
                    if q_text not in existing_questions_text and len(ai_sa_list) < ai_sa_needed:
                        existing_questions_text.add(q_text)
                        ai_sa_list.append(q)
            
            # DB 문제를 QuestionItem으로 변환
            db_mc_items = [QuestionItem(**q.question_json) for q in db_mc_questions]
            db_sa_items = [QuestionItem(**q.question_json) for q in db_sa_questions]
            
            # 최종 조합: 객관식 3개 + 주관식 2개
            final_mc = db_mc_items + ai_mc_list
            final_sa = db_sa_items + ai_sa_list
            
            final_list = final_mc[:3] + final_sa[:2]
            random.shuffle(final_list)
            
            mc_count = len([q for q in final_list if q.type == 'MULTIPLE_CHOICE'])
            sa_count = len([q for q in final_list if q.type == 'SHORT_ANSWER'])
            logger.info(f"MIXED 최종: MC={mc_count}, SA={sa_count}, Total={len(final_list)}")
            
            # 5개 미만이면 에러 (안전장치)
            if len(final_list) < 5:
                logger.error(f"문제 생성 부족: {len(final_list)}개만 생성됨")
                raise BusinessException(ErrorCode.AI_GENERATION_FAILED, "문제 생성에 실패했습니다. 다시 시도해주세요.")
            
            # 새로 생성된 AI 문제는 DB에 저장 (재사용 위해)
            try:
                for q_item in ai_mc_list + ai_sa_list:
                    new_test_row = Test(
                        stack_name=request.stack,
                        question_json=q_item.model_dump(),
                        difficulty=request.difficulty,
                        source_prompt="MIXED Generation"
                    )
                    await repo.create_test(new_test_row)
                logger.info(f"AI 생성 문제 {len(ai_mc_list) + len(ai_sa_list)}개 DB 저장 완료")
            except Exception as e:
                logger.warning(f"DB 저장 실패: {e}")
            
            return QuestionResponse(questions=final_list)

        # 3. SHORT_ANSWER도 100% AI 생성
        if request.type == "SHORT_ANSWER":
            logger.info("SHORT_ANSWER request: generating all from AI.")
            ai_questions = await self._generate_questions_from_ai(request.stack, request.difficulty, target_count, "SHORT_ANSWER")
            return QuestionResponse(questions=ai_questions)

        # 4. MULTIPLE_CHOICE: DB + AI 혼합
        existing_questions: list[Test] = []
        try:
            existing_questions = await repo.get_random_questions(request.stack, request.difficulty, db_limit)
        except Exception:
            logger.warning("Failed to fetch existing questions (DB Error). Fetching all from AI.")
        
        current_count = len(existing_questions)
        needed_from_ai = target_count - current_count
        
        # 최소 2개는 AI가 새로 만들도록 보장
        if needed_from_ai < 2:
            needed_from_ai = 2
            
        ai_questions_item = []
        if needed_from_ai > 0:
            ai_questions_item = await self._generate_questions_from_ai(request.stack, request.difficulty, needed_from_ai, "MULTIPLE_CHOICE")
            
            # 새로 생성된 문제는 DB에 저장 (실패 시 무시)
            try:
                for q_item in ai_questions_item:
                    new_test_row = Test(
                        stack_name=request.stack,
                        question_json=q_item.model_dump(),
                        difficulty=request.difficulty,
                        source_prompt="Hybrid Generation"
                    )
                    await repo.create_test(new_test_row)
            except Exception:
                logger.warning("Failed to save generated questions to DB.")
        
        # DB 형식을 응답 형식으로 변환
        db_questions_item = [QuestionItem(**q.question_json) for q in existing_questions]
        
        # 합치기 및 셔플
        final_list = db_questions_item + ai_questions_item
        random.shuffle(final_list)
        
        # 정확히 target_count 개수만큼 자르기
        final_list = final_list[:target_count]
        
        return QuestionResponse(questions=final_list)

    async def _generate_questions_from_ai(self, stack: str, difficulty: str, count: int, q_type: str = "MULTIPLE_CHOICE", target_mc: int = 3, target_sa: int = 2) -> list[QuestionItem]:
        # '면접관' -> '프로젝트 테크 리드'로 페르소나 변경
        system_prompt = "당신은 실무 중심의 프로젝트 테크 리드(Tech Lead)입니다. 이론적인 지식보다는 실제 개발 상황에서의 문제 해결 능력과 트러블 슈팅 역량을 검증하는 데 집중하세요. JSON 배열만 출력합니다."
        
        if q_type == "MIXED":
            # 동적으로 객관식/주관식 개수 지정
            total_count = target_mc + target_sa
            user_prompt = f"""
'{stack}' 기술 테스트 문제를 생성합니다. 반드시 아래 형식을 정확히 따르세요.

[필수 조건]
- 총 {total_count}개 문제 생성
- 객관식(MULTIPLE_CHOICE): 정확히 {target_mc}개
- 주관식(SHORT_ANSWER): 정확히 {target_sa}개
- 난이도: {difficulty}

[객관식 형식]
{{
  "type": "MULTIPLE_CHOICE",
  "question": "질문 내용",
  "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
  "answer": 0,
  "explanation": "해설"
}}

[주관식 형식]
{{
  "type": "SHORT_ANSWER",
  "question": "코드나 상황을 주고 해결책을 물어보는 질문",
  "options": [],
  "answer": "모범 답안 키워드",
  "explanation": "해설",
  "grading_criteria": "채점 기준"
}}

JSON 배열만 출력하세요. 객관식 {target_mc}개 먼저, 그 다음 주관식 {target_sa}개 순서로.
"""
        elif q_type == "SHORT_ANSWER":
            user_prompt = f"""
            '{stack}' 기술을 사용하여 프로젝트를 진행할 예비 팀원을 선발하려 합니다.
            {difficulty} 난이도의 실무 중심 '주관식(단답형 또는 코드 트러블슈팅)' 문제 {count}개를 한국어로 생성하세요.
            
            [출제 가이드]
            1. 코드 스니펫을 제시하고 버그를 찾거나, 특정 상황에서의 해결책을 서술하게 하세요.
            2. 정답은 명확한 키워드나 핵심 로직이 포함되어야 합니다.
            
            [출력 형식]
            JSON 배열 (각 객체는 question, answer, explanation, grading_criteria 포함)
            - type: "SHORT_ANSWER" (필수)
            - question: 구체적인 상황이나 코드가 포함된 질문 (한국어)
            - answer: 모범 답안 (핵심 키워드 포함 필수)
            - explanation: 해설 및 실무 팁
            - grading_criteria: 채점 기준 (AI가 채점할 때 참고할 핵심 포인트 1-2문장)
            - options: [] (빈 리스트)
            
            JSON 데이터만 출력하세요.
            """
        else:
            user_prompt = f"""
            '{stack}' 기술을 사용하여 프로젝트를 진행할 예비 팀원을 선발하려 합니다.
            {difficulty} 난이도의 실무 중심 '객관식' 문제 {count}개를 한국어로 생성하세요.
            
            [출제 가이드]
            1. 단순 문법이나 암기형 지식보다는, '프로젝트 수행 중 마주칠 수 있는 문제 상황'을 제시하세요.
               (예: "API 응답이 느릴 때 가장 적절한 캐싱 전략은?", "메모리 누수가 의심될 때 우선적으로 확인해야 할 것은?")
            2. 실제 개발 현장에서 실수하기 쉬운 부분이나 베스트 프랙티스를 다루세요.
            
            [출력 형식]
            JSON 배열 (각 객체는 question, options[], answer(0-3), explanation 포함)
            - type: "MULTIPLE_CHOICE" (필수)
            - question: 구체적인 상황이나 코드가 포함된 질문 (한국어)
            - options: 4개의 선택지 (실무적으로 타당해 보이는 오답 포함)
            - answer: 정답 인덱스 (0~3)
            - explanation: 정답인 이유와 실무 적용 팁 (한국어)
            
            JSON 데이터만 출력하세요. 마크다운 포맷이나 부가 설명 없이.
            """
        try:
            result_text = await self._invoke_bedrock(system_prompt, user_prompt)
            # Markdown cleaning
            cleaned_text = result_text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned_text)
            
            logger.info(f"AI returned {len(data)} questions for type={q_type}")
            
            # 후처리: type 필드 검증 및 보정
            processed_data = []
            for item in data:
                if 'type' not in item:
                    # options가 있고 내용이 있으면 객관식, 아니면 주관식으로 추론
                    if item.get('options') and len(item['options']) > 0:
                        item['type'] = 'MULTIPLE_CHOICE'
                    else:
                        item['type'] = 'SHORT_ANSWER'
                        item['options'] = []
                
                # 주관식일 경우 options 빈 리스트 보장
                if item['type'] == 'SHORT_ANSWER':
                    item['options'] = []
                    if 'grading_criteria' not in item:
                        item['grading_criteria'] = "핵심 개념 이해도와 실무 적용력을 평가"

                processed_data.append(item)
            
            # MIXED 타입일 경우: 정확히 객관식 3개 + 주관식 2개 보장
            if q_type == "MIXED" and len(processed_data) >= 5:
                mc_questions = [q for q in processed_data if q.get('type') == 'MULTIPLE_CHOICE']
                sa_questions = [q for q in processed_data if q.get('type') == 'SHORT_ANSWER']
                
                logger.info(f"MIXED mode: {len(mc_questions)} MC, {len(sa_questions)} SA questions found")
                
                # 객관식이 3개 초과면 초과분을 주관식으로 변환
                while len(mc_questions) > 3 and len(sa_questions) < 2:
                    q = mc_questions.pop()
                    q['type'] = 'SHORT_ANSWER'
                    if isinstance(q.get('answer'), int) and q.get('options'):
                        answer_idx = q['answer']
                        if 0 <= answer_idx < len(q['options']):
                            q['answer'] = q['options'][answer_idx]
                    q['options'] = []
                    q['grading_criteria'] = q.get('grading_criteria') or "핵심 개념 이해도와 논리적 설명력을 평가"
                    sa_questions.append(q)
                
                # 주관식이 2개 미만이면 객관식에서 변환
                while len(sa_questions) < 2 and len(mc_questions) > 0:
                    q = mc_questions.pop()
                    q['type'] = 'SHORT_ANSWER'
                    if isinstance(q.get('answer'), int) and q.get('options'):
                        answer_idx = q['answer']
                        if 0 <= answer_idx < len(q['options']):
                            q['answer'] = q['options'][answer_idx]
                    q['options'] = []
                    q['grading_criteria'] = q.get('grading_criteria') or "핵심 개념 이해도와 논리적 설명력을 평가"
                    sa_questions.append(q)
                
                # 최종 조합: 객관식 3개 + 주관식 2개
                processed_data = mc_questions[:3] + sa_questions[:2]
                logger.info(f"MIXED final: {len([q for q in processed_data if q.get('type') == 'MULTIPLE_CHOICE'])} MC, {len([q for q in processed_data if q.get('type') == 'SHORT_ANSWER'])} SA")

            return [QuestionItem(**item) for item in processed_data]
        except Exception as e:
            logger.error(f"AI question generation failed: {str(e)}")
            raise BusinessException(ErrorCode.AI_INVALID_RESPONSE, "Failed to parse AI question response")

    async def analyze_results(self, request: AnalysisRequest, repo: TestRepository, user_id: str) -> AnalysisResponse:
        # 레벨 결정 로직
        level = self._determine_level(request.score)
        
        # 정답률 계산
        accuracy = round((request.correct_count / request.total_questions) * 100, 1) if request.total_questions > 0 else 0
        
        # AI 피드백 생성 (JSON 구조화: 상세 분석)
        # 면접관 -> 팀 리더 / 지원자 -> 예비 팀원
        system_prompt = "당신은 프로젝트의 성공을 이끄는 테크 리드(Tech Lead)입니다. 예비 팀원의 테스트 결과를 바탕으로, 이 사람이 우리 팀에서 얼마나 실무적으로 기여할 수 있을지 따뜻하지만 냉철하게 분석해주세요."
        
        user_prompt = f"""
        '{request.stack}' 기술 스택을 사용하는 프로젝트의 예비 팀원 역량 테스트 결과입니다.
        
        [테스트 결과]
        - 기술 스택: {request.stack}
        - 총 문항 수: {request.total_questions}
        - 정답 수: {request.correct_count}
        - 정답률: {accuracy}%
        - 점수: {request.score}점 ({level})
        
        위 데이터를 바탕으로 다음 JSON 항목을 채워주세요:
        {{
            "summary": "(3-4문장) 이 예비 팀원의 실무 역량 요약. 단순 점수 나열보다는 '프로젝트 투입 시 기대되는 모습'을 서술해주세요.",
            "strengths": "(2-3문장) 프로젝트 수행 관점에서의 강점. (예: '트러블 슈팅 감각이 뛰어남', '최적화에 대한 이해도가 높음')",
            "improvements": "(2-3문장) 팀 차원에서 보완해주거나 학습이 필요한 부분. (예: '비동기 처리에 대한 실무 경험 보완 필요')",
            "growth_guide": "(3-4문장) 이 팀원이 프로젝트 에이스로 성장하기 위한 가이드. 실무 프로젝트 주제나 심화 기술 키워드 추천.",
            "hiring_guide": "(2-3문장) (팀 빌딩 조언) 이 팀원에게 가장 적합한 역할(Role)이나 태스크 유형 추천. (예: 'API 설계보다는 UI 인터랙션 구현에 강점이 있음')",
            "encouragement": "(1-2문장) 함께 성장하자는 톤의 긍정적인 메시지."
        }}
        
        JSON 데이터만 출력하세요. 마크다운 포맷 없이.
        """
        try:
            feedback = await self._invoke_bedrock(system_prompt, user_prompt)
            # Markdown 코드 블럭 제거 (혹시 포함될 경우)
            feedback = feedback.replace("```json", "").replace("```", "").strip()
        except Exception as e:
            logger.error(f"Failed to generate AI feedback: {e}", exc_info=True)
            feedback = f"AI 분석 서비스를 일시적으로 사용할 수 없습니다. (Error: {str(e)[:50]}...)"

        # 결과 DB 저장
        try:
            new_result = TestResult(
                user_id=user_id,
                project_id=request.project_id,
                application_id=request.application_id,
                test_type="APPLICATION" if request.project_id else "PRACTICE",
                score=request.score,
                feedback=feedback
            )
            print(f"DEBUG: Saving TestResult for user {user_id}...")
            await repo.create_test_result(new_result)
            print(f"DEBUG: TestResult saved successfully!")
        except Exception as e:
            print(f"DEBUG: Failed to save test result: {e}")
            logger.error(f"Failed to save test result: {e}")
            # 저장은 실패해도 리턴은 해주는게 UX상 나음 (선택사항)
            # raise BusinessException(ErrorCode.DB_ERROR, "결과 저장 실패")
        
        return AnalysisResponse(
            score=request.score,
            level=level,
            feedback=feedback
        )

    async def get_latest_result(self, user_id: str, repo: TestRepository) -> Optional[AnalysisResponse]:
        try:
            result = await repo.get_latest_result_by_user(user_id)
            if not result:
                return None
            
            # Level 계산 (DB에 없으므로)
            score = result.score or 0
            level = "고급" if score >= 80 else "중급" if score >= 60 else "초급"
            
            return AnalysisResponse(
                score=score,
                level=level,
                feedback=result.feedback or ""
            )
        except Exception as e:
            logger.error(f"Error fetching test result: {e}")
            return None

    def _determine_level(self, score: int) -> str:
        if score >= 90: return '고급 (Expert)'
        if score >= 65: return '중급 (Advanced)'
        if score >= 35: return '초급 (Beginner)'
        return '입문 (Novice)'

    async def predict_applicant_suitability(self, applicants_data: list[dict]) -> str:
        system_prompt = "You are an expert HR manager and technical team lead."
        user_prompt = f"""
        Analyze the following candidates for a software project team:
        {json.dumps(applicants_data, ensure_ascii=False, indent=2)}

        Task:
        1. Recommend the most suitable candidate(s).
        2. Briefly analyze each candidate's strengths and weaknesses based on their score, feedback, and message.
        3. Provide final selection advice for the team leader.
        
        Language: Korean
        Format: Markdown (Use bullet points and bold text)
        """
        return await self._invoke_bedrock(system_prompt, user_prompt)

    async def generate_minutes_from_chat(self, chat_text: str) -> dict:
        """회의록 생성: 채팅 텍스트를 분석하여 구조화된 회의록 JSON 반환"""
        system_prompt = "You are an expert meeting secretary. Output purely JSON."
        user_prompt = f"""
    Summarize the following meeting chat logs into a structured JSON.
    JSON Structure: {{
        "date": "YYYY-MM-DD",
        "attendees": ["Name", ...],
        "agenda": "Main Topic",
        "decisions": ["Decision 1", ...],
        "action_items": [ {{"task": "Task description", "assignee": "Name"}} ],
        "summary": "Overall summary of the meeting"
    }}
    Language: Korean.
    
    [Chat Logs]
    {chat_text}
    """
        response_text = await self._invoke_bedrock(system_prompt, user_prompt)
        try:
             cleaned = response_text.strip().replace("```json", "").replace("```", "").strip()
             return json.loads(cleaned)
        except Exception:
             # Fallback if JSON parsing fails
             logger.warning("Failed to parse AI response as JSON. Returning raw text.")
             return {"summary": response_text}

    async def grade_answer(self, question: str, user_answer: str, model_answer: str, criteria: str) -> dict:
        """
        주관식 답변 AI 채점
        """
        system_prompt = "당신은 공정하고 꼼꼼한 기술 면접관입니다. 사용자 답안을 채점하여 JSON으로 반환하세요."
        user_prompt = f"""
        다음 주관식 문제에 대한 사용자의 답안을 채점해주세요.
        
        [문제] {question}
        [모범 답안] {model_answer}
        [채점 기준] {criteria}
        [사용자 답안] {user_answer}
        
        [요청사항]
        1. 모범 답안의 핵심 키워드나 로직이 사용자 답안에 포함되어 있는지 확인하세요.
        2. 점수는 0~100점 사이의 정수로 매기세요. (70점 이상이면 통과)
        3. 피드백은 구체적으로 작성하세요 (무엇이 좋았고, 무엇이 부족한지).
        
        [출력 형식 (JSON)]
        {{
            "score": 85,
            "is_correct": true,
            "feedback": "핵심 개념인 A는 잘 설명했으나, B에 대한 언급이 부족합니다."
        }}
        """
        try:
            res_text = await self._invoke_bedrock(system_prompt, user_prompt)
            cleaned = res_text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
        except Exception:
            # 채점 실패 시 보수적으로 처리 (오답 처리 방지 위해 0점보단 수동확인 필요 등)
            return {"score": 0, "is_correct": False, "feedback": "AI 채점 실패. 재시도 필요."}

ai_service = AiService()
