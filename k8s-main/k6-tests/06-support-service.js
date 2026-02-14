/**
 * Portforge - Support Service 부하 테스트
 * 
 * 테스트 대상: 공지사항, 배너, 이벤트 등 Support API
 * 
 * 호출 API:
 *   1. GET /notices - 공지사항 목록
 *   2. GET /banners - 배너 목록
 *   3. GET /events - 이벤트 목록
 * 
 * 테스트 방식: RPS(초당 요청 수) 기반, 최소 10,000건 이상
 * 
 * 실행 방법:
 *   k6 run k8s/k6-tests/06-support-service.js
 */

import http from 'k6/http';
import { check, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 목표: 최소 10,000건 이상의 요청
const TARGET_RPS = 50;
const TEST_DURATION = '200s';
const TARGET_ITERATIONS = 10000;

// 커스텀 메트릭
const errorRate = new Rate('errors');
const noticesLatency = new Trend('notices_latency', true);
const bannersLatency = new Trend('banners_latency', true);
const eventsLatency = new Trend('events_latency', true);
const totalRequests = new Counter('total_requests');

// ============================================================
// 테스트 시나리오 설정 (RPS 기반)
// ============================================================
export const options = {
  scenarios: {
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
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.05'],
    notices_latency: ['p(95)<300'],
    banners_latency: ['p(95)<300'],
    events_latency: ['p(95)<300'],
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

  group('Support Service API', function () {
    
    // 1. 공지사항 조회
    group('공지사항', function () {
      const res = http.get(`${BASE_URL}/notices`, {
        ...params,
        tags: { name: 'GET_notices' },
      });

      noticesLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'notices: status 200': (r) => r.status === 200,
        'notices: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!ok);
    });

    // 2. 배너 조회
    group('배너', function () {
      const res = http.get(`${BASE_URL}/banners`, {
        ...params,
        tags: { name: 'GET_banners' },
      });

      bannersLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'banners: status 200': (r) => r.status === 200,
        'banners: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!ok);
    });

    // 3. 이벤트 조회
    group('이벤트', function () {
      const res = http.get(`${BASE_URL}/events`, {
        ...params,
        tags: { name: 'GET_events' },
      });

      eventsLatency.add(res.timings.duration);
      totalRequests.add(1);

      const ok = check(res, {
        'events: status 200': (r) => r.status === 200,
        'events: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!ok);
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
    testName: 'Support Service 부하 테스트 (RPS 기반)',
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
      notices: {
        avg: data.metrics.notices_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.notices_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      banners: {
        avg: data.metrics.banners_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.banners_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      events: {
        avg: data.metrics.events_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.events_latency?.values['p(95)']?.toFixed(2) || 0,
      },
    },
    thresholds: data.thresholds,
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k8s/k6-tests/results/support-service-summary.json': JSON.stringify(summary, null, 2),
  };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
