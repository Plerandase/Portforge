/**
 * Portforge - 프로젝트 상세 + MSA 통신 부하 테스트
 * 
 * 테스트 대상: 프로젝트 상세 조회 시 MSA 간 통신 부하
 * 
 * 호출 API:
 *   1. GET /projects/{id} - 프로젝트 상세 (내부: Team Service 호출)
 *   2. GET /api/v1/teams/{id}/stats - 팀 정보 직접 조회
 * 
 * 테스트 방식: RPS(초당 요청 수) 기반, 최소 10,000건 이상
 * 
 * 실행 방법:
 *   k6 run k8s/k6-tests/02-project-detail-apply.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 테스트할 프로젝트 ID 범위 (실제 존재하는 ID로 조정 필요)
const MIN_PROJECT_ID = 1;
const MAX_PROJECT_ID = 20;

// 목표: 최소 10,000건 이상의 요청
// 계산: 50 RPS × 200초 = 10,000건
const TARGET_RPS = 50;
const TEST_DURATION = '200s';
const TARGET_ITERATIONS = 10000;

// 커스텀 메트릭
const errorRate = new Rate('errors');
const projectDetailLatency = new Trend('project_detail_latency', true);
const teamStatsLatency = new Trend('team_stats_latency', true);
const totalRequests = new Counter('total_requests');

// ============================================================
// 테스트 시나리오 설정 (RPS 기반)
// ============================================================
export const options = {
  scenarios: {
    // RPS 기반 부하 테스트 - 최소 10,000건 보장
    rps_load_test: {
      executor: 'constant-arrival-rate',
      rate: TARGET_RPS,
      timeUnit: '1s',
      duration: TEST_DURATION,
      preAllocatedVUs: 100,
      maxVUs: 200,
      tags: { test_type: 'rps_load' },
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
    errors: ['rate<0.05'],
    project_detail_latency: ['p(95)<800'],
    team_stats_latency: ['p(95)<500'],
    total_requests: ['count>=10000'],
  },
};

// ============================================================
// 테스트 실행
// ============================================================
export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  };

  // 랜덤 프로젝트 ID 선택
  const projectId = Math.floor(Math.random() * (MAX_PROJECT_ID - MIN_PROJECT_ID + 1)) + MIN_PROJECT_ID;

  group('프로젝트 상세 + MSA 통신', function () {
    
    // Step 1: 프로젝트 상세 조회 (내부에서 Team/Auth Service 호출)
    group('프로젝트 상세', function () {
      const detailRes = http.get(`${BASE_URL}/projects/${projectId}`, {
        ...params,
        tags: { name: 'GET_project_detail' },
      });

      projectDetailLatency.add(detailRes.timings.duration);
      totalRequests.add(1);

      const detailOk = check(detailRes, {
        'detail: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        'detail: response time < 1000ms': (r) => r.timings.duration < 1000,
        'detail: has data': (r) => {
          if (r.status === 404) return true;
          try {
            const body = JSON.parse(r.body);
            return body.project_id || body.title;
          } catch {
            return false;
          }
        },
      });

      errorRate.add(!detailOk && detailRes.status !== 404);
    });

    // Step 2: 팀 정보 조회 (Team Service 직접 호출)
    group('팀 정보', function () {
      const teamRes = http.get(`${BASE_URL}/api/v1/teams/${projectId}/stats`, {
        ...params,
        tags: { name: 'GET_team_stats' },
      });

      teamStatsLatency.add(teamRes.timings.duration);
      totalRequests.add(1);

      const teamOk = check(teamRes, {
        'team: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        'team: response time < 500ms': (r) => r.timings.duration < 500,
      });

      errorRate.add(!teamOk && teamRes.status !== 404);
    });
  });
}

// ============================================================
// 테스트 종료 후 요약
// ============================================================
export function handleSummary(data) {
  const totalReqs = data.metrics.http_reqs?.values?.count || 0;
  
  const summary = {
    timestamp: new Date().toISOString(),
    testName: '프로젝트 상세 + MSA 통신 테스트 (RPS 기반)',
    testConfig: {
      targetRPS: TARGET_RPS,
      duration: TEST_DURATION,
      targetIterations: TARGET_ITERATIONS,
    },
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: totalReqs,
      achievedRPS: (totalReqs / 200).toFixed(2),
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 0,
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 0,
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2) + '%',
    },
    apiMetrics: {
      projectDetail: {
        avg: data.metrics.project_detail_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.project_detail_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      teamStats: {
        avg: data.metrics.team_stats_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.team_stats_latency?.values['p(95)']?.toFixed(2) || 0,
      },
    },
    thresholds: data.thresholds,
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k8s/k6-tests/results/project-detail-summary.json': JSON.stringify(summary, null, 2),
  };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
