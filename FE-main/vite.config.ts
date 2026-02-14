import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        // Auth Service (8000) - 인증, 사용자 관리
        '/auth': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/users': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        // Project Service (8001) - 프로젝트, 지원서 관리
        '/projects': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
        },
        '/enriched': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
        },
        '/applications': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
        },
        // Team Service (8002) - 팀 관리
        '/api/v1/teams': {
          target: 'http://localhost:8002',
          changeOrigin: true,
          secure: false,
        },
        '/api/v1/integration': {
          target: 'http://localhost:8002',
          changeOrigin: true,
          secure: false,
        },
        // AI Service (8003) - AI 테스트, 회의록
        '/ai': {
          target: 'http://localhost:8003',
          changeOrigin: true,
          secure: false,
        },
        // Support Service (8004) - 채팅, 고객지원, 공지사항 등
        '/chat': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/support': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/notifications': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/events': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/admin': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/banners': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/notices': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/teams': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/test': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        },
        '/health': {
          target: 'http://localhost:8004',
          changeOrigin: true,
          secure: false,
        }
      }
    },
    plugins: [react()],
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    }
  };
});
