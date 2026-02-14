
import React, { useState, useMemo } from 'react';
import { useAuth, EventItem } from '../contexts/AuthContext';

const CATEGORIES = ['전체', '해커톤', '컨퍼런스', '공모전', '부트캠프'];

const EventsPage: React.FC = () => {
  const { user, events, addEvent } = useAuth();
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
