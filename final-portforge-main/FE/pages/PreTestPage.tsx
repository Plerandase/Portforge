import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth, TestResult } from '../contexts/AuthContext';
import { fetchQuestions, analyzeResults, gradeUserAnswer } from '../api/aiClient';

// 스택 카테고리 정의
const STACK_CATEGORIES_BASE: Record<string, string[]> = {
  '프론트엔드': ['React', 'Vue', 'Nextjs', 'TypeScript', 'JavaScript', 'Angular', 'Svelte'],
  '백엔드': ['Java', 'Spring', 'Nodejs', 'Python', 'Django', 'Go', 'Express'],
  'DB': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle'],
  '인프라': ['AWS', 'Docker', 'Kubernetes', 'GCP', 'Azure', 'Terraform'],
  '디자인': ['Figma', 'AdobeXD', 'Sketch', 'Photoshop']
};

const TEST_CATEGORIES = [
  { id: 'frontend', name: '프론트엔드', icon: '💻', stacks: STACK_CATEGORIES_BASE['프론트엔드'] },
  { id: 'backend', name: '백엔드', icon: '⚙️', stacks: STACK_CATEGORIES_BASE['백엔드'] },
  { id: 'db', name: 'DB', icon: '🗄️', stacks: STACK_CATEGORIES_BASE['DB'] },
  { id: 'infra', name: '인프라', icon: '☁️', stacks: STACK_CATEGORIES_BASE['인프라'] },
  { id: 'design', name: '디자인', icon: '🎨', stacks: STACK_CATEGORIES_BASE['디자인'] }
];

const getStackLogoUrl = (stack: string) => {
  const logos: Record<string, string> = {
    'React': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg',
    'Vue': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/vuejs/vuejs-original.svg',
    'Nextjs': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nextjs/nextjs-original.svg',
    'TypeScript': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg',
    'JavaScript': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/javascript/javascript-original.svg',
    'Java': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/java/java-original.svg',
    'Spring': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/spring/spring-original.svg',
    'Nodejs': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg',
    'Python': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg',
    'Django': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/django/django-plain.svg',
    'MySQL': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mysql/mysql-original.svg',
    'PostgreSQL': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg',
    'MongoDB': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/mongodb/mongodb-original.svg',
    'Redis': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/redis/redis-original.svg',
    'AWS': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/amazonwebservices/amazonwebservices-original.svg',
    'Docker': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg',
    'Kubernetes': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/kubernetes/kubernetes-plain.svg',
    'Figma': 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/figma/figma-original.svg',
  };
  return logos[stack] || 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/devicon/devicon-original.svg';
};

interface Question {
  question: string;
  options: string[];
  answer: number | string;
  explanation: string;
  type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER';
  grading_criteria?: string;
}

const PreTestPage: React.FC = () => {
  const { user, addTestResult } = useAuth();
  const [step, setStep] = useState<'category' | 'stack' | 'ready' | 'testing' | 'result'>('category');
  const [selectedCat, setSelectedCat] = useState<typeof TEST_CATEGORIES[0] | null>(null);
  const [selectedStack, setSelectedStack] = useState<string>('');

  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [userAnswers, setUserAnswers] = useState<(number | string)[]>([]);
  const [correctCount, setCorrectCount] = useState(0);
  const [result, setResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState('');

  const [timeLeft, setTimeLeft] = useState(30);
  const [timerActive, setTimerActive] = useState(false);
  const [shortAnswerInput, setShortAnswerInput] = useState("");
  const [gradingResult, setGradingResult] = useState<{ score: number, feedback: string } | null>(null);

  // Refs for timer logic to avoid stale closure
  const currentIdxRef = useRef(currentIdx);
  const questionsRef = useRef(questions);
  const shortAnswerInputRef = useRef(shortAnswerInput);

  useEffect(() => { currentIdxRef.current = currentIdx; }, [currentIdx]);
  useEffect(() => { questionsRef.current = questions; }, [questions]);
  useEffect(() => { shortAnswerInputRef.current = shortAnswerInput; }, [shortAnswerInput]);

  // 테스트 종료
  const finishTest = useCallback(async (finalCorrectCount: number, totalQuestions: number) => {
    setTimerActive(false);
    setLoading(true);
    setLoadingMsg('AI가 최종 역량 리포트를 작성 중입니다...');

    const score = totalQuestions > 0 ? Math.round((finalCorrectCount / totalQuestions) * 100) : 0;

    try {
      const analysisResult = await analyzeResults(
        user?.id || 'anonymous',
        selectedStack,
        totalQuestions,
        finalCorrectCount,
        score
      );

      const newResult: TestResult = {
        skill: selectedStack,
        score,
        date: new Date().toLocaleDateString(),
        feedback: analysisResult.feedback || "테스트 완료!",
        level: analysisResult.level || (score >= 80 ? '고급' : score >= 50 ? '중급' : '초급')
      };

      setResult(newResult);
      addTestResult(newResult);
      setStep('result');
    } catch (e) {
      console.error(e);
      const newResult: TestResult = {
        skill: selectedStack,
        score,
        date: new Date().toLocaleDateString(),
        feedback: "테스트를 완주하셨습니다.",
        level: score >= 80 ? '고급' : score >= 50 ? '중급' : '초급'
      };
      setResult(newResult);
      addTestResult(newResult);
      setStep('result');
    } finally {
      setLoading(false);
    }
  }, [selectedStack, addTestResult, user?.id]);

  // 문제 가져오기
  const fetchMoreQuestions = async (isInitial = false) => {
    setLoadingMsg('AI가 맞춤형 문제를 출제하고 있습니다... (객관식 3 + 주관식 2)');
    setLoading(true);

    try {
      const difficulty = userAnswers.length > 0 && correctCount / userAnswers.length > 0.7 ? "고급" : "초급";
      // 중요: type을 'MIXED'로 전달
      const newQuestions = await fetchQuestions(selectedStack, difficulty, 'MIXED');

      console.log("📥 받은 문제들:", newQuestions);

      const formattedQuestions: Question[] = newQuestions.map(q => ({
        ...q,
        answer: q.answer,
        explanation: q.explanation || '',
        // options가 있고 길이가 0보다 크면 객관식, 아니면 주관식
        type: (q.options && q.options.length > 0) ? 'MULTIPLE_CHOICE' : 'SHORT_ANSWER',
        grading_criteria: q.grading_criteria
      }));

      console.log("📋 포맷된 문제들:", formattedQuestions);

      setQuestions(prev => [...prev, ...formattedQuestions]);

      if (isInitial && formattedQuestions.length > 0) {
        setStep('testing');
        setTimerActive(true);
        const firstQ = formattedQuestions[0];
        setTimeLeft(firstQ.type === 'SHORT_ANSWER' ? 120 : 30);
      }
    } catch (error) {
      console.error("AI API Error:", error);
      alert("AI 문제 생성에 실패했습니다.");
      if (isInitial) setStep('ready');
    } finally {
      setLoading(false);
    }
  };

  // 다음 문제로 이동
  const moveToNextQuestion = useCallback(() => {
    setShortAnswerInput("");
    setGradingResult(null);

    const nextIdx = currentIdxRef.current + 1;
    const qs = questionsRef.current;

    if (nextIdx < qs.length) {
      setCurrentIdx(nextIdx);
      const nextQ = qs[nextIdx];
      setTimeLeft(nextQ.type === 'SHORT_ANSWER' ? 120 : 30);
    } else {
      // 더 이상 문제 없음 -> 추가 로드하거나 종료
      fetchMoreQuestions();
      setCurrentIdx(nextIdx);
      setTimeLeft(30);
    }
  }, []);

  // 객관식 답변 처리
  const handleAnswer = useCallback((ansIdx: number) => {
    const q = questionsRef.current[currentIdxRef.current];
    if (!q) return;

    const isCorrect = ansIdx === q.answer;
    if (isCorrect) setCorrectCount(prev => prev + 1);
    setUserAnswers(prev => [...prev, ansIdx]);
    moveToNextQuestion();
  }, [moveToNextQuestion]);

  // 주관식 답변 처리
  const handleShortAnswerSubmit = useCallback(async (isTimeOut = false) => {
    if (isTimeOut) {
      setUserAnswers(prev => [...prev, "(시간 초과)"]);
      moveToNextQuestion();
      return;
    }

    const input = shortAnswerInputRef.current.trim();
    if (!input) {
      alert("답안을 입력해주세요.");
      return;
    }

    setLoading(true);
    try {
      const q = questionsRef.current[currentIdxRef.current];
      const result = await gradeUserAnswer(
        q.question,
        input,
        String(q.answer),
        q.grading_criteria || ""
      );

      setGradingResult({ score: result.score, feedback: result.feedback });


      if (result.is_correct) {
        setCorrectCount(prev => prev + 1);
      }
      setUserAnswers(prev => [...prev, input]);
    } catch (e) {
      console.error("채점 실패", e);
      moveToNextQuestion();
    } finally {
      setLoading(false);
    }
  }, [moveToNextQuestion]);

  // 타이머 로직 - useRef로 타임아웃 처리
  const timeoutTriggeredRef = useRef(false);

  useEffect(() => {
    // loading 중이거나 비활성 상태면 타이머 중지
    if (!timerActive || gradingResult || loading) return;

    // 새 문제 시작 시 타임아웃 플래그 리셋
    timeoutTriggeredRef.current = false;

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timerActive, gradingResult, currentIdx, loading]); // loading 추가

  // 시간 초과 감지 및 다음 문제 이동 처리 (별도 useEffect)
  useEffect(() => {
    // 이미 처리했거나, 조건 불충족 시 무시
    if (timeLeft !== 0 || !timerActive || gradingResult || timeoutTriggeredRef.current || loading) return;

    // 중복 실행 방지
    timeoutTriggeredRef.current = true;

    console.log("⏰ 시간 초과! 다음 문제로 이동합니다.");

    // 시간이 0이 되면 즉시 다음 문제로 이동
    const q = questionsRef.current[currentIdxRef.current];
    if (q?.type === 'SHORT_ANSWER') {
      handleShortAnswerSubmit(true);
    } else {
      handleAnswer(-1); // 오답 처리
    }
  }, [timeLeft, timerActive, gradingResult, handleAnswer, handleShortAnswerSubmit, loading]);

  // 부정행위 방지 로직
  useEffect(() => {
    if (step !== 'testing') return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        alert("⚠️ 경고: 화면 이탈이 감지되었습니다!\n테스트 중 다른 화면으로 이동하면 부정행위로 간주됩니다.");
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'PrintScreen') {
        e.preventDefault();
        alert("⚠️ 화면 캡처는 허용되지 않습니다.");
        navigator.clipboard.writeText("");
      }
      // Ctrl+C, Ctrl+V 차단
      if (e.ctrlKey && (e.key === 'c' || e.key === 'v' || e.key === 'C' || e.key === 'V')) {
        e.preventDefault();
        alert("🚫 복사/붙여넣기는 허용되지 않습니다.");
      }
    };

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();
      alert("🚫 우클릭은 허용되지 않습니다.");
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('contextmenu', handleContextMenu);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('contextmenu', handleContextMenu);
    };
  }, [step]);

  // ========== 렌더링 ==========

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-32 space-y-8 animate-fadeIn">
      <div className="relative w-24 h-24">
        <div className="absolute inset-0 border-4 border-primary/20 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center text-2xl animate-pulse">🤖</div>
      </div>
      <div className="text-center space-y-2">
        <p className="text-xl font-black text-text-main">AI 역량 분석 시스템</p>
        <p className="text-text-sub font-medium px-4">{loadingMsg}</p>
      </div>
    </div>
  );

  if (step === 'category') return (
    <div className="max-w-4xl mx-auto space-y-12 animate-fadeIn py-10">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-black text-text-main tracking-tight">AI 실시간 역량 검증</h1>
        <p className="text-text-sub font-medium text-lg">객관식 3문제 + 주관식 2문제 혼합 테스트</p>
      </div>
      <div className="grid sm:grid-cols-3 md:grid-cols-5 gap-6">
        {TEST_CATEGORIES.map(cat => (
          <button key={cat.id} onClick={() => { setSelectedCat(cat); setStep('stack'); }} className="group bg-white p-8 rounded-[2.5rem] border-2 border-transparent hover:border-primary hover:shadow-2xl transition-all text-left shadow-sm flex flex-col items-center text-center">
            <div className="text-5xl mb-4 group-hover:scale-110 transition-transform drop-shadow-sm">{cat.icon}</div>
            <h3 className="text-lg font-black mb-1 text-text-main">{cat.name}</h3>
          </button>
        ))}
      </div>
    </div>
  );

  if (step === 'stack' && selectedCat) return (
    <div className="max-w-4xl mx-auto space-y-10 animate-fadeIn py-10">
      <div className="flex items-center gap-4">
        <button onClick={() => setStep('category')} className="p-3 bg-white rounded-2xl shadow-sm hover:text-primary">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" /></svg>
        </button>
        <h2 className="text-3xl font-black text-text-main">{selectedCat.name} 스택 선택</h2>
      </div>
      <div className="bg-white p-10 rounded-[3rem] shadow-xl border border-gray-100 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {selectedCat.stacks.map(stack => (
          <button
            key={stack}
            onClick={() => { setSelectedStack(stack); setStep('ready'); }}
            className="p-4 rounded-2xl border-2 border-gray-50 bg-gray-50/50 hover:border-primary hover:bg-primary/5 hover:text-primary transition-all font-black text-sm flex flex-col items-center gap-3"
          >
            <img src={getStackLogoUrl(stack)} className="w-10 h-10 object-contain rounded-md" alt={stack} />
            {stack}
          </button>
        ))}
      </div>
    </div>
  );

  if (step === 'ready') return (
    <div className="max-w-xl mx-auto space-y-10 animate-fadeIn py-10 text-center">
      <div className="bg-white p-12 rounded-[3.5rem] shadow-xl border border-gray-100 space-y-8">
        <div className="flex flex-col items-center gap-4 mb-4">
          <img src={getStackLogoUrl(selectedStack)} className="w-24 h-24 object-contain rounded-xl shadow-lg" alt={selectedStack} />
          <h2 className="text-3xl font-black text-text-main">{selectedStack} 챌린지</h2>
        </div>

        <div className="bg-gray-50 p-6 rounded-2xl text-left space-y-3 border border-gray-100">
          <p className="text-sm font-bold text-text-main">⏱️ 제한 시간: <span className="text-primary">객관식 30초 / 주관식 2분</span></p>
          <p className="text-sm font-bold text-text-main">📝 문제 구성: <span className="text-primary">객관식 3문제 + 주관식 2문제</span></p>
          <p className="text-xs font-medium text-text-sub italic">
            ⚠️ 부정행위 방지: 복사/붙여넣기, 화면 이탈, 캡처 금지
          </p>
        </div>
        <button onClick={() => fetchMoreQuestions(true)} className="w-full text-white py-6 rounded-3xl font-black text-xl shadow-xl shadow-primary/20 bg-primary hover:scale-[1.02] transition-all">
          종합 역량 테스트 시작
        </button>
      </div>
    </div>
  );

  if (step === 'testing' && questions.length > 0 && currentIdx < questions.length) {
    const q = questions[currentIdx];
    const maxTime = q.type === 'SHORT_ANSWER' ? 120 : 30;
    const timerProgress = Math.max(0, (timeLeft / maxTime) * 100);

    return (
      <div
        className="max-w-3xl mx-auto space-y-8 animate-fadeIn py-10"
        style={{ userSelect: 'none', WebkitUserSelect: 'none' }}
        onContextMenu={(e) => { e.preventDefault(); alert("🚫 우클릭 금지"); }}
      >
        <div className="flex justify-between items-center bg-white px-8 py-4 rounded-full border border-gray-100 shadow-sm">
          <div className="flex items-center gap-4">
            <span className="text-lg font-black text-primary">{currentIdx + 1}번째 문제</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-lg font-black text-secondary">정답: {correctCount}</span>
          </div>
          <button
            onClick={() => finishTest(correctCount, userAnswers.length)}
            className="px-6 py-2 bg-red-50 text-red-500 rounded-full text-xs font-black border border-red-100 hover:bg-red-500 hover:text-white transition-all"
          >
            종료
          </button>
        </div>

        <div className="space-y-3">
          <div className="flex justify-between items-end px-2">
            <span className={`text-sm font-bold px-3 py-1 rounded-full ${q.type === 'SHORT_ANSWER' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'}`}>
              {q.type === 'SHORT_ANSWER' ? '📝 SCENARIO' : '✅ QUIZ'}
            </span>
            <span className={`text-xl font-black ${timeLeft <= 5 ? 'text-red-500 animate-pulse' : 'text-primary'}`}>
              {Math.floor(timeLeft / 60)}:{(timeLeft % 60).toString().padStart(2, '0')}
            </span>
          </div>
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div className={`h-full transition-all duration-1000 ${timeLeft <= 5 ? 'bg-red-500' : 'bg-primary'}`} style={{ width: `${timerProgress}%` }}></div>
          </div>
        </div>

        <div className="bg-white p-12 rounded-[3.5rem] shadow-2xl border border-gray-100 space-y-10">
          <h3 className="text-2xl font-black text-text-main leading-tight whitespace-pre-wrap">{q.question}</h3>

          {q.type === 'SHORT_ANSWER' ? (
            <div className="space-y-6">
              {!gradingResult ? (
                <>
                  <textarea
                    className="w-full p-6 rounded-3xl bg-gray-50 border-2 border-gray-100 focus:border-secondary focus:ring-4 focus:ring-secondary/10 transition-all font-medium text-lg min-h-[200px] resize-none"
                    style={{ userSelect: 'text' }}
                    placeholder="직접 타이핑해서 답변해주세요 (복사/붙여넣기 금지)"
                    value={shortAnswerInput}
                    onChange={(e) => setShortAnswerInput(e.target.value)}
                    onPaste={(e) => { e.preventDefault(); alert("🚫 붙여넣기 금지!"); }}
                    onCopy={(e) => { e.preventDefault(); }}
                    onCut={(e) => { e.preventDefault(); }}
                    autoComplete="off"
                    spellCheck={false}
                  />
                  <button
                    onClick={() => handleShortAnswerSubmit(false)}
                    className="w-full py-5 bg-secondary text-white rounded-3xl font-black text-xl shadow-lg"
                  >
                    답안 제출 & AI 피드백
                  </button>
                </>
              ) : (
                <div className="space-y-6 animate-fadeIn">
                  <div className={`p-8 rounded-[2.5rem] border-2 ${gradingResult.score >= 70 ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'}`}>
                    <h4 className={`text-xl font-black mb-4 ${gradingResult.score >= 70 ? 'text-green-800' : 'text-amber-800'}`}>
                      {gradingResult.score}점 / {gradingResult.score >= 70 ? '통과 🎉' : '아쉬워요 🤔'}
                    </h4>
                    <p className="text-lg font-medium text-gray-700 leading-relaxed">{gradingResult.feedback}</p>
                  </div>
                  <button
                    onClick={moveToNextQuestion}
                    className="w-full py-5 bg-gray-900 text-white rounded-3xl font-black text-xl"
                  >
                    다음 문제로
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="grid gap-4">
              {q.options.map((opt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAnswer(idx)}
                  className="group flex items-center justify-between p-6 rounded-[2rem] border-2 border-gray-50 bg-gray-50/30 hover:border-primary hover:bg-primary/5 transition-all text-left"
                >
                  <span className="font-bold text-text-main group-hover:text-primary">{opt}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (step === 'result' && result) {
    let feedbackData: any = null;
    try {
      feedbackData = JSON.parse(result.feedback);
    } catch {
      // 파싱 실패
    }

    return (
      <div className="max-w-4xl mx-auto space-y-10 animate-fadeIn py-10">
        <div className="bg-white p-12 rounded-[4rem] shadow-2xl border border-gray-100 space-y-10 text-center">
          <div className="space-y-4">
            <div className="inline-block p-4 bg-primary/10 rounded-3xl mb-2"><span className="text-5xl">🏆</span></div>
            <h2 className="text-4xl font-black text-text-main">{selectedStack} 역량 리포트</h2>
          </div>

          <div className="grid grid-cols-3 gap-6">
            <div className="p-6 bg-gradient-to-br from-primary/10 to-primary/5 rounded-[2rem] border border-primary/20">
              <p className="text-xs font-black text-primary/60 uppercase mb-1">Score</p>
              <p className="text-4xl font-black text-primary">{result.score}<span className="text-lg">점</span></p>
            </div>
            <div className="p-6 bg-gradient-to-br from-secondary/10 to-secondary/5 rounded-[2rem] border border-secondary/20">
              <p className="text-xs font-black text-secondary/60 uppercase mb-1">Level</p>
              <p className="text-xl font-black text-secondary">{result.level}</p>
            </div>
            <div className="p-6 bg-gradient-to-br from-gray-100 to-gray-50 rounded-[2rem] border border-gray-200">
              <p className="text-xs font-black text-gray-400 uppercase mb-1">Questions</p>
              <p className="text-xl font-black text-text-main">{correctCount}/{userAnswers.length}</p>
            </div>
          </div>
        </div>

        {feedbackData ? (
          <div className="space-y-6">
            <div className="bg-white p-8 rounded-[2.5rem] shadow-lg border border-gray-100">
              <h3 className="text-xl font-black text-text-main mb-4">📊 종합 평가</h3>
              <p className="text-text-main leading-relaxed text-lg">{feedbackData.summary}</p>
            </div>
            {feedbackData.strengths && (
              <div className="bg-emerald-50 p-8 rounded-[2.5rem] shadow-lg border border-emerald-100">
                <h3 className="text-lg font-black text-emerald-700 mb-4">💪 강점</h3>
                <p className="text-text-main leading-relaxed">{feedbackData.strengths}</p>
              </div>
            )}
            {feedbackData.improvements && (
              <div className="bg-amber-50 p-8 rounded-[2.5rem] shadow-lg border border-amber-100">
                <h3 className="text-lg font-black text-amber-700 mb-4">🎯 개선 포인트</h3>
                <p className="text-text-main leading-relaxed">{feedbackData.improvements}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white p-10 rounded-[3rem] shadow-lg border border-gray-100">
            <p className="text-text-main font-medium leading-relaxed text-lg">"{result.feedback}"</p>
          </div>
        )}

        <div className="flex gap-4">
          <button onClick={() => { setStep('category'); setQuestions([]); setCurrentIdx(0); setUserAnswers([]); setCorrectCount(0); }} className="flex-1 bg-white py-5 rounded-3xl font-black text-text-sub border border-gray-200">
            다른 테스트 하기
          </button>
          <button
            onClick={() => window.location.href = '/#/mypage?tab=test'}
            className="flex-1 bg-primary text-white py-5 rounded-3xl font-black text-lg shadow-xl shadow-primary/20"
          >
            내 성적표 보기
          </button>
        </div>
      </div>
    );
  }

  return null;
};

export default PreTestPage;
