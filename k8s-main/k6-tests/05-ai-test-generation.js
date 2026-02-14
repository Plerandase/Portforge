/**
 * Portforge - AI 테스트 문제 생성 부하 테스트
 * 
 * 테스트 대상: AWS Bedrock API 호출, AI 서비스 안정성
 * 
 * 호출 API (AI Service):
 *   1. POST /ai/test/questions - AI 문제 생성 (Bedrock 호출)
 *   2. POST /ai/test/grade - AI 답안 채점 (Bedrock 호출)
 *   3. POST /ai/test/analyze - 테스트 결과 분석 (Bedrock 호출)
 * 
 * 테스트 방식: RPS(초당 요청 수) 기반
 * 
 * 주의사항:
 *   - Bedrock API 호출 비용 발생
 *   - AI 서비스는 응답 시간이 길어 RPS를 낮게 설정
 *   - 10,000건은 비용 문제로 1,000건으로 조정 (필요시 수정)
 * 
 * 실행 방법:
 *   k6 run k8s/k6-tests/05-ai-test-generation.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 테스트할 기술 스택
const TECH_STACKS = ['React', 'Spring Boot', 'Python', 'Node.js', 'TypeScript'];
const DIFFICULTIES = ['EASY', 'MEDIUM', 'HARD'];
const QUESTION_TYPES = ['MULTIPLE_CHOICE', 'SHORT_ANSWER', 'MIXED'];

// AI 서비스는 Bedrock 비용 때문에 RPS를 낮게 설정
// 필요시 TARGET_RPS와 TEST_DURATION 조정
const TARGET_RPS = 5;            // 초당 5건 (Bedrock throttling 고려)
const TEST_DURATION = '200s';    // 200초
const TARGET_ITERATIONS = 1000;  // AI는 비용 문제로 1,000건 (필요시 조정)

// 커스텀 메트릭
const errorRate = new Rate('errors');
const questionGenLatency = new Trend('question_gen_latency', true);
const gradeLatency = new Trend('grade_latency', true);
const analyzeLatency = new Trend('analyze_latency', true);
const questionsGenerated = new Counter('questions_generated');
const bedrockCalls = new Counter('bedrock_calls');
const totalRequests = new Counter('total_requests');

// ============================================================
// 테스트 시나리오 설정 (RPS 기반)
// ============================================================
export const options = {
  scenarios: {
    // RPS 기반 부하 테스트
    rps_load_test: {
      executor: 'constant-arrival-rate',
      rate: TARGET_RPS,
      timeUnit: '1s',
      duration: TEST_DURATION,
      preAllocatedVUs: 50,
      maxVUs: 100,
      tags: { test_type: 'rps_load' },
    },
  },

  thresholds: {
    // AI 응답은 느릴 수 있으므로 여유있게 설정
    http_req_duration: ['p(95)<30000', 'p(99)<60000'],
    errors: ['rate<0.2'],
    question_gen_latency: ['p(95)<25000'],
    grade_latency: ['p(95)<10000'],
    analyze_latency: ['p(95)<15000'],
    total_requests: ['count>=1000'],
  },
};

// ============================================================
// 헬퍼 함수
// ============================================================
function getRandomStack() {
  return TECH_STACKS[Math.floor(Math.random() * TECH_STACKS.length)];
}

function getRandomDifficulty() {
  return DIFFICULTIES[Math.floor(Math.random() * DIFFICULTIES.length)];
}

function getRandomType() {
  return QUESTION_TYPES[Math.floor(Math.random() * QUESTION_TYPES.length)];
}

// ============================================================
// 테스트 실행
// ============================================================
export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    timeout: '60s',
  };

  const stack = getRandomStack();
  const difficulty = getRandomDifficulty();

  group('AI 테스트 문제 생성', function () {
    
    // 1. 문제 생성 요청 (Bedrock 호출)
    group('문제 생성', function () {
      const payload = JSON.stringify({
        stack: stack,
        difficulty: difficulty,
        type: getRandomType(),
        count: 5,
      });

      const res = http.post(
        `${BASE_URL}/ai/test/questions`,
        payload,
        { ...params, tags: { name: 'POST_generate_questions' } }
      );

      questionGenLatency.add(res.timings.duration);
      bedrockCalls.add(1);
      totalRequests.add(1);

      const ok = check(res, {
        'gen: status 200': (r) => r.status === 200,
        'gen: has questions': (r) => {
          try {
            const body = JSON.parse(r.body);
            return body.questions && body.questions.length > 0;
          } catch {
            return false;
          }
        },
      });

      if (ok) {
        try {
          const body = JSON.parse(res.body);
          questionsGenerated.add(body.questions?.length || 0);
        } catch {}
      }

      errorRate.add(!ok);

      // 생성된 문제로 채점 테스트 (30% 확률)
      if (ok && Math.random() > 0.7) {
        try {
          const body = JSON.parse(res.body);
          const questions = body.questions || [];
          const shortAnswer = questions.find(q => q.type === 'SHORT_ANSWER');
          
          if (shortAnswer) {
            // 2. AI 채점 요청
            group('답안 채점', function () {
              const gradePayload = JSON.stringify({
                question: shortAnswer.question,
                user_answer: '테스트 답변입니다. 핵심 개념을 설명하면...',
                model_answer: shortAnswer.answer || '모범 답안',
                grading_criteria: shortAnswer.grading_criteria || '핵심 개념 이해도 평가',
              });

              const gradeRes = http.post(
                `${BASE_URL}/ai/test/grade`,
                gradePayload,
                { ...params, tags: { name: 'POST_grade_answer' } }
              );

              gradeLatency.add(gradeRes.timings.duration);
              bedrockCalls.add(1);
              totalRequests.add(1);

              const gradeOk = check(gradeRes, {
                'grade: status 200': (r) => r.status === 200,
              });

              errorRate.add(!gradeOk);
            });
          }
        } catch {}
      }
    });

    // 결과 분석 요청 (20% 확률)
    if (Math.random() > 0.8) {
      group('결과 분석', function () {
        const analyzePayload = JSON.stringify({
          stack: stack,
          total_questions: 5,
          correct_count: Math.floor(Math.random() * 5) + 1,
          score: Math.floor(Math.random() * 100),
          user_id: `test_user_${Date.now()}`,
        });

        const analyzeRes = http.post(
          `${BASE_URL}/ai/test/analyze`,
          analyzePayload,
          { ...params, tags: { name: 'POST_analyze_results' } }
        );

        analyzeLatency.add(analyzeRes.timings.duration);
        bedrockCalls.add(1);
        totalRequests.add(1);

        const analyzeOk = check(analyzeRes, {
          'analyze: status 200': (r) => r.status === 200,
        });

        errorRate.add(!analyzeOk);
      });
    }
  });
}

// ============================================================
// 테스트 종료 후 요약
// ============================================================
export function handleSummary(data) {
  const totalReqs = data.metrics.http_reqs?.values?.count || 0;
  
  const summary = {
    timestamp: new Date().toISOString(),
    testName: 'AI 테스트 문제 생성 부하 테스트 (RPS 기반)',
    testConfig: {
      targetRPS: TARGET_RPS,
      duration: TEST_DURATION,
      targetIterations: TARGET_ITERATIONS,
    },
    warning: 'Bedrock API 호출 비용이 발생합니다!',
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: totalReqs,
      achievedRPS: (totalReqs / 200).toFixed(2),
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 0,
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 0,
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2) + '%',
      questionsGenerated: data.metrics.questions_generated?.values?.count || 0,
      bedrockCalls: data.metrics.bedrock_calls?.values?.count || 0,
    },
    apiMetrics: {
      questionGeneration: {
        avg: data.metrics.question_gen_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.question_gen_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      grading: {
        avg: data.metrics.grade_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.grade_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      analysis: {
        avg: data.metrics.analyze_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.analyze_latency?.values['p(95)']?.toFixed(2) || 0,
      },
    },
    thresholds: data.thresholds,
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k8s/k6-tests/results/ai-test-generation-summary.json': JSON.stringify(summary, null, 2),
  };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
