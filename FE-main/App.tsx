
import React, { useEffect } from 'react';
import { HashRouter, Routes, Route, Outlet, Navigate, useLocation } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import FindAccountPage from './pages/FindAccountPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import TeamCreationPage from './pages/TeamCreationPage';
import TeamSpacePage from './pages/TeamSpacePage';
import MyPage from './pages/MyPage';
import AnnouncementsPage from './pages/AnnouncementsPage';
import EventsPage from './pages/EventsPage';
import DirectChatPage from './pages/DirectChatPage';
import AdminPage from './pages/AdminPage';
import ApplicationSuccessPage from './pages/ApplicationSuccessPage';
import AuthCallbackPage from './pages/AuthCallbackPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AiProvider } from './contexts/AiContext';
import { authAPI } from './api/apiClient';

// OAuth 콜백 처리 (HashRouter 바깥에서 실행)
const OAuthCodeHandler: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isProcessing, setIsProcessing] = React.useState(false);
  const [processed, setProcessed] = React.useState(false);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      // URL 쿼리에서 code 파라미터 확인
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const error = urlParams.get('error');

      if (error) {
        console.error('OAuth error:', urlParams.get('error_description'));
        // URL에서 파라미터 제거
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
      }

      if (!code || processed) return;

      setIsProcessing(true);
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
          id: response.user.user_id,
          name: response.user.nickname,
          email: response.user.email,
          role: (response.user.role || '').toUpperCase() === 'ADMIN' ? 'ADMIN' : 'USER',
          myStacks: response.user.myStacks || [],
          appliedProjects: [],
          testResults: []
        };
        localStorage.setItem('portforge_v8_user', JSON.stringify(user));

        // URL 정리 후 새로고침 (reload 후에는 코드 실행 안 됨)
        window.history.replaceState({}, document.title, window.location.pathname);
        window.location.reload();
        return; // reload 후 코드 실행 방지
      } catch (err: any) {
        console.error('Social login callback failed:', err);
        // 이미 저장되었을 수 있으므로 팝업 대신 콘솔에만 로그
        // URL 정리
        window.history.replaceState({}, document.title, window.location.pathname);
        setIsProcessing(false);
        setProcessed(true);
      }
    };

    handleOAuthCallback();
  }, [processed]);

  if (isProcessing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p className="mt-4 text-text-secondary font-medium">소셜 로그인 처리 중...</p>
      </div>
    );
  }

  return <>{children}</>;
};

const LoadingSpinner = () => (
  <div className="flex items-center justify-center min-h-[50vh]">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
  </div>
);

const ProtectedRoute = () => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
};

const GuestRoute = ({ children }: { children?: React.ReactNode }) => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
};

const AdminRoute = () => {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner />;
  if (user?.role !== 'ADMIN') return <Navigate to="/" replace />;
  return <Outlet />;
};

const ScrollToTop = () => {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
};

const App: React.FC = () => {
  return (
    <OAuthCodeHandler>
      <AuthProvider>
        <HashRouter>
          <AiProvider>
            <ScrollToTop />
            <div className="flex flex-col min-h-screen bg-background text-text-main">
              <Header />
              <main className="flex-grow container mx-auto px-4 py-8">
                <Routes>
                  {/* 메인 진입 페이지: 프로젝트 탐색 허브 */}
                  <Route path="/" element={<HomePage />} />

                  <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
                  <Route path="/signup" element={<GuestRoute><SignUpPage /></GuestRoute>} />
                  <Route path="/find-account" element={<GuestRoute><FindAccountPage /></GuestRoute>} />
                  <Route path="/verify-email" element={<VerifyEmailPage />} />
                  <Route path="/auth/callback" element={<AuthCallbackPage />} />
                  <Route path="/projects/:id" element={<ProjectDetailPage />} />
                  <Route path="/announcements" element={<AnnouncementsPage />} />
                  <Route path="/events" element={<EventsPage />} />
                  <Route path="/apply-success" element={<ApplicationSuccessPage />} />

                  <Route element={<ProtectedRoute />}>
                    <Route path="/team/create" element={<TeamCreationPage />} />
                    <Route path="/team-space/:id" element={<TeamSpacePage />} />
                    <Route path="/chat/:id" element={<DirectChatPage />} />
                    <Route path="/mypage" element={<MyPage />} />
                  </Route>

                  <Route element={<AdminRoute />}>
                    <Route path="/admin" element={<AdminPage />} />
                  </Route>

                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
              <Footer />
            </div>
          </AiProvider>
        </HashRouter>
      </AuthProvider>
    </OAuthCodeHandler>
  );
};

export default App;
