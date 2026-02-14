/**
 * Portforge - 팀 스페이스 대시보드 부하 테스트
 * 
 * 테스트 대상: MSA 간 통신 지연 누적 측정
 * 
 * 호출 API (Team Service):
 *   1. GET /api/v1/teams/{id}/stats - 팀 대시보드 (내부: Auth Service 호출)
 *   2. GET /api/v1/teams/{id}/tasks - 칸반 보드 태스크
 *   3. GET /api/v1/teams/{id}/files - 팀 파일 목록
 *   4. GET /api/v1/teams/{id}/meetings - 회의 목록
 *   5. GET /api/v1/teams/{id}/reports - 회의록 목록
 * 
 * 테스트 방식: RPS(초당 요청 수) 기반, 최소 10,000건 이상
 * 
 * 실행 방법:
 *   k6 run k8s/k6-tests/03-teamspace-dashboard.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 테스트할 프로젝트 ID 범위
const MIN_PROJECT_ID = 1;
const MAX_PROJECT_ID = 20;

// 목표: 최소 10,000건 이상의 요청
// 대시보드는 5개 API 호출 → 2,000 iterations × 5 = 10,000건
const TARGET_RPS = 40;
const TEST_DURATION = '250s';
const TARGET_ITERATIONS = 10000;

// 커스텀 메트릭
const errorRate = new Rate('errors');
const teamStatsLatency = new Trend('team_stats_latency', true);
const tasksLatency = new Trend('tasks_latency', true);
const filesLatency = new Trend('files_latency', true);
const meetingsLatency = new Trend('meetings_latency', true);
const reportsLatency = new Trend('reports_latency', true);
const totalDashboardLatency = new Trend('total_dashboard_latency', true);
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
    http_req_duration: ['p(95)<1500', 'p(99)<3000'],
    errors: ['rate<0.1'],
    team_stats_latency: ['p(95)<800'],
    tasks_latency: ['p(95)<500'],
    files_latency: ['p(95)<500'],
    meetings_latency: ['p(95)<500'],
    reports_latency: ['p(95)<500'],
    total_dashboard_latency: ['p(95)<2000'],
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

  const projectId = Math.floor(Math.random() * (MAX_PROJECT_ID - MIN_PROJECT_ID + 1)) + MIN_PROJECT_ID;
  const dashboardStart = Date.now();

  group('팀 스페이스 대시보드', function () {
    
    // 1. 팀 대시보드 정보 (MSA: Auth Service 호출)
    group('팀 정보 + 멤버', function () {
      const res = http.get(`${BASE_URL}/api/v1/teams/${projectId}/stats`, {
        ...params,
        tags: { name: 'GET_team_stats' },
      });

      teamStatsLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'stats: status 200': (r) => r.status === 200,
        'stats: response time < 800ms': (r) => r.timings.duration < 800,
      });

      errorRate.add(!ok);
    });

    // 2. 칸반 보드 태스크
    group('태스크 목록', function () {
      const res = http.get(`${BASE_URL}/api/v1/teams/${projectId}/tasks`, {
        ...params,
        tags: { name: 'GET_tasks' },
      });

      tasksLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'tasks: status 200': (r) => r.status === 200,
        'tasks: response time < 500ms': (r) => r.timings.duration < 500,
      });

      errorRate.add(!ok);
    });

    // 3. 팀 파일 목록
    group('파일 목록', function () {
      const res = http.get(`${BASE_URL}/api/v1/teams/${projectId}/files`, {
        ...params,
        tags: { name: 'GET_files' },
      });

      filesLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'files: status 200': (r) => r.status === 200,
        'files: response time < 500ms': (r) => r.timings.duration < 500,
      });

      errorRate.add(!ok);
    });

    // 4. 회의 목록
    group('회의 목록', function () {
      const res = http.get(`${BASE_URL}/api/v1/teams/${projectId}/meetings`, {
        ...params,
        tags: { name: 'GET_meetings' },
      });

      meetingsLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'meetings: status 200': (r) => r.status === 200,
        'meetings: response time < 500ms': (r) => r.timings.duration < 500,
      });

      errorRate.add(!ok);
    });

    // 5. 회의록 목록
    group('회의록 목록', function () {
      const res = http.get(`${BASE_URL}/api/v1/teams/${projectId}/reports`, {
        ...params,
        tags: { name: 'GET_reports' },
      });

      reportsLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'reports: status 200': (r) => r.status === 200,
        'reports: response time < 500ms': (r) => r.timings.duration < 500,
      });

      errorRate.add(!ok);
    });
  });

  // 전체 대시보드 로드 시간 기록
  const dashboardEnd = Date.now();
  totalDashboardLatency.add(dashboardEnd - dashboardStart);
}

// ============================================================
// 테스트 종료 후 요약
// ============================================================
export function handleSummary(data) {
  const totalReqs = data.metrics.http_reqs?.values?.count || 0;
  
  const summary = {
    timestamp: new Date().toISOString(),
    testName: '팀 스페이스 대시보드 테스트 (RPS 기반)',
    testConfig: {
      targetRPS: TARGET_RPS,
      duration: TEST_DURATION,
      targetIterations: TARGET_ITERATIONS,
    },
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: totalReqs,
      achievedRPS: (totalReqs / 250).toFixed(2),
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 0,
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 0,
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2) + '%',
    },
    apiMetrics: {
      teamStats: {
        avg: data.metrics.team_stats_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.team_stats_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      tasks: {
        avg: data.metrics.tasks_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.tasks_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      files: {
        avg: data.metrics.files_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.files_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      meetings: {
        avg: data.metrics.meetings_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.meetings_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      reports: {
        avg: data.metrics.reports_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.reports_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      totalDashboard: {
        avg: data.metrics.total_dashboard_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.total_dashboard_latency?.values['p(95)']?.toFixed(2) || 0,
      },
    },
    thresholds: data.thresholds,
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k8s/k6-tests/results/teamspace-dashboard-summary.json': JSON.stringify(summary, null, 2),
  };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
