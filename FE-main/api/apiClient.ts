// =====================================================
// Portforge API Client - 백엔드 연동용 API 클라이언트
// =====================================================
// 로컬 개발: Vite 프록시를 통해 각 서비스로 라우팅됩니다.
// 프로덕션: api.portforge.org로 직접 요청합니다.
// - /auth, /users -> Auth Service (8000)
// - /projects, /applications -> Project Service (8001)
// - /api/v1/teams -> Team Service (8002)
// - /ai -> AI Service (8003)
// - /chat, /support, /notices, /banners, /events -> Support Service (8004)
// =====================================================

// API 기본 URL 설정 (로컬: 상대경로, 배포: api.portforge.org)
const API_BASE_URL = typeof window !== 'undefined' &&
    !window.location.hostname.includes('localhost') &&
    !window.location.hostname.includes('127.0.0.1')
    ? 'https://api.portforge.org'
    : '';

// 전역 fetch 래핑 (API 경로에 자동으로 BASE_URL 추가)
if (typeof window !== 'undefined' && API_BASE_URL) {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
        if (typeof input === 'string' && input.startsWith('/')) {
            return originalFetch(`${API_BASE_URL}${input}`, init);
        }
        return originalFetch(input, init);
    };
}

// API fetch 헬퍼 함수 (하위 호환성 유지)
const apiFetch = (path: string, options?: RequestInit) => {
    return fetch(`${API_BASE_URL}${path}`, options);
};

const getAuthHeaders = () => {
    const idToken = localStorage.getItem('id_token');
    const accessToken = localStorage.getItem('access_token');
    const token = idToken || accessToken; // id_token 우선, 없으면 access_token
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    };
};

// =====================================================
// Auth Service API (Port 8000)
// =====================================================

export interface LoginRequest {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    id_token?: string;
    user: {
        user_id: string;
        email: string;
        nickname: string;
        role: string;
        profile_image_url?: string;
        myStacks?: string[];
    };
}

export interface SignUpRequest {
    email: string;
    password: string;
    nickname: string;
}

export const authAPI = {
    // 소셜 로그인 콜백 (Code -> Token)
    socialCallback: async (code: string): Promise<LoginResponse> => {
        const response = await apiFetch('/auth/social/callback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '소셜 로그인에 실패했습니다.');
        }
        return response.json();
    },

    // 로그인
    login: async (credentials: LoginRequest): Promise<LoginResponse> => {
        const response = await apiFetch('/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            // [수정] 백엔드 BusinessException의 message 필드 우선 확인
            throw new Error(error.message || error.detail || '로그인에 실패했습니다.');
        }
        return response.json();
    },

    // 회원가입
    signUp: async (data: SignUpRequest): Promise<any> => {
        const response = await apiFetch('/auth/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            // [수정] 백엔드 BusinessException의 message 필드 우선 확인
            throw new Error(error.message || error.detail || '회원가입에 실패했습니다.');
        }
        return response.json();
    },

    // 닉네임 중복 확인
    checkNickname: async (nickname: string): Promise<{ available: boolean; message: string }> => {
        try {
            const response = await apiFetch(`/auth/validate_nickname?nickname=${encodeURIComponent(nickname)}`);
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.message || error.detail || '닉네임 확인에 실패했습니다.');
            }
            return response.json();
        } catch (error: any) {
            // 네트워크 오류 (백엔드 미실행)
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('서버에 연결할 수 없습니다. 백엔드 서비스가 실행 중인지 확인하세요.');
            }
            throw error;
        }
    },

    // [추가] 이메일 인증
    verifyEmail: async (email: string, code: string): Promise<{ success: boolean; message: string }> => {
        const response = await apiFetch('/auth/verify-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, code }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.detail || '이메일 인증에 실패했습니다.');
        }
        return response.json();
    },

    // [추가] 인증 코드 재발송
    resendCode: async (email: string): Promise<{ success: boolean; message: string }> => {
        const response = await apiFetch(`/auth/resend-code?email=${encodeURIComponent(email)}`, {
            method: 'POST',
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.detail || '인증 코드 재발송에 실패했습니다.');
        }
        return response.json();
    },


    // 내 정보 조회
    getMe: async (): Promise<any> => {
        const response = await apiFetch('/users/me', {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('사용자 정보를 가져오는데 실패했습니다.');
        }
        return response.json();
    },

    // 사용자 정보 일괄 조회 (닉네임 등)
    getUsersBatch: async (userIds: string[]): Promise<any[]> => {
        try {
            const response = await apiFetch('/users/batch', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ user_ids: userIds }),
            });
            if (!response.ok) {
                console.warn('사용자 정보 일괄 조회 실패');
                return [];
            }
            return response.json();
        } catch (e) {
            console.warn('사용자 정보 일괄 조회 오류:', e);
            return [];
        }
    },

    // 프로필 이미지 업로드 (S3)
    uploadProfileImage: async (userId: string, file: File): Promise<string> => {
        const formData = new FormData();
        formData.append('file', file);

        // access_token 또는 id_token 사용
        const token = localStorage.getItem('access_token') || localStorage.getItem('id_token');

        const response = await apiFetch(`/users/${userId}/profile-image`, {
            method: 'POST',
            headers: {
                ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || '이미지 업로드 실패');
        }

        const result = await response.json();
        return result.url;
    },

    // 프로필 수정
    updateProfile: async (data: { name?: string; myStacks?: string[]; avatarUrl?: string }): Promise<void> => {
        // avatarUrl은 이제 S3 URL이므로 그대로 전송
        const payload: any = {};
        if (data.name) payload.name = data.name;
        if (data.myStacks) payload.myStacks = data.myStacks;
        if (data.avatarUrl) payload.profile_image_url = data.avatarUrl;

        const response = await apiFetch('/users/me', {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.detail || '프로필 수정 실패');
        }
    },

    // 로그아웃
    logout: async (): Promise<void> => {
        await apiFetch('/auth/logout', {
            method: 'POST',
            headers: getAuthHeaders(),
        });
    },

    // 프로젝트 좋아요 토글
    toggleLikeProject: async (projectId: number): Promise<{ action: string; liked_project_ids: number[] }> => {
        const response = await apiFetch(`/users/me/likes/${projectId}`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('좋아요 처리에 실패했습니다.');
        }
        return response.json();
    },

    // 비밀번호 변경
    changePassword: async (userId: string, oldPassword: string, newPassword: string): Promise<void> => {
        // [중요] Cognito changePassword API는 AccessToken을 요구합니다
        const accessToken = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
        };

        const response = await apiFetch(`/users/${userId}/password`, {
            method: 'PUT',
            headers: headers,
            body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || error.detail || '비밀번호 변경에 실패했습니다.');
        }
    },

    // 회원 탈퇴
    deleteAccount: async (userId: string, password: string, reason?: string): Promise<any> => {
        const idToken = localStorage.getItem('id_token');
        const accessToken = localStorage.getItem('access_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(idToken ? { 'Authorization': `Bearer ${idToken}` } : {}),
            ...(!idToken && accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
        };
        const response = await apiFetch(`/users/${userId}`, {
            method: 'DELETE',
            headers,
            body: JSON.stringify({ password, reason }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.detail || '회원 탈퇴 실패');
        }
        return response.json();
    },

    // ,

    // 비밀번호 찾기 (이메일로 코드 발송)
    forgotPassword: async (email: string): Promise<{ message: string }> => {
        const response = await apiFetch('/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.detail || '요청 실패');
        }
        return response.json();
    },

    // 비밀번호 재설정 (코드 검증 및 새 비번 설정)
    confirmForgotPassword: async (data: { email: string; code: string; new_password: string }): Promise<{ message: string }> => {
        const response = await apiFetch('/auth/confirm-forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.message || error.detail || '비밀번호 재설정 실패');
        }
        return response.json();
    },


};

// =====================================================
// Project Service API (Port 8001)
// =====================================================

export interface ProjectData {
    id?: number;
    type: string;
    title: string;
    description: string;
    start_date: string;
    end_date: string;
    method: string;
    test_required: boolean;
    recruitment_positions: {
        position_type: string;
        required_stacks: string[];
        target_count: number;
    }[];
}

export const projectAPI = {
    // 프로젝트 목록 조회
    getProjects: async (page = 1, size = 10, filters?: any): Promise<any> => {
        const params = new URLSearchParams({ page: String(page), size: String(size) });
        if (filters?.type) params.append('type', filters.type);
        if (filters?.status) params.append('status', filters.status);

        const response = await apiFetch(`/projects?${params.toString()}`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            // 인증 없이도 목록 조회 가능하도록 빈 배열 반환
            if (response.status === 401 || response.status === 403) {
                console.warn('인증 없이 프로젝트 목록 조회 - 빈 배열 반환');
                return [];
            }
            throw new Error('프로젝트 목록을 가져오는데 실패했습니다.');
        }
        return response.json();
    },


    // 프로젝트 상세 조회
    getProject: async (projectId: number): Promise<any> => {
        const response = await apiFetch(`/projects/${projectId}`);
        if (!response.ok) {
            throw new Error('프로젝트 정보를 가져오는데 실패했습니다.');
        }
        return response.json();
    },

    // 프로젝트 생성
    createProject: async (data: ProjectData): Promise<any> => {
        const response = await apiFetch('/projects', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '프로젝트 생성에 실패했습니다.');
        }
        return response.json();
    },

    // 프로젝트 수정
    updateProject: async (projectId: number, data: Partial<ProjectData>): Promise<any> => {
        const response = await apiFetch(`/projects/${projectId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('프로젝트 수정에 실패했습니다.');
        }
        return response.json();
    },

    // 프로젝트 삭제
    deleteProject: async (projectId: number): Promise<void> => {
        const response = await apiFetch(`/projects/${projectId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('프로젝트 삭제에 실패했습니다.');
        }
    },

    // 지원하기
    applyToProject: async (projectId: number, positionType: string, message: string): Promise<any> => {
        // LocalStorage에서 userId 가져오기
        const savedUser = localStorage.getItem('portforge_v8_user');
        const userId = savedUser ? JSON.parse(savedUser).id : null;

        if (!userId) {
            throw new Error('로그인이 필요합니다.');
        }

        const response = await apiFetch(`/projects/${projectId}/applications`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ user_id: userId, position_type: positionType, message }),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '지원에 실패했습니다.');
        }
        return response.json();
    },

    // 지원자 목록 조회
    getApplications: async (projectId: number): Promise<any[]> => {
        const response = await apiFetch(`/projects/${projectId}/applications`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('지원자 목록을 가져오는데 실패했습니다.');
        }
        return response.json();
    },

    // application detail
    getApplication: async (applicationId: number): Promise<any> => {
        const response = await apiFetch(`/projects/applications/${applicationId}`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('Failed to fetch application detail.');
        }
        return response.json();
    },

    // 지원 처리 (수락/거절)
    handleApplication: async (projectId: number, applicationId: number, status: 'accepted' | 'rejected'): Promise<void> => {
        const response = await apiFetch(`/projects/${projectId}/applications/${applicationId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ status }),
        });
        if (!response.ok) {
            throw new Error('지원 처리에 실패했습니다.');
        }
    },

    // 사용자의 지원 내역 조회
    getMyApplications: async (userId: string): Promise<any> => {
        const response = await apiFetch(`/projects/user/${userId}/applications`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            console.warn('지원 내역 조회 실패, 빈 배열 반환');
            return { data: { applications: [] } };
        }
        return response.json();
    },
};

// =====================================================
// Team Service API (Port 8002)
// =====================================================

export const teamAPI = {
    // 팀 목록 조회
    getTeams: async (): Promise<any[]> => {
        const response = await apiFetch('/api/v1/teams', {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('팀 목록을 가져오는데 실패했습니다.');
        }
        return response.json();
    },

    // 팀 상세 조회
    getTeam: async (teamId: number): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${teamId}`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('팀 정보를 가져오는데 실패했습니다.');
        }
        return response.json();
    },

    // 팀 대시보드 통계 조회 (멤버, 최근 활동 등)
    getTeamStats: async (projectId: number): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/stats`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            return null;
        }
        return response.json();
    },

    // 사용자 팀 목록 조회
    getUserTeams: async (userId: string): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/user/${userId}/teams`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            console.warn('팀 목록 조회 실패, 빈 배열 반환');
            return { data: [] };
        }
        return response.json();
    },

    // 팀 생성
    createTeam: async (data: any): Promise<any> => {
        const response = await apiFetch('/api/v1/teams', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '팀 생성에 실패했습니다.');
        }
        return response.json();
    },

    // 팀 정보 수정
    updateTeam: async (projectId: number, data: any): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('팀 정보 수정에 실패했습니다.');
        }
        return response.json();
    },

    // 팀 태스크 조회
    getTasks: async (projectId: number, status?: string): Promise<any[]> => {
        const params = status ? `?status=${status}` : '';
        const response = await apiFetch(`/api/v1/teams/${projectId}/tasks${params}`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            return []; // 태스크가 없을 수도 있음
        }
        return response.json();
    },

    // 태스크 생성
    createTask: async (projectId: number, data: any): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/tasks`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('태스크 생성에 실패했습니다.');
        }
        return response.json();
    },

    // 태스크 수정
    updateTask: async (projectId: number, taskId: number, data: any): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/tasks/${taskId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('태스크 수정에 실패했습니다.');
        }
        return response.json();
    },

    // 태스크 삭제
    deleteTask: async (projectId: number, taskId: number): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/tasks/${taskId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('태스크 삭제에 실패했습니다.');
        }
        return response.json();
    },

    // 회의록 목록 조회
    getMeetings: async (projectId: number): Promise<any[]> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/meetings`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            return [];
        }
        return response.json();
    },

    // 회의록 생성
    createMeeting: async (projectId: number, data: any): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/meetings`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('회의록 생성에 실패했습니다.');
        }
        return response.json();
    },

    // 회의록 AI 요약 요청
    summarizeMeeting: async (
        projectId: number,
        meetingId: number,
        notes?: string,
        messages?: any[],
        attendees?: string[],
        meetingDate?: string
    ): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/meetings/${meetingId}/summaries`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ notes, messages, attendees, meeting_date: meetingDate }),
        });
        if (!response.ok) {
            throw new Error('회의록 요약 요청에 실패했습니다.');
        }
        return response.json();
    },

    getMeetingReports: async (projectId: number, reportType: string = 'MEETING_MINUTES'): Promise<any[]> => {
        const params = new URLSearchParams();
        if (reportType) params.append('report_type', reportType);
        const response = await apiFetch(`/api/v1/teams/${projectId}/reports?${params.toString()}`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            return [];
        }
        return response.json();
    },

    getMeetingReportContent: async (projectId: number, reportId: number): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/reports/${reportId}/content`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            throw new Error('회의록 내용을 불러오지 못했습니다.');
        }
        return response.json();
    },

    // 회의 시작/종료 트리거
    triggerMeeting: async (projectId: number, action: 'start' | 'stop'): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/meeting_trigger`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ action }),
        });
        if (!response.ok) {
            throw new Error('회의 트리거에 실패했습니다.');
        }
        return response.json();
    },

    // 파일 목록 조회
    getFiles: async (projectId: number): Promise<any[]> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/files`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) {
            return [];
        }
        return response.json();
    },

    // 파일 업로드 (메타데이터 저장)
    uploadFile: async (projectId: number, data: any): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/files`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('파일 업로드에 실패했습니다.');
        }
        return response.json();
    },

    // 팀원 초대 링크 생성
    createInvitation: async (projectId: number, data: any): Promise<any> => {
        const response = await apiFetch(`/api/v1/teams/${projectId}/invitations`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('초대 링크 생성에 실패했습니다.');
        }
        return response.json();
    },
};

// =====================================================
// Support Service API (Port 8004)
// =====================================================

// 헬퍼 함수: ResponseEnvelope에서 data 추출
const extractData = (response: any) => {
    // ResponseEnvelope 구조: { success, code, message, data }
    if (response && typeof response === 'object' && 'data' in response) {
        return response.data;
    }
    return response;
};

export const supportAPI = {
    // 공지사항 목록
    getNotices: async (): Promise<any[]> => {
        const response = await apiFetch('/notices');
        if (!response.ok) return [];
        const json = await response.json();
        return extractData(json) || [];
    },

    // 공지사항 생성
    createNotice: async (data: { title: string; content: string }): Promise<any> => {
        const response = await apiFetch('/notices', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('공지사항 생성 실패');
        const json = await response.json();
        return extractData(json);
    },

    // 공지사항 수정
    updateNotice: async (noticeId: number, data: { title?: string; content?: string }): Promise<any> => {
        const response = await apiFetch(`/admin/notices/${noticeId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('공지사항 수정 실패');
        const json = await response.json();
        return extractData(json);
    },

    // 공지사항 삭제
    deleteNotice: async (noticeId: number): Promise<void> => {
        const response = await apiFetch(`/admin/notices/${noticeId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
        if (!response.ok) throw new Error('공지사항 삭제 실패');
    },

    // 배너 목록
    getBanners: async (): Promise<any[]> => {
        const response = await apiFetch('/banners');
        if (!response.ok) return [];
        const json = await response.json();
        return extractData(json) || [];
    },

    // 배너 생성
    createBanner: async (data: { title: string; link?: string; active?: boolean }): Promise<any> => {
        const response = await apiFetch('/admin/banners', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ title: data.title, link: data.link, is_active: data.active ?? true }),
        });
        if (!response.ok) throw new Error('배너 생성 실패');
        const json = await response.json();
        return extractData(json);
    },

    // 배너 수정
    updateBanner: async (bannerId: number, data: { title?: string; link?: string; active?: boolean }): Promise<any> => {
        const response = await apiFetch(`/admin/banners/${bannerId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ title: data.title, link: data.link, is_active: data.active }),
        });
        if (!response.ok) throw new Error('배너 수정 실패');
        const json = await response.json();
        return extractData(json);
    },

    // 배너 삭제
    deleteBanner: async (bannerId: number): Promise<void> => {
        const response = await apiFetch(`/admin/banners/${bannerId}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
        if (!response.ok) throw new Error('배너 삭제 실패');
    },

    // 이벤트 목록
    getEvents: async (category?: string): Promise<any[]> => {
        const params = category ? `?category=${encodeURIComponent(category)}` : '';
        const response = await apiFetch(`/events${params}`);
        if (!response.ok) return [];
        const json = await response.json();
        return extractData(json) || [];
    },

    // 알림 목록 조회
    getNotifications: async (userId: string): Promise<any[]> => {
        const response = await apiFetch(`/notifications?user_id=${userId}`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) return [];
        const json = await response.json();
        return extractData(json) || [];
    },

    // 알림 읽음 처리
    markNotificationsRead: async (userId: string): Promise<void> => {
        await apiFetch(`/notifications/read?user_id=${userId}`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });
    },

    // reports / inquiries / bugs
    createReport: async (data: { project_id?: number; type: string; content: string }): Promise<any> => {
        const response = await apiFetch('/support/reports', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });
        if (!response.ok) throw new Error('Report create failed');
        const json = await response.json();
        return extractData(json);
    },

    getReports: async (): Promise<any[]> => {
        const response = await apiFetch('/admin/reports', {
            headers: getAuthHeaders(),
        });
        if (!response.ok) return [];
        const json = await response.json();
        return extractData(json) || [];
    },

    updateReport: async (reportId: number, action: string, note?: string): Promise<any> => {
        const response = await apiFetch(`/admin/reports/${reportId}`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ action, note }),
        });
        if (!response.ok) throw new Error('Report update failed');
        const json = await response.json();
        return extractData(json);
    },

    // 채팅 메시지 조회
    getChatMessages: async (projectId: number): Promise<any[]> => {
        const response = await apiFetch(`/chat/${projectId}/messages`, {
            headers: getAuthHeaders(),
        });
        if (!response.ok) return [];
        const json = await response.json();
        return extractData(json) || [];
    },

    // 채팅 메시지 전송
    sendChatMessage: async (projectId: number, message: string): Promise<any> => {
        const response = await apiFetch(`/chat/${projectId}/messages`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ message }),
        });
        if (!response.ok) throw new Error('메시지 전송 실패');
        const json = await response.json();
        return extractData(json);
    },
};

export default {
    auth: authAPI,
    project: projectAPI,
    team: teamAPI,
    support: supportAPI,
};
