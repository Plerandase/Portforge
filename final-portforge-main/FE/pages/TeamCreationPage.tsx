
import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { projectAPI } from '../api/apiClient';

const RECRUIT_POSITIONS = [
  { id: 'frontend', name: '프론트엔드', icon: '💻', cat: '프론트엔드' },
  { id: 'backend', name: '백엔드', icon: '⚙️', cat: '백엔드' },
  { id: 'db', name: 'DB', icon: '🗄️', cat: 'DB' },
  { id: 'infra', name: '인프라', icon: '☁️', cat: '인프라' },
  { id: 'design', name: '디자인', icon: '🎨', cat: '디자인' },
  { id: 'etc', name: '기타', icon: '➕', cat: '기타' }
];

const STACK_CATEGORIES: any = {
  '인기': ['JavaScript', 'TypeScript', 'React', 'Vue', 'Nextjs', 'Nodejs', 'Java', 'Spring', 'Kotlin', 'Nestjs', 'Swift', 'Flutter', 'Figma', 'AWS', 'Docker'],
  '프론트엔드': ['React', 'Vue', 'Nextjs', 'Svelte', 'Angular', 'TypeScript', 'JavaScript', 'TailwindCSS', 'StyledComponents', 'Redux', 'Recoil', 'Vite', 'Webpack'],
  '백엔드': ['Java', 'Spring', 'Nodejs', 'Nestjs', 'Go', 'Python', 'Django', 'Flask', 'Express', 'php', 'Laravel', 'GraphQL', 'RubyOnRails', 'C#', '.NET'],
  'DB': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQLite', 'MariaDB', 'Cassandra', 'DynamoDB', 'FirebaseFirestore', 'ElasticSearch', 'Prisma'],
  '인프라': ['AWS', 'Docker', 'Kubernetes', 'GCP', 'Azure', 'Terraform', 'Jenkins', 'GithubActions', 'Nginx', 'Linux', 'Vercel', 'Netlify'],
  '디자인': ['Figma', 'AdobeXD', 'Sketch', 'Canva', 'Photoshop', 'Illustrator', 'Blender', 'UI/UX 디자인', '브랜딩'],
  '기타': ['Git', 'Slack', 'Jira', 'Notion', 'Discord', 'Postman', 'Swagger', 'Zeplin']
};

const getStackLogoUrl = (stack: string) => {
  const mapping: Record<string, string> = {
    'JavaScript': 'js', 'TypeScript': 'ts', 'React': 'react', 'Vue': 'vue', 'Nextjs': 'nextjs', 'Nodejs': 'nodejs',
    'Java': 'java', 'Spring': 'spring', 'Kotlin': 'kotlin', 'Nestjs': 'nestjs', 'Swift': 'swift', 'Flutter': 'flutter',
    'Figma': 'figma', 'AWS': 'aws', 'Docker': 'docker', 'Svelte': 'svelte', 'Angular': 'angular', 'TailwindCSS': 'tailwind',
    'StyledComponents': 'styledcomponents', 'Redux': 'redux', 'Vite': 'vite', 'Webpack': 'webpack', 'Python': 'python',
    'Django': 'django', 'Flask': 'flask', 'MySQL': 'mysql', 'PostgreSQL': 'postgres', 'MongoDB': 'mongodb',
    'Redis': 'redis', 'FirebaseFirestore': 'firebase', 'Kubernetes': 'kubernetes', 'GithubActions': 'githubactions',
    'Nginx': 'nginx', 'Linux': 'linux', 'Git': 'git', 'Slack': 'slack', 'Discord': 'discord', 'Postman': 'postman',
    'Vercel': 'vercel',
  };
  const slug = mapping[stack] || stack.toLowerCase();
  return `https://skillicons.dev/icons?i=${slug}`;
};

const TeamCreationPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  if (!user) { navigate('/login'); return null; }

  const [formData, setFormData] = useState({
    type: '프로젝트' as '프로젝트' | '스터디',
    title: '',
    method: 'ONLINE' as 'ONLINE' | 'OFFLINE' | 'MIXED',
    positionCounts: {
      frontend: 0,
      backend: 0,
      db: 0,
      infra: 0,
      design: 0,
      etc: 0
    } as Record<string, number>,
    studyCapacity: 4,
    selectedStacks: [] as string[],
    startDate: '',
    endDate: '',
    recruitDeadline: '',
    testRequired: false,
    description: ''
  });

  const [activeStackCat, setActiveStackCat] = useState('인기');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateCount = (posId: string, delta: number) => {
    setFormData(prev => ({
      ...prev,
      positionCounts: {
        ...prev.positionCounts,
        [posId]: Math.max(0, (prev.positionCounts[posId] || 0) + delta)
      }
    }));
  };

  const updateStudyCapacity = (delta: number) => {
    setFormData(prev => ({
      ...prev,
      studyCapacity: Math.max(2, prev.studyCapacity + delta)
    }));
  };

  const toggleStack = (stack: string) => {
    setFormData(prev => ({
      ...prev,
      selectedStacks: prev.selectedStacks.includes(stack)
        ? prev.selectedStacks.filter(s => s !== stack)
        : [...prev.selectedStacks, stack]
    }));
  };

  const isPosValid = (posId: string) => {
    if (formData.type === '스터디') return true;
    const pos = RECRUIT_POSITIONS.find(p => p.id === posId);
    if (!pos || formData.positionCounts[posId] === 0) return true;
    const relatedStacks = STACK_CATEGORIES[pos.cat] || [];
    return formData.selectedStacks.some(s => relatedStacks.includes(s));
  };

  // 기술 스택 선택이 필요한 카테고리들 추출
  const unsatisfiedCats = useMemo(() => {
    if (formData.type === '스터디') return formData.selectedStacks.length === 0 ? ['스터디'] : [];
    return RECRUIT_POSITIONS
      .filter(pos => formData.positionCounts[pos.id] > 0 && !isPosValid(pos.id))
      .map(pos => pos.cat);
  }, [formData.positionCounts, formData.selectedStacks, formData.type]);

  const totalMembers = formData.type === '프로젝트'
    ? (Object.values(formData.positionCounts) as number[]).reduce((a, b) => a + b, 0)
    : formData.studyCapacity;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return alert('제목을 입력해주세요.');

    if (!formData.recruitDeadline) return alert('모집 마감일을 선택해주세요.');
    if (!formData.startDate) return alert('활동 시작일을 선택해주세요.');
    if (!formData.endDate) return alert('예상 종료일을 선택해주세요.');
    
    // 날짜 유효성 검사
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const recruitDeadline = new Date(formData.recruitDeadline);
    const startDate = new Date(formData.startDate);
    const endDate = new Date(formData.endDate);
    
    if (recruitDeadline < today) return alert('모집 마감일은 오늘 이후여야 합니다.');
    if (startDate < recruitDeadline) return alert('활동 시작일은 모집 마감일 이후여야 합니다.');
    if (endDate < startDate) return alert('예상 종료일은 활동 시작일 이후여야 합니다.');

    if (formData.type === '프로젝트') {
      if (totalMembers === 0) return alert('모집할 포지션 인원을 1명 이상 설정해주세요.');
      const invalidPositions = RECRUIT_POSITIONS.filter(p => !isPosValid(p.id));
      if (invalidPositions.length > 0) {
        alert(`다음 포지션의 기술 스택을 최소 하나 이상 선택해주세요: ${invalidPositions.map(p => p.name).join(', ')}`);
        setActiveStackCat(invalidPositions[0].cat);
        return;
      }
    } else {
      if (formData.selectedStacks.length === 0) return alert('어떤 주제로 스터디를 할지 기술 스택을 최소 하나 선택해주세요.');
    }

    setIsSubmitting(true);

    try {
      // API 요청 데이터 구성
      // 각 포지션에 해당 카테고리의 스택 + 공통 스택(인기)을 모두 포함
      const recruitmentPositions = formData.type === '프로젝트'
        ? RECRUIT_POSITIONS
          .filter(pos => formData.positionCounts[pos.id] > 0)
          .map(pos => {
            // 해당 포지션 카테고리에 속하는 스택 필터링
            const categoryStacks = STACK_CATEGORIES[pos.cat] || [];
            const positionStacks = formData.selectedStacks.filter(s => categoryStacks.includes(s));
            
            // 만약 해당 카테고리에 매칭되는 스택이 없으면 선택된 모든 스택 사용
            const finalStacks = positionStacks.length > 0 ? positionStacks : formData.selectedStacks;
            
            return {
              position_type: pos.name,
              target_count: formData.positionCounts[pos.id],
              required_stacks: finalStacks,
              recruitment_deadline: formData.recruitDeadline
            };
          })
        : [{ 
            position_type: '스터디원', 
            target_count: formData.studyCapacity, 
            required_stacks: formData.selectedStacks,
            recruitment_deadline: formData.recruitDeadline
          }];

      console.log('📋 생성할 모집 포지션:', recruitmentPositions);

      const projectData = {
        user_id: user.id,  // 사용자 ID 추가
        type: formData.type === '프로젝트' ? 'PROJECT' : 'STUDY',
        title: formData.title,
        description: formData.description,
        start_date: formData.startDate,
        end_date: formData.endDate,
        method: formData.method,
        test_required: formData.testRequired,
        recruitment_positions: recruitmentPositions
      };

      console.log('📤 프로젝트 생성 요청 데이터:', projectData);

      await projectAPI.createProject(projectData);

      alert(`${formData.type} 모집 공고가 게시되었습니다!`);
      navigate('/');
    } catch (error: any) {
      console.error('Failed to create project:', error);
      alert(error.message || '프로젝트 생성에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="max-w-4xl mx-auto space-y-12 py-10 animate-fadeIn">
      <div className="space-y-4">
        <h1 className="text-4xl font-black tracking-tight text-text-main">
          {formData.type === '프로젝트' ? '프로젝트 팀 빌딩 🚀' : '스터디 멤버 모집 📚'}
        </h1>
        <p className="text-text-sub font-medium text-lg">새로운 항해를 함께할 팀원을 모집합니다.</p>
      </div>

      <div className="bg-white p-12 rounded-[3.5rem] shadow-2xl border border-gray-100">
        <form className="space-y-12" onSubmit={handleSubmit}>

          <div className="space-y-10">
            <FormItem label="모집 공고 제목" required>
              <input
                type="text"
                value={formData.title}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
                className="w-full bg-gray-50 p-6 rounded-3xl font-black border-none outline-none focus:ring-2 focus:ring-primary/20 shadow-inner text-xl"
                placeholder="공고 제목을 입력하세요"
              />
            </FormItem>

            <div className="grid md:grid-cols-2 gap-10">
              <FormItem label="모집 유형" required>
                <div className="flex gap-2 p-1.5 bg-gray-50 rounded-2xl">
                  {['프로젝트', '스터디'].map(t => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setFormData({
                        ...formData,
                        type: t as any,
                        testRequired: t === '스터디' ? false : formData.testRequired
                      })}
                      className={`flex-1 py-4 rounded-xl text-sm font-black transition-all ${formData.type === t ? 'bg-white text-primary shadow-sm' : 'text-gray-400'}`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </FormItem>
              <FormItem label="진행 방식" required>
                <div className="flex gap-2 p-1.5 bg-gray-50 rounded-2xl">
                  {[
                    { value: 'ONLINE', label: '온라인' },
                    { value: 'OFFLINE', label: '오프라인' },
                    { value: 'MIXED', label: '온/오프라인' }
                  ].map(m => (
                    <button key={m.value} type="button" onClick={() => setFormData({ ...formData, method: m.value as any })} className={`flex-1 py-4 rounded-xl text-sm font-black transition-all ${formData.method === m.value ? 'bg-white text-primary shadow-sm' : 'text-gray-400'}`}>{m.label}</button>
                  ))}
                </div>
              </FormItem>
            </div>

            <FormItem label="AI 역량 테스트 활성화">
              <div className="flex gap-2 p-1.5 bg-gray-50 rounded-2xl max-w-xs">
                {[true, false].map(b => {
                  const isStudy = formData.type === '스터디';
                  const isDisabled = isStudy && b === true;
                  return (
                    <button
                      key={String(b)}
                      type="button"
                      disabled={isDisabled}
                      onClick={() => setFormData({ ...formData, testRequired: b })}
                      className={`flex-1 py-4 rounded-xl text-sm font-black transition-all ${
                        formData.testRequired === b ? 'bg-white text-secondary shadow-sm' : 'text-gray-400'
                      } ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''}`}
                    >
                      {b ? 'ON' : 'OFF'}
                    </button>
                  );
                })}
              </div>
            </FormItem>
          </div>

          <div className="grid md:grid-cols-3 gap-8 pt-6 border-t border-gray-50">
            <FormItem label="모집 마감일" required>
              <input 
                type="date" 
                required 
                value={formData.recruitDeadline} 
                onChange={e => setFormData({ ...formData, recruitDeadline: e.target.value })} 
                min={new Date().toISOString().split('T')[0]}
                className="w-full bg-gray-50 p-5 rounded-2xl font-black border-none outline-none text-sm focus:ring-2 focus:ring-primary/20 accent-primary" 
              />
            </FormItem>
            <FormItem label="활동 시작일" required>
              <input 
                type="date" 
                required 
                value={formData.startDate} 
                onChange={e => setFormData({ ...formData, startDate: e.target.value })} 
                min={formData.recruitDeadline || new Date().toISOString().split('T')[0]}
                className="w-full bg-gray-50 p-5 rounded-2xl font-black border-none outline-none text-sm focus:ring-2 focus:ring-primary/20 accent-primary" 
              />
            </FormItem>
            <FormItem label="예상 종료일" required>
              <input 
                type="date" 
                required 
                value={formData.endDate} 
                onChange={e => setFormData({ ...formData, endDate: e.target.value })} 
                min={formData.startDate || new Date().toISOString().split('T')[0]}
                className="w-full bg-gray-50 p-5 rounded-2xl font-black border-none outline-none text-sm focus:ring-2 focus:ring-primary/20 accent-primary" 
              />
            </FormItem>
          </div>

          {formData.type === '프로젝트' ? (
            <div className="space-y-8">
              <div className="flex justify-between items-end px-1">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">포지션별 모집 인원 <span className="text-red-500">*</span></label>
                <span className="text-sm font-black text-primary">총 {totalMembers}명</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {RECRUIT_POSITIONS.map((pos) => {
                  const needsStack = formData.positionCounts[pos.id] > 0 && !isPosValid(pos.id);
                  return (
                    <div key={pos.id} className={`p-6 rounded-[2rem] border-2 transition-all bg-white flex items-center justify-between relative overflow-hidden ${needsStack ? 'border-red-100 ring-2 ring-red-50' : 'border-gray-50'}`}>
                      {needsStack && (
                        <div className="absolute top-0 right-0 bg-red-500 text-white px-3 py-1 text-[8px] font-black rounded-bl-xl animate-pulse">
                          ⚠️ 기술 선택 필요
                        </div>
                      )}
                      <div className="flex items-center gap-4">
                        <span className="text-2xl">{pos.icon}</span>
                        <span className="font-black text-text-main">{pos.name}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <button type="button" onClick={() => updateCount(pos.id, -1)} className="w-8 h-8 rounded-full border flex items-center justify-center font-black">-</button>
                        <span className="font-black">{formData.positionCounts[pos.id]}</span>
                        <button type="button" onClick={() => updateCount(pos.id, 1)} className="w-8 h-8 rounded-full border flex items-center justify-center font-black">+</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 p-8 rounded-[2.5rem] border border-gray-100 flex justify-between items-center">
              <h4 className="font-black">스터디 총 모집 인원 <span className="text-red-500">*</span></h4>
              <div className="flex items-center gap-6">
                <button type="button" onClick={() => updateStudyCapacity(-1)} className="w-10 h-10 rounded-full bg-white font-black shadow-sm">-</button>
                <span className="text-2xl font-black text-primary">{formData.studyCapacity}명</span>
                <button type="button" onClick={() => updateStudyCapacity(1)} className="w-10 h-10 rounded-full bg-white font-black shadow-sm">+</button>
              </div>
            </div>
          )}

          {/* 복구 및 시각적 피드백 강화된 기술 스택 선택 영역 */}
          <div className="space-y-6">
            <FormItem label="기술 스택 설정" required>
              <div className="bg-gray-50 p-8 rounded-[2.5rem] space-y-8">
                <div className="flex gap-4 overflow-x-auto hide-scrollbar pb-2">
                  {Object.keys(STACK_CATEGORIES).map(cat => {
                    const isSelected = activeStackCat === cat;
                    const hasSelectionInCat = STACK_CATEGORIES[cat].some((s: string) => formData.selectedStacks.includes(s));
                    const isRequired = unsatisfiedCats.includes(cat);

                    return (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => setActiveStackCat(cat)}
                        className={`px-6 py-3 rounded-full text-xs font-black transition-all whitespace-nowrap border-2 relative ${isSelected
                            ? 'bg-primary text-white border-primary shadow-lg'
                            : isRequired
                              ? 'bg-white text-red-500 border-red-200'
                              : hasSelectionInCat
                                ? 'bg-white text-primary border-primary/30'
                                : 'bg-white text-gray-400 border-transparent hover:border-gray-200'
                          }`}
                      >
                        {cat}
                        {isRequired && (
                          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white animate-bounce"></span>
                        )}
                        {!isRequired && hasSelectionInCat && (
                          <span className="ml-1.5 opacity-50 text-[8px]">✓</span>
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                  {STACK_CATEGORIES[activeStackCat].map((stack: string) => {
                    const isSelected = formData.selectedStacks.includes(stack);
                    return (
                      <button
                        key={stack}
                        type="button"
                        onClick={() => toggleStack(stack)}
                        className={`flex items-center gap-3 p-3 rounded-2xl border-2 transition-all group ${isSelected ? 'bg-white border-primary shadow-md' : 'bg-white border-transparent hover:border-gray-100 opacity-60 hover:opacity-100'}`}
                      >
                        <img src={getStackLogoUrl(stack)} className="w-6 h-6 object-contain" alt={stack} />
                        <span className={`text-[11px] font-bold truncate ${isSelected ? 'text-primary' : 'text-text-sub'}`}>{stack}</span>
                        {isSelected && <span className="ml-auto text-primary text-[10px]">✓</span>}
                      </button>
                    );
                  })}
                </div>
                <div className="pt-4 flex flex-wrap gap-2">
                  {formData.selectedStacks.length > 0 ? (
                    formData.selectedStacks.map(s => (
                      <span key={s} className="px-3 py-1.5 bg-primary/10 text-primary rounded-lg text-[10px] font-black border border-primary/20 flex items-center gap-2">
                        {s}
                        <button type="button" onClick={() => toggleStack(s)} className="hover:text-primary-dark">✕</button>
                      </span>
                    ))
                  ) : (
                    <p className="text-[11px] text-gray-400 italic">모집하시는 포지션에 맞춰 기술 스택을 선택해 주세요.</p>
                  )}
                </div>
              </div>
            </FormItem>
          </div>

          <FormItem label="상세 소개" required>
            <textarea
              rows={8}
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              className="w-full bg-gray-50 p-8 rounded-[2.5rem] font-medium leading-relaxed border-none outline-none focus:ring-2 focus:ring-primary/20 shadow-inner"
              placeholder="프로젝트나 스터디의 목표와 협업 방식을 상세히 들려주세요."
            ></textarea>
          </FormItem>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-primary text-white py-6 rounded-[2.5rem] font-black text-xl shadow-2xl shadow-primary/20 hover:scale-[1.01] transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {isSubmitting ? '생성 중...' : '모집 시작하기'}
          </button>
        </form>
      </div>
    </div>
  );
};

const FormItem = ({ label, children, required }: any) => (
  <div className="space-y-4">
    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">
      {label} {required && <span className="text-red-500">*</span>}
    </label>
    {children}
  </div>
);

export default TeamCreationPage;
