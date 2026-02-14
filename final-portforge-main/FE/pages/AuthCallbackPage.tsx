
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { authAPI } from '../api/apiClient';

const AuthCallbackPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const [error, setError] = useState('');
    const [processing, setProcessing] = useState(true);

    useEffect(() => {
        const handleCallback = async () => {
            const code = searchParams.get('code');
            const errorParam = searchParams.get('error');
            const errorDescription = searchParams.get('error_description');

            if (errorParam) {
                setError(errorDescription || '소셜 로그인에 실패했습니다.');
                setProcessing(false);
                return;
            }

            if (!code) {
                setError('인증 코드가 없습니다.');
                setProcessing(false);
                return;
            }

            try {
                // 백엔드에 code 전송하여 토큰 교환
                const response = await authAPI.socialCallback(code);

                // 토큰 저장
                localStorage.setItem('access_token', response.access_token);
                if (response.id_token) {
                    localStorage.setItem('id_token', response.id_token);
                }

                // 사용자 정보 저장
                const user = {
                    id: response.user.user_id, // [수정] UUID 사용
                    name: response.user.nickname,
                    email: response.user.email,
                    role: (response.user.role || '').toUpperCase() === 'ADMIN' ? 'ADMIN' : 'USER',
                    appliedProjects: [],
                    testResults: []
                };
                localStorage.setItem('portforge_v8_user', JSON.stringify(user));

                // 메인 페이지로 이동 (새로고침 효과를 위해 href 사용)
                window.location.href = '/';

            } catch (err: any) {
                console.error('Social login callback failed:', err);
                setError(err.message || '소셜 로그인 처리 중 오류가 발생했습니다.');
                setProcessing(false);
            }
        };

        handleCallback();
    }, [searchParams, navigate]);

    if (processing) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                <p className="text-text-secondary font-medium">소셜 로그인 처리 중...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
                <div className="bg-red-50 text-red-600 p-6 rounded-2xl text-center max-w-md">
                    <h2 className="text-xl font-bold mb-2">로그인 실패</h2>
                    <p className="text-sm">{error}</p>
                </div>
                <button
                    onClick={() => navigate('/login')}
                    className="px-6 py-3 bg-primary text-white rounded-xl font-bold hover:bg-primary-dark transition-colors"
                >
                    로그인 페이지로 돌아가기
                </button>
            </div>
        );
    }

    return null;
};

export default AuthCallbackPage;
