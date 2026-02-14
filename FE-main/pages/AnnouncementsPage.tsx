
import React, { useState } from 'react';
import { useAuth, Notice } from '../contexts/AuthContext';

const AnnouncementsPage: React.FC = () => {
  const { notices } = useAuth();
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);

  return (
    <div className="max-w-4xl mx-auto py-10 animate-fadeIn px-4">
      <div className="text-center mb-16 space-y-4">
        <h1 className="text-4xl font-black text-text-main tracking-tight">공지사항</h1>
        <p className="text-lg text-text-sub font-medium">Portforge의 새로운 소식과 업데이트 내역을 확인하세요.</p>
      </div>
      
      <div className="bg-white rounded-[3rem] shadow-sm border border-gray-100 overflow-hidden">
        <div className="divide-y divide-gray-50">
          {notices.map(notice => (
            <div 
              key={notice.id} 
              onClick={() => setSelectedNotice(notice)}
              className="p-8 hover:bg-gray-50/50 transition-all flex flex-col md:flex-row justify-between items-start md:items-center gap-4 group cursor-pointer"
            >
              <div className="space-y-2 flex-grow">
                <span className="text-[10px] font-black text-primary uppercase tracking-widest">Official Notice</span>
                <h3 className="text-xl font-black text-text-main group-hover:text-primary transition-colors">{notice.title}</h3>
                <p className="text-sm text-text-sub font-medium line-clamp-1">{notice.content}</p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className="text-sm font-bold text-gray-400 whitespace-nowrap">{notice.date}</span>
                <span className="text-[10px] font-black text-primary opacity-0 group-hover:opacity-100 transition-opacity">자세히 보기 →</span>
              </div>
            </div>
          ))}
          {notices.length === 0 && (
            <div className="py-20 text-center space-y-4">
              <div className="text-5xl opacity-20">📭</div>
              <p className="text-text-sub font-bold">등록된 공지사항이 없습니다.</p>
            </div>
          )}
        </div>
      </div>

      {/* 공지사항 상세 모달 */}
      {selectedNotice && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-[3rem] p-10 max-w-xl w-full shadow-2xl animate-slideDown relative">
            <button onClick={() => setSelectedNotice(null)} className="absolute top-8 right-8 text-gray-400 hover:text-text-main text-2xl">✕</button>
            <div className="space-y-6">
              <div className="space-y-2">
                <span className="text-[10px] font-black text-primary uppercase tracking-widest">{selectedNotice.date}</span>
                <h2 className="text-2xl font-black text-text-main">{selectedNotice.title}</h2>
              </div>
              <div className="bg-gray-50 p-8 rounded-[2rem] text-text-main font-medium leading-relaxed whitespace-pre-wrap min-h-[200px]">
                {selectedNotice.content}
              </div>
              <button onClick={() => setSelectedNotice(null)} className="w-full bg-text-main text-white py-4 rounded-2xl font-black shadow-xl">닫기</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnnouncementsPage;
