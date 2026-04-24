import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
});

export const uploadFiles = async (files: File[]) => {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  return api.post('/upload', formData);
};

export const getSummary = async (detailLevel: string) => {
  return api.get(`/summary?detail_level=${detailLevel}`);
};

export const chat = async (query: string, history?: string) => {
  const formData = new FormData();
  formData.append('query', query);
  if (history) formData.append('history', history);
  return api.post('/chat', formData);
};

export const voiceChat = async (audioBlob: Blob) => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'voice_input.webm');
  return api.post('/voice-chat', formData);
};

export const generateQuiz = async (topic: string, num: number, difficulty: string) => {
  const formData = new FormData();
  formData.append('topic', topic);
  formData.append('num', num.toString());
  formData.append('difficulty', difficulty);
  return api.post('/quiz', formData);
};

export const getMindMap = async () => {
  return api.get('/mindmap');
};

export const getFlashcards = async (num: number) => {
  return api.get(`/flashcards?num=${num}`);
};

export const videoToNotes = async (file: File) => {
  const formData = new FormData();
  formData.append('video', file);
  return api.post('/video-notes', formData);
};

export const startInterview = async () => {
  return api.post('/interview/start');
};

export const submitInterviewAnswer = async (sessionId: string, audioBlob?: Blob, textAns?: string) => {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  if (audioBlob) formData.append('audio', audioBlob, 'answer.webm');
  if (textAns) formData.append('text_ans', textAns);
  return api.post('/interview/submit', formData);
};

export const nextInterviewQuestion = async (sessionId: string) => {
  const formData = new FormData();
  formData.append('session_id', sessionId);
  return api.post('/interview/next', formData);
};

export const login = async (username: string, password: string) => {
  return api.post('/login', { username, password });
};

export const register = async (username: string, password: string) => {
  return api.post('/register', { username, password });
};

export const logout = async (token: string) => {
  const formData = new FormData();
  formData.append('token', token);
  return api.post('/logout', formData);
};
