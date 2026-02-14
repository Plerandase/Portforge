/**
 * API Configuration
 * 
 * 환경변수 기반 API 엔드포인트 관리
 * - 개발 환경: Vite 프록시 사용 (빈 문자열)
 * - 프로덕션 환경: AWS API Gateway 또는 ALB 엔드포인트
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
