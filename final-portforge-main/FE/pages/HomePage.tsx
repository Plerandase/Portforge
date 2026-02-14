
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, Project, Notice } from '../contexts/AuthContext';
import { projectAPI, supportAPI } from '../api/apiClient'; // ✅ API 클라이언트 추가

// 기본 기술 스택 데이터베이스 (분류용)
export const STACK_CATEGORIES_BASE: any = {
  '프론트엔드': ['React', 'Vue', 'Nextjs', 'Svelte', 'Angular', 'TypeScript', 'JavaScript', 'TailwindCSS', 'StyledComponents', 'Redux', 'Recoil', 'Vite', 'Webpack'],
  '백엔드': ['Java', 'Spring', 'Nodejs', 'Nestjs', 'Go', 'Python', 'Django', 'Flask', 'Express', 'php', 'Laravel', 'GraphQL', 'RubyOnRails', 'C#', '.NET'],
  'DB': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQLite', 'MariaDB', 'Cassandra', 'DynamoDB', 'FirebaseFirestore', 'Prisma'],
  '인프라': ['AWS', 'Docker', 'Kubernetes', 'GCP', 'Azure', 'Terraform', 'Jenkins', 'GithubActions', 'Nginx', 'Linux', 'Vercel', 'Netlify'],
  '디자인': ['Figma', 'AdobeXD', 'Sketch', 'Canva', 'Photoshop', 'Illustrator', 'Blender', 'UI/UX 디자인', '브랜딩'],
  '기타': ['Git', 'Slack', 'Jira', 'Notion', 'Discord', 'Postman', 'Swagger', 'Zeplin']
};

export const getStackLogoUrl = (stack: string) => {
  const mapping: Record<string, string> = {
    'JavaScript': 'js', 'TypeScript': 'ts', 'React': 'react', 'Vue': 'vue', 'Nextjs': 'nextjs', 'Nodejs': 'nodejs',
    'Java': 'java', 'Spring': 'spring', 'Kotlin': 'kotlin', 'Nestjs': 'nestjs', 'Swift': 'swift', 'Flutter': 'flutter',
    'Figma': 'figma', 'AWS': 'aws', 'Docker': 'docker', 'Svelte': 'svelte', 'Angular': 'angular', 'TailwindCSS': 'tailwind',
    'StyledComponents': 'styledcomponents', 'Redux': 'redux', 'Vite': 'vite', 'Webpack': 'webpack', 'Python': 'python',
    'Django': 'django', 'Flask': 'flask', 'MySQL': 'mysql', 'PostgreSQL': 'postgres', 'MongoDB': 'mongodb',
    'Redis': 'redis', 'FirebaseFirestore': 'firebase', 'Kubernetes': 'kubernetes', 'GithubActions': 'githubactions',
    'Nginx': 'nginx', 'Linux': 'linux', 'Git': 'git', 'Slack': 'slack', 'Discord': 'discord', 'Postman': 'postman',
    'Vercel': 'vercel', 'AdobeXD': 'xd', 'Sketch': 'sketch', 'Canva': 'canva', 'Photoshop': 'ps', 'Illustrator': 'ai',
    'Blender': 'blender'
  };
  const slug = mapping[stack] || stack.toLowerCase();
  return `https://skillicons.dev/icons?i=${slug}`;
};

export const parseRecruitment = (membersStr: string) => {
  if (!membersStr) return [];
  return membersStr.split(', ').map(part => {
    const lastSpaceIndex = part.lastIndexOf(' ');
    const pos = part.substring(0, lastSpaceIndex);
    const count = part.substring(lastSpaceIndex + 1);
    const [current, target] = count.split('/').map(v => parseInt(v));
    return { pos, current, target };
  });
};

const getPosIcon = (pos: string) => {
  if (pos.includes('프론트')) return '💻';
  if (pos.includes('백엔드')) return '⚙️';
  if (pos.includes('DB') || pos.includes('데이터베이스')) return '🗄️';
  if (pos.includes('인프라')) return '☁️';
  if (pos.includes('디자인')) return '🎨';
  return '👥';
};

export const StatusChip: React.FC<{ pos: string, current: number, target: number }> = ({ pos, current, target }) => {
  const isFull = current >= target;
  return (
    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-[11px] font-black transition-all ${isFull ? 'bg-gray-50 border-gray-100 text-gray-400' : 'bg-white border-primary/20 text-text-main shadow-sm'
      }`}>
      <span className="opacity-70">{getPosIcon(pos)}</span>
      <span className="whitespace-nowrap">{pos}</span>
      <span className={`ml-1 ${isFull ? 'text-gray-300' : 'text-primary'}`}>{current}/{target}</span>
    </div>
  );
};

export const calculateDDay = (targetDate: string) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(targetDate);
  target.setHours(0, 0, 0, 0);
  const diffTime = target.getTime() - today.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return '모집마감';
  if (diffDays === 0) return 'D-Day';
  return `D-${diffDays}`;
};

export const calculateDuration = (start: string, end: string) => {
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffTime = Math.abs(endDate.getTime() - startDate.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
};

// 프로젝트 타입을 한글로 변환 (영어로 올 경우 대비)
export const getProjectTypeKorean = (type: string) => {
  const typeMap: Record<string, string> = {
    'PROJECT': '프로젝트',
    'STUDY': '스터디',
    'project': '프로젝트',
    'study': '스터디',
    '프로젝트': '프로젝트',
    '스터디': '스터디'
  };
  return typeMap[type] || type;
};

// 모집 마감일 중 가장 빠른 날짜 추출
const getEarliestRecruitmentDeadline = (positions: any[] | undefined): string | null => {
  if (!positions || positions.length === 0) return null;
  const deadlines = positions
    .map(p => p.recruitment_deadline)
    .filter(d => d); // null/undefined 제외
  if (deadlines.length === 0) return null;
  return deadlines.sort()[0]; // 가장 빠른 날짜
};

// API 응답 데이터 변환 함수
// 백엔드(project_crud.py)가 recruitment_deadline 기반으로 D-day를 계산해서 deadline 필드로 보내줌
const transformProject = (apiProject: any): Project => {
  // 백엔드에서 이미 계산된 deadline 필드 우선 사용
  // 없으면 recruitment_positions에서 추출, 그것도 없으면 end_date 사용
  let deadline = apiProject.deadline;
  if (!deadline) {
    const recruitmentDeadline = getEarliestRecruitmentDeadline(apiProject.recruitment_positions);
    const deadlineDate = recruitmentDeadline || apiProject.end_date || apiProject.endDate;
    deadline = calculateDDay(deadlineDate);
  }

  // members 문자열 생성 - 백엔드에서 제공하거나 recruitment_positions에서 생성
  let members = apiProject.members;
  if (!members || members === '0/0명') {
    const positions = apiProject.recruitment_positions || [];
    if (positions.length > 0) {
      const posNameMap: Record<string, string> = {
        'FRONTEND': '프론트엔드',
        'BACKEND': '백엔드',
        'DESIGN': '디자인',
        'DB': 'DB',
        'INFRA': '인프라',
        'ETC': '기타',
        'STUDY_MEMBER': '스터디원',
        '프론트엔드': '프론트엔드',
        '백엔드': '백엔드',
        '디자인': '디자인',
        '스터디원': '스터디원'
      };
      members = positions.map((p: any) => {
        const posName = posNameMap[p.position_type] || p.position_type;
        return `${posName} ${p.current_count || 0}/${p.target_count || 0}`;
      }).join(', ');
    }
  }

  // tags 추출 - 백엔드에서 제공하거나 recruitment_positions에서 추출
  let tags = apiProject.tags || [];
  if ((!tags || tags.length === 0) && apiProject.recruitment_positions) {
    const allStacks = new Set<string>();
    apiProject.recruitment_positions.forEach((p: any) => {
      const stacks = p.required_stacks || [];
      stacks.forEach((s: string) => allStacks.add(s));
    });
    tags = Array.from(allStacks);
  }

  const methodMap: Record<string, string> = {
    'ONLINE': '온라인',
    'OFFLINE': '오프라인',
    'MIXED': '온/오프라인'
  };

  return {
    id: apiProject.project_id || apiProject.id,
    type: apiProject.type === 'PROJECT' ? '프로젝트' : apiProject.type === 'STUDY' ? '스터디' : (apiProject.type === '프로젝트' || apiProject.type === '스터디' ? apiProject.type : '프로젝트'),
    title: apiProject.title,
    description: apiProject.description || '',
    deadline: deadline,
    views: apiProject.views || 0,
    members: members || '',
    tags: tags,
    position: apiProject.position || apiProject.recruitment_positions?.[0]?.position_type || '미정',
    method: methodMap[apiProject.method] || apiProject.method || '온/오프라인',
    status: apiProject.status === 'RECRUITING' ? '모집중' : (apiProject.status === '모집중' || apiProject.status === '모집완료' ? apiProject.status : '모집완료'),
    authorId: apiProject.user_id || apiProject.authorId || '',
    authorName: apiProject.leader_name || apiProject.leaderName || '익명',
    startDate: apiProject.start_date || apiProject.startDate || '',
    endDate: apiProject.end_date || apiProject.endDate || '',
    testRequired: apiProject.test_required || apiProject.testRequired || false,
    applicants: []
  };
};

const HomePage: React.FC = () => {
  const { user, toggleLike, filterResetKey, resetAllFilters } = useAuth();
  const navigate = useNavigate();

  // ✅ [수정] API 데이터 로드 상태 추가
  const [projects, setProjects] = useState<Project[]>([]);
  const [banners, setBanners] = useState<any[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<'전체' | '프로젝트' | '스터디'>('전체');
  const [showStackFilterArea, setShowStackFilterArea] = useState(false);
  const [activeStackCat, setActiveStackCat] = useState('인기');
  const [selectedStacks, setSelectedStacks] = useState<string[]>([]);
  const [activePos, setActivePos] = useState('전체');
  const [activeMethod, setActiveMethod] = useState('전체');
  const [showBookmarks, setShowBookmarks] = useState(false);
  const [displayCount, setDisplayCount] = useState(6);
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);

  // Banner Carousel State
  const [currentBannerIdx, setCurrentBannerIdx] = useState(0);

  // ✅ [수정] 데이터 로드 useEffect (백엔드 연동)
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // 프로젝트 목록 가져오기
        const projectsData = await projectAPI.getProjects(1, 50);
        const projectList = Array.isArray(projectsData) ? projectsData : projectsData.projects || [];
        setProjects(projectList.map(transformProject));

        // 배너 가져오기 (API 없으면 기본값)
        try {
          const bannersData = await supportAPI.getBanners();
          setBanners(bannersData.length > 0 ? bannersData : [{ id: 1, title: '🚀 Portforge에 오신 것을 환영합니다!', link: '/events', active: true }]);
        } catch (e) {
          setBanners([{ id: 1, title: '🚀 Portforge에 오신 것을 환영합니다!', link: '/events', active: true }]);
        }

        // 공지사항 가져오기
        try {
          const noticesData = await supportAPI.getNotices();
          setNotices(noticesData.length > 0 ? noticesData : [{ id: 1, title: 'Portforge 정식 오픈!', content: '환영합니다.', date: new Date().toISOString().split('T')[0] }]);
        } catch (e) {
          setNotices([{ id: 1, title: 'Portforge 정식 오픈!', content: '환영합니다.', date: new Date().toISOString().split('T')[0] }]);
        }

      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const nextBanner = useCallback(() => {
    if (banners.length <= 1) return;
    setCurrentBannerIdx(prev => (prev + 1) % banners.length);
  }, [banners.length]);

  const prevBanner = useCallback(() => {
    if (banners.length <= 1) return;
    setCurrentBannerIdx(prev => (prev - 1 + banners.length) % banners.length);
  }, [banners.length]);

  useEffect(() => {
    if (banners.length <= 1) return;
    const timer = setInterval(nextBanner, 7000);
    return () => clearInterval(timer);
  }, [nextBanner, banners.length]);

  // 인기 스택 추출
  const popularStacks = useMemo(() => {
    const validTechSet = new Set(Object.values(STACK_CATEGORIES_BASE).flat() as string[]);
    const counts: Record<string, number> = {};
    projects.forEach(p => {
      p.tags.forEach(tag => {
        if (validTechSet.has(tag)) counts[tag] = (counts[tag] || 0) + 1;
      });
    });
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15)
      .map(entry => entry[0]);
  }, [projects]);

  const dynamicStackCategories = useMemo(() => ({
    '인기': popularStacks,
    ...STACK_CATEGORIES_BASE
  }), [popularStacks]);

  // 필터 초기화
  useEffect(() => {
    setActiveTab('전체');
    setSelectedStacks([]);
    setActivePos('전체');
    setActiveMethod('전체');
    setShowBookmarks(false);
    setDisplayCount(6);
  }, [filterResetKey]);

  const toggleStack = (stack: string) => {
    setSelectedStacks(prev => prev.includes(stack) ? prev.filter(s => s !== stack) : [...prev, stack]);
    setDisplayCount(6);
  };

  const filteredProjects = useMemo(() => {
    return projects.filter(p => {
      const matchesTab = activeTab === '전체' || p.type === activeTab;
      const recruitments = parseRecruitment(p.members);
      const matchesPos = activePos === '전체' || recruitments.some(rec => rec.pos.includes(activePos));
      const matchesMethod = activeMethod === '전체' || p.method === activeMethod;
      const matchesBookmarks = showBookmarks ? user?.likedProjects?.includes(p.id) : true;
      const matchesStacks = selectedStacks.length === 0 || selectedStacks.some(s => p.tags.includes(s));
      return matchesTab && matchesPos && matchesMethod && matchesBookmarks && matchesStacks;
    });
  }, [projects, activeTab, activePos, activeMethod, showBookmarks, selectedStacks, user?.likedProjects]);

  const visibleProjects = filteredProjects.slice(0, displayCount);

  // ✅ [수정] 로딩 인디케이터
  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-12 pb-20 max-w-7xl mx-auto px-4">
      {/* Hero Banner Section */}
      {banners.length > 0 && (
        <section className="relative h-[200px] md:h-[260px] w-full overflow-hidden rounded-[2.5rem] shadow-2xl animate-fadeIn group">
          <div className="absolute inset-0 bg-gradient-to-r from-primary via-primary-dark to-secondary animate-pulse-soft"></div>
          <div className="relative h-full">
            {banners.map((banner, idx) => (
              <div
                key={banner.id}
                className={`absolute inset-0 flex flex-col items-center justify-center text-center p-6 space-y-4 z-10 transition-all duration-1000 ${currentBannerIdx === idx ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-4 scale-95 pointer-events-none'}`}
              >
                <span className="bg-white/20 backdrop-blur-md text-white px-4 py-1 rounded-full text-[9px] font-black tracking-[0.2em] uppercase border border-white/20">Hot Topic</span>
                <h1 className="text-3xl md:text-5xl font-black text-white tracking-tighter leading-none drop-shadow-lg">{banner.title}</h1>
                <Link to={banner.link} className="bg-white text-primary px-10 py-3 rounded-full font-black shadow-xl hover:scale-105 transition-all text-sm">자세히 보기 →</Link>
              </div>
            ))}
          </div>

          {banners.length > 1 && (
            <>
              <button onClick={prevBanner} className="absolute left-6 top-1/2 -translate-y-1/2 z-20 w-12 h-12 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center text-white border border-white/20 hover:bg-white/30 transition-all opacity-0 group-hover:opacity-100 shadow-lg">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M15 19l-7-7 7-7" /></svg>
              </button>
              <button onClick={nextBanner} className="absolute right-6 top-1/2 -translate-y-1/2 z-20 w-12 h-12 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center text-white border border-white/20 hover:bg-white/30 transition-all opacity-0 group-hover:opacity-100 shadow-lg">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" /></svg>
              </button>
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-2.5 z-20">
                {banners.map((_, idx) => (
                  <button key={idx} onClick={() => setCurrentBannerIdx(idx)} className={`w-2 h-2 rounded-full transition-all duration-300 ${currentBannerIdx === idx ? 'bg-white w-8 shadow-sm' : 'bg-white/40 hover:bg-white/60'}`} />
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {/* 인기 프로젝트 TOP 3 (조회수 기준, 모집마감 제외) */}
      <section className="space-y-6">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔥</span>
          <h2 className="text-2xl font-black text-text-main tracking-tight">인기 프로젝트 TOP 3</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {projects
            .filter(p => p.status !== '모집완료' && p.deadline !== '모집마감')
            .sort((a, b) => (b.views || 0) - (a.views || 0))
            .slice(0, 3)
            .map((p, idx) => (
              <ProjectCard key={p.id} project={p} rank={idx + 1} isLiked={user?.likedProjects?.includes(p.id) || false} onLike={() => toggleLike(p.id)} />
            ))}
        </div>
      </section>

      {/* 공지사항 - 인기 프로젝트와 프로젝트 리스트 사이 */}
      <section className="bg-white p-8 rounded-[2.5rem] border border-gray-100 shadow-sm space-y-4 animate-fadeIn">
        <div className="flex justify-between items-center border-b border-gray-50 pb-4">
          <div className="flex items-center gap-2"><span className="text-base">📢</span><h3 className="text-lg font-black text-text-main">공지사항</h3></div>
          <Link to="/announcements" className="text-xs font-black text-primary hover:underline">전체 보기</Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {notices.slice(0, 4).map(notice => (
            <div key={notice.id} onClick={() => setSelectedNotice(notice)} className="group cursor-pointer flex items-center justify-between p-4 rounded-2xl hover:bg-gray-50 transition-all border border-transparent hover:border-gray-100">
              <div className="flex items-center gap-4 truncate">
                <span className="text-[10px] font-black text-primary px-2 py-0.5 bg-primary/5 rounded whitespace-nowrap">{notice.date}</span>
                <span className="text-sm font-bold text-text-main group-hover:text-primary transition-colors truncate">{notice.title}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 필터 및 프로젝트 리스트 */}
      <div className="space-y-8">
        <div className="flex items-center gap-8 text-2xl font-black text-gray-300 border-b border-gray-100 pb-2">
          {['전체', '프로젝트', '스터디'].map(tab => (
            <button key={tab} onClick={() => { setActiveTab(tab as any); setDisplayCount(6); }} className={`pb-4 transition-all relative whitespace-nowrap ${activeTab === tab ? 'text-text-main' : 'hover:text-gray-400'}`}>
              {tab}
              {activeTab === tab && <div className="absolute bottom-0 left-0 w-full h-1 bg-primary rounded-full"></div>}
            </button>
          ))}
        </div>

        {/* 필터 탭 바 */}
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4 py-2">
            <button onClick={() => setShowStackFilterArea(!showStackFilterArea)} className={`flex items-center justify-between gap-3 px-6 py-3 bg-white border rounded-full text-sm font-bold transition-all min-w-[140px] ${showStackFilterArea ? 'border-primary text-primary ring-2 ring-primary/10' : 'border-gray-100 text-text-sub hover:border-gray-200 shadow-sm'}`}>
              <span>기술 스택 필터</span>
              <svg className={`w-4 h-4 transition-transform ${showStackFilterArea ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <FilterDropdown label="포지션" options={['전체', '프론트엔드', '백엔드', 'DB', '인프라', '디자인', '기타']} onSelect={(val) => { setActivePos(val); setDisplayCount(6); }} />
            <FilterDropdown label="진행 방식" options={['전체', '온라인', '오프라인', '온/오프라인']} onSelect={(val) => { setActiveMethod(val); setDisplayCount(6); }} />
            <button onClick={() => { setShowBookmarks(!showBookmarks); setDisplayCount(6); }} className={`flex items-center gap-2 px-6 py-3 rounded-full text-sm font-bold transition-all border shadow-sm ${showBookmarks ? 'bg-amber-50 border-amber-200 text-amber-600 ring-2 ring-amber-100' : 'bg-white border-gray-100 text-text-sub'}`}>
              ⭐ {showBookmarks ? '내 북마크 필터링 중' : '내 북마크'}
            </button>
            <button onClick={resetAllFilters} className="ml-auto text-[10px] font-black text-gray-400 hover:text-primary flex items-center gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
              필터 초기화
            </button>
          </div>

          {showStackFilterArea && (
            <div className="bg-white rounded-[2.5rem] border border-gray-100 shadow-xl p-8 space-y-8 animate-slideDown">
              <div className="flex items-center gap-8 text-lg font-black text-gray-400 border-b border-gray-50 pb-2 overflow-x-auto hide-scrollbar">
                {Object.keys(dynamicStackCategories).map(cat => (
                  <button key={cat} onClick={() => setActiveStackCat(cat)} className={`pb-3 transition-all relative whitespace-nowrap ${activeStackCat === cat ? 'text-text-main' : 'hover:text-gray-600'}`}>
                    {cat}
                    {activeStackCat === cat && <div className="absolute bottom-0 left-0 w-full h-1 bg-primary"></div>}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-3">
                {(dynamicStackCategories as any)[activeStackCat]?.map((stack: string) => (
                  <button key={stack} onClick={() => toggleStack(stack)} className={`flex items-center gap-2.5 px-5 py-2.5 rounded-full border-2 transition-all font-bold text-xs ${selectedStacks.includes(stack) ? 'border-primary bg-primary/5 text-primary shadow-sm' : 'border-gray-50 bg-white text-text-sub hover:border-gray-200'}`}>
                    <img src={getStackLogoUrl(stack)} className="w-5 h-5 rounded-md object-contain" alt={stack} />
                    {stack}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 w-full animate-fadeIn">
          {visibleProjects.map(p => (
            <ProjectCard key={p.id} project={p} isLiked={user?.likedProjects?.includes(p.id) || false} onLike={() => toggleLike(p.id)} />
          ))}
          {visibleProjects.length === 0 && (
            <div className="col-span-full py-20 text-center space-y-4">
              <div className="text-5xl">🔍</div>
              <p className="text-text-sub font-bold text-lg">해당 조건에 맞는 프로젝트가 없습니다.</p>
              <button onClick={resetAllFilters} className="text-primary font-black underline">전체 보기</button>
            </div>
          )}
        </div>

        {filteredProjects.length > displayCount && (
          <div className="flex justify-center pt-8">
            <button onClick={() => setDisplayCount(prev => prev + 6)} className="bg-white border-2 border-gray-100 text-text-main px-12 py-4 rounded-[1.5rem] font-black hover:border-primary hover:text-primary transition-all shadow-sm">프로젝트 더 보기</button>
          </div>
        )}
      </div>

      {/* 공지 상세 모달 */}
      {selectedNotice && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-[3rem] p-10 max-w-xl w-full shadow-2xl animate-slideDown relative">
            <button onClick={() => setSelectedNotice(null)} className="absolute top-8 right-8 text-gray-400 hover:text-text-main text-2xl">✕</button>
            <div className="space-y-6">
              <span className="text-[10px] font-black text-primary uppercase">{selectedNotice.date}</span>
              <h2 className="text-2xl font-black text-text-main">{selectedNotice.title}</h2>
              <div className="bg-gray-50 p-8 rounded-[2rem] text-text-main font-medium leading-relaxed whitespace-pre-wrap min-h-[150px]">{selectedNotice.content}</div>
              <button onClick={() => setSelectedNotice(null)} className="w-full bg-text-main text-white py-4 rounded-2xl font-black">닫기</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ProjectCard = ({ project, isLiked, onLike, rank }: { project: any, isLiked: boolean, onLike: () => void, rank?: number }) => {
  const navigate = useNavigate();

  // 모집 포지션 파싱
  const recruitments = parseRecruitment(project.members);
  
  // 총 모집 현황 계산
  const totalCurrent = recruitments.reduce((sum, r) => sum + r.current, 0);
  const totalTarget = recruitments.reduce((sum, r) => sum + r.target, 0);
  
  // 순위 배지 색상
  const rankColors = rank === 1 ? 'from-amber-400 to-yellow-600' : rank === 2 ? 'from-gray-300 to-gray-500' : 'from-orange-400 to-orange-600';

  return (
    <div
      onClick={() => navigate(`/projects/${project.id}`)}
      className="cursor-pointer group bg-white rounded-[1.5rem] border border-gray-100 hover:border-primary/30 hover:shadow-lg transition-all p-5 space-y-4 flex flex-col h-full relative overflow-hidden"
    >
      {/* 순위 배지 (인기 프로젝트용) */}
      {rank && (
        <div className={`absolute top-0 left-0 px-3 py-1.5 bg-gradient-to-br ${rankColors} text-white font-black text-xs rounded-br-xl z-20`}>
          #{rank}
        </div>
      )}

      {/* 상단: 모집마감일과 좋아요 버튼 */}
      <div className={`flex justify-between items-center ${rank ? 'mt-4' : ''}`}>
        <span className="text-gray-500 text-xs font-bold">
          {project.deadline}
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onLike(); }}
          className={`p-1.5 rounded-full transition-all ${isLiked ? 'text-red-500' : 'text-gray-300 hover:text-red-400'}`}
        >
          <svg className="w-4 h-4" fill={isLiked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path>
          </svg>
        </button>
      </div>

      {/* 프로젝트 타입, 진행방식, AI 테스트 배지 */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="bg-primary/10 text-primary px-2.5 py-1 rounded-lg text-xs font-black">
          {getProjectTypeKorean(project.type)}
        </span>
        <span className="bg-gray-100 text-gray-600 px-2.5 py-1 rounded-lg text-xs font-bold">
          {project.method}
        </span>
        {project.testRequired && (
          <span className="bg-amber-100 text-amber-600 px-2.5 py-1 rounded-lg text-xs font-black">
            🤖 AI 테스트
          </span>
        )}
      </div>

      {/* 제목 */}
      <div className="flex-grow">
        <h3 className="text-lg font-black text-primary leading-tight line-clamp-2 group-hover:text-primary-dark transition-colors mb-2">
          {project.title}
        </h3>

        {/* 설명 */}
        <p className="text-gray-600 text-sm font-medium line-clamp-2 leading-relaxed">
          {project.description}
        </p>
      </div>

      {/* 모집 포지션 현황 */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {recruitments.slice(0, 3).map((rec, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="text-sm">{getPosIcon(rec.pos)}</span>
              <span className="text-xs font-bold text-gray-700">{rec.pos}</span>
              <span className={`text-xs font-black ${rec.current >= rec.target ? 'text-gray-400' : 'text-primary'}`}>
                {rec.current}/{rec.target}
              </span>
            </div>
          ))}
          {recruitments.length > 3 && (
            <span className="text-xs text-gray-400 font-bold">+{recruitments.length - 3}</span>
          )}
        </div>

        {/* 기술 스택 - 해시태그 형태 */}
        {project.tags && project.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {project.tags.slice(0, 4).map((tag: string, idx: number) => (
              <span
                key={idx}
                className="text-[10px] font-bold text-primary/70 bg-primary/5 px-2 py-0.5 rounded-md"
              >
                #{tag}
              </span>
            ))}
            {project.tags.length > 4 && (
              <span className="text-[10px] text-gray-400 px-1 font-bold">
                +{project.tags.length - 4}
              </span>
            )}
          </div>
        )}
      </div>

      {/* 하단: 프로젝트 기간과 모집 현황 */}
      <div className="flex justify-between items-end pt-3 border-t border-gray-100">
        <div className="text-xs text-gray-500">
          <span className="font-bold block mb-0.5">진행기간</span>
          <span className="text-gray-600 text-[10px]">{project.startDate} ~ {project.endDate}</span>
        </div>
        <div className="text-right">
          <span className="text-xs font-bold text-gray-500 block mb-0.5">모집 현황</span>
          <span className={`text-sm font-black ${totalCurrent >= totalTarget ? 'text-gray-400' : 'text-primary'}`}>
            {totalCurrent}/{totalTarget}명
          </span>
        </div>
      </div>
    </div>
  );
};

const FilterDropdown = ({ label, options, onSelect }: { label: string, options: string[], onSelect: (val: string) => void }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(label);
  return (
    <div className="relative">
      <button onClick={() => setIsOpen(!isOpen)} className={`flex items-center justify-between gap-3 px-6 py-3 bg-white border rounded-full text-sm font-bold transition-all min-w-[120px] ${isOpen ? 'border-primary ring-1 ring-primary/10 shadow-sm' : 'border-gray-100 text-text-sub hover:border-gray-200'}`}>
        <span>{selected}</span>
        <svg className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
      </button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)}></div>
          <div className="absolute top-full left-0 mt-2 w-48 bg-white border border-gray-100 rounded-2xl shadow-xl z-50 overflow-hidden animate-slideDown">
            {options.map(opt => (
              <button key={opt} onClick={() => { setSelected(opt); onSelect(opt); setIsOpen(false); }} className="w-full text-left px-5 py-3 text-sm font-bold text-text-sub hover:bg-gray-50 hover:text-primary transition-colors">{opt}</button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default HomePage;
