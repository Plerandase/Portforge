/**
 * Portforge - 실시간 채팅 부하 테스트
 * 
 * 테스트 대상: DynamoDB 동시 읽기/쓰기, 메시지 도배 시나리오
 * 
 * 실제 시나리오:
 *   - 팀당 5~6명 참여
 *   - 한 사람이 빠르게 연속 메시지 전송 (도배)
 *   - 여러 팀이 동시에 채팅
 * 
 * 실행 방법:
 *   k6 run k6-tests/04-realtime-chat.js
 *   k6 run --vus 10 --duration 1m k6-tests/04-realtime-chat.js
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// ============================================================
// 설정
// ============================================================
const BASE_URL = __ENV.BASE_URL || 'https://api.portforge.org';

// 테스트할 프로젝트/팀 ID 범위 (여러 팀 동시 채팅)
const MIN_PROJECT_ID = 1;
const MAX_PROJECT_ID = 5;

// 팀당 멤버 수
const TEAM_MEMBERS = ['팀장', '프론트1', '프론트2', '백엔드1', '백엔드2', '디자이너'];

// 커스텀 메트릭
const errorRate = new Rate('errors');
const messageLoadLatency = new Trend('message_load_latency', true);
const messageSendLatency = new Trend('message_send_latency', true);
const messagesSent = new Counter('messages_sent');

// ============================================================
// 테스트 시나리오 설정
// ============================================================
export const options = {
  scenarios: {
    // 1. 일반 채팅 (5~6명이 천천히 대화)
    normal_chat: {
      executor: 'constant-vus',
      vus: 6,  // 한 팀 6명
      duration: '1m',
      startTime: '0s',
      tags: { test_type: 'normal' },
      env: { CHAT_MODE: 'normal' },
    },
    // 2. 도배 시나리오 (한 명이 빠르게 연속 전송)
    spam_chat: {
      executor: 'constant-vus',
      vus: 2,  // 도배하는 사람 2명
      duration: '30s',
      startTime: '1m',  // 일반 채팅 후 시작
      tags: { test_type: 'spam' },
      env: { CHAT_MODE: 'spam' },
    },
    // 3. 여러 팀 동시 채팅
    multi_team: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 15 },  // 3팀 x 5명
        { duration: '1m', target: 15 },
        { duration: '30s', target: 0 },
      ],
      startTime: '1m35s',
      tags: { test_type: 'multi_team' },
      env: { CHAT_MODE: 'normal' },
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.05'],
    message_load_latency: ['p(95)<300'],
    message_send_latency: ['p(95)<400'],
  },
};

// ============================================================
// 헬퍼 함수
// ============================================================
function generateMessage() {
  const messages = [
    '안녕하세요!',
    '회의 시작할까요?',
    '네, 좋습니다',
    '오늘 할 일 정리해봅시다',
    '프론트엔드 작업 완료했습니다',
    '백엔드 API 연동 중입니다',
    '코드 리뷰 부탁드립니다',
    '배포 준비 완료!',
    '테스트 결과 공유합니다',
    '수고하셨습니다 👍',
    'ㅋㅋㅋㅋㅋ',
    'ㅇㅋ',
    '넵!',
    '잠시만요',
    '확인했습니다',
  ];
  return messages[Math.floor(Math.random() * messages.length)];
}

function getRandomMember() {
  return TEAM_MEMBERS[Math.floor(Math.random() * TEAM_MEMBERS.length)];
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
  };

  const projectId = Math.floor(Math.random() * (MAX_PROJECT_ID - MIN_PROJECT_ID + 1)) + MIN_PROJECT_ID;
  const teamId = projectId;
  const userName = getRandomMember();
  
  // 도배 모드 확인
  const isSpamMode = __ENV.CHAT_MODE === 'spam';
  const messageCount = isSpamMode ? 10 : 1;  // 도배: 10개 연속, 일반: 1개

  group('실시간 채팅', function () {
    
    // 1. 채팅방 입장 - 메시지 목록 로드
    group('메시지 목록 조회', function () {
      const res = http.get(
        `${BASE_URL}/chat/messages/${teamId}/${projectId}`,
        { ...params, tags: { name: 'GET_chat_messages' } }
      );

      messageLoadLatency.add(res.timings.duration);

      const ok = check(res, {
        'load: status 200': (r) => r.status === 200,
        'load: response time < 300ms': (r) => r.timings.duration < 300,
      });

      errorRate.add(!ok);
    });

    // 2. 메시지 전송 (도배 모드면 연속 전송)
    group('메시지 전송', function () {
      for (let i = 0; i < messageCount; i++) {
        const payload = JSON.stringify({
          team_id: teamId,
          project_id: projectId,
          user: userName,
          message: isSpamMode ? `도배 테스트 ${i + 1}` : generateMessage(),
          is_in_meeting: false,
        });

        const res = http.post(
          `${BASE_URL}/chat/message`,
          payload,
          { ...params, tags: { name: 'POST_chat_message' } }
        );

        messageSendLatency.add(res.timings.duration);

        const ok = check(res, {
          'send: status 200': (r) => r.status === 200,
          'send: response time < 400ms': (r) => r.timings.duration < 400,
        });

        if (ok) messagesSent.add(1);
        errorRate.add(!ok);

        // 도배 모드: 0.1초 간격, 일반: 대기 없음
        if (isSpamMode && i < messageCount - 1) {
          sleep(0.1);
        }
      }
    });
  });

  // 다음 행동 전 대기 (도배: 짧게, 일반: 길게)
  sleep(isSpamMode ? 0.5 : Math.random() * 3 + 2);
}

// ============================================================
// 테스트 종료 후 요약
// ============================================================
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    testName: '실시간 채팅 부하 테스트 (도배 시나리오 포함)',
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: data.metrics.http_reqs?.values?.count || 0,
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 0,
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 0,
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2) + '%',
      messagesSent: data.metrics.messages_sent?.values?.count || 0,
    },
    apiMetrics: {
      messageLoad: {
        avg: data.metrics.message_load_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.message_load_latency?.values['p(95)']?.toFixed(2) || 0,
      },
      messageSend: {
        avg: data.metrics.message_send_latency?.values?.avg?.toFixed(2) || 0,
        p95: data.metrics.message_send_latency?.values['p(95)']?.toFixed(2) || 0,
      },
    },
  };

  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'k6-tests/results/realtime-chat-summary.json': JSON.stringify(summary, null, 2),
  };
}

import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.1/index.js';
