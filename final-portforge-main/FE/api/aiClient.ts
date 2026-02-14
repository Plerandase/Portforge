

export interface QuestionItem {
    question: string;
    options: string[];
    answer: number | string; // 객관식(index), 주관식(string)
    explanation?: string;
    grading_criteria?: string; // 주관식 채점 기준
    type?: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER';
}

export interface QuestionResponse {
    questions: QuestionItem[];
}

// 하드코딩된 프로젝트 제목 매핑을 제거하고, 동적으로 설정할 수 있도록 projectId만 유지
export interface TestResultAnalysis {
    score: number;
    stack: string;
    level: string;
    feedback: string;
    date: string;
    projectId?: number;
    projectTitle?: string;
    applicationId?: number;
}

export interface GradeResponse {
    score: number;
    is_correct: boolean;
    feedback: string;
}

export const fetchQuestions = async (stack: string, difficulty: string = '초급', type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'MIXED' = 'MULTIPLE_CHOICE'): Promise<QuestionItem[]> => {
    try {
        const response = await fetch('/ai/test/questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stack, difficulty, count: 5, type })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to fetch questions');
        }

        const data: QuestionResponse = await response.json();
        // 응답 데이터에 type 주입 (서버가 안 보내줄 경우 options 유무로 판단)
        return data.questions.map(q => ({
            ...q,
            type: q.type || (q.options && q.options.length > 0 ? 'MULTIPLE_CHOICE' : 'SHORT_ANSWER')
        }));
    } catch (error) {
        console.error("AI API Error:", error);
        throw error;
    }
};

export const gradeUserAnswer = async (question: string, userAnswer: string, modelAnswer: string, criteria: string): Promise<GradeResponse> => {
    try {
        const response = await fetch('/ai/test/grade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                user_answer: userAnswer,
                model_answer: modelAnswer,
                grading_criteria: criteria
            })
        });

        if (!response.ok) throw new Error('Grading failed');
        return await response.json();
    } catch (error) {
        console.error("AI Grading Error:", error);
        // 에러 시 기본값 반환
        return { score: 0, is_correct: false, feedback: "채점 중 오류가 발생했습니다." };
    }
};

export const analyzeResults = async (userId: string, stack: string, total: number, correct: number, score: number, wrong_answers: string[] = [], projectId?: number, applicationId?: number): Promise<TestResultAnalysis> => {
    try {
        const response = await fetch('/ai/test/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, stack, total_questions: total, correct_count: correct, score, wrong_answers, project_id: projectId, application_id: applicationId })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Failed to analyze results');
        }

        // 반환값에 projectId가 포함되어 있을 수 있음
        const result = await response.json();
        return {
            ...result,
            date: new Date().toLocaleDateString() // 오늘 날짜
        };
    } catch (error) {
        console.error("AI Analysis Error:", error);
        throw error;
    }
};

export const fetchUserTestResult = async (userId: string): Promise<TestResultAnalysis | null> => {
    try {
        const response = await fetch(`/ai/test/result/${userId}`);
        if (response.status === 404) return null;
        if (!response.ok) throw new Error('Failed to fetch user test result');
        return await response.json();
    } catch (e) {
        // console.error("AI Fetch Error:", e); // 404가 흔하므로 로그 생략 가능
        return null;
    }
};



// 사용자의 모든 테스트 결과 조회
export const fetchUserTestResults = async (userId: string): Promise<TestResultAnalysis[]> => {
    try {
        const response = await fetch(`/ai/test-results/user/${userId}`);
        if (response.status === 404) return [];
        if (!response.ok) throw new Error('Failed to fetch user test results');
        const data = await response.json();
        return data.map((r: any) => ({
            score: r.score,
            stack: r.test_type || 'Unknown',
            level: r.score >= 80 ? '고급' : r.score >= 60 ? '중급' : '초급',
            feedback: r.feedback || '',
            date: r.created_at ? new Date(r.created_at).toLocaleDateString() : new Date().toLocaleDateString(),
            projectId: r.project_id,
            applicationId: r.application_id
        }));
    } catch (e) {
        console.error("AI Fetch Error:", e);
        return [];
    }
};

// 테스트 결과에 application_id 연결 (지원서 제출 후 호출)
export const linkTestResultToApplication = async (userId: string, projectId: number, applicationId: number): Promise<boolean> => {
    try {
        const response = await fetch('/ai/test-results/link-application', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, project_id: projectId, application_id: applicationId })
        });
        return response.ok;
    } catch (e) {
        console.error("Link Test Result Error:", e);
        return false;
    }
};
export interface ApplicantData {
    name: string;
    position: string;
    message: string;
    score?: number;
    feedback?: string;
}

export const analyzeApplicants = async (applicants: ApplicantData[]): Promise<string> => {
    try {
        const response = await fetch('/ai/recruit/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ applicants })
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to analyze applicants');
        }
        const data = await response.json();
        return data.analysis;
    } catch (e) {
        console.error("AI Applicant Analysis Error:", e);
        throw e;
    }
};
export interface PortfolioResult {
    portfolio_id?: number;
    role: string;
    period: string;
    stack: string;
    contributions: { category: string; text: string }[];
    aiAnalysis: string;
    // 추가 속성들
    title?: string;
    summary?: string;
    role_description?: string;
    tech_stack_usage?: string;
    problem_solving?: string;
    growth_point?: string;
    external_links?: string;
    created_at?: string;
}

export const generatePortfolio = async (userId: string, projectId: number, isTeamLeader: boolean = false): Promise<PortfolioResult> => {
    try {
        const response = await fetch('/ai/portfolio/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, project_id: projectId, is_team_leader: isTeamLeader })
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to generate portfolio');
        }
        const data = await response.json();
        return data.result;
    } catch (e) {
        console.error("Portfolio Generation Error:", e);
        throw e;
    }
};


export const fetchTestResultByApplication = async (applicationId: number): Promise<TestResultAnalysis | null> => {
    try {
        const response = await fetch(`/ai/test-results/${applicationId}`);
        if (response.status === 404) return null;
        if (!response.ok) throw new Error('Failed to fetch test result by application');
        return await response.json();
    } catch (e) {
        console.error("AI Fetch Error:", e);
        return null;
    }
};

