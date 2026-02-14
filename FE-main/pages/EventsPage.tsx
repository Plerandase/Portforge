
import React, { useState, useMemo } from 'react';
import { useAuth, EventItem } from '../contexts/AuthContext';

const CATEGORIES = ['전체', '해커톤', '컨퍼런스', '공모전', '부트캠프'];

// Mock 이벤트 데이터
const MOCK_EVENTS: EventItem[] = [
  {
    id: 1001,
    category: '해커톤',
    title: '2026 AWS GameDay 해커톤',
    date: '2026년 2월 15일(토) 09:00 - 18:00',
    method: '오프라인',
    imageUrl: 'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=400&h=300&fit=crop',
    description: 'AWS 클라우드 서비스를 활용한 실시간 문제 해결 해커톤입니다.\n\n🎯 참가 대상: 클라우드에 관심 있는 개발자 누구나\n💰 총 상금: 500만원\n📍 장소: 서울 강남 AWS 코리아 오피스\n\n팀 구성: 3-5인 1팀\n준비물: 노트북, AWS 계정'
  },
  {
    id: 1002,
    category: '컨퍼런스',
    title: 'DEVIEW 2026',
    date: '2026년 3월 8일(월) - 9일(화)',
    method: '온/오프라인',
    imageUrl: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=400&h=300&fit=crop',
    description: '네이버가 주최하는 국내 최대 개발자 컨퍼런스입니다.\n\nAI, 클라우드, 프론트엔드, 백엔드 등 다양한 기술 세션이 준비되어 있습니다.\n\n✅ 사전 등록 필수\n✅ 온라인 동시 스트리밍 지원\n📍 장소: 코엑스 그랜드볼룸'
  },
  {
    id: 1003,
    category: '부트캠프',
    title: '카카오 테크 부트캠프 4기',
    date: '2026년 3월 ~ 8월 (6개월)',
    method: '오프라인',
    imageUrl: 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=400&h=300&fit=crop',
    description: '카카오와 함께하는 풀스택 개발자 양성 프로그램\n\n📚 커리큘럼:\n- Frontend: React, TypeScript\n- Backend: Spring Boot, Kotlin\n- DevOps: Docker, Kubernetes\n\n💡 특전: 수료 후 카카오 계열사 채용 연계\n💰 교육비 전액 무료 (국비지원)'
  },
  {
    id: 1004,
    category: '공모전',
    title: '2026 공개SW 개발자대회',
    date: '접수: 2026년 2월 1일 ~ 3월 31일',
    method: '온라인',
    imageUrl: 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=300&fit=crop',
    description: '과학기술정보통신부 주최 오픈소스 소프트웨어 공모전\n\n🏆 시상 내역:\n- 대상 (1팀): 3,000만원\n- 금상 (2팀): 1,500만원\n- 은상 (3팀): 1,000만원\n\n참가 자격: 대한민국 국민 누구나\n팀 구성: 1~5인'
  },
  {
    id: 1005,
    category: '해커톤',
    title: 'Junction Asia 2026',
    date: '2026년 4월 12일(금) - 14일(일)',
    method: '오프라인',
    imageUrl: 'https://images.unsplash.com/photo-1531482615713-2afd69097998?w=400&h=300&fit=crop',
    description: '아시아 최대 규모의 국제 해커톤!\n\n🌏 전 세계 1,500+ 개발자 참가\n⏰ 48시간 논스톱 해킹\n🎁 글로벌 기업 후원 및 채용 연계\n\n📍 장소: 부산 벡스코\n🍕 식사 및 간식 무료 제공'
  },
  {
    id: 1006,
    category: '컨퍼런스',
    title: 'if(kakao) 2026',
    date: '2026년 5월 20일(수) - 21일(목)',
    method: '온/오프라인',
    imageUrl: 'https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=400&h=300&fit=crop',
    description: '카카오 개발자 컨퍼런스 2026\n\n올해 주요 세션:\n- 카카오톡 AI 어시스턴트 개발기\n- 대규모 트래픽 처리 노하우\n- 카카오페이 보안 아키텍처\n\n📍 장소: 삼성동 코엑스\n🎁 참가자 전원 굿즈 증정'
  },
  {
    id: 1007,
    category: '부트캠프',
    title: '우아한테크코스 7기',
    date: '2026년 2월 ~ 11월 (10개월)',
    method: '오프라인',
    imageUrl: 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=400&h=300&fit=crop',
    description: '우아한형제들이 운영하는 개발자 교육 프로그램\n\n🎯 과정 소개:\n- 프론트엔드 / 백엔드 / 안드로이드 트랙\n- 페어 프로그래밍 & 코드 리뷰 중심\n- 실무 프로젝트 경험\n\n💰 교육비 무료\n📍 장소: 잠실 우아한형제들 교육장'
  },
  {
    id: 1008,
    category: '공모전',
    title: 'Samsung AI Challenge 2026',
    date: '접수: 2026년 3월 1일 ~ 4월 15일',
    method: '온라인',
    imageUrl: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=400&h=300&fit=crop',
    description: '삼성전자 주최 AI/ML 경진대회\n\n📋 과제: 온디바이스 AI 모델 최적화\n\n🏆 시상:\n- 1등: 5,000만원 + 삼성전자 입사 가산점\n- 2등: 3,000만원\n- 3등: 1,000만원\n\n참가 자격: 대학(원)생 및 일반인'
  },
  {
    id: 1009,
    category: '해커톤',
    title: 'Google Solution Challenge 2026',
    date: '2026년 2월 ~ 3월 (온라인 예선)',
    method: '온라인',
    imageUrl: 'https://images.unsplash.com/photo-1573164713714-d95e436ab8d6?w=400&h=300&fit=crop',
    description: 'UN 지속가능발전목표(SDGs) 해결을 위한 글로벌 해커톤\n\n🌍 Google 기술을 활용한 사회 문제 해결\n🎓 전 세계 대학생 대상\n\n🏆 Top 100팀 멘토링 제공\n🏆 Top 10팀 Google I/O 초청\n\n필수 기술: Google Cloud, Firebase, Flutter 등'
  }
];

const EventsPage: React.FC = () => {
  const { user, addEvent } = useAuth();
  // Mock 데이터 사용
  const events = MOCK_EVENTS;
  const [activeCategory, setActiveCategory] = useState<string>('전체');
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null);

  const [newEvent, setNewEvent] = useState({
    category: '해커톤' as any,
    title: '',
    date: '',
    method: '온라인',
    imageUrl: 'https://picsum.photos/400/300?random=' + Date.now(),
    description: ''
  });

  const filteredEvents = useMemo(() => {
    if (activeCategory === '전체') return events;
    return events.filter(e => e.category === activeCategory);
  }, [events, activeCategory]);

  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newEvent.title) return;
    
    addEvent({
      ...newEvent,
      imageUrl: `https://picsum.photos/400/300?random=${Date.now()}`
    });
    
    setShowAddModal(false);
    setNewEvent({ category: '해커톤', title: '', date: '', method: '온라인', imageUrl: '', description: '' });
    alert('행사가 성공적으로 등록되었습니다.');
  };

  return (
    <div className="space-y-10 pb-20 max-w-7xl mx-auto px-4 w-full">
      <section className="bg-primary/5 rounded-[2.5rem] p-12 border border-primary/10 flex flex-col md:flex-row justify-between items-center overflow-hidden gap-8">
        <div className="space-y-4">
          <h1 className="text-4xl font-black text-text-main tracking-tight">IT 행사 정보 센터</h1>
          <p className="text-text-sub font-medium text-lg">성장의 기회가 되는 해커톤과 부트캠프를 한눈에 확인하세요.</p>
        </div>
        <div className="text-6xl animate-bounce">🎟️</div>
      </section>

      <div className="flex justify-between items-center border-b border-gray-100 pb-4 overflow-x-auto gap-8">
        <div className="flex gap-8">
          {CATEGORIES.map(cat => (
            <button key={cat} onClick={() => setActiveCategory(cat)} className={`text-xl font-black relative pb-4 transition-all ${activeCategory === cat ? 'text-text-main' : 'text-gray-300'}`}>
              {cat}
              {activeCategory === cat && <div className="absolute bottom-0 left-0 w-full h-1 bg-primary"></div>}
            </button>
          ))}
        </div>
        {user?.role === 'ADMIN' && <button onClick={() => setShowAddModal(true)} className="bg-primary text-white px-6 py-2 rounded-xl text-sm font-black shadow-lg shadow-primary/20 shrink-0">+ 행사 등록</button>}
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {filteredEvents.map(event => (
          <div key={event.id} onClick={() => setSelectedEvent(event)} className="group cursor-pointer bg-white rounded-3xl overflow-hidden border border-gray-100 shadow-sm hover:shadow-xl transition-all">
            <div className="aspect-video overflow-hidden">
              <img src={event.imageUrl} className="w-full h-full object-cover group-hover:scale-105 transition-transform" alt={event.title} />
            </div>
            <div className="p-6 space-y-2">
              <span className="text-[10px] font-black text-primary uppercase">{event.category}</span>
              <h4 className="text-lg font-black text-text-main line-clamp-1 group-hover:text-primary transition-colors">{event.title}</h4>
              <p className="text-xs font-bold text-gray-400">{event.date} | {event.method}</p>
            </div>
          </div>
        ))}
        {filteredEvents.length === 0 && (
          <div className="col-span-full py-20 text-center opacity-40 font-black">해당 카테고리의 행사가 없습니다.</div>
        )}
      </section>

      {/* 상세 보기 모달 */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[110] flex items-center justify-center p-4">
           <div className="bg-white rounded-[3rem] max-w-2xl w-full overflow-hidden animate-slideDown shadow-2xl">
              <img src={selectedEvent.imageUrl} className="w-full h-64 object-cover" alt="header" />
              <div className="p-10 space-y-6">
                 <div className="flex justify-between items-start">
                    <div className="space-y-1">
                       <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-[10px] font-black uppercase">{selectedEvent.category}</span>
                       <h2 className="text-3xl font-black text-text-main mt-2 leading-tight">{selectedEvent.title}</h2>
                    </div>
                    <button onClick={() => setSelectedEvent(null)} className="p-2 bg-gray-50 rounded-full text-gray-400 hover:text-text-main transition-colors">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                 </div>
                 <div className="bg-gray-50 p-6 rounded-2xl space-y-2 border border-gray-100">
                    <p className="text-sm font-bold text-text-sub">🗓️ 일정: <span className="text-text-main">{selectedEvent.date}</span></p>
                    <p className="text-sm font-bold text-text-sub">📍 방식: <span className="text-text-main">{selectedEvent.method}</span></p>
                 </div>
                 <p className="text-text-main font-medium leading-relaxed whitespace-pre-wrap">{selectedEvent.description || "상세 정보가 아직 업데이트되지 않았습니다. 공식 홈페이지를 참고해 주세요."}</p>
                 <button onClick={() => setSelectedEvent(null)} className="w-full bg-text-main text-white py-4 rounded-2xl font-black shadow-xl">목록으로 돌아가기</button>
              </div>
           </div>
        </div>
      )}

      {/* 등록 모달 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 z-[120] flex items-center justify-center p-4">
           <form onSubmit={handleAddSubmit} className="bg-white rounded-[3rem] p-10 max-w-lg w-full space-y-4 shadow-2xl animate-fadeIn relative">
              <button type="button" onClick={()=>setShowAddModal(false)} className="absolute top-8 right-8 text-gray-400">✕</button>
              <h2 className="text-2xl font-black mb-4">새로운 IT 행사 등록</h2>
              <div className="grid grid-cols-2 gap-4">
                 <div className="space-y-1">
                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">카테고리</label>
                    <select value={newEvent.category} onChange={e=>setNewEvent({...newEvent, category: e.target.value as any})} className="w-full p-4 bg-gray-50 rounded-xl font-bold border-none ring-1 ring-gray-200">
                        {CATEGORIES.filter(c=>c!=='전체').map(c=><option key={c}>{c}</option>)}
                    </select>
                 </div>
                 <div className="space-y-1">
                    <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">방식</label>
                    <select value={newEvent.method} onChange={e=>setNewEvent({...newEvent, method: e.target.value})} className="w-full p-4 bg-gray-50 rounded-xl font-bold border-none ring-1 ring-gray-200">
                        <option>온라인</option><option>오프라인</option><option>온/오프라인</option>
                    </select>
                 </div>
              </div>
              <div className="space-y-1">
                 <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">행사명</label>
                 <input type="text" value={newEvent.title} onChange={e=>setNewEvent({...newEvent, title: e.target.value})} placeholder="행사 제목을 입력하세요" className="w-full p-4 bg-gray-50 rounded-xl font-bold border-none ring-1 ring-gray-200" required />
              </div>
              <div className="space-y-1">
                 <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">날짜 및 시간</label>
                 <input type="text" value={newEvent.date} onChange={e=>setNewEvent({...newEvent, date: e.target.value})} placeholder="예: 11월 12일(월) 14:00" className="w-full p-4 bg-gray-50 rounded-xl font-bold border-none ring-1 ring-gray-200" required />
              </div>
              <div className="space-y-1">
                 <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">행사 설명</label>
                 <textarea value={newEvent.description} onChange={e=>setNewEvent({...newEvent, description: e.target.value})} rows={4} placeholder="상세 정보를 입력하세요" className="w-full p-4 bg-gray-50 rounded-xl font-medium border-none ring-1 ring-gray-200"></textarea>
              </div>
              <div className="flex gap-4 pt-4">
                 <button type="submit" className="flex-1 bg-primary text-white py-4 rounded-2xl font-black shadow-lg shadow-primary/10">등록 완료</button>
              </div>
           </form>
        </div>
      )}
    </div>
  );
};

export default EventsPage;
