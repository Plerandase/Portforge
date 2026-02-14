
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Footer: React.FC = () => {
  const { user, addReport } = useAuth();
  const [showInquiry, setShowInquiry] = useState(false);
  const [inquiryType, setInquiryType] = useState('광고/제휴 문의');
  const [targetUserId, setTargetUserId] = useState('');
  const [content, setContent] = useState('');

  const openInquiry = (type: string) => {
    setInquiryType(type);
    setShowInquiry(true);
  };

  const handleInquirySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return alert('로그인 후 문의가 가능합니다.');
    
    await addReport({
      title: `[${inquiryType}] 푸터 문의 접수`,
      content: inquiryType === '버그 제보/신고' 
        ? `대상 유저: ${targetUserId}\n상세 내용: ${content}`
        : content,
      reporter: user.id,
      type: inquiryType === '버그 제보/신고' ? '신고' : '문의'
    });
    
    alert('문의가 성공적으로 전달되었습니다. 관리자 센터에서 확인 가능합니다.');
    setTargetUserId('');
    setContent('');
    setShowInquiry(false);
  };

  return (
    <footer className="bg-white border-t border-gray-100 pt-16 pb-12 text-text-main">
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-4 gap-12 border-b border-gray-100 pb-12 mb-8">
          <div className="col-span-1 md:col-span-2 space-y-6">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white font-black text-lg">P</div>
              <span className="text-xl font-black text-secondary tracking-tight">Portforge</span>
            </div>
            <p className="text-sm text-text-sub leading-relaxed max-w-sm font-medium">
              AI가 검증하고 우리가 연결합니다. <br/>최고의 협업 파트너, Portforge.
            </p>
          </div>
          
          <div className="space-y-4">
            <h4 className="text-[10px] font-black text-primary uppercase tracking-widest">Service</h4>
            <ul className="space-y-2 text-sm text-text-sub font-bold">
              <li><Link to="/announcements" className="hover:text-primary transition-colors">공지사항</Link></li>
              <li><Link to="/signup" className="hover:text-primary transition-colors">회원가입</Link></li>
            </ul>
          </div>

          <div className="space-y-4">
            <h4 className="text-[10px] font-black text-primary uppercase tracking-widest">Contact</h4>
            <div className="space-y-3 flex flex-col items-start">
              <button onClick={() => openInquiry('버그 제보/신고')} className="text-sm text-text-sub hover:text-primary font-bold transition-colors">버그 제보 및 유저 신고</button>
              <Link to="/find-account" className="text-sm text-text-sub hover:text-primary font-bold transition-colors">계정 정보 찾기</Link>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] text-text-sub/40 font-black uppercase tracking-widest">
          <div className="flex gap-6">
            <span>&copy; {new Date().getFullYear()} Portforge Inc.</span>
            <Link to="/privacy" className="hover:text-primary">이용약관</Link>
            <Link to="/privacy" className="hover:text-primary">개인정보처리방침</Link>
          </div>
          <div className="flex space-x-6">
            <span className="cursor-pointer hover:text-primary">Instagram</span>
            <span className="cursor-pointer hover:text-primary">LinkedIn</span>
          </div>
        </div>
      </div>

      {showInquiry && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-[3rem] p-10 max-w-lg w-full shadow-2xl animate-slideDown overflow-y-auto max-h-[90vh] relative">
            <button onClick={() => setShowInquiry(false)} className="absolute top-8 right-8 text-gray-400 hover:text-text-main transition-colors text-xl">✕</button>
            <div className="mb-8">
              <h2 className="text-2xl font-black text-primary mb-2">{inquiryType}</h2>
              <p className="text-text-sub text-xs font-bold">내용은 관리자 센터로 즉시 전달되어 검토됩니다.</p>
            </div>
            <form className="space-y-5" onSubmit={handleInquirySubmit}>
              {inquiryType === '버그 제보/신고' && (
                <div className="space-y-2">
                  <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">대상 유저 아이디 (선택)</label>
                  <input 
                    type="text" 
                    value={targetUserId}
                    onChange={(e) => setTargetUserId(e.target.value)}
                    className="w-full bg-gray-50 p-4 rounded-xl font-bold outline-none border-2 border-transparent focus:border-primary transition-all" 
                    placeholder="예: user_dev_01" 
                  />
                </div>
              )}
              <div className="space-y-2">
                <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-1">문의 상세 내용</label>
                <textarea 
                  rows={6} 
                  required 
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  className="w-full bg-gray-50 p-4 rounded-xl font-medium outline-none border-2 border-transparent focus:border-primary transition-all" 
                  placeholder="내용을 구체적으로 입력해주세요."
                ></textarea>
              </div>
              <button type="submit" className="w-full bg-primary text-white py-5 rounded-2xl font-black text-lg shadow-xl shadow-primary/10 hover:bg-primary-dark transition-all mt-4">문의 접수하기</button>
            </form>
          </div>
        </div>
      )}
    </footer>
  );
};

export default Footer;
