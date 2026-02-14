
import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GoogleGenAI } from "@google/genai";
import { useAuth } from '../contexts/AuthContext';

interface Message {
  id: string;
  sender: 'me' | 'leader';
  text: string;
  timestamp: string;
}

const DirectChatPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'leader',
      text: '안녕하세요! 프로젝트에 관심 가져주셔서 감사합니다. 궁금하신 점 편하게 물어보세요!',
      timestamp: '오후 2:00'
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Mock project data
  const projectTitle = "AI 기반 맞춤형 학습 플랫폼";
  const leaderName = "김민준 팀장";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      sender: 'me',
      text: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // AI Response Simulation (Leader being away)
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const response = await ai.models.generateContent({
        model: "gemini-3-flash-preview",
        contents: `사용자가 프로젝트 "${projectTitle}"의 팀장 ${leaderName}에게 보낸 메시지: "${input}"
        당신은 팀장 ${leaderName}의 부재중 AI 비서입니다. 
        사용자에게 현재 팀장이 회의 중이라 대신 답변한다고 친절하게 말하고, 위 메시지에 대해 프로젝트 내용을 바탕으로 아주 전문적이고 환영하는 태도로 답변해주세요.`,
        config: {
            systemInstruction: "당신은 IT 프로젝트 팀장의 스마트 비서입니다. 답변은 항상 한국어로 자연스럽고 친절해야 합니다."
        }
      });

      setTimeout(() => {
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          sender: 'leader',
          text: response.text || '현재 팀장님이 외부 미팅 중입니다. 잠시 후 직접 연락 드릴 예정입니다!',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages(prev => [...prev, aiMessage]);
        setIsTyping(false);
      }, 1000);

    } catch (error) {
      console.error(error);
      setIsTyping(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-180px)] flex flex-col bg-white rounded-[2.5rem] shadow-2xl border border-gray-100 overflow-hidden animate-fadeIn">
      {/* Header */}
      <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-white/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-50 rounded-full transition-colors">
            <svg className="w-6 h-6 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path></svg>
          </button>
          <div className="relative">
            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Minjun" className="w-12 h-12 rounded-full border-2 border-primary/20" alt="leader" />
            <div className="absolute bottom-0 right-0 w-3 h-3 bg-secondary border-2 border-white rounded-full"></div>
          </div>
          <div>
            <h3 className="font-black text-text-primary">{leaderName}</h3>
            <p className="text-xs text-secondary font-bold uppercase tracking-tighter">● Online (AI Support Active)</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
            <button className="p-2 text-text-secondary hover:text-primary transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"></path></svg>
            </button>
            <button className="p-2 text-text-secondary hover:text-primary transition-colors">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path></svg>
            </button>
        </div>
      </div>

      {/* Messages Area */}
      <div ref={scrollRef} className="flex-grow overflow-y-auto p-6 space-y-6 bg-gray-50/30">
        <div className="text-center">
            <span className="inline-block px-4 py-1.5 bg-gray-100 rounded-full text-[10px] font-bold text-text-secondary uppercase tracking-widest mb-8">
                {projectTitle} 문의가 시작되었습니다
            </span>
        </div>

        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.sender === 'me' ? 'justify-end' : 'justify-start'} animate-scaleUp`}>
            <div className={`flex max-w-[85%] ${m.sender === 'me' ? 'flex-row-reverse' : 'flex-row'}`}>
              {m.sender === 'leader' && (
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Minjun" className="w-8 h-8 rounded-full self-end mb-1 mr-2" alt="leader" />
              )}
              <div className={`group relative ${m.sender === 'me' ? 'mr-0' : 'ml-0'}`}>
                <div className={`px-5 py-3.5 rounded-[1.5rem] shadow-sm text-sm font-medium leading-relaxed ${
                  m.sender === 'me' 
                    ? 'bg-primary text-white rounded-br-none shadow-indigo-100' 
                    : 'bg-white text-text-primary border border-gray-100 rounded-bl-none'
                }`}>
                  {m.text}
                </div>
                <p className={`text-[10px] font-bold text-gray-400 mt-1.5 ${m.sender === 'me' ? 'text-right mr-1' : 'text-left ml-1'}`}>
                  {m.timestamp}
                </p>
              </div>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start animate-pulse">
            <div className="bg-white border border-gray-100 px-4 py-2 rounded-2xl flex space-x-1">
              <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce"></div>
              <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.2s]"></div>
              <div className="w-1.5 h-1.5 bg-gray-300 rounded-full animate-bounce [animation-delay:0.4s]"></div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white border-t border-gray-100">
        <form onSubmit={handleSendMessage} className="flex items-center space-x-3">
          <button type="button" className="p-3 text-text-secondary hover:text-primary transition-colors bg-gray-50 rounded-2xl">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
          </button>
          <div className="flex-grow relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="팀장님께 궁금한 점을 메시지로 남겨보세요..."
              className="w-full bg-gray-50 border-2 border-transparent focus:border-primary focus:bg-white rounded-2xl py-3.5 px-6 outline-none transition-all font-medium text-sm"
            />
          </div>
          <button 
            type="submit" 
            disabled={!input.trim() || isTyping}
            className="bg-primary text-white p-3.5 rounded-2xl font-bold hover:bg-primary-dark transition-all shadow-lg shadow-indigo-100 disabled:opacity-50 disabled:bg-gray-300"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
          </button>
        </form>
      </div>
    </div>
  );
};

export default DirectChatPage;
