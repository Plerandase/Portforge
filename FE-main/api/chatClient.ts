/**
 * Chat API Client
 * - 채팅 메시지 저장 (DynamoDB)
 * - 일단위 회의록 생성/조회 (S3)
 */

import { API_BASE_URL } from './config';

export interface ChatMessage {
    user: string;
    msg: string;
    time: string;
    timestamp?: number;
    is_in_meeting?: boolean;
}

export interface MinutesResponse {
    report_id: number;
    title: string;
    status: string;
    s3_key: string | null;
    created_at: string;
}

export const saveChatMessage = async (
    teamId: number,
    projectId: number,
    user: string,
    message: string,
    isInMeeting: boolean = false,
    retryCount: number = 0
): Promise<ChatMessage> => {
    try {
        const response = await fetch(`${API_BASE_URL}/chat/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                team_id: teamId,
                project_id: projectId,
                user,
                message,
                is_in_meeting: isInMeeting
            })
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            if (response.status === 500 && retryCount < 2) {
                await new Promise(resolve => setTimeout(resolve, 1000));
                return saveChatMessage(teamId, projectId, user, message, isInMeeting, retryCount + 1);
            }
            throw new Error(err.detail || '메시지 저장 실패');
        }

        return response.json();
    } catch (error) {
        if (retryCount < 2 && error instanceof TypeError) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            return saveChatMessage(teamId, projectId, user, message, isInMeeting, retryCount + 1);
        }
        throw error;
    }
};

export const getChatMessages = async (
    teamId: number,
    projectId: number,
    options?: { startDate?: string; endDate?: string; meetingOnly?: boolean; limit?: number; }
): Promise<{ messages: ChatMessage[]; count: number }> => {
    const params = new URLSearchParams();
    if (options?.startDate) params.append('start_date', options.startDate);
    if (options?.endDate) params.append('end_date', options.endDate);
    if (options?.meetingOnly) params.append('meeting_only', 'true');
    if (options?.limit) params.append('limit', String(options.limit));

    const url = `${API_BASE_URL}/chat/messages/${teamId}/${projectId}${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);

    if (!response.ok) throw new Error('메시지 조회 실패');
    return response.json();
};

export const generateDailyMinutes = async (
    teamId: number,
    projectId: number,
    messages: ChatMessage[],
    retryCount: number = 0
): Promise<MinutesResponse> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
        const response = await fetch(`${API_BASE_URL}/ai/minutes/daily`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ team_id: teamId, project_id: projectId, messages }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            if (response.status === 500 && retryCount < 1) {
                await new Promise(resolve => setTimeout(resolve, 3000));
                return generateDailyMinutes(teamId, projectId, messages, retryCount + 1);
            }
            throw new Error(err.detail || '회의록 생성 실패');
        }

        return response.json();
    } catch (error: any) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('회의록 생성 시간이 초과되었습니다.');
        }
        throw error;
    }
};

export const getDailyMinutesList = async (
    teamId: number,
    projectId: number,
    retryCount: number = 0
): Promise<MinutesResponse[]> => {
    try {
        const response = await fetch(`${API_BASE_URL}/ai/minutes/daily/${teamId}/${projectId}`);

        // 404는 아직 회의록이 없는 정상 상태 - 빈 배열 반환
        if (response.status === 404) {
            return [];
        }

        if (!response.ok) {
            if (response.status === 500 && retryCount < 2) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                return getDailyMinutesList(teamId, projectId, retryCount + 1);
            }
            throw new Error(`회의록 목록 조회 실패: ${response.status}`);
        }

        return response.json();
    } catch (error) {
        if (retryCount < 2 && error instanceof TypeError) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            return getDailyMinutesList(teamId, projectId, retryCount + 1);
        }
        throw error;
    }
};

export const getMinutesContent = async (reportId: number): Promise<any> => {
    const response = await fetch(`${API_BASE_URL}/ai/minutes/${reportId}/content`);
    if (!response.ok) throw new Error(`회의록 내용 조회 실패: ${response.status}`);
    return response.json();
};
