/**
 * Portforge - 메인 페이지 부하 테스트
 * 
 * 테스트 대상: 사용자가 메인 페이지 접속 시 발생하는 API 호출 패턴
 * 
 * 호출 API:
 *   1. GET /projects - 프로젝트 목록 (Project Service)
 *   2. GET /notices - 공지사항 (Support Service)
 *   3. GET /banners - 배너 (Support Service)
 * 
 * 테스트 방식: RPS(초당 요청 수) 기반, 최소 10,000건 이상
 * 
 * 실행 방법:
 *   k6 run k8s/k6-tests/01-main-page-load.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 목표: 최소 10,000건 이상의 요청
// 계산: 50 RPS × 200초 = 10,000건
const TARGET_RPS = 50;           // 초당 50건 요청
const TEST_DURATION = '200s';    // 200초 동안 실행
const TARGET_ITERATIONS = 10000; // 최소 10,000건 보장

// 커스텀 메트릭
const errorRate = new Rate('errors');
const projectsLatency = new Trend('projects_latency', true);
const noticesLatency = new Trend('notices_latency', true);
const bannersLatency = new Trend('banners_latency', true);
const totalRequests = new Counter('total_requests');

// ============================================================
// 테스트 시나리오 설정 (RPS 기반)
// ============================================================
export const options = {
  scenarios: {
    // RPS 기반 부하 테스트 - 최소 10,000건 보장
    rps_load_test: {
      executor: 'constant-arrival-rate',
      rate: TARGET_RPS,              // 초당 50건
      timeUnit: '1s',
      duration: TEST_DURATION,       // 200초
      preAllocatedVUs: 100,          // 미리 할당할 VU
      maxVUs: 200,                   // 최대 VU (부하 증가 시 자동 확장)
      tags: { test_type: 'rps_load' },
    },
  },

  // 성능 임계값 (SLO)
  thresholds: {
    // 전체 요청의 95%가 500ms 이내
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    // 에러율 1% 미만
    errors: ['rate<0.01'],
    // 개별 API 응답 시간
    projects_latency: ['p(95)<400'],
    notices_latency: ['p(95)<300'],
    banners_latency: ['p(95)<300'],
    // 최소 요청 건수 확인
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
    tags: { name: 'main_page' },
  };

  group('메인 페이지 로드', function () {
    // 1. 프로젝트 목록 조회 (가장 중요)
    group('프로젝트 목록', function () {
      const projectsRes = http.get(`${BASE_URL}/projects?page=1&size=20`, {
        ...params,
        tags: { name: 'GET_projects' },
      });

      projectsLatency.add(projectsRes.timings.duration);
      totalRequests.add(1);

      const projectsOk = check(projectsRes, {
        'projects: status 200': (r) => r.status === 200,
        'projects: response time < 500ms': (r) => r.timings.duration < 500,
        'projects: has data': (r) => {
          try {
            const body = JSON.parse(r.body);
            return Array.isArray(body) || (body && body.projects);
          } catch {
            return false;
          }
        },
      });

      errorRate.add(!projectsOk);
    });

    // 2. 공지사항 조회
    group('공지사항', function () {
      const noticesRes = http.get(`${BASE_URL}/notices`, {
        ...params,
        tags: { name: 'GET_notices' },
      });

      noticesLatency.add(noticesRes.timings.duration);
      totalRequests.add(1);

      const noticesOk = check(noticesRes, {
        'notices: status 200': (r) => r.status === 200,
        'notices: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!noticesOk);
    });

    // 3. 배너 조회
    group('배너', function () {
      const bannersRes = http.get(`${BASE_URL}/banners`, {
        ...params,
        tags: { name: 'GET_banners' },
      });

      bannersLatency.add(bannersRes.timings.duration);
      totalRequests.add(1);

      const bannersOk = check(bannersRes, {
        'banners: status 200': (r) => r.status === 200,
        'banners: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!bannersOk);
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
    testName: '메인 페이지 부하 테스트 (RPS 기반)',
    testConfig: {
      targetRPS: TARGET_RPS,
      duration: TEST_DURATION,
      targetIterations: TARGET_ITERATIONS,
    },
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: totalReqs,
      achievedRPS: (totalReqs / 200).toFixed(2),
      failedRequests: data.metrics.http_req_failed?.values?.passes || 0,
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 0,
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 0,
      p99ResponseTime: data.metrics.http_req_duration?.values['p(99)']?.toFixed(2) || 0,
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2) + '%',
    },
    apiMetrics: {
      projects: {
        avg: data.metrics.projects_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.projects_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      notices: {
        avg: data.metrics.notices_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.notices_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      banners: {
        avg: data.metrics.banners_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.banners_latency?.values['p(95)']?.toFixed(2) || 0,
      },
    },
    thresholds: data.thresholds,
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k8s/k6-tests/results/main-page-summary.json': JSON.stringify(summary, null, 2),
  };
}

// k6 내장 텍스트 요약 함수
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
