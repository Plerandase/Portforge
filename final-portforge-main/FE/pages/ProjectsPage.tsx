
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Card from '../components/Card';
import { projectAPI } from '../api/apiClient';

interface Project {
  id: number;
  title: string;
  description: string;
  type: string;
  method: string;
  start_date: string;
  end_date: string;
  status: string;
  views: number;
  created_at: string;
  deadline?: string;  // 백엔드에서 계산된 D-day 값
  recruitment_positions?: any[];
}

const ProjectsPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const data = await projectAPI.getProjects(1, 20);
        // API 응답 구조에 따라 조정 (data.projects 또는 data 자체일 수 있음)
        setProjects(Array.isArray(data) ? data : data.projects || []);
      } catch (err: any) {
        console.error('Failed to fetch projects:', err);
        setError('프로젝트 목록을 불러오는데 실패했습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchProjects();
  }, []);

  // 마감일 표시 (백엔드에서 계산된 deadline 우선 사용)
  const getDeadlineDisplay = (project: Project) => {
    // 백엔드에서 이미 계산해서 보내준 deadline 필드 우선 사용
    if (project.deadline) {
      return project.deadline;
    }

    // fallback: recruitment_positions에서 가장 빠른 recruitment_deadline 추출
    const deadlines = project.recruitment_positions
      ?.map(p => p.recruitment_deadline)
      .filter(d => d);

    const targetDate = deadlines && deadlines.length > 0
      ? deadlines.sort()[0]
      : project.end_date;

    if (!targetDate) return '미정';

    const end = new Date(targetDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    const diff = Math.ceil((end.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    return diff > 0 ? `D-${diff}` : diff === 0 ? 'D-DAY' : '마감';
  };

  // 멤버 정보 포맷
  const positionTypeMap: Record<string, string> = {
    'FRONTEND': '프론트엔드',
    'BACKEND': '백엔드',
    'DESIGN': '디자인',
    'DB': 'DB',
    'INFRA': '인프라',
    'ETC': '기타',
    'STUDY_MEMBER': '스터디원',
  };

  const formatMembers = (positions: any[] | undefined) => {
    if (!positions || positions.length === 0) return '모집 중';
    return positions.map(p => {
      const posName = positionTypeMap[p.position_type] || p.position_type;
      return `${posName} ${p.current_count || 0}/${p.target_count}`;
    }).join(', ');
  };

  // 기술 스택 추출
  const getTags = (positions: any[] | undefined) => {
    if (!positions || positions.length === 0) return [];
    const stacks = new Set<string>();
    positions.forEach(p => {
      if (p.required_stacks) {
        p.required_stacks.forEach((s: string) => stacks.add(s));
      }
    });
    return Array.from(stacks).slice(0, 3); // 최대 3개
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-12">
      <div className="max-w-3xl mx-auto text-center space-y-4">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">프로젝트 탐색</h1>
        <p className="text-xl text-text-secondary leading-relaxed">
          다양한 분야의 프로젝트와 공모전이 여러분을 기다리고 있습니다.<br />
          함께 성장할 팀을 찾고 첫걸음을 떼보세요.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-2xl text-center font-bold">
          {error}
        </div>
      )}

      {projects.length === 0 && !error && (
        <div className="text-center py-20">
          <p className="text-text-secondary text-lg">등록된 프로젝트가 없습니다.</p>
          <Link to="/projects/new" className="inline-block mt-4 px-6 py-3 bg-primary text-white rounded-xl font-bold hover:bg-primary-dark transition-colors">
            첫 프로젝트 등록하기
          </Link>
        </div>
      )}

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
        {projects.map(project => (
          <Link to={`/projects/${project.id}`} key={project.id} className="group">
            <Card className="h-full border border-transparent hover:border-primary transition-all">
              <div className="relative overflow-hidden">
                <img
                  src={`https://picsum.photos/400/200?random=${project.id}`}
                  alt={project.title}
                  className="w-full h-48 object-cover group-hover:scale-105 transition-transform duration-300"
                />
                <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm shadow-md px-3 py-1 rounded-full text-xs font-bold text-primary">
                  {getDeadlineDisplay(project)}
                </div>
                <div className={`absolute top-4 left-4 px-3 py-1 rounded-full text-xs font-bold ${project.status === 'RECRUITING' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                  {project.status === 'RECRUITING' ? '모집중' : project.status === 'COMPLETED' ? '모집완료' : project.status}
                </div>
              </div>
              <div className="p-6">
                <div className="flex items-center gap-2 mb-2">
                  <span className="bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded">
                    {project.type === 'PROJECT' ? '프로젝트' : project.type === 'STUDY' ? '스터디' : project.type}
                  </span>
                  <span className="text-xs text-text-secondary">
                    {project.method === 'ONLINE' ? '온라인' : project.method === 'OFFLINE' ? '오프라인' : '온/오프 병행'}
                  </span>
                </div>
                <h3 className="text-xl font-bold mb-3 truncate group-hover:text-primary transition-colors">
                  {project.title}
                </h3>
                <p className="text-sm text-text-secondary line-clamp-2 mb-4 h-10">
                  {project.description}
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs font-medium text-text-secondary mb-6 bg-gray-50 p-3 rounded-lg">
                  <div className="flex items-center">
                    <svg className="w-4 h-4 mr-1.5 text-primary/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                    {project.start_date?.split('T')[0]}
                  </div>
                  <div className="flex items-center justify-end">
                    <svg className="w-4 h-4 mr-1.5 text-primary/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                    {project.views || 0} 조회
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {getTags(project.recruitment_positions).map(tag => (
                    <span key={tag} className="bg-gray-100 text-gray-700 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default ProjectsPage;
