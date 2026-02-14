
import React, { useState } from 'react';
import { useAuth, Notice, Banner, Report, Project } from '../contexts/AuthContext';

const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'banners' | 'notices' | 'reports' | 'projects'>('reports');

  return (
    <div className="max-w-6xl mx-auto py-8 space-y-8 animate-fadeIn">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-black text-text-main tracking-tight">Portforge Admin Center</h1>
      </div>
      <div className="flex space-x-1 bg-gray-100 p-1.5 rounded-2xl">
        <TabButton active={activeTab === 'banners'} onClick={() => setActiveTab('banners')} label="배너 관리" />
        <TabButton active={activeTab === 'notices'} onClick={() => setActiveTab('notices')} label="공지사항" />
        <TabButton active={activeTab === 'reports'} onClick={() => setActiveTab('reports')} label="신고/문의" />
        <TabButton active={activeTab === 'projects'} onClick={() => setActiveTab('projects')} label="모니터링" />
      </div>
      <div className="bg-white p-12 rounded-[2.5rem] shadow-sm border border-gray-100 min-h-[600px] relative overflow-hidden">
        {activeTab === 'banners' && <BannerManager />}
        {activeTab === 'notices' && <NoticeManager />}
        {activeTab === 'reports' && <ReportManager />}
        {activeTab === 'projects' && <ProjectModerator />}
      </div>
    </div>
  );
};

const TabButton = ({ active, onClick, label }: any) => (
  <button onClick={onClick} className={`flex-1 py-4 px-6 text-sm font-black rounded-xl transition-all ${active ? 'bg-white text-text-main shadow-lg' : 'text-text-sub hover:bg-white/50'}`}>{label}</button>
);

const BannerManager = () => {
  const { banners, addBanner, updateBanner, deleteBanner } = useAuth();
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ title: '', link: '', active: true });

  const handleSave = () => {
    if (!form.title) return;
    if (editingId) updateBanner(editingId, form);
    else addBanner(form);
    setIsAdding(false); setEditingId(null); setForm({ title: '', link: '', active: true });
  };

  return (
    <div className="space-y-8 animate-slideDown">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-black">홈 배너 관리</h3>
        <button onClick={() => setIsAdding(true)} className="bg-primary text-white px-6 py-2 rounded-xl text-xs font-black shadow-lg shadow-primary/20">+ 새 배너 추가</button>
      </div>

      {(isAdding || editingId) && (
        <div className="bg-gray-50 p-8 rounded-[2rem] border-2 border-primary/20 space-y-4">
           <input type="text" value={form.title} onChange={e=>setForm({...form, title: e.target.value})} placeholder="배너 제목" className="w-full p-4 rounded-xl border-none ring-1 ring-gray-200 font-bold" />
           <input type="text" value={form.link} onChange={e=>setForm({...form, link: e.target.value})} placeholder="링크" className="w-full p-4 rounded-xl border-none ring-1 ring-gray-200 font-bold" />
           <div className="flex gap-4">
             <button onClick={handleSave} className="flex-1 bg-primary text-white py-3 rounded-xl font-black">저장</button>
             <button onClick={() => {setIsAdding(false); setEditingId(null);}} className="flex-1 bg-gray-200 py-3 rounded-xl font-black">취소</button>
           </div>
        </div>
      )}

      <div className="grid gap-4">
        {banners.map(b => (
          <div key={b.id} className="p-6 border rounded-2xl flex justify-between items-center group hover:bg-gray-50 transition-all">
             <div><p className="font-black">{b.title}</p><p className="text-xs text-text-sub">{b.link}</p></div>
             <div className="flex gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
               <button onClick={() => {setEditingId(b.id); setForm(b);}} className="text-primary font-black text-xs">편집</button>
               <button onClick={() => {if(confirm('삭제하시겠습니까?')) deleteBanner(b.id)}} className="text-red-500 font-black text-xs">삭제</button>
             </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const NoticeManager = () => {
  const { notices, addNotice, updateNotice, deleteNotice } = useAuth();
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ title: '', content: '' });

  const handleSave = async () => {
    if (!form.title) return;
    if (editingId) updateNotice(editingId, form);
    else await addNotice(form);
    setIsAdding(false); setEditingId(null); setForm({ title: '', content: '' });
  };

  return (
    <div className="space-y-8 animate-slideDown">
      <div className="flex justify-between items-center">
        <h3 className="text-xl font-black">공지사항 관리</h3>
        <button onClick={() => setIsAdding(true)} className="bg-primary text-white px-6 py-2 rounded-xl text-xs font-black shadow-lg shadow-primary/20">+ 공지 작성</button>
      </div>

      {(isAdding || editingId) && (
        <div className="bg-gray-50 p-8 rounded-[2rem] border-2 border-primary/20 space-y-4">
           <input type="text" value={form.title} onChange={e=>setForm({...form, title: e.target.value})} placeholder="제목" className="w-full p-4 rounded-xl border-none ring-1 ring-gray-200 font-bold" />
           <textarea value={form.content} onChange={e=>setForm({...form, content: e.target.value})} rows={5} placeholder="내용" className="w-full p-4 rounded-xl border-none ring-1 ring-gray-200 font-medium"></textarea>
           <div className="flex gap-4">
             <button onClick={handleSave} className="flex-1 bg-primary text-white py-3 rounded-xl font-black">게시</button>
             <button onClick={() => {setIsAdding(false); setEditingId(null);}} className="flex-1 bg-gray-200 py-3 rounded-xl font-black">취소</button>
           </div>
        </div>
      )}

      <div className="grid gap-4">
        {notices.map(n => (
          <div key={n.id} className="p-6 border rounded-2xl flex justify-between items-center group hover:bg-gray-50 transition-all">
             <div><p className="font-black">{n.title}</p><p className="text-xs text-text-sub">{n.date}</p></div>
             <div className="flex gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
               <button onClick={() => {setEditingId(n.id); setForm(n);}} className="text-primary font-black text-xs">편집</button>
               <button onClick={() => {if(confirm('삭제하시겠습니까?')) deleteNotice(n.id)}} className="text-red-500 font-black text-xs">삭제</button>
             </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ReportManager = () => {
  const { reports, resolveReport } = useAuth();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const handleAction = (id: number, type: string) => {
    let msg = type === 'deleted' ? '해당 프로젝트를 영구 삭제' : type === 'warned' ? '작성자에게 경고 조치' : '신고를 기각';
    if (confirm(`${msg} 하시겠습니까?`)) {
      resolveReport(id, type);
      alert('처리가 완료되었습니다.');
    }
  };

  return (
    <div className="space-y-8 animate-slideDown">
      <h3 className="text-xl font-black">신고 및 고객 문의 관리</h3>
      <div className="grid gap-6">
        {reports.map(r => (
          <div key={r.id} className={`border rounded-[2.5rem] overflow-hidden ${r.status === 'resolved' ? 'opacity-50 grayscale bg-gray-50' : 'bg-white shadow-sm border-gray-100'}`}>
            <div onClick={() => setSelectedId(selectedId === r.id ? null : r.id)} className="p-8 cursor-pointer flex justify-between items-center group">
              <div className="space-y-2">
                <div className="flex gap-2">
                   <span className={`text-[10px] font-black px-3 py-1 rounded-lg ${r.type === '신고' ? 'bg-red-50 text-red-500' : 'bg-blue-50 text-blue-500'}`}>{r.type}</span>
                   {r.status === 'resolved' && <span className="text-[10px] font-black bg-gray-200 px-3 py-1 rounded-lg">처리 완료 ({r.resolutionType})</span>}
                </div>
                <p className="font-black text-lg group-hover:text-primary transition-colors">{r.title}</p>
                <div className="flex gap-4 text-[11px] font-bold text-gray-400"><span>신고자: {r.reporter}</span><span>일자: {r.date}</span></div>
              </div>
              <svg className={`w-5 h-5 transition-transform ${selectedId === r.id ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7" /></svg>
            </div>
            {selectedId === r.id && (
              <div className="px-8 pb-8 space-y-6 animate-fadeIn">
                <div className="bg-gray-50 p-6 rounded-2xl text-sm font-medium whitespace-pre-wrap">{r.content}</div>
                {r.status === 'pending' && (
                  <div className="flex flex-wrap gap-2">
                    {r.type === '신고' ? (
                      <>
                        <button onClick={()=>handleAction(r.id, 'deleted')} className="bg-red-500 text-white px-6 py-3 rounded-xl text-xs font-black">해당 프로젝트 삭제</button>
                        <button onClick={()=>handleAction(r.id, 'warned')} className="bg-orange-500 text-white px-6 py-3 rounded-xl text-xs font-black">작성자 경고 조치</button>
                        <button onClick={()=>handleAction(r.id, 'dismissed')} className="bg-gray-400 text-white px-6 py-3 rounded-xl text-xs font-black">무혐의(기각)</button>
                      </>
                    ) : (
                      <button onClick={()=>handleAction(r.id, 'answered')} className="bg-primary text-white px-6 py-3 rounded-xl text-xs font-black">답변 발송 및 완료</button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const ProjectModerator = () => {
  const { projects, deleteProject } = useAuth();
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-black">전체 프로젝트 모니터링</h3>
      <div className="grid gap-4">
        {projects.map(p => (
          <div key={p.id} className="flex justify-between items-center p-6 border rounded-2xl group hover:bg-gray-50">
             <div><p className="font-black">{p.title}</p><p className="text-xs text-text-sub">{p.authorName}</p></div>
             <button onClick={() => {if(confirm('삭제하시겠습니까?')) deleteProject(p.id)}} className="text-red-500 opacity-0 group-hover:opacity-100 transition-opacity font-black text-xs">즉시 삭제</button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminPage;
