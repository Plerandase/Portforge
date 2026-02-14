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
 * 인프라:
 *   - AWS ALB (Application Load Balancer)
 *   - Route 53 + ACM (HTTPS)
 *   - EKS 클러스터
 * 
 * 실행 방법:
 *   k6 run k6-tests/01-main-page-load.js
 *   k6 run --vus 50 --duration 1m k6-tests/01-main-page-load.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 커스텀 메트릭
const errorRate = new Rate('errors');
const projectsLatency = new Trend('projects_latency', true);
const noticesLatency = new Trend('notices_latency', true);
const bannersLatency = new Trend('banners_latency', true);

// ============================================================
// 테스트 시나리오 설정
// ============================================================
export const options = {
  // 시나리오 정의
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
        { duration: '1m', target: 30 },   // 1분간 30 VU까지 증가
        { duration: '3m', target: 30 },   // 3분간 30 VU 유지
        { duration: '1m', target: 0 },    // 1분간 0으로 감소
      ],
      startTime: '35s',  // smoke 테스트 후 시작
      tags: { test_type: 'load' },
    },
    // 3. Stress Test: 한계 테스트 (주석 해제하여 사용)
    // stress: {
    //   executor: 'ramping-vus',
    //   startVUs: 0,
    //   stages: [
    //     { duration: '2m', target: 50 },
    //     { duration: '3m', target: 100 },
    //     { duration: '2m', target: 150 },
    //     { duration: '1m', target: 0 },
    //   ],
    //   startTime: '6m',
    //   tags: { test_type: 'stress' },
    // },
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

      const bannersOk = check(bannersRes, {
        'banners: status 200': (r) => r.status === 200,
        'banners: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!bannersOk);
    });
  });

  // 사용자 행동 시뮬레이션: 페이지 로드 후 1-3초 대기
  sleep(Math.random() * 2 + 1);
}

// ============================================================
// 테스트 종료 후 요약
// ============================================================
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    testName: '메인 페이지 부하 테스트',
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: data.metrics.http_reqs?.values?.count || 0,
      failedRequests: data.metrics.http_req_failed?.values?.passes || 0,
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 0,
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 0,
      p99ResponseTime: data.metrics.http_req_duration?.values['p(99)']?.toFixed(2) || 0,
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2) + '%',
    },
    thresholds: data.thresholds,
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6-tests/results/main-page-summary.json': JSON.stringify(summary, null, 2),
  };
}

// k6 내장 텍스트 요약 함수
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
