
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const LoginPage: React.FC = () => {
  const { login, loginWithSocial } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isEmailLoading, setIsEmailLoading] = useState(false);
  const [activeSocial, setActiveSocial] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log("🚀 handleLogin 호출됨"); // 디버깅용
    setError('');
    setIsEmailLoading(true);
    try {
      console.log("🔑 로그인 시도:", email); // 디버깅용
      await login(email, password);
      console.log("✅ 로그인 성공"); // 디버깅용
      navigate('/');
    } catch (err: any) {
      console.log("❌ 로그인 에러 잡힘:", err); // 디버깅용
      // API 응답에서 에러 메시지 추출 (FastAPI는 detail, 일반 API는 message 등)
      // API 응답에서 에러 메시지 추출 (FastAPI는 detail, 일반 API는 message 등)
      const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || '로그인 정보를 다시 확인해 주세요.';

      // [수정] 로그인 실패 시 팝업으로 알림
      alert(`로그인 실패\n\n${errorMsg}`);

      // 이메일 인증 관련 에러인지 확인
      if (errorMsg.includes('이메일 인증') || errorMsg.includes('UserNotConfirmedException')) {
        setError('📧 이메일 인증이 완료되지 않았습니다. 받은편지함에서 인증 링크를 확인해주세요.');
      } else {
        setError(errorMsg);
      }
    } finally {
      setIsEmailLoading(false);
    }
  };

  const handleSocialLogin = async (provider: 'Google' | 'Kakao' | 'GitHub' | 'Naver') => {
    setError('');
    setActiveSocial(provider);
    try {
      await loginWithSocial(provider);
      navigate('/');
    } catch (err: any) {
      setError(err.message || `${provider} 로그인에 실패했습니다.`);
    } finally {
      setActiveSocial(null);
    }
  };

  return (
    <div className="flex items-center justify-center py-12 px-4 animate-fadeIn">
      <div className="max-w-md w-full space-y-8 bg-surface p-10 rounded-[3rem] shadow-2xl border border-gray-100">
        <div className="text-center">
          <Link to="/" className="inline-flex items-center space-x-2 mb-6 group">
            <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-white font-black text-2xl group-hover:rotate-12 transition-transform shadow-lg shadow-primary/20">P</div>
            <span className="text-3xl font-black text-secondary tracking-tighter">Portforge</span>
          </Link>
          <h2 className="text-2xl font-black text-text-main tracking-tight">돌아오신 것을 환영합니다!</h2>
          <p className="mt-2 text-text-sub font-medium">프로젝트 팀 매칭 플랫폼</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-2xl text-xs font-bold border border-red-100 text-center">
            {error}
          </div>
        )}

        <form className="space-y-4" onSubmit={handleLogin}>
          <input
            type="text"
            required
            disabled={isEmailLoading || !!activeSocial}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent rounded-[1.5rem] focus:border-primary focus:bg-white focus:outline-none transition-all font-bold text-sm"
            placeholder="이메일"
          />
          <input
            type="password"
            required
            disabled={isEmailLoading || !!activeSocial}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent rounded-[1.5rem] focus:border-primary focus:bg-white focus:outline-none transition-all font-bold text-sm"
            placeholder="비밀번호"
          />
          <div className="flex justify-end px-2">
            <Link to="/find-account" className="text-[11px] font-black text-text-sub hover:text-primary transition-colors uppercase tracking-widest">
              정보 찾기
            </Link>
          </div>
          <button
            type="submit"
            disabled={isEmailLoading || !!activeSocial}
            className="w-full py-4 text-white bg-primary rounded-[1.5rem] font-black text-lg hover:bg-secondary transition-all shadow-xl shadow-primary/10 disabled:opacity-50"
          >
            {isEmailLoading ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <div className="relative flex items-center py-4">
          <div className="flex-grow border-t border-gray-100"></div>
          <span className="flex-shrink mx-6 text-text-sub text-[10px] font-black uppercase tracking-[0.2em]">소셜 로그인</span>
          <div className="flex-grow border-t border-gray-100"></div>
        </div>

        <div className="flex flex-col gap-3">
          <SocialBtn label="카카오톡으로 로그인" color="bg-[#FEE500] text-black" onClick={() => handleSocialLogin('Kakao')} icon="💬" />
          <SocialBtn label="구글로 로그인" color="bg-white border border-gray-100 text-gray-700" onClick={() => handleSocialLogin('Google')} icon="G" />
        </div>

        <div className="text-center pt-2">
          <p className="text-xs text-text-sub font-bold">
            아직 회원이 아니신가요?{' '}
            <Link to="/signup" className="text-primary font-black hover:underline underline-offset-4">
              회원가입
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

const SocialBtn = ({ label, color, onClick, icon, disabled }: any) => (
  <button
    onClick={disabled ? undefined : onClick}
    disabled={disabled}
    className={`${color} w-full py-3.5 rounded-2xl flex items-center px-6 font-bold text-sm transition-all shadow-sm relative overflow-hidden group ${disabled ? 'opacity-60' : 'hover:opacity-90'}`}
  >
    <span className="w-6 text-center text-lg">{icon}</span>
    <span className="flex-grow text-center">{label}</span>
  </button>
);

export default LoginPage;
