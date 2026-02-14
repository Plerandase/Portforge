
import React, { useState, useEffect, useRef } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Header: React.FC = () => {
  const { user, logout, resetAllFilters, notifications, markNotificationsRead, refreshNotifications } = useAuth();
  const navigate = useNavigate();
  const [showNoti, setShowNoti] = useState(false);
  const [showTeamDropdown, setShowTeamDropdown] = useState(false);
  const teamDropdownRef = useRef<HTMLDivElement>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (teamDropdownRef.current && !teamDropdownRef.current.contains(event.target as Node)) {
        setShowTeamDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogoClick = () => {
    // 모든 검색/필터 상태를 초기화하고 메인 화면으로 이동
    resetAllFilters();
    navigate('/');
  };

  // 참여 중인 팀 목록 (승인된 프로젝트)
  const acceptedTeams = user?.appliedProjects?.filter(p => p.status === 'accepted') || [];

  const myNotis = notifications.filter(n => 
    String(n.userId) === String(user?.id) || (user?.role === 'ADMIN' && n.role === 'ADMIN')
  );
  const unreadCount = myNotis.filter(n => !n.read).length;

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-xl text-sm font-bold transition-all ${isActive ? 'text-primary bg-primary/5' : 'text-text-sub hover:text-text-main hover:bg-gray-50'
    }`;

  return (
    <header className="bg-white border-b border-gray-100 sticky top-0 z-[100]">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-20">
          <div className="flex items-center space-x-2">
            <button onClick={handleLogoClick} className="flex items-center space-x-2 mr-6 group">
              <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-white font-black text-xl shadow-lg shadow-primary/20 group-hover:scale-110 transition-transform">P</div>
              <span className="text-2xl font-black text-text-main tracking-tighter">Portforge</span>
            </button>
            <nav className="hidden md:flex items-center space-x-1">
              <NavLink to="/events" className={navLinkClass}>행사 정보</NavLink>
              {user?.role === 'ADMIN' && <NavLink to="/admin" className="px-4 py-2 rounded-xl text-sm font-black text-red-500 bg-red-50 hover:bg-red-100 transition-all">관리자 센터</NavLink>}
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-4">
                  {/* 참여 중인 팀 스페이스 바로가기 (드롭다운) */}
                  {acceptedTeams.length > 0 && (
                    <div className="relative" ref={teamDropdownRef}>
                      <button
                        onClick={() => setShowTeamDropdown(!showTeamDropdown)}
                        className="hidden sm:flex items-center gap-2 bg-secondary text-white px-5 py-3 rounded-full text-xs font-black hover:bg-secondary/90 transition-all shadow-lg shadow-secondary/20"
                      >
                        <span>🚀</span> 팀 스페이스
                        {acceptedTeams.length > 1 && (
                          <svg className={`w-3 h-3 transition-transform ${showTeamDropdown ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                          </svg>
                        )}
                      </button>
                      
                      {/* 팀이 1개면 바로 이동, 여러 개면 드롭다운 */}
                      {showTeamDropdown && acceptedTeams.length > 1 && (
                        <div className="absolute top-full right-0 mt-2 w-72 bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden animate-slideDown z-50">
                          <div className="p-3 border-b bg-gray-50/50">
                            <p className="text-[10px] font-black text-text-sub uppercase tracking-wider">참여 중인 팀</p>
                          </div>
                          <div className="max-h-64 overflow-y-auto">
                            {acceptedTeams.map((team) => {
                              const isLeader = team.userRole === 'Leader';
                              // 팀장이면 "팀장"만 표시, 팀원이면 포지션 표시
                              const roleDisplay = isLeader 
                                ? '👑 팀장' 
                                : `👤 ${team.selectedPosition || team.position || '팀원'}`;
                              
                              return (
                                <button
                                  key={team.id}
                                  onClick={() => {
                                    navigate(`/team-space/${team.id}`);
                                    setShowTeamDropdown(false);
                                  }}
                                  className="w-full p-4 text-left hover:bg-gray-50 transition-colors border-b border-gray-50 last:border-0"
                                >
                                  <p className="text-sm font-bold text-text-main truncate">
                                    {team.projectTitle || team.title || `프로젝트 #${team.id}`}
                                  </p>
                                  <p className="text-[10px] text-text-sub mt-1">
                                    {roleDisplay}
                                  </p>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                      
                      {/* 팀이 1개면 클릭 시 바로 이동 */}
                      {acceptedTeams.length === 1 && (
                        <div 
                          className="absolute inset-0 cursor-pointer" 
                          onClick={() => navigate(`/team-space/${acceptedTeams[0].id}`)}
                        />
                      )}
                    </div>
                  )}
                  <Link to="/team/create" className="hidden sm:flex items-center gap-2 bg-primary text-white px-6 py-3 rounded-full text-xs font-black hover:bg-primary-dark transition-all shadow-xl shadow-primary/20"><span>+</span> 팀원 모집하기</Link>
                </div>

                <div className="relative">
                  <button onClick={() => setShowNoti(!showNoti)} className="p-2.5 bg-gray-50 rounded-full hover:bg-gray-100 transition-colors relative">
                    <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
                    {unreadCount > 0 && (
                      <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-black flex items-center justify-center rounded-full border-2 border-white animate-pulse">
                        {unreadCount > 99 ? '99+' : unreadCount}
                      </span>
                    )}
                  </button>
                  {showNoti && (
                    <div className="absolute top-full right-0 mt-3 w-80 bg-white rounded-[2rem] shadow-2xl border border-gray-100 overflow-hidden animate-slideDown z-50">
                      <div className="p-5 border-b bg-gray-50/50 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-black text-text-main">새로운 알림</span>
                          {unreadCount > 0 && (
                            <span className="bg-red-500 text-white text-[9px] font-black px-2 py-0.5 rounded-full">
                              {unreadCount}개
                            </span>
                          )}
                        </div>
                        <button onClick={() => {
                          setShowNoti(false);
                          markNotificationsRead(); // 알림 모달을 닫을 때 읽음 처리
                        }} className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors">닫기</button>
                      </div>
                      <div className="max-h-96 overflow-y-auto divide-y divide-gray-50">
                        {myNotis.length > 0 ? myNotis.map(n => (
                          <div key={n.id} onClick={() => {
                            navigate(n.link);
                            setShowNoti(false);
                            markNotificationsRead(); // 알림 항목 클릭 시에도 읽음 처리
                          }} className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${!n.read ? 'bg-primary/5 border-l-4 border-primary' : ''}`}>
                            <div className="flex gap-2 items-start">
                              <span className={`text-[8px] font-black px-1.5 py-0.5 rounded ${n.role === 'ADMIN' ? 'bg-red-100 text-red-500' : 'bg-primary/10 text-primary'}`}>{n.role}</span>
                              {!n.read && <span className="w-2 h-2 bg-red-500 rounded-full flex-shrink-0 mt-1"></span>}
                              <p className="text-xs font-bold text-text-main leading-snug flex-1">{n.message}</p>
                            </div>
                            <span className="text-[9px] text-gray-400 mt-1 block ml-8">{n.date}</span>
                          </div>
                        )) : (
                          <div className="p-10 text-center">
                            <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                            </svg>
                            <p className="text-xs text-gray-400 font-bold">알림이 없습니다.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-3 border-l pl-4">
                  <Link to="/mypage" className="flex items-center space-x-2 group">
                    <img src={user.avatarUrl || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.id}`} className="w-10 h-10 rounded-full border-2 border-primary/20 bg-gray-50 object-cover" alt="avatar" />
                    <div className="hidden lg:block"><p className="text-xs font-black text-text-main">{user.name}</p></div>
                  </Link>
                  <button onClick={logout} className="text-xs font-bold text-text-sub hover:text-red-500 transition-colors ml-2">로그아웃</button>
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <Link to="/login" className="text-sm font-black text-text-sub hover:text-primary transition-colors">로그인</Link>
                <Link to="/signup" className="bg-primary text-white px-6 py-3 rounded-full text-sm font-black hover:bg-primary-dark transition-all shadow-xl shadow-primary/10">회원가입</Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
