
import React, { createContext, useContext, useState, ReactNode } from 'react';
import { fetchQuestions, analyzeResults, QuestionItem, TestResultAnalysis } from '../api/aiClient';

interface AiContextType {
    questions: QuestionItem[];
    loading: boolean;
    error: string | null;
    lastResult: TestResultAnalysis | null;
    generateTest: (stack: string, difficulty?: string, type?: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'MIXED') => Promise<void>;
    submitTest: (userId: string, stack: string, total: number, correct: number, score: number, projectId?: number, applicationId?: number) => Promise<any>;
    clearError: () => void;
}

const AiContext = createContext<AiContextType | undefined>(undefined);

export const AiProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [questions, setQuestions] = useState<QuestionItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastResult, setLastResult] = useState<TestResultAnalysis | null>(null);

    const generateTest = async (stack: string, difficulty: string = '초급', type: 'MULTIPLE_CHOICE' | 'SHORT_ANSWER' | 'MIXED' = 'MIXED') => {
        setLoading(true);
        setError(null);
        setQuestions([]); // Reset
        try {
            const data = await fetchQuestions(stack, difficulty, type);
            setQuestions(data);
        } catch (e: any) {
            setError(e.message || "Failed to generate test.");
        } finally {
            setLoading(false);
        }
    };

    const submitTest = async (userId: string, stack: string, total: number, correct: number, score: number, projectId?: number, applicationId?: number) => {
        setLoading(true);
        setError(null);
        try {
            // wrong_answers는 현재 수집하지 않으므로 빈 배열 전달
            const result = await analyzeResults(userId, stack, total, correct, score, [], projectId, applicationId);
            setLastResult(result);
            return result; // Add return so ProjectDetailPage can use it
        } catch (e: any) {
            setError(e.message || "Failed to submit test.");
        } finally {
            setLoading(false);
        }
    };

    const clearError = () => setError(null);

    return (
        <AiContext.Provider value={{ questions, loading, error, lastResult, generateTest, submitTest, clearError }}>
            {children}
        </AiContext.Provider>
    );
};

export const useAi = () => {
    const context = useContext(AiContext);
    if (!context) throw new Error('useAi must be used within an AiProvider');
    return context;
};
