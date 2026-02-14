
import React from 'react';
import { Link } from 'react-router-dom';

const ApplicationSuccessPage: React.FC = () => {
  return (
    <div className="max-w-2xl mx-auto py-20 px-4 animate-fadeIn text-center space-y-10">
      <div className="relative inline-block">
        <div className="text-9xl mb-4 animate-bounce">🎉</div>
        <div className="absolute top-0 -right-4 bg-primary text-white text-xs px-3 py-1 rounded-full font-black rotate-12 shadow-lg">SUCCESS!</div>
      </div>
      
      <div className="space-y-4">
        <h1 className="text-4xl font-black text-text-main tracking-tight">지원 완료!</h1>
        <p className="text-text-sub text-lg font-medium leading-relaxed">
          프로젝트 지원서가 성공적으로 전달되었습니다.<br/>
          팀장님이 확인하는 대로 알림을 드릴게요.
        </p>
      </div>

      <div className="bg-gray-50/50 p-8 rounded-[2.5rem] border border-gray-100 text-left space-y-4">
        <h3 className="font-black text-sm text-text-sub uppercase tracking-widest">다음 할 일</h3>
        <ul className="space-y-3 text-text-main font-bold">
          <li className="flex items-center gap-3">
            <span className="w-6 h-6 bg-white rounded-full shadow-sm flex items-center justify-center text-xs">1</span>
            마이페이지에서 내 지원 상태를 수시로 확인하세요.
          </li>
          <li className="flex items-center gap-3">
            <span className="w-6 h-6 bg-white rounded-full shadow-sm flex items-center justify-center text-xs">2</span>
            관심 있는 다른 프로젝트도 둘러보며 기회를 넓히세요.
          </li>
        </ul>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 pt-4">
        <Link 
          to="/" 
          className="flex-1 bg-primary text-white py-5 rounded-[1.5rem] font-black text-xl shadow-xl shadow-primary/20 hover:scale-[1.02] transition-all"
        >
          메인 페이지로 가기
        </Link>
        <Link 
          to="/mypage" 
          className="flex-1 bg-white border-2 border-gray-100 text-text-sub py-5 rounded-[1.5rem] font-black text-xl hover:bg-gray-50 transition-all"
        >
          지원 내역 확인
        </Link>
      </div>
    </div>
  );
};

export default ApplicationSuccessPage;
