/**
 * Portforge - 프로젝트 상세 + MSA 통신 부하 테스트
 * 
 * 테스트 대상: 프로젝트 상세 조회 시 MSA 간 통신 부하
 * 
 * 호출 API:
 *   1. GET /projects/{id} - 프로젝트 상세 (내부: Team Service 호출)
 *   2. GET /api/v1/teams/{id}/stats - 팀 정보 직접 조회
 * 
 * MSA 간 통신:
 *   - Project Service → Team Service (팀장 닉네임 조회)
 *   - Project Service → Auth Service (사용자 정보 조회)
 * 
 * 실행 방법:
 *   k6 run k6-tests/02-project-detail-apply.js
 *   k6 run --vus 20 --duration 1m k6-tests/02-project-detail-apply.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 테스트할 프로젝트 ID 범위 (실제 존재하는 ID로 조정 필요)
const MIN_PROJECT_ID = 1;
const MAX_PROJECT_ID = 20;

// 커스텀 메트릭
const errorRate = new Rate('errors');
const projectDetailLatency = new Trend('project_detail_latency', true);
const teamStatsLatency = new Trend('team_stats_latency', true);

// ============================================================
// 테스트 시나리오 설정
// ============================================================
export const options = {
  scenarios: {
    // 1. Smoke Test: 기본 동작 확인
    smoke: {
      executor: 'constant-vus',
      vus: 2,
      duration: '30s',
      startTime: '0s',
      tags: { test_type: 'smoke' },
    },
    // 2. Load Test: 일반 부하
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },
        { duration: '2m', target: 20 },
        { duration: '1m', target: 0 },
      ],
      startTime: '35s',
      tags: { test_type: 'load' },
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
    errors: ['rate<0.05'],
    project_detail_latency: ['p(95)<800'],
    team_stats_latency: ['p(95)<500'],
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

    // 사용자가 상세 페이지를 읽는 시간
    sleep(Math.random() * 2 + 1);

    // Step 2: 팀 정보 조회 (Team Service 직접 호출)
    group('팀 정보', function () {
      const teamRes = http.get(`${BASE_URL}/api/v1/teams/${projectId}/stats`, {
        ...params,
        tags: { name: 'GET_team_stats' },
      });

      teamStatsLatency.add(teamRes.timings.duration);

      const teamOk = check(teamRes, {
        'team: status 200 or 404': (r) => r.status === 200 || r.status === 404,
        'team: response time < 500ms': (r) => r.timings.duration < 500,
      });

      errorRate.add(!teamOk && teamRes.status !== 404);
    });
  });

  // 다음 행동 전 대기
  sleep(Math.random() * 2 + 1);
}

// ============================================================
// 테스트 종료 후 요약
// ============================================================
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    testName: '프로젝트 상세 + MSA 통신 테스트',
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: data.metrics.http_reqs?.values?.count || 0,
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
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6-tests/results/project-detail-summary.json': JSON.stringify(summary, null, 2),
  };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
