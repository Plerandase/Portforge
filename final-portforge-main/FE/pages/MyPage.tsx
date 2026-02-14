
import React, { useState, useRef, useEffect } from 'react';
import { useAuth, User, TestResult } from '../contexts/AuthContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { STACK_CATEGORIES_BASE, getStackLogoUrl } from './HomePage';
import { authAPI, projectAPI } from '../api/apiClient';

const MyPage: React.FC = () => {
  const { user, updateProfile, changePassword, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const queryParams = new URLSearchParams(location.search);
  const initialTab = (queryParams.get('tab') as any) || 'profile';
  const [activeTab, setActiveTab] = useState<'profile' | 'teams' | 'test' | 'security'>(initialTab);

  useEffect(() => {
    if (queryParams.get('tab')) {
      setActiveTab(queryParams.get('tab') as any);
    }
  }, [location.search]);

  if (!user) { navigate('/login'); return null; }

  const handleAvatarClick = () => !isUploading && fileInputRef.current?.click();
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && user) {
      // 파일 크기 검증 (5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('파일 크기는 5MB 이하여야 합니다.');
        return;
      }
      
      // 파일 형식 검증
      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        alert('지원하지 않는 이미지 형식입니다. (jpg, png, gif, webp)');
        return;
      }
      
      setIsUploading(true);
      try {
        console.log('프로필 이미지 업로드 시작:', file.name, file.size);
        // S3에 업로드하고 URL 받기
        const imageUrl = await authAPI.uploadProfileImage(user.id, file);
        console.log('업로드 성공:', imageUrl);
        // 프로필 업데이트
        await updateProfile({ avatarUrl: imageUrl });
        alert('프로필 사진이 변경되었습니다.');
      } catch (error: any) {
        console.error('프로필 이미지 업로드 실패:', error);
        alert(error.message || '이미지 업로드에 실패했습니다.');
      } finally {
        setIsUploading(false);
        // input 초기화
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    }
  };

  const avatarSrc = user.avatarUrl || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.id}`;

  return (
    <div className="max-w-6xl mx-auto py-8 flex flex-col lg:flex-row gap-8 animate-fadeIn">
      <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" />

      <aside className="lg:w-1/4 space-y-6">
        <div className="bg-white p-8 rounded-[3rem] shadow-sm border border-gray-100 text-center relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-2 bg-primary"></div>
          <div className="relative w-32 h-32 mx-auto mb-4 group cursor-pointer">
            <img src={avatarSrc} className="w-full h-full rounded-full border-4 border-primary/10 shadow-lg object-cover" alt="avatar" />
          </div>
          <h2 className="text-2xl font-black">{user.name}</h2>
          <p className="text-primary text-[10px] font-black uppercase tracking-[0.2em] mt-1">{user.role}</p>
        </div>

        <nav className="bg-white p-4 rounded-[2.5rem] shadow-sm border border-gray-100 space-y-1">
          <MenuBtn active={activeTab === 'profile'} onClick={() => setActiveTab('profile')} label="내 프로필" icon="👤" />
          <MenuBtn active={activeTab === 'test'} onClick={() => setActiveTab('test')} label="테스트 결과" icon="🏆" />
          <MenuBtn active={activeTab === 'teams'} onClick={() => setActiveTab('teams')} label="참여 팀 / 지원현황" icon="🚀" />
          <MenuBtn active={activeTab === 'security'} onClick={() => setActiveTab('security')} label="계정 및 보안" icon="🔒" />
        </nav>
      </aside>

      <main className="flex-1">
        <div className="bg-white p-12 rounded-[3.5rem] shadow-sm border border-gray-100 min-h-[600px]">
          {activeTab === 'profile' && <ProfileEditor user={user} updateProfile={updateProfile} />}
          {activeTab === 'test' && <TestResultSection testResults={user.testResults || []} />}
          {activeTab === 'teams' && <TeamSection user={user} />}
          {activeTab === 'security' && <SecuritySection user={user} changePassword={changePassword} logout={logout} />}
        </div>
      </main>
    </div>
  );
};

const ProfileEditor = ({ user, updateProfile }: any) => {
  const { validateName } = useAuth();
  const [name, setName] = useState(user.name);
  const [myStacks, setMyStacks] = useState<string[]>(user.myStacks || []);
  const [stackInput, setStackInput] = useState('');
  const [nameError, setNameError] = useState('');

  const addStack = (stack: string) => {
    if (!myStacks.includes(stack)) {
      setMyStacks([...myStacks, stack]);
    }
    setStackInput('');
  };

  const removeStack = (stack: string) => {
    setMyStacks(myStacks.filter(s => s !== stack));
  };

  const allStacks = Object.values(STACK_CATEGORIES_BASE).flat() as string[];
  const filteredSuggestions = stackInput
    ? [...new Set(allStacks)].filter(s => s.toLowerCase().includes(stackInput.toLowerCase()) && !myStacks.includes(s)).slice(0, 5)
    : [];

  const handleSave = async () => {
    const v = validateName(name);
    if (!v.available) {
      setNameError(v.message);
      return;
    }
    try {
      await updateProfile({ name, myStacks });
      alert('프로필이 저장되었습니다.');
      setNameError('');
    } catch (e: any) {
      setNameError(e.message);
    }
  };

  return (
    <div className="space-y-10 animate-fadeIn">
      <h3 className="text-3xl font-black">기본 정보 편집</h3>
      <div className="space-y-8">
        <InputField label="활동 닉네임" value={name} onChange={(val: string) => { setName(val); setNameError(''); }} />
        <div className="space-y-4">
          <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">보유 기술 스택</label>
          <div className="flex flex-wrap gap-2">
            {myStacks.map((s: string) => (
              <span key={s} className="flex items-center gap-2 px-4 py-2 bg-primary/10 border border-primary/20 rounded-xl text-xs font-bold text-primary">
                {s}
                <button onClick={() => removeStack(s)}>✕</button>
              </span>
            ))}
          </div>
          <div className="relative">
            <input
              type="text"
              value={stackInput}
              onChange={(e) => setStackInput(e.target.value)}
              className="w-full bg-gray-50 p-5 rounded-2xl border-none outline-none focus:ring-2 focus:ring-primary/20 font-bold text-sm"
              placeholder="기술 스택 검색"
            />
            {filteredSuggestions.length > 0 && (
              <div className="absolute top-full left-0 w-full mt-2 bg-white border border-gray-100 rounded-2xl shadow-xl z-10 overflow-hidden">
                {filteredSuggestions.map(s => (
                  <button key={s} onClick={() => addStack(s)} className="w-full text-left px-6 py-3 hover:bg-gray-50 font-bold text-sm text-text-sub flex items-center gap-3">
                    <img src={getStackLogoUrl(s)} className="w-5 h-5 object-contain" alt={s} />
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
      <button onClick={handleSave} className="bg-primary text-white px-10 py-4 rounded-2xl font-black shadow-lg shadow-primary/20 hover:scale-105 transition-all">저장하기</button>
    </div>
  );
};

const TeamSection = ({ user }: { user: User }) => {
  const [userProjects, setUserProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // 백엔드에서 사용자 프로젝트 목록 로드 (실패 시 정적 데이터 사용)
  // Load applied projects from the Project Service only.
  useEffect(() => {
    const loadUserProjects = async () => {
      if (!user?.id) {
        setLoading(false);
        return;
      }

      try {
        const applicationsResponse = await projectAPI.getMyApplications(user.id);
        const applications = applicationsResponse?.data?.applications || [];

        if (applications.length === 0) {
          setUserProjects([]);
          return;
        }

        const projectIds = applications.map((app: any) => app.project_id);
        const projectResults = await Promise.all(
          projectIds.map((id: number) => projectAPI.getProject(id).catch(() => null))
        );
        const projectMap = new Map<number, any>();
        projectResults.forEach((project: any) => {
          if (project?.project_id) {
            projectMap.set(project.project_id, project);
          }
        });

        const transformedProjects = applications.map((app: any) => {
          const project = projectMap.get(app.project_id);
          const positions = project?.recruitment_positions || [];
          const techSet = new Set<string>();
          positions.forEach((pos: any) => {
            const stacks = pos.required_stacks;
            if (Array.isArray(stacks)) {
              stacks.forEach((s: string) => techSet.add(s));
            } else if (typeof stacks === 'string') {
              try {
                const parsed = JSON.parse(stacks);
                if (Array.isArray(parsed)) {
                  parsed.forEach((s: string) => techSet.add(s));
                }
              } catch {
                // ignore parse errors
              }
            }
          });

          const status = (app.status || '').toLowerCase();
          return {
            id: app.project_id,
            title: project?.title || app.project_title || `프로젝트 #${app.project_id}`,
            userRole: status === 'accepted' ? 'Member' : 'Applicant',
            selectedPosition: app.position_type || '?? ??',
            status,
            tech_stacks: Array.from(techSet)
          };
        });

        setUserProjects(transformedProjects);
      } catch (error) {
        console.error('Failed to load applied projects:', error);
        setUserProjects([]);
      } finally {
        setLoading(false);
      }
    };

    loadUserProjects();
  }, [user?.id]);

  if (loading) {
    return (
      <div className="space-y-10 animate-fadeIn">
        <h3 className="text-3xl font-black">참여 중인 팀 및 지원 현황</h3>
        <div className="text-center py-20 text-gray-400">
          <p className="text-2xl mb-2">⏳</p>
          <p>프로젝트 목록을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-10 animate-fadeIn">
      <h3 className="text-3xl font-black">참여 중인 팀 및 지원 현황</h3>
      <div className="grid gap-6">
        {userProjects.length > 0 ? userProjects.map(p => {
          const pStatus = (p.status || '').toLowerCase();
          const pRole = (p.userRole || '').toLowerCase();
          return (
            <div key={p.id} className="p-8 border border-gray-100 rounded-[2.5rem] hover:bg-gray-50/50 transition-colors shadow-sm">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${pRole === 'leader' ? 'bg-amber-100 text-amber-600' :
                      pRole === 'applicant' ? 'bg-blue-100 text-blue-600' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                      {pRole === 'leader' ? '👑 리더' : pRole === 'applicant' ? '📝 지원자' : '👤 멤버'}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${pStatus === 'accepted' ? 'bg-primary/10 text-primary' :
                      pStatus === 'rejected' ? 'bg-red-50 text-red-500' :
                        'bg-yellow-50 text-yellow-500'
                      }`}>
                      {pStatus === 'accepted' ? '승인됨' : pStatus === 'rejected' ? '거절됨' : '심사중'}
                    </span>
                  </div>
                  <h4 className="text-xl font-black text-text-main leading-tight">{p.title}</h4>
                  <p className="text-xs text-text-sub font-bold">{p.selectedPosition || (pRole === 'leader' ? '팀 관리' : '포지션 미정')}</p>
                  {p.tech_stacks && p.tech_stacks.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {p.tech_stacks.slice(0, 3).map((tech: string, idx: number) => (
                        <span key={idx} className="text-[10px] bg-primary/5 text-primary px-2 py-0.5 rounded font-bold">
                          {tech}
                        </span>
                      ))}
                      {p.tech_stacks.length > 3 && (
                        <span className="text-[10px] text-gray-400 px-2 py-0.5">+{p.tech_stacks.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
                <Link to={`/projects/${p.id}`} className="bg-primary text-white px-6 py-3 rounded-2xl text-xs font-black shadow-lg shadow-primary/10 whitespace-nowrap hover:scale-105 transition-all">
                  프로젝트 공고 보기 →
                </Link>
              </div>

              {/* 승인된 프로젝트에 팀 스페이스 버튼 */}
              {pStatus === 'accepted' && (
                <div className="mt-4">
                  <Link to={`/team-space/${p.id}`} className="inline-flex items-center gap-2 bg-secondary text-white px-6 py-3 rounded-2xl text-xs font-black shadow-lg shadow-secondary/10 hover:scale-105 transition-all">
                    🚀 팀 스페이스 이동
                  </Link>
                </div>
              )}

              {/* 승인된 프로젝트에만 업무 현황 및 파일 공유 바로가기 표시 */}
              {pStatus === 'accepted' && (
                <div className="mt-6 pt-6 border-t border-gray-100">
                  <div className="flex flex-wrap gap-3">
                    <Link
                      to={`/team-space/${p.id}?tab=jira`}
                      className="flex items-center gap-2 px-4 py-2.5 bg-blue-50 text-blue-600 rounded-xl text-xs font-bold hover:bg-blue-100 transition-colors"
                    >
                      <span>📋</span> 업무 현황
                    </Link>
                    <Link
                      to={`/team-space/${p.id}?tab=files`}
                      className="flex items-center gap-2 px-4 py-2.5 bg-green-50 text-green-600 rounded-xl text-xs font-bold hover:bg-green-100 transition-colors"
                    >
                      <span>📁</span> 파일 공유
                    </Link>
                    <Link
                      to={`/team-space/${p.id}?tab=chat`}
                      className="flex items-center gap-2 px-4 py-2.5 bg-purple-50 text-purple-600 rounded-xl text-xs font-bold hover:bg-purple-100 transition-colors"
                    >
                      <span>💬</span> 팀 채팅
                    </Link>
                    <Link
                      to={`/team-space/${p.id}?tab=meetings`}
                      className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 text-amber-600 rounded-xl text-xs font-bold hover:bg-amber-100 transition-colors"
                    >
                      <span>📄</span> 회의록
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )
        }) : (
          <div className="py-20 text-center opacity-40">참여 중인 팀이 없습니다.</div>
        )}
      </div>
    </div>
  );
};

const TestResultSection = ({ testResults }: { testResults: TestResult[] }) => (
  <div className="space-y-10 animate-fadeIn">
    <h3 className="text-3xl font-black">AI 역량 테스트 결과</h3>
    <div className="grid gap-6">
      {testResults.length > 0 ? testResults.map((result, idx) => (
        <div key={idx} className="bg-gray-50/50 p-6 rounded-[2.5rem] border border-gray-100 flex flex-col gap-6">
          <div className="flex justify-between items-center border-b border-gray-100 pb-4">
            <div>
              <span className="text-xs font-black text-primary bg-primary/10 px-3 py-1 rounded-full">{result.skill}</span>
              {result.projectTitle && (
                <span className="ml-2 text-xs font-black text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  📂 {result.projectTitle}
                </span>
              )}
              {!result.projectTitle && result.projectId && (
                <span className="ml-2 text-xs font-black text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                  📂 {'\uD504\uB85C\uC81D\uD2B8'} #{result.projectId}
                </span>
              )}
              <span className="ml-3 text-xs text-text-sub font-bold">{result.date}</span>
            </div>
            <div className="text-lg font-black text-text-main">
              {result.score}점 <span className="text-sm font-medium text-gray-400">({result.level})</span>
            </div>
          </div>

          <div className="space-y-4">
            {(() => {
              try {
                const data = JSON.parse(result.feedback);
                return (
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="bg-white p-5 rounded-2xl shadow-sm border border-indigo-50/50">
                      <strong className="block text-indigo-600 mb-2 flex items-center gap-2 text-sm">
                        <span>📊</span> 강점 및 보완점
                      </strong>
                      <p className="text-sm text-text-main leading-relaxed whitespace-pre-wrap">{data.summary}</p>
                    </div>
                    <div className="bg-white p-5 rounded-2xl shadow-sm border border-emerald-50/50">
                      <strong className="block text-emerald-600 mb-2 flex items-center gap-2 text-sm">
                        <span>🌱</span> 성장 가이드
                      </strong>
                      <p className="text-sm text-text-main leading-relaxed whitespace-pre-wrap">{data.growth_guide}</p>
                    </div>
                  </div>
                );
              } catch {
                return <p className="text-sm text-text-sub leading-relaxed whitespace-pre-wrap bg-white p-4 rounded-xl">"{result.feedback}"</p>;
              }
            })()}
          </div>
        </div>
      )) : <div className="py-20 text-center opacity-40">테스트 내역이 없습니다.</div>}
    </div>
  </div>
);

const SecuritySection = ({ user, changePassword, logout }: any) => {
    const navigate = useNavigate();
    const [oldPw, setOldPw] = useState('');
    const [newPw, setNewPw] = useState('');
    const [deletePw, setDeletePw] = useState('');
    const [deleteReason, setDeleteReason] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);

    const handlePwChange = async () => {
      try {
        await changePassword(oldPw, newPw);
        alert('비밀번호가 변경되었습니다.');
        setOldPw('');
        setNewPw('');
      } catch (e: any) {
        alert(e.message || '오류가 발생했습니다.');
      }
    };

    const handleDeleteAccount = async () => {
      if (!user?.id) return;
      if (!deletePw) {
        alert('탈퇴를 진행하려면 비밀번호를 입력해주세요.');
        return;
      }
      if (!confirm('정말 회원탈퇴를 진행하시겠습니까?')) return;

      setIsDeleting(true);
      try {
        await authAPI.deleteAccount(user.id, deletePw, deleteReason || undefined);
        await logout();
        alert('회원탈퇴가 완료되었습니다.');
        navigate('/');
      } catch (e: any) {
        alert(e.message || '회원탈퇴에 실패했습니다.');
      } finally {
        setIsDeleting(false);
        setDeletePw('');
      }
    };

    return (
      <div className="space-y-12 animate-fadeIn">
        <h3 className="text-3xl font-black">계정 및 보안</h3>
        <div className="max-w-md space-y-6">
          <InputField label="현재 비밀번호" type="password" value={oldPw} onChange={setOldPw} />
          <InputField label="새 비밀번호" type="password" value={newPw} onChange={setNewPw} />
          <button onClick={handlePwChange} className="w-full bg-text-main text-white py-4 rounded-2xl font-black shadow-xl">비밀번호 변경하기</button>
        </div>

        <div className="border-t border-gray-100 pt-8">
          <h4 className="text-lg font-black text-red-600 mb-4">회원 탈퇴</h4>
          <div className="max-w-md space-y-4">
            <InputField label="비밀번호 확인" type="password" value={deletePw} onChange={setDeletePw} />
            <div className="space-y-2">
              <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">탈퇴 사유 (선택)</label>
              <textarea
                rows={3}
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                className="w-full bg-gray-50 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-red-200 font-medium"
                placeholder="탈퇴 사유를 적어주세요."
              />
            </div>
            <button
              onClick={handleDeleteAccount}
              className="w-full bg-red-500 text-white py-4 rounded-2xl font-black shadow-xl disabled:opacity-60"
              disabled={isDeleting}
            >
              {isDeleting ? '처리 중...' : '회원탈퇴 진행'}
            </button>
          </div>
        </div>
      </div>
    );
  };

const InputField = ({ label, value, onChange, type = "text" }: any) => (
  <div className="space-y-2">
    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">{label}</label>
    <input type={type} value={value} onChange={e => onChange(e.target.value)} className="w-full bg-gray-50 p-5 rounded-2xl border-none outline-none focus:ring-2 focus:ring-primary/20 font-bold" />
  </div>
);

const MenuBtn = ({ active, onClick, label, icon }: any) => (
  <button onClick={onClick} className={`w-full text-left px-8 py-5 rounded-2xl font-bold transition-all flex items-center gap-4 ${active ? 'bg-primary text-white shadow-lg' : 'text-text-secondary hover:bg-gray-50'}`}>
    <span className="text-xl">{icon}</span> <span>{label}</span>
  </button>
);

export default MyPage;
