
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authAPI } from '../api/apiClient';

const SignUpPage: React.FC = () => {
  const { checkNickname } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({ name: '', email: '', password: '', passwordConfirm: '' });
  const [nicknameStatus, setNicknameStatus] = useState<{ checked: boolean, available: boolean, message: string }>({
    checked: false,
    available: false,
    message: ''
  });
  const [isChecking, setIsChecking] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleNicknameCheck = async () => {
    if (!formData.name) return alert('닉네임을 입력해주세요.');
    setIsChecking(true);
    const result = await checkNickname(formData.name);
    setNicknameStatus({
      checked: true,
      available: result.available,
      message: result.message
    });
    setIsChecking(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nicknameStatus.available) {
      setError('닉네임 중복 확인을 해주세요.');
      return;
    }
    if (formData.password !== formData.passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await authAPI.signUp({
        email: formData.email,
        password: formData.password,
        nickname: formData.name,
      });
      // [수정] 이메일 인증 페이지로 이동 (이메일 및 비밀번호 정보 전달 - 자동 로그인용)
      navigate('/verify-email', { state: { email: formData.email, password: formData.password } });
    } catch (err: any) {
      setError(err.message || '회원가입에 실패했습니다.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center py-12 px-4 animate-fadeIn">
      <div className="max-w-md w-full space-y-8 bg-surface p-10 rounded-[2.5rem] shadow-2xl border border-gray-100">
        <div className="text-center">
          <h2 className="text-3xl font-black text-text-main tracking-tight">Portforge 시작하기</h2>
          <p className="mt-2 text-text-sub font-medium">새로운 항해를 준비하세요!</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-2xl text-xs font-bold border border-red-100 text-center">
            {error}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">이메일 계정</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-5 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:border-primary focus:bg-white outline-none font-bold shadow-sm"
              placeholder="email@example.com"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">활동 닉네임 (2~10자, 특문불가)</label>
            <div className="flex gap-2">
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => {
                  setFormData({ ...formData, name: e.target.value });
                  setNicknameStatus({ checked: false, available: false, message: '' });
                }}
                className={`flex-grow px-5 py-4 bg-gray-50 border-2 rounded-2xl focus:bg-white outline-none font-bold shadow-sm transition-all ${nicknameStatus.checked ? (nicknameStatus.available ? 'border-green-400' : 'border-red-400') : 'border-transparent'
                  }`}
                placeholder="2~10자 사이"
              />
              <button
                type="button"
                onClick={handleNicknameCheck}
                disabled={isChecking}
                className="bg-gray-100 px-5 py-2 rounded-xl text-xs font-black hover:bg-gray-200 transition-colors whitespace-nowrap"
              >
                {isChecking ? '...' : '중복 확인'}
              </button>
            </div>
            {nicknameStatus.checked && (
              <p className={`text-[11px] font-bold ml-1 animate-fadeIn ${nicknameStatus.available ? 'text-green-600' : 'text-red-500'}`}>
                {nicknameStatus.available ? '✅ ' : '❌ '} {nicknameStatus.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">비밀번호</label>
            <input
              type="password"
              required
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full px-5 py-4 bg-gray-50 border-2 border-transparent rounded-2xl focus:border-primary focus:bg-white outline-none font-bold shadow-sm"
              placeholder="8자 이상"
            />
            <p className="text-[11px] text-gray-400 ml-1">영문, 숫자, 특수문자 중 2가지 이상 조합 (8~20자)</p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">비밀번호 확인</label>
            <input
              type="password"
              required
              value={formData.passwordConfirm}
              onChange={(e) => setFormData({ ...formData, passwordConfirm: e.target.value })}
              className={`w-full px-5 py-4 bg-gray-50 border-2 rounded-2xl focus:bg-white outline-none font-bold shadow-sm transition-all ${formData.passwordConfirm && formData.password !== formData.passwordConfirm ? 'border-red-400' : 'border-transparent focus:border-primary'}`}
              placeholder="비밀번호를 다시 입력해주세요"
            />
            {formData.passwordConfirm && formData.password !== formData.passwordConfirm && (
              <p className="text-[11px] text-red-500 font-bold ml-1">비밀번호가 일치하지 않습니다</p>
            )}
          </div>

          <button
            type="submit"
            disabled={!nicknameStatus.available || isSubmitting}
            className="w-full py-5 text-white bg-primary rounded-2xl font-black text-lg hover:bg-primary-dark transition-all shadow-xl shadow-primary/20 disabled:bg-gray-200 disabled:shadow-none mt-4"
          >
            {isSubmitting ? '가입 중...' : '시작하기'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default SignUpPage;

