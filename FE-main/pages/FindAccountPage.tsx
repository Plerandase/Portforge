
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import apiClient from '../api/apiClient';

const FindAccountPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'id' | 'pw'>('id'); // 현재는 'pw'만 구현
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');

  // 단계: 'input-email' -> 'input-code' -> 'success'
  const [step, setStep] = useState<'input-email' | 'input-code' | 'success'>('input-email');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 이메일로 인증 코드 요청
  const handleRequestCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setError('');
    setIsLoading(true);

    try {
      if (activeTab === 'id') {
        setError('아이디 찾기 기능은 아직 지원되지 않습니다.');
        setIsLoading(false);
        return;
      }

      await apiClient.auth.forgotPassword(email);
      setStep('input-code'); // 코드 입력 단계로 이동
    } catch (err: any) {
      setError(err.message || '인증 코드 발송에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  // 인증 코드 확인 및 비밀번호 재설정
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code || !newPassword) return;

    setError('');
    setIsLoading(true);

    try {
      await apiClient.auth.confirmForgotPassword({
        email,
        code,
        new_password: newPassword
      });
      setStep('success'); // 성공 화면
    } catch (err: any) {
      setError(err.message || '비밀번호 재설정에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto py-12 px-4 animate-fadeIn">
      <div className="bg-white p-10 rounded-[3rem] shadow-2xl border border-gray-100 space-y-8">
        <div className="text-center">
          <h2 className="text-3xl font-black text-text-main">계정 찾기</h2>
          <p className="text-text-sub font-medium mt-2">
            {step === 'input-email' && "정보를 잊으셨나요? 본인 인증을 통해 도와드릴게요."}
            {step === 'input-code' && "이메일로 발송된 인증 코드를 입력해주세요."}
            {step === 'success' && "비밀번호가 성공적으로 변경되었습니다!"}
          </p>
        </div>

        {/* 탭 메뉴 (성공 화면이 아닐 때만 노출) */}
        {step !== 'success' && (
          <div className="flex bg-gray-50 p-1.5 rounded-2xl">
            <button onClick={() => { setActiveTab('id'); setStep('input-email'); setError(''); }} className={`flex-1 py-3 text-xs font-black rounded-xl transition-all ${activeTab === 'id' ? 'bg-white text-primary shadow-sm' : 'text-gray-400'}`}>아이디 찾기</button>
            <button onClick={() => { setActiveTab('pw'); setStep('input-email'); setError(''); }} className={`flex-1 py-3 text-xs font-black rounded-xl transition-all ${activeTab === 'pw' ? 'bg-white text-primary shadow-sm' : 'text-gray-400'}`}>비밀번호 찾기</button>
          </div>
        )}

        {/* 에러 메시지 */}
        {error && (
          <div className="p-4 bg-red-50 text-red-500 text-sm font-bold rounded-xl text-center animate-shake">
            {error}
          </div>
        )}

        {/* --- Step 3: 성공 화면 --- */}
        {step === 'success' ? (
          <div className="text-center py-8 space-y-4">
            <div className="text-6xl">🎉</div>
            <p className="font-bold text-text-main">새로운 비밀번호로<br />로그인해주세요.</p>
            <Link to="/login" className="inline-block bg-primary text-white px-8 py-3 rounded-xl font-black mt-4 shadow-lg hover:bg-primary-dark transition-colors">로그인으로 돌아가기</Link>
          </div>
        ) : step === 'input-code' ? (
          /* --- Step 2: 인증 코드 & 새 비밀번호 입력 --- */
          <form onSubmit={handleResetPassword} className="space-y-6">
            <div className="space-y-4">
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">인증 코드</label>
                <input
                  type="text"
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="w-full px-6 py-4 bg-gray-50 border-2 border-transparent rounded-[1.5rem] focus:border-primary focus:bg-white outline-none font-bold"
                  placeholder="123456"
                />
              </div>
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">새 비밀번호</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-6 py-4 bg-gray-50 border-2 border-transparent rounded-[1.5rem] focus:border-primary focus:bg-white outline-none font-bold"
                  placeholder="새 비밀번호 입력"
                />
              </div>
            </div>
            <button type="submit" disabled={isLoading} className="w-full py-4 bg-primary text-white rounded-[1.5rem] font-black text-lg shadow-xl shadow-primary/10 hover:bg-primary-dark transition-colors disabled:opacity-50">
              {isLoading ? '처리 중...' : '비밀번호 변경하기'}
            </button>
            <button type="button" onClick={() => setStep('input-email')} className="w-full text-gray-400 text-sm font-bold mt-2">
              이메일 다시 입력하기
            </button>
          </form>
        ) : (
          /* --- Step 1: 이메일 입력 --- */
          <form onSubmit={handleRequestCode} className="space-y-6">
            <div className="space-y-2">
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">가입 시 사용한 이메일</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-6 py-4 bg-gray-50 border-2 border-transparent rounded-[1.5rem] focus:border-primary focus:bg-white outline-none font-bold"
                placeholder="email@example.com"
              />
            </div>
            <button type="submit" disabled={isLoading} className="w-full py-4 bg-primary text-white rounded-[1.5rem] font-black text-lg shadow-xl shadow-primary/10 hover:bg-primary-dark transition-colors disabled:opacity-50">
              {isLoading ? '발송 중...' : '인증 코드 받기'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default FindAccountPage;
