import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { authAPI } from '../api/apiClient';
import { useAuth } from '../contexts/AuthContext';

const VerifyEmailPage: React.FC = () => {
    const { login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const emailFromState = location.state?.email || '';
    const passwordFromState = location.state?.password;

    const [email, setEmail] = useState(emailFromState);
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isResending, setIsResending] = useState(false);

    const handleVerify = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setIsLoading(true);

        try {
            const result = await authAPI.verifyEmail(email, code);
            setSuccess(result.message || '이메일 인증이 완료되었습니다!');

            // [자동 로그인 시도]
            if (passwordFromState && email === emailFromState) {
                try {
                    await login(email, passwordFromState);
                    setSuccess('인증 완료! 환영합니다.');
                    setTimeout(() => navigate('/'), 1000);
                    return;
                } catch (loginErr) {
                    console.error('자동 로그인 실패:', loginErr);
                    // 자동 로그인 실패 시 아래 로직(로그인 페이지 이동)으로 진행
                }
            }

            setTimeout(() => navigate('/login'), 2000);
        } catch (err: any) {
            setError(err.message || '인증에 실패했습니다.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleResend = async () => {
        if (!email) {
            setError('이메일을 입력해주세요.');
            return;
        }

        setIsResending(true);
        setError('');

        try {
            const result = await authAPI.resendCode(email);
            setSuccess(result.message || '인증 코드가 재발송되었습니다.');
        } catch (err: any) {
            setError(err.message || '코드 재발송에 실패했습니다.');
        } finally {
            setIsResending(false);
        }
    };

    return (
        <div className="flex items-center justify-center py-12 px-4 animate-fadeIn">
            <div className="max-w-md w-full space-y-8 bg-surface p-10 rounded-[2.5rem] shadow-2xl border border-gray-100">
                <div className="text-center">
                    <Link to="/" className="inline-flex items-center space-x-2 mb-6 group">
                        <div className="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-white font-black text-2xl group-hover:rotate-12 transition-transform shadow-lg shadow-primary/20">P</div>
                        <span className="text-3xl font-black text-secondary tracking-tighter">Portforge</span>
                    </Link>
                    <h2 className="text-2xl font-black text-text-main tracking-tight">이메일 인증</h2>
                    <p className="text-sm text-text-sub mt-2">
                        가입하신 이메일로 발송된 인증 코드를 입력해주세요.
                    </p>
                </div>

                <form onSubmit={handleVerify} className="space-y-6">
                    <div>
                        <label className="text-sm font-bold text-text-main mb-2 block">이메일</label>
                        <input
                            type="email"
                            className="w-full px-4 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-primary focus:border-transparent font-medium"
                            placeholder="example@email.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div>
                        <label className="text-sm font-bold text-text-main mb-2 block">인증 코드</label>
                        <input
                            type="text"
                            className="w-full px-4 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-2 focus:ring-primary focus:border-transparent font-medium tracking-widest text-center text-xl"
                            placeholder="123456"
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            maxLength={6}
                            required
                        />
                    </div>

                    {error && (
                        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-red-600 text-sm font-bold text-center">
                            ⚠️ {error}
                        </div>
                    )}

                    {success && (
                        <div className="p-4 bg-green-50 border border-green-200 rounded-2xl text-green-600 text-sm font-bold text-center">
                            ✅ {success}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={isLoading || !email || !code}
                        className="w-full py-4 px-4 bg-gradient-to-r from-primary to-secondary text-white rounded-2xl font-black text-sm hover:opacity-90 transition-opacity shadow-lg shadow-primary/30 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading ? '인증 중...' : '인증 완료'}
                    </button>

                    <button
                        type="button"
                        onClick={handleResend}
                        disabled={isResending || !email}
                        className="w-full py-3 px-4 bg-gray-100 text-gray-700 rounded-2xl font-bold text-sm hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                        {isResending ? '발송 중...' : '📧 인증 코드 다시 받기'}
                    </button>
                </form>

                <div className="text-center pt-2">
                    <p className="text-xs text-text-sub font-bold">
                        이미 인증을 완료하셨나요?{' '}
                        <Link to="/login" className="text-primary font-black hover:underline underline-offset-4">
                            로그인하기
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default VerifyEmailPage;
