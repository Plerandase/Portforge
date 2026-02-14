
import React, { useState, useMemo, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth, Project } from '../contexts/AuthContext';
import { useAi } from '../contexts/AiContext';
import { fetchUserTestResult, gradeUserAnswer } from '../api/aiClient';
import { projectAPI } from '../api/apiClient';
import { STACK_CATEGORIES_BASE, parseRecruitment, calculateDDay, calculateDuration, getStackLogoUrl } from './HomePage';

// API 응답을 프론트엔드 형식으로 변환
const positionTypeMap: Record<string, string> = {
  'FRONTEND': '프론트엔드',
  'BACKEND': '백엔드',
  'DESIGN': '디자인',
  'DB': 'DB',
  'INFRA': '인프라',
  'ETC': '기타',
  'STUDY_MEMBER': '스터디원',
};

const transformProject = (apiProject: any): Project => {
  // recruitment_positions에서 가장 빠른 recruitment_deadline 추출
  const deadlines = apiProject.recruitment_positions
    ?.map((p: any) => p.recruitment_deadline)
    .filter((d: any) => d);
  const recruitmentDeadline = deadlines && deadlines.length > 0 ? deadlines.sort()[0] : null;
  const deadlineDate = recruitmentDeadline || apiProject.end_date || apiProject.endDate;

  return {
    id: apiProject.project_id || apiProject.id,
    type: apiProject.type === 'PROJECT' ? '프로젝트' : '스터디',
    title: apiProject.title,
    description: apiProject.description || '',
    deadline: calculateDDay(deadlineDate),
    views: apiProject.views || 0,
    members: apiProject.recruitment_positions?.map((p: any) => {
      const posName = positionTypeMap[p.position_type] || p.position_type;
      return `${posName} ${p.current_count || 0}/${p.target_count}`;
    }).join(', ') || '',
    tags: apiProject.recruitment_positions?.flatMap((p: any) => p.required_stacks || []) || [],
    position: positionTypeMap[apiProject.recruitment_positions?.[0]?.position_type] || apiProject.recruitment_positions?.[0]?.position_type || '미정',
    method: apiProject.method === 'ONLINE' ? '온라인' : apiProject.method === 'OFFLINE' ? '오프라인' : '온/오프라인',
    status: apiProject.status === 'RECRUITING' ? '모집중' : '모집완료',
    authorId: apiProject.user_id || '',
    authorName: apiProject.leader_name || apiProject.leaderName || '익명',
    startDate: apiProject.start_date || '',
    endDate: apiProject.end_date || '',
    testRequired: apiProject.test_required || false,
    applicants: []
  };
};

const ProjectDetailPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, applyToProject, addReport, addTestResult, handleApplication } = useAuth();
  const { questions: contextQuestions, loading: isTestLoading, error: testError, generateTest, submitTest, clearError } = useAi();

  // 프로젝트 데이터 상태
  const [projectData, setProjectData] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [applyStep, setApplyStep] = useState<'detail' | 'position_select' | 'testing' | 'form'>('detail');
  const [selectedPosition, setSelectedPosition] = useState<string>('');
  const [applyMsg, setApplyMsg] = useState('');
  const [showReportModal, setShowReportModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [reportForm, setReportForm] = useState({ reason: '부적절한 홍보/스팸', content: '' });
  const [editForm, setEditForm] = useState<{
    title: string;
    description: string;
    startDate: string;
    endDate: string;
    method: string;
  }>({ title: '', description: '', startDate: '', endDate: '', method: '온라인' });

  // Testing States
  const [currentIdx, setCurrentIdx] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [testTimeLeft, setTestTimeLeft] = useState(30);
  const [shortAnswerInput, setShortAnswerInput] = useState('');
  const [isGrading, setIsGrading] = useState(false);

  // 지원자 정보 보강 (DB에서 점수 조회) - Hook은 early return 전에 선언
  const [enrichedApplicants, setEnrichedApplicants] = useState<any[]>([]);
  const [isLoadingApplicants, setIsLoadingApplicants] = useState(false);

  // 팀 멤버 정보 (백엔드에서 조회) - 리더 여부 확인용
  const [teamMembers, setTeamMembers] = useState<any[]>([]);

  const projectId = Number(id);

  // 프로젝트 상세 로드
  useEffect(() => {
    const fetchProject = async () => {
      if (!projectId) return;
      setLoading(true);
      try {
        const data = await projectAPI.getProject(projectId);
        setProjectData(transformProject(data));
      } catch (err: any) {
        console.error('Failed to fetch project:', err);
        setError('프로젝트를 찾을 수 없습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchProject();
  }, [projectId]);

  // 테스트 타이머 - Hook은 early return 전에 선언
  useEffect(() => {
    let timer: any;
    if (applyStep === 'testing' && !isTestLoading && !isGrading && testTimeLeft > 0) {
      timer = setInterval(() => setTestTimeLeft(prev => prev - 1), 1000);
    }
    return () => clearInterval(timer);
  }, [applyStep, isTestLoading, isGrading, testTimeLeft]);

  // 시간 초과 시 자동으로 다음 문제로 이동
  useEffect(() => {
    if (applyStep !== 'testing' || isTestLoading || isGrading || testTimeLeft > 0) return;
    
    const q = contextQuestions[currentIdx];
    if (!q) return;

    // 시간 초과 - 오답 처리 후 다음 문제로
    if (currentIdx < contextQuestions.length - 1) {
      setCurrentIdx(prev => prev + 1);
      setShortAnswerInput('');
      const nextQ = contextQuestions[currentIdx + 1];
      setTestTimeLeft(nextQ?.type === 'SHORT_ANSWER' ? 120 : 30);
    } else {
      // 마지막 문제 - 테스트 종료
      finishTest(correctCount);
    }
  }, [testTimeLeft, applyStep, isTestLoading, isGrading, currentIdx, contextQuestions, correctCount]);

  const isAuthor = !!(user?.id && projectData?.authorId && (user.id === projectData.authorId || String(user.id) === String(projectData.authorId)));
  // 로그인한 사용자가 이 프로젝트에 지원했거나 참여중인지 확인
  const application = user?.appliedProjects?.find(p =>
    p.id === projectId || p.id === Number(projectId) || String(p.id) === String(projectId)
  );
  // 프로젝트의 applicants에서도 확인 (백엔드에서 로드된 데이터)
  const applicationFromProject = projectData?.applicants?.find(a =>
    a.userId === user?.id || String(a.userId) === String(user?.id)
  );
  const hasApplied = !!application || !!applicationFromProject;
  // 팀 멤버로 등록되어 있는지 확인 (백엔드 데이터 기반)
  const isTeamMember = teamMembers.some(m =>
    m.user_id === user?.id || String(m.user_id) === String(user?.id)
  );
  // 승인된 멤버인지 확인 (대소문자 모두 처리)
  const applicationStatus = (application?.status || '').toLowerCase();
  const applicationFromProjectStatus = (applicationFromProject?.status || '').toLowerCase();
  const isRejected = applicationStatus === 'rejected' || applicationFromProjectStatus === 'rejected';
  const isAcceptedMember = applicationStatus === 'accepted' || applicationFromProjectStatus === 'accepted' || isTeamMember;
  // 리더로 등록된 프로젝트인지 확인 (appliedProjects + 백엔드 팀 멤버 데이터)
  const isLeaderFromApplied = user?.appliedProjects?.some(p =>
    (p.id === projectId || String(p.id) === String(projectId)) && p.userRole === 'Leader'
  );
  // 백엔드 팀 멤버 데이터에서 리더 여부 확인
  const isLeaderFromTeam = teamMembers.some(m =>
    (m.user_id === user?.id || String(m.user_id) === String(user?.id)) && m.role === 'LEADER'
  );
  // 리더 여부: 작성자이거나, 리더 역할로 참여 중이거나, 팀 멤버 중 리더 역할인 경우
  // 스터디의 경우에도 isAuthor이면 리더 권한을 가짐
  const isLeader = isAuthor || isLeaderFromApplied || isLeaderFromTeam;

  // 지원자 데이터 로드 - Hook은 early return 전에 선언
  useEffect(() => {
    const fetchApplicantsData = async () => {
      if (!projectData?.applicants) return;

      const updated = await Promise.all(projectData.applicants.map(async (app) => {
        if (app.score !== undefined) return app;

        const result = await fetchUserTestResult(app.userId);
        if (result) {
          return { ...app, score: result.score, level: result.level, feedback: result.feedback };
        }
        return app;
      }));
      setEnrichedApplicants(updated);
    };

    if (showReviewModal && projectData) {
      fetchApplicantsData();
    }
  }, [showReviewModal, projectData]);

  // 팀 멤버 정보 로드 (리더 여부 확인용)
  useEffect(() => {
    if (projectData?.id && user?.id) {
      const loadTeamMembers = async () => {
        try {
          const response = await fetch(`/api/v1/teams/${projectData.id}/stats`);
          if (response.ok) {
            const data = await response.json();
            if (data?.members) {
              setTeamMembers(data.members);
              console.log('📋 팀 멤버 로드 완료:', data.members);
            }
          }
        } catch (e) {
          console.warn('팀 멤버 로드 실패:', e);
        }
      };
      loadTeamMembers();
    }
  }, [projectData?.id, user?.id]);

  // 지원자 목록 로드 함수
  const loadApplications = async () => {
    if (!projectData?.id) return;
    
    setIsLoadingApplicants(true);
    try {
      const response = await projectAPI.getApplications(projectData.id) as any;

      // API 응답이 배열로 직접 오거나, { data: { applications: [] } } 구조일 수 있음
      const applicationsList = Array.isArray(response)
        ? response
        : (response?.data?.applications || response?.applications || []);

      if (applicationsList.length > 0) {
        // 사용자 ID 목록 추출
        const userIds = applicationsList.map((app: any) => app.user_id);

        // Auth 서비스에서 사용자 정보 일괄 조회 (닉네임, 프로필 이미지)
        let usersMap: Record<string, { nickname: string; profileImage?: string }> = {};
        try {
          const { authAPI } = await import('../api/apiClient');
          const usersData = await authAPI.getUsersBatch(userIds);
          if (usersData && usersData.length > 0) {
            usersData.forEach((u: any) => {
              usersMap[u.user_id] = {
                nickname: u.nickname || u.email?.split('@')[0] || u.user_id,
                profileImage: u.profile_image_url
              };
            });
          }
        } catch (e) {
          console.warn('사용자 닉네임 조회 실패:', e);
        }

        // AI 서비스에서 테스트 결과 조회
        let testResultsMap: Record<number, { score?: number; feedback?: string; level?: string }> = {};
        let userProjectResults: Record<string, Record<number, { score?: number; feedback?: string; level?: string }>> = {};
        try {
          const { fetchTestResultByApplication, fetchUserTestResults, fetchTestResultByUserProject } = await import('../api/aiClient');
          const applicationIds = applicationsList
            .map((app: any) => app.application_id)
            .filter((id: any) => id);

          const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
          const fetchWithRetry = async (applicationId: number, retries = 5, delayMs = 1000) => {
            for (let attempt = 0; attempt < retries; attempt += 1) {
              const result = await fetchTestResultByApplication(applicationId);
              if (result) return result;
              if (attempt < retries - 1) {
                await sleep(delayMs);
              }
            }
            return null;
          };

          const appResults = await Promise.all(
            applicationIds.map((id: number) => fetchWithRetry(id))
          );

          appResults.forEach((result, idx) => {
            if (result && applicationIds[idx]) {
              testResultsMap[applicationIds[idx]] = {
                score: result.score,
                feedback: result.feedback,
                level: result.level
              };
            }
          });

          // application_id로 조회 실패한 경우 user_id + project_id로 fallback 조회
          for (const app of applicationsList) {
            if (!testResultsMap[app.application_id] && app.user_id && app.project_id) {
              try {
                const fallbackResult = await fetchTestResultByUserProject(app.user_id, app.project_id);
                if (fallbackResult) {
                  testResultsMap[app.application_id] = {
                    score: fallbackResult.score,
                    feedback: fallbackResult.feedback,
                    level: fallbackResult.level
                  };
                }
              } catch (e) {
                console.warn(`Fallback test result lookup failed for user ${app.user_id}:`, e);
              }
            }
          }

          for (const userId of userIds) {
            const results = await fetchUserTestResults(userId);
            if (results && results.length > 0) {
              results.forEach((result) => {
                if (result.projectId) {
                  if (!userProjectResults[userId]) {
                    userProjectResults[userId] = {};
                  }
                  if (!userProjectResults[userId][result.projectId]) {
                    userProjectResults[userId][result.projectId] = {
                      score: result.score,
                      feedback: result.feedback,
                      level: result.level
                    };
                  }
                }
              });
            }
          }
        } catch (e) {
          console.warn('AI test result lookup failed:', e);
        }

        const apps = applicationsList.map((app: any) => ({
          userId: app.user_id,
          userName: usersMap[app.user_id]?.nickname || app.user_id,
          profileImage: usersMap[app.user_id]?.profileImage,
          position: app.position_type,
          message: app.message || '',
          status: app.status.toLowerCase(),
          score: app.score ?? (testResultsMap[app.application_id]?.score ?? userProjectResults[app.user_id]?.[app.project_id]?.score),
          level: app.level ?? (testResultsMap[app.application_id]?.level ?? userProjectResults[app.user_id]?.[app.project_id]?.level),
          feedback: app.feedback ?? (testResultsMap[app.application_id]?.feedback ?? userProjectResults[app.user_id]?.[app.project_id]?.feedback),
        }));

        console.log('📋 지원자 목록 로드 완료:', apps);
        setEnrichedApplicants(apps);
      } else {
        setEnrichedApplicants([]);
      }
    } catch (e) {
      console.warn('지원자 목록 로드 실패:', e);
      setEnrichedApplicants([]);
    } finally {
      setIsLoadingApplicants(false);
    }
  };

  // 모달 열 때마다 지원자 목록 새로 로드
  useEffect(() => {
    if (showReviewModal && projectData?.id && (isLeader || isAuthor)) {
      loadApplications();
    }
  }, [showReviewModal, projectData?.id, isLeader, isAuthor]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error || !projectData) {
    return <div className="p-20 text-center font-black text-text-sub">{error || '프로젝트를 찾을 수 없습니다.'}</div>;
  }



  // 디버그 로그
  console.log('📋 프로젝트 상세 디버그:', {
    projectId,
    isAuthor,
    isLeader,
    isLeaderFromApplied,
    isLeaderFromTeam,
    authorId: projectData.authorId,
    userId: user?.id,
    teamMembers,
    appliedProjects: user?.appliedProjects,
    application,
    isAcceptedMember
  });
  // deadline이 이미 "D-7" 형식인지, 날짜인지 확인
  const dDay = projectData.deadline && projectData.deadline.startsWith('D')
    ? projectData.deadline
    : calculateDDay(projectData.deadline || projectData.startDate);
  const totalDuration = calculateDuration(projectData.startDate, projectData.endDate);

  const recruitments = (() => {
    const raw = parseRecruitment(projectData.members);
    return raw.map(r => {
      let categoryKey = '';
      if (r.pos.includes('프론트')) categoryKey = '프론트엔드';
      else if (r.pos.includes('백엔드')) categoryKey = '백엔드';
      else if (r.pos.includes('DB')) categoryKey = 'DB';
      else if (r.pos.includes('인프라')) categoryKey = '인프라';
      else if (r.pos.includes('디자인')) categoryKey = '디자인';

      const matchedStack = projectData.tags.find(t => categoryKey && STACK_CATEGORIES_BASE[categoryKey]?.includes(t));
      const acceptedMembers = projectData.applicants?.filter(a => a.position === r.pos && (a.status || '').toLowerCase() === 'accepted') || [];
      return { ...r, stack: matchedStack || '', acceptedMembers };
    });
  })();

  // 프로젝트 수정 핸들러
  const handleEditProject = async () => {
    if (!projectData || !editForm.title.trim()) {
      alert('제목을 입력해주세요.');
      return;
    }
    try {
      // method 값을 백엔드 enum 형식으로 변환
      const methodMap: Record<string, string> = {
        '온라인': 'ONLINE',
        '오프라인': 'OFFLINE',
        '온/오프라인': 'HYBRID'
      };
      const response = await fetch(`/projects/${projectData.id}?user_id=${user?.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
        body: JSON.stringify({
          title: editForm.title,
          description: editForm.description,
          start_date: editForm.startDate,
          end_date: editForm.endDate,
          method: methodMap[editForm.method] || 'ONLINE',
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || '수정 실패');
      }
      alert('프로젝트가 수정되었습니다.');
      setShowEditModal(false);
      // 페이지 새로고침
      window.location.reload();
    } catch (error: any) {
      alert(error.message || '프로젝트 수정에 실패했습니다.');
    }
  };

  // 프로젝트 삭제 핸들러
  const handleDeleteProject = async () => {
    if (!projectData) return;
    setIsDeleting(true);
    try {
      const response = await fetch(`/projects/${projectData.id}?user_id=${user?.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      if (!response.ok) throw new Error('삭제 실패');
      alert('프로젝트가 삭제되었습니다.');
      navigate('/');
    } catch (error) {
      alert('프로젝트 삭제에 실패했습니다.');
    } finally {
      setIsDeleting(false);
    }
  };

  // 수정 모달 열기
  const openEditModal = () => {
    if (projectData) {
      setEditForm({ 
        title: projectData.title, 
        description: projectData.description,
        startDate: projectData.startDate,
        endDate: projectData.endDate,
        method: projectData.method
      });
      setShowEditModal(true);
    }
  };

  const handlePositionSelect = async (pos: string) => {
    setSelectedPosition(pos);
    if (projectData.testRequired) {
      setApplyStep('testing');
      // 포지션에 해당하는 기술 스택 찾기
      const positionData = recruitments.find(r => r.pos === pos);
      const stack = positionData?.stack || projectData.tags?.[0] || pos;
      // AI 문제 생성 요청 (기술 스택 기반)
      await generateTest(stack, '초급');
      setCurrentIdx(0);
      setCorrectCount(0);
      setTestTimeLeft(30);
    } else {
      setApplyStep('form');
    }
  };

  const handleTestAnswer = async (ansIdx: number) => {
    const q = contextQuestions[currentIdx];
    if (!q) return;

    if (ansIdx === q.answer) {
      setCorrectCount(prev => prev + 1);
    }

    // 로컬 계산 (비동기 상태 반영 전)
    const nextCorrect = (ansIdx === q.answer) ? correctCount + 1 : correctCount;

    if (currentIdx < contextQuestions.length - 1) {
      setCurrentIdx(prev => prev + 1);
      setShortAnswerInput('');
      setTestTimeLeft(q.type === 'SHORT_ANSWER' ? 120 : 30);
    } else {
      // 테스트 종료
      await finishTest(nextCorrect);
    }
  };

  // 주관식 답변 제출
  const handleShortAnswerSubmit = async () => {
    const q = contextQuestions[currentIdx];
    if (!q || !shortAnswerInput.trim()) return;

    setIsGrading(true);
    try {
      const result = await gradeUserAnswer(
        q.question,
        shortAnswerInput,
        String(q.answer),
        q.grading_criteria || ''
      );

      const nextCorrect = result.is_correct ? correctCount + 1 : correctCount;
      if (result.is_correct) {
        setCorrectCount(prev => prev + 1);
      }

      if (currentIdx < contextQuestions.length - 1) {
        setCurrentIdx(prev => prev + 1);
        setShortAnswerInput('');
        const nextQ = contextQuestions[currentIdx + 1];
        setTestTimeLeft(nextQ?.type === 'SHORT_ANSWER' ? 120 : 30);
      } else {
        await finishTest(nextCorrect);
      }
    } catch (e) {
      console.error('채점 실패:', e);
    } finally {
      setIsGrading(false);
    }
  };

  // 테스트 종료 처리
  const finishTest = async (finalCorrect: number) => {
    setApplyStep('form');
    const total = contextQuestions.length;
    const score = Math.round((finalCorrect / total) * 100);

    // 결과 서버 전송 (분석 수행) -> 실제 AI 피드백 수신
    const analysisResult = await submitTest(user?.id || 'anonymous', selectedPosition, total, finalCorrect, score, Number(projectData?.id));

    const level = analysisResult?.level || (score >= 80 ? '고급' : score >= 60 ? '중급' : '초급');
    const feedback = analysisResult?.feedback || `[AI 분석] ${selectedPosition} 분야에 대한 ${level} 수준의 이해도를 보이고 있습니다. (상세 분석 생성 실패)`;

    if (user?.id && projectData?.id) {
      try {
        const appsResponse = await projectAPI.getMyApplications(user.id);
        const apps = appsResponse?.data?.applications || [];
        const target = apps.find((app: any) => String(app.project_id) === String(projectData.id));
        if (target?.application_id) {
          const { linkTestResultToApplication } = await import('../api/aiClient');
          await linkTestResultToApplication(user.id, Number(projectData.id), target.application_id);
          if (showReviewModal && (isLeader || isAuthor)) {
            await loadApplications();
          }
        }
      } catch (e) {
        console.warn('Failed to link test result after analysis:', e);
      }
    }

    addTestResult({
      skill: selectedPosition,
      score,
      date: new Date().toLocaleDateString(),
      level: score >= 60 ? '통과' : '미흡',
      feedback: feedback
    });
  };



  const handleApplySubmit = async () => {
    try {
      await applyToProject(projectId, selectedPosition, applyMsg);
      navigate('/apply-success');
    } catch (e) {
      alert('지원 신청 중 오류가 발생했습니다.');
    }
  };

  const handleReportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await addReport({
      title: `[프로젝트 신고] ${projectData.title}`,
      content: `사유: ${reportForm.reason}\n내용: ${reportForm.content}`,
      reporter: user?.id || 'anonymous',
      type: '신고',
      targetProjectId: projectData.id
    });
    alert('신고가 접수되었습니다.');
    setShowReportModal(false);
  };

  // Review Modal Component (Inline)
  const ReviewModal = () => {
    // 거절된 지원자를 제외하고 보여줌 (대소문자 모두 처리)
    const visibleApplicants = enrichedApplicants.filter(app => (app.status || '').toLowerCase() !== 'rejected');

    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[70] flex items-center justify-center p-4">
        <div className="bg-white rounded-[2.5rem] w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col shadow-2xl animate-scaleIn">
          <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
            <div>
              <h3 className="text-2xl font-black text-text-main">지원자 관리</h3>
              <p className="text-sm text-text-sub font-bold mt-1">총 {visibleApplicants.length}명의 지원자가 있습니다.</p>
            </div>
            <button onClick={() => setShowReviewModal(false)} className="w-10 h-10 rounded-full bg-white border border-gray-200 flex items-center justify-center text-gray-400 hover:text-red-500 hover:border-red-200 transition-all">✕</button>
          </div>

          <div className="flex-1 overflow-y-auto p-8 space-y-4 custom-scrollbar">
            {isLoadingApplicants ? (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
                <p className="text-text-sub font-bold">지원자 목록을 불러오는 중...</p>
              </div>
            ) : visibleApplicants.length > 0 ? (
              visibleApplicants.map((app, idx) => {
                const appStatus = (app.status || '').toLowerCase();
                return (
                  <div key={idx} className="bg-white border border-gray-100 p-8 rounded-[2rem] hover:shadow-lg transition-all animate-fadeIn">
                    <div className="flex justify-between items-start mb-6">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center text-3xl shadow-inner overflow-hidden">
                          {app.profileImage ? (
                            <img src={app.profileImage} alt={app.userName} className="w-full h-full object-cover" />
                          ) : (
                            '👤'
                          )}
                        </div>
                        <div>
                          <h4 className="text-xl font-black text-text-main">{app.userName}</h4>
                          <div className="flex gap-2 mt-1">
                            <span className="text-xs font-bold text-primary bg-primary/10 px-3 py-1 rounded-lg">{app.position} 지원</span>
                            <span className={`text-xs font-bold px-3 py-1 rounded-lg ${appStatus === 'accepted' ? 'bg-green-100 text-green-600' : appStatus === 'rejected' ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'}`}>
                              {appStatus === 'accepted' ? '승인됨' : appStatus === 'rejected' ? '거절됨' : '심사중'}
                            </span>
                          </div>
                        </div>
                      </div>
                      {app.score !== undefined && (
                        <div className="text-right">
                          <span className="block text-[10px] font-black text-primary uppercase tracking-widest mb-1">AI 역량 점수</span>
                          <div className="text-2xl font-black text-text-main">{app.score}점 <span className="text-sm text-gray-400 font-medium">/ 100</span></div>
                        </div>
                      )}
                    </div>

                    <div className="space-y-4">
                      {/* AI Analysis Report */}
                      {app.feedback ? (
                        <div className="bg-indigo-50/50 p-5 rounded-2xl border border-indigo-100">
                          <div className="flex items-center gap-2 mb-3">
                            <span className="text-lg">🤖</span>
                            <span className="text-xs font-black text-indigo-900 uppercase tracking-wider">AI 인재 분석 리포트</span>
                          </div>

                          {(() => {
                            try {
                              const data = JSON.parse(app.feedback);
                              return (
                                <div className="grid md:grid-cols-2 gap-4 text-sm leading-relaxed">
                                  <div className="bg-white p-4 rounded-xl shadow-sm border border-indigo-50">
                                    <strong className="block text-indigo-600 mb-2 flex items-center gap-1">
                                      <span>📊</span> 장단점 요약
                                    </strong>
                                    <span className="whitespace-pre-wrap text-gray-700">{data.summary}</span>
                                  </div>
                                  <div className="bg-white p-4 rounded-xl shadow-sm border border-indigo-50">
                                    <strong className="block text-indigo-600 mb-2 flex items-center gap-1">
                                      <span>👔</span> 선택 가이드
                                    </strong>
                                    <span className="whitespace-pre-wrap text-gray-700">{data.hiring_guide}</span>
                                  </div>
                                </div>
                              );
                            } catch {
                              return <p className="text-xs text-text-main leading-relaxed whitespace-pre-wrap bg-white p-4 rounded-xl">{app.feedback}</p>;
                            }
                          })()}
                        </div>
                      ) : (
                        <div className="bg-gray-50 p-4 rounded-2xl text-center text-xs text-gray-400">
                          AI 분석 데이터가 없습니다.
                        </div>
                      )}

                      {/* Applicant Message */}
                      <div className="bg-gray-50 p-5 rounded-2xl">
                        <p className="text-[10px] text-text-sub font-black uppercase mb-2">지원자 메시지</p>
                        <p className="text-sm text-text-main font-medium leading-relaxed whitespace-pre-wrap">"{app.message}"</p>
                      </div>
                    </div>

                    {appStatus === 'pending' && (
                      <div className="flex gap-3 pt-2">
                        <button
                          onClick={() => {
                            if (confirm(`'${app.userName}' 지원자를 팀원으로 승인하시겠습니까?`)) {
                              handleApplication(projectId, app.userId, 'accepted');
                            }
                          }}
                          className="flex-1 py-3 bg-primary text-white rounded-xl font-black shadow-lg shadow-primary/20 hover:bg-primary-dark transition-all"
                        >
                          승인하기
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`'${app.userName}' 지원자를 거절하시겠습니까?`)) {
                              handleApplication(projectId, app.userId, 'rejected');
                            }
                          }}
                          className="flex-1 py-3 bg-white border border-gray-200 text-text-sub rounded-xl font-bold hover:bg-gray-50 hover:text-red-500 transition-all"
                        >
                          거절하기
                        </button>
                      </div>
                    )}
                  </div>
                )
              })
            ) : (
              <div className="text-center py-20 text-gray-400 font-bold">아직 지원자가 없습니다.</div>
            )}
          </div>
        </div>
      </div>
    );
  };


  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-fadeIn pb-20 relative">
      {/* Header Section */}
      <div className="bg-white rounded-[2.5rem] shadow-xl overflow-hidden border border-gray-100">
        <div className="bg-gradient-to-r from-primary to-secondary h-32 md:h-48 w-full relative">
          {!isAuthor && (
            <button onClick={() => setShowReportModal(true)} className="absolute top-6 right-6 bg-black/20 text-white px-5 py-2 rounded-full text-xs font-black backdrop-blur-md border border-white/20">🚨 신고</button>
          )}
        </div>
        <div className="pt-16 pb-12 px-10">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
            <div className="space-y-4">
              <div className="flex gap-3 items-center">
                <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-[10px] font-black uppercase">{projectData.type}</span>
                <span className="text-xs font-bold text-text-sub">팀장: <span className="text-primary font-black">{projectData.authorName}</span></span>
                {projectData.testRequired && (
                  <span className="bg-amber-100 text-amber-600 px-3 py-1 rounded-full text-[9px] font-black uppercase">AI 역량 검증 필수</span>
                )}
                <span className={`px-3 py-1 rounded-full text-[10px] font-black border ${projectData.status === '모집중' ? 'bg-green-50 text-green-600 border-green-100' : 'bg-gray-50 text-gray-400 border-gray-100'}`}>
                  {projectData.status}
                </span>
              </div>
              <h1 className="text-3xl md:text-4xl font-black text-text-main tracking-tight leading-tight">{projectData.title}</h1>
            </div>

            <div className="flex flex-col items-center gap-3">
              {(isAuthor || isLeader) && (
                <>
                  <button
                    onClick={() => setShowReviewModal(true)}
                    className="w-full bg-white text-text-main border-2 border-gray-100 px-12 py-4 rounded-[2rem] font-bold transition-all shadow-lg hover:shadow-xl hover:bg-gray-50 flex items-center justify-center gap-2"
                  >
                    <span>👥</span> 지원자 관리
                    {projectData.applicants && projectData.applicants.filter(a => (a.status || '').toLowerCase() === 'pending').length > 0 && (
                      <span className="bg-red-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full animate-pulse">
                        {projectData.applicants.filter(a => (a.status || '').toLowerCase() === 'pending').length}
                      </span>
                    )}
                  </button>
                  <div className="flex gap-2 w-full">
                    <button
                      onClick={openEditModal}
                      className="flex-1 bg-blue-50 text-blue-600 border border-blue-200 px-4 py-3 rounded-xl font-bold transition-all hover:bg-blue-100 flex items-center justify-center gap-2"
                    >
                      <span>✏️</span> 수정
                    </button>
                    <button
                      onClick={() => setShowDeleteModal(true)}
                      className="flex-1 bg-red-50 text-red-600 border border-red-200 px-4 py-3 rounded-xl font-bold transition-all hover:bg-red-100 flex items-center justify-center gap-2"
                    >
                      <span>🗑️</span> 삭제
                    </button>
                  </div>
                </>
              )}
              {isAuthor || isLeader || isAcceptedMember ? (
                <Link to={`/team-space/${projectId}`} className="bg-secondary text-white px-12 py-5 rounded-[2rem] font-black transition-all shadow-xl text-lg hover:scale-105 shadow-secondary/20 flex items-center gap-2">
                  <span>🚀</span> 팀 스페이스 가기
                </Link>
              ) : !user ? (
                <button
                  onClick={() => navigate('/login')}
                  className="px-12 py-5 rounded-[2rem] font-black transition-all shadow-xl text-lg bg-primary text-white hover:scale-105 shadow-primary/20"
                >
                  로그인하고 지원하기
                </button>
              ) : (
                <button
                  onClick={() => setApplyStep('position_select')}
                  disabled={hasApplied || projectData.status === '모집완료'}
                  className={`px-12 py-5 rounded-[2rem] font-black transition-all shadow-xl text-lg ${hasApplied || projectData.status === '모집완료' ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-primary text-white hover:scale-105 shadow-primary/20'}`}
                >
                  {projectData.status === '모집완료'
                    ? '모집이 종료되었습니다'
                    : (hasApplied
                      ? (isRejected
                        ? '지원 거절됨'
                        : (applicationStatus === 'pending' || applicationFromProjectStatus === 'pending'
                          ? '지원 심사 중'
                          : '지원 완료'))
                      : '지금 지원하기')}
                </button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap justify-between items-start gap-y-10 mt-12 pt-10 border-t border-gray-50">
            <div className="flex flex-wrap gap-x-12 gap-y-10 flex-grow">
              <div className="space-y-4">
                <div className="space-y-1">
                  <p className="text-[10px] text-primary font-black uppercase tracking-[0.2em]">모집 마감일</p>
                  <span className={`inline-block px-4 py-1.5 rounded-xl text-sm font-black border ${dDay === '모집마감' ? 'bg-gray-50 text-gray-400 border-gray-100' : 'bg-primary/10 text-primary border-primary/20'}`}>{dDay}</span>
                </div>
                <div className="space-y-2">
                  <p className="text-[10px] text-text-sub font-black uppercase">진행 기간</p>
                  <p className="text-base font-black">{projectData.startDate} ~ {projectData.endDate}</p>
                  <p className="text-sm font-black text-primary">총 {totalDuration}일간의 대장정</p>
                </div>
              </div>
              <div className="space-y-4 min-w-[300px]">
                <p className="text-[10px] text-text-sub font-black uppercase">모집 현황 및 확정 팀원</p>
                <div className="grid grid-cols-1 gap-3">
                  {recruitments.map((rec, i) => (
                    <div key={i} className={`p-5 rounded-2xl border transition-all flex flex-col gap-3 ${rec.current >= rec.target ? 'bg-gray-50' : 'bg-white border-primary/10 shadow-sm'}`}>
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-3">
                          <span className="font-black text-base text-text-main">{rec.pos}</span>
                        </div>
                        <span className={`text-sm font-black ${rec.current >= rec.target ? 'text-gray-400' : 'text-primary'}`}>{rec.current}/{rec.target}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 기술 스택 - 아이콘과 이름 함께 표시 */}
              {projectData.tags && projectData.tags.length > 0 && (
                <div className="space-y-4 w-full">
                  <p className="text-[10px] text-text-sub font-black uppercase">사용 기술 스택</p>
                  <div className="flex flex-wrap gap-2">
                    {projectData.tags.map((tag: string, idx: number) => (
                      <div key={idx} className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-xl border border-gray-100">
                        <img src={getStackLogoUrl(tag)} className="w-5 h-5 object-contain" alt={tag} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                        <span className="text-xs font-bold text-text-main">{tag}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-12 space-y-4">
            <h4 className="text-[10px] font-black text-text-sub uppercase tracking-widest">상세 소개</h4>
            <div className="bg-gray-50 p-8 rounded-[2rem] font-medium leading-relaxed whitespace-pre-wrap">
              {projectData.description}
            </div>
          </div>
        </div>
      </div>

      {/* --- Modals --- */}

      {/* 1. 포지션 선택 모달 */}
      {applyStep === 'position_select' && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-[2.5rem] w-full max-w-lg shadow-2xl animate-scaleIn">
            <h3 className="text-2xl font-black text-text-main mb-6">지원할 포지션을 선택하세요</h3>
            <div className="space-y-3">
              {recruitments.filter(r => r.current < r.target).map((r, i) => (
                <button
                  key={i}
                  onClick={() => handlePositionSelect(r.pos)}
                  className="w-full p-4 rounded-xl border-2 border-gray-100 hover:border-primary hover:bg-primary/5 transition-all text-left flex justify-between items-center group"
                >
                  <span className="font-bold text-text-main group-hover:text-primary">{r.pos}</span>
                  <span className="text-sm font-black text-text-sub">{r.current}/{r.target}</span>
                </button>
              ))}
            </div>
            <button onClick={() => setApplyStep('detail')} className="mt-6 w-full py-4 rounded-xl text-text-sub font-bold hover:bg-gray-100">취소</button>
          </div>
        </div>
      )}

      {/* 2. 테스트 진행 모달 */}
      {applyStep === 'testing' && (
        <div className="fixed inset-0 bg-white z-[60] p-6 overflow-y-auto">
          <div className="max-w-3xl mx-auto space-y-8 animate-fadeIn py-10">
            {testError ? (
              <div className="text-center py-20 space-y-6 animate-scaleIn">
                <div className="text-6xl animate-bounce">⚠️</div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-black text-red-500">테스트 생성 오류</h3>
                  <p className="text-text-sub font-medium">AI 서비스 연결 중 문제가 발생했습니다.</p>
                  <p className="text-sm text-gray-400 bg-gray-50 inline-block px-4 py-2 rounded-lg">{testError}</p>
                </div>
                <div className="pt-4">
                  <button
                    onClick={() => { clearError(); setApplyStep('detail'); }}
                    className="px-8 py-3 bg-gray-100 rounded-xl font-bold text-text-sub hover:bg-gray-200 transition-colors"
                  >
                    이전 화면으로 돌아가기
                  </button>
                </div>
              </div>
            ) : isTestLoading ? (
              <div className="text-center py-20">
                <div className="animate-spin w-12 h-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
                <h3 className="text-xl font-black text-text-main">AI가 역량 테스트 문제를 출제하고 있습니다...</h3>
              </div>
            ) : contextQuestions.length > 0 && currentIdx < contextQuestions.length ? (
              <>
                <div className="flex justify-between items-center bg-gray-50 px-8 py-4 rounded-full border border-gray-100">
                  <div className="flex items-center gap-4">
                    <span className="text-lg font-black text-primary">{currentIdx + 1} / {contextQuestions.length}</span>
                    <span className={`text-sm font-bold px-3 py-1 rounded-full ${contextQuestions[currentIdx].type === 'SHORT_ANSWER' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'}`}>
                      {contextQuestions[currentIdx].type === 'SHORT_ANSWER' ? '📝 주관식' : '✅ 객관식'}
                    </span>
                  </div>
                  <div className="text-xl font-black text-red-500">{testTimeLeft}s</div>
                </div>

                <div className="bg-white p-12 rounded-[3.5rem] shadow-2xl border border-gray-100 space-y-10">
                  <h3 className="text-2xl font-black text-text-main leading-tight whitespace-pre-wrap">Q. {contextQuestions[currentIdx].question}</h3>
                  
                  {/* 주관식 */}
                  {contextQuestions[currentIdx].type === 'SHORT_ANSWER' ? (
                    <div className="space-y-4">
                      <textarea
                        className="w-full p-6 rounded-2xl bg-gray-50 border-2 border-gray-100 focus:border-primary focus:ring-4 focus:ring-primary/10 transition-all font-medium text-lg min-h-[150px] resize-none"
                        placeholder="답변을 입력해주세요..."
                        value={shortAnswerInput}
                        onChange={(e) => setShortAnswerInput(e.target.value)}
                        disabled={isGrading}
                      />
                      <button
                        onClick={handleShortAnswerSubmit}
                        disabled={isGrading || !shortAnswerInput.trim()}
                        className="w-full py-4 bg-primary text-white rounded-2xl font-black text-lg shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isGrading ? '채점 중...' : '답안 제출'}
                      </button>
                    </div>
                  ) : (
                    /* 객관식 */
                    <div className="grid gap-4">
                      {contextQuestions[currentIdx].options?.map((opt, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleTestAnswer(idx)}
                          className="group flex items-center justify-between p-6 rounded-[2rem] border-2 border-gray-50 bg-gray-50/30 hover:border-primary hover:bg-primary/5 transition-all text-left"
                        >
                          <span className="font-bold text-text-main group-hover:text-primary">{opt}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* 3. 지원서 작성 모달 (테스트 통과 후 or 테스트 없는 경우) */}
      {applyStep === 'form' && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-[2.5rem] w-full max-w-lg shadow-2xl animate-scaleIn">
            <h3 className="text-2xl font-black text-text-main mb-2">지원 메시지 작성</h3>
            <p className="text-sm text-text-sub mb-6">팀 리더에게 전할 메시지를 작성해주세요.</p>
            <textarea
              value={applyMsg}
              onChange={e => setApplyMsg(e.target.value)}
              placeholder="안녕하세요! 이 프로젝트에 꼭 참여하고 싶습니다..."
              className="w-full h-40 p-4 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none resize-none mb-6"
            />
            <div className="flex gap-4">
              <button onClick={() => setApplyStep('detail')} className="flex-1 py-4 rounded-xl text-text-sub font-bold hover:bg-gray-100">취소</button>
              <button onClick={handleApplySubmit} className="flex-1 bg-primary text-white py-4 rounded-xl font-black shadow-xl shadow-primary/20 hover:bg-primary-dark">지원 완료</button>
            </div>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {showReportModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-[2rem] w-full max-w-md p-8 animate-scaleIn shadow-2xl">
            <h3 className="text-xl font-black text-text-main mb-6">🚨 프로젝트 신고</h3>
            <form onSubmit={handleReportSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-black text-text-sub mb-2 uppercase">신고 사유</label>
                <select
                  value={reportForm.reason}
                  onChange={e => setReportForm({ ...reportForm, reason: e.target.value })}
                  className="w-full p-3 rounded-xl border border-gray-200 bg-gray-50 focus:border-primary outline-none"
                >
                  <option>부적절한 홍보/스팸</option>
                  <option>욕설/비하 발언</option>
                  <option>허위 사실 유포</option>
                  <option>기타</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-black text-text-sub mb-2 uppercase">상세 내용</label>
                <textarea
                  value={reportForm.content}
                  onChange={e => setReportForm({ ...reportForm, content: e.target.value })}
                  className="w-full p-3 rounded-xl border border-gray-200 bg-gray-50 focus:border-primary outline-none h-24 resize-none"
                  placeholder="신고 사유를 자세히 적어주세요."
                  required
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowReportModal(false)} className="flex-1 py-3 rounded-xl font-bold text-gray-400 hover:bg-gray-100">취소</button>
                <button type="submit" className="flex-1 py-3 rounded-xl font-black bg-red-500 text-white shadow-lg shadow-red-500/20 hover:bg-red-600">신고하기</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Review Modal */}
      {showReviewModal && <ReviewModal />}

      {/* 프로젝트 수정 모달 */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white p-8 rounded-[2.5rem] w-full max-w-lg shadow-2xl animate-scaleIn my-8">
            <h3 className="text-2xl font-black text-text-main mb-6">프로젝트 수정</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-bold text-text-sub mb-2">제목</label>
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                  placeholder="프로젝트 제목"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-text-sub mb-2">설명</label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none min-h-[120px] resize-none"
                  placeholder="프로젝트 설명"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold text-text-sub mb-2">시작일</label>
                  <input
                    type="date"
                    value={editForm.startDate}
                    onChange={(e) => setEditForm({ ...editForm, startDate: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-text-sub mb-2">종료일</label>
                  <input
                    type="date"
                    value={editForm.endDate}
                    onChange={(e) => setEditForm({ ...editForm, endDate: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-bold text-text-sub mb-2">진행 방식</label>
                <select
                  value={editForm.method}
                  onChange={(e) => setEditForm({ ...editForm, method: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-primary focus:ring-2 focus:ring-primary/20 outline-none"
                >
                  <option value="온라인">온라인</option>
                  <option value="오프라인">오프라인</option>
                  <option value="온/오프라인">온/오프라인</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowEditModal(false)}
                className="flex-1 py-4 rounded-xl text-text-sub font-bold hover:bg-gray-100 border border-gray-200"
              >
                취소
              </button>
              <button
                onClick={handleEditProject}
                className="flex-1 py-4 rounded-xl bg-primary text-white font-bold hover:bg-primary-dark"
              >
                수정하기
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 프로젝트 삭제 확인 모달 */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white p-8 rounded-[2.5rem] w-full max-w-md shadow-2xl animate-scaleIn text-center">
            <div className="text-5xl mb-4">⚠️</div>
            <h3 className="text-2xl font-black text-text-main mb-2">프로젝트 삭제</h3>
            <p className="text-text-sub mb-6">
              정말로 이 프로젝트를 삭제하시겠습니까?<br />
              <span className="text-red-500 font-bold">이 작업은 되돌릴 수 없습니다.</span>
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 py-4 rounded-xl text-text-sub font-bold hover:bg-gray-100 border border-gray-200"
                disabled={isDeleting}
              >
                취소
              </button>
              <button
                onClick={handleDeleteProject}
                className="flex-1 py-4 rounded-xl bg-red-500 text-white font-bold hover:bg-red-600 disabled:opacity-50"
                disabled={isDeleting}
              >
                {isDeleting ? '삭제 중...' : '삭제하기'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDetailPage;
