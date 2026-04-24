import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, MessageSquare, BookOpen, Brain,
  Mic, Play, CheckCircle, FileText,
  Map as MapIcon, GraduationCap, ChevronRight,
  Volume2, Sparkles, Send, Layout,
  Info, AlertCircle, Loader2,
  Square, Settings, HelpCircle, History as HistoryIcon,
  LogOut
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  uploadFiles, getSummary, chat, voiceChat,
  generateQuiz, getMindMap, getFlashcards,
  videoToNotes, startInterview, submitInterviewAnswer, nextInterviewQuestion,
  login, register, logout
} from './api';

// --- Types ---
type TabType = 'setup' | 'summary' | 'chat' | 'quizzes' | 'study' | 'interview';

// --- Shared Components ---

const ProcessingIndicator: React.FC<{ message?: string }> = ({ message }) => {
  const [displayMessage, setDisplayMessage] = useState(message || "Analyzing lecture content...");
  
  const messages = [
    "Analyzing lecture content...",
    "Extracting key concepts...",
    "Organizing study notes...",
    "Generating flashcards...",
    "Preparing study summary...",
    "AI is thinking...",
    "Building your knowledge base..."
  ];

  useEffect(() => {
    if (message) {
      setDisplayMessage(message);
      return;
    }
    const interval = setInterval(() => {
      setDisplayMessage(prev => {
        const currentIndex = messages.indexOf(prev);
        return messages[(currentIndex + 1) % messages.length];
      });
    }, 3000);
    return () => clearInterval(interval);
  }, [message]);

  return (
    <div className="processing-indicator animate-fade-in">
      <div className="pulse-ring">
        <Sparkles className="text-white" size={24} />
      </div>
      <div className="space-y-2">
        <p className="text-xl font-semibold text-gradient">{displayMessage}</p>
        <p className="text-sm text-text-muted">Our AI is processing your request with precision.</p>
      </div>
    </div>
  );
};

const SkeletonLoader: React.FC<{ type?: 'text' | 'card' | 'list' }> = ({ type = 'text' }) => {
  if (type === 'card') {
    return (
      <div className="glass-card p-6 space-y-4">
        <div className="skeleton-loader h-6 w-3/4"></div>
        <div className="space-y-2">
          <div className="skeleton-loader h-4 w-full"></div>
          <div className="skeleton-loader h-4 w-full"></div>
          <div className="skeleton-loader h-4 w-2/3"></div>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-2 w-full">
      <div className="skeleton-loader h-4 w-full"></div>
      <div className="skeleton-loader h-4 w-11/12"></div>
      <div className="skeleton-loader h-4 w-4/5"></div>
    </div>
  );
};

const EmptyState: React.FC<{ icon: React.ReactNode, title: string, description: string }> = ({ icon, title, description }) => (
  <div className="empty-state animate-fade-in">
    <div className="mb-4">{icon}</div>
    <h3 className="text-xl font-bold text-text-main">{title}</h3>
    <p className="text-text-muted max-w-xs">{description}</p>
  </div>
);

// --- Advanced UI Components ---

const MindMapNode: React.FC<{ node: any; depth: number }> = ({ node, depth }) => {
  const [isOpen, setIsOpen] = useState(depth < 2);
  const children = node.children || [];

  return (
    <div className={`flex flex-col ${depth > 0 ? 'ml-8 mt-2' : ''} animate-fade-in`}>
      <div className="flex items-start gap-4 group">
        <div className="flex flex-col items-center">
          <div 
            onClick={() => setIsOpen(!isOpen)}
            className={`
              w-10 h-10 rounded-2xl flex items-center justify-center cursor-pointer transition-all duration-500
              ${depth === 0 ? 'bg-primary shadow-primary-glow text-white' : 'bg-surface border border-white/10 group-hover:border-primary/50'}
            `}
          >
            {depth === 0 ? <Brain size={20} /> : children.length > 0 ? (isOpen ? <Square size={12} fill="currentColor" /> : <ChevronRight size={16} />) : <div className="w-2 h-2 rounded-full bg-primary/40 shadow-sm" />}
          </div>
          {isOpen && children.length > 0 && <div className="w-px flex-1 bg-gradient-to-b from-primary/40 to-transparent my-2" />}
        </div>

        <div className="flex-1 py-1">
          <div className="flex flex-col">
            <span 
              onClick={() => setIsOpen(!isOpen)}
              className={`font-bold transition-colors cursor-pointer ${depth === 0 ? 'text-xl text-white' : 'text-lg text-text-main group-hover:text-primary'}`}
            >
              {node.topic || node.title}
            </span>
            {node.details && (
              <span className="text-sm text-text-muted mt-1 leading-relaxed border-l-2 border-white/5 pl-3 py-1 italic">{node.details}</span>
            )}
          </div>
        </div>
      </div>

      {isOpen && children.length > 0 && (
        <div className="flex flex-col">
          {children.map((child: any, idx: number) => (
            <MindMapNode key={idx} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

// --- Main Auth Component ---

const AuthScreen: React.FC<{ onLogin: (user: any) => void }> = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true);
    setError('');
    try {
      if (isLogin) {
        const res = await login(username, password);
        onLogin(res.data);
      } else {
        await register(username, password);
        const res = await login(username, password);
        onLogin(res.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0f172a] p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card max-w-md w-full p-10 space-y-8"
      >
        <div className="text-center space-y-2">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <GraduationCap className="text-primary" size={32} />
          </div>
          <h2 className="text-3xl font-bold text-white">StudyAI</h2>
          <p className="text-text-muted">{isLogin ? 'Welcome back, Scholar' : 'Start your AI learning journey'}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-text-muted">Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)}
              className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 focus:border-primary outline-none transition-all"
              placeholder="shyam_kumar"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-text-muted">Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)}
              className="w-full bg-black/20 border border-white/10 rounded-xl px-4 py-3 focus:border-primary outline-none transition-all"
              placeholder="••••••••"
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button 
            type="submit" 
            disabled={loading}
            className="w-full button-primary py-4 rounded-xl flex justify-center items-center gap-2 group"
          >
            {loading ? <Loader2 className="animate-spin" size={20} /> : <Sparkles className="group-hover:animate-pulse" size={18} />}
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="text-center">
          <button 
            onClick={() => setIsLogin(!isLogin)} 
            className="text-sm text-primary hover:text-white transition-colors"
          >
            {isLogin ? "Don't have an account? Sign Up" : "Already have an account? Sign In"}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// --- Components ---

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('setup');
  const [isLoaded, setIsLoaded] = useState(false);
  const [user, setUser] = useState<any>(null);

  const handleLogout = async () => {
    if (user?.token) {
      try { await logout(user.token); } catch (e) {}
    }
    setUser(null);
    setIsLoaded(false);
  };

  if (!user) return <AuthScreen onLogin={setUser} />;

  return (
    <div className="dashboard-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">
            <GraduationCap className="text-white" size={20} />
          </div>
          <div className="font-bold text-xl tracking-tight">StudyAI</div>
        </div>
        
        <nav className="nav-links">
          <TabButton icon={<Upload size={20}/>} label="Documents" active={activeTab === 'setup'} onClick={() => setActiveTab('setup')} />
          <TabButton icon={<FileText size={20}/>} label="Summaries" active={activeTab === 'summary'} onClick={() => setActiveTab('summary')} />
          <TabButton icon={<MessageSquare size={20}/>} label="AI Chat" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} />
          <TabButton icon={<CheckCircle size={20}/>} label="Quizzes" active={activeTab === 'quizzes'} onClick={() => setActiveTab('quizzes')} />
          <TabButton icon={<Brain size={20}/>} label="Study Kit" active={activeTab === 'study'} onClick={() => setActiveTab('study')} />
          <TabButton icon={<Mic size={20}/>} label="Interview" active={activeTab === 'interview'} onClick={() => setActiveTab('interview')} />
        </nav>

        <div className="mt-auto pt-8 border-t border-surface-border">
          <TabButton icon={<LogOut size={18}/>} label="Logout" active={false} onClick={handleLogout} />
          <TabButton icon={<Settings size={18}/>} label="Settings" active={false} onClick={() => {}} />
          <TabButton icon={<HelpCircle size={18}/>} label="Help Center" active={false} onClick={() => {}} />
        </div>
      </aside>

      {/* Main Panel */}
      <main className="main-content">
        <header className="top-header">
          <div className="flex items-center gap-2 text-sm text-text-dim">
            <Layout size={14}/>
            <span>Dashboard</span>
            <ChevronRight size={14}/>
            <span className="text-text-main font-medium capitalize">{activeTab}</span>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${isLoaded ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-orange-500/10 text-orange-400 border border-orange-500/20'}`}>
              {isLoaded ? <CheckCircle size={12}/> : <AlertCircle size={12}/>}
              {isLoaded ? 'Docs Loaded' : 'No Docs'}
            </div>
            <div className="w-8 h-8 rounded-full bg-surface-hover border border-surface-border flex items-center justify-center text-xs font-bold uppercase">{user?.username?.[0] || 'U'}</div>
          </div>
        </header>

        <div className="content-area">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, scale: 0.98, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 1.02, y: -10 }}
              transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="h-full"
            >
              {activeTab === 'setup' && <SetupTab onLoaded={() => setIsLoaded(true)} />}
              {activeTab === 'summary' && <SummaryTab isLoaded={isLoaded} />}
              {activeTab === 'chat' && <ChatTab isLoaded={isLoaded} />}
              {activeTab === 'quizzes' && <QuizzesTab isLoaded={isLoaded} />}
              {activeTab === 'study' && <StudyTab isLoaded={isLoaded} />}
              {activeTab === 'interview' && <InterviewTab isLoaded={isLoaded} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

// --- Helper Components ---

const TabButton: React.FC<{ icon: React.ReactNode, label: string, active: boolean, onClick: () => void }> = ({ icon, label, active, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${active ? 'bg-primary text-white shadow-lg shadow-primary-glow' : 'text-text-muted hover:text-white hover:bg-white/5'}`}
  >
    {icon}
    <span className="text-sm font-medium">{label}</span>
  </button>
);

const SetupTab: React.FC<{ onLoaded: () => void }> = ({ onLoaded }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    setUploading(true);
    setLogs(['🚀 Processing documents...']);
    try {
      const res = await uploadFiles(Array.from(e.target.files));
      setLogs(res.data.logs);
      if (res.data.is_loaded) onLoaded();
    } catch (err) {
      setLogs(['❌ Error uploading files. Please try again.']);
    }
    setUploading(false);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h2 className="text-4xl font-bold">Welcome to <span className="text-primary text-glow">StudyAI</span></h2>
        <p className="text-text-muted">Upload your study materials (PDF, DOCX, PPTX) to build your personal knowledge base.</p>
      </div>

      <div className="glass-card p-12 flex flex-col items-center justify-center border-dashed border-2 border-primary/30 hover:border-primary/60 transition-colors cursor-pointer relative group">
        <input
          type="file"
          multiple
          onChange={onFileChange}
          className="absolute inset-0 opacity-0 cursor-pointer"
          accept=".pdf,.docx,.pptx,.txt"
        />
        <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
          {uploading ? <Loader2 className="text-primary animate-spin" size={40} /> : <Upload className="text-primary" size={40} />}
        </div>
        <p className="text-xl font-semibold mb-2">Drop files here or click to browse</p>
        <p className="text-text-muted text-sm">PDF, Word, PowerPoint, Text</p>
      </div>

      {logs.length > 0 && (
        <div className="glass-card p-6 bg-black/40">
          <h3 className="text-sm font-semibold uppercase text-primary mb-4 flex items-center gap-2">
            <Info size={16} /> System Event Log
          </h3>
          <div className="font-mono text-xs space-y-2 max-h-40 overflow-y-auto pr-2">
            {logs.map((log, i) => (
              <div key={i} className="animate-fade-in flex items-start gap-2">
                <span className="text-primary-glow opacity-50">›</span>
                <span>{log}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const SummaryTab: React.FC<{ isLoaded: boolean }> = ({ isLoaded }) => {
  const [level, setLevel] = useState('Normal');
  const [summaries, setSummaries] = useState<{ topic: string, summary: string }[]>([]);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await getSummary(level);
      setSummaries(res.data.summaries);
    } catch (err) { alert('Check documents or server connection.'); }
    setLoading(false);
  };

  if (!isLoaded) return <div className="text-center p-10 text-text-muted">Please upload documents first.</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold mb-2">Auto-Summarization</h2>
          <p className="text-text-muted">Let AI break down your documents into concise, readable summaries.</p>
        </div>
        <div className="flex flex-col items-end gap-4">
          <div className="flex gap-2 p-1 glass rounded-lg">
            {['Brief', 'Normal', 'Detailed'].map(l => (
              <button
                key={l}
                onClick={() => setLevel(l)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${level === l ? 'bg-primary text-white shadow-md' : 'text-text-muted hover:text-white'}`}
              >
                {l}
              </button>
            ))}
          </div>
          <button onClick={generate} disabled={loading} className="button-primary">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
            {loading ? 'Analyzing...' : 'Generate Summaries'}
          </button>
        </div>
      </div>

      <div className="grid gap-6">
        {loading && (
          <div className="space-y-6">
            <SkeletonLoader type="card" />
            <SkeletonLoader type="card" />
            <SkeletonLoader type="card" />
          </div>
        )}

        {!loading && summaries.length === 0 && (
          <EmptyState 
            icon={<FileText size={64} className="text-text-dim" />}
            title="No Summaries Generated"
            description="Select a detail level and click 'Generate Now' to begin auto-summarization."
          />
        )}
        {summaries.map((s, i) => (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            key={i}
            className="glass-card p-10 group"
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-1 h-8 bg-primary rounded-full" />
              <h3 className="text-2xl font-bold group-hover:text-primary transition-colors">{s.topic}</h3>
            </div>
            <div className="text-text-main/90 leading-relaxed text-lg whitespace-pre-wrap">{s.summary}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

const ChatTab: React.FC<{ isLoaded: boolean }> = ({ isLoaded }) => {
  const [messages, setMessages] = useState<{ role: 'user' | 'ai', content: string, audio?: string }[]>([]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const [sending, setSending] = useState(false);

  const sendMsg = async () => {
    if (!input.trim() || sending) return;
    const text = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setSending(true);
    try {
      const res = await chat(text);
      setMessages(prev => [...prev, { role: 'ai', content: res.data.answer }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'ai', content: '⚠️ Server error. Is Ollama running?' }]);
    }
    setSending(false);
  };

  const startRecord = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(stream);
    audioChunks.current = [];
    mediaRecorder.current.ondataavailable = (e) => audioChunks.current.push(e.data);
    mediaRecorder.current.onstop = async () => {
      const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
      setSending(true);
      try {
        const res = await voiceChat(audioBlob);
        setMessages(prev => [...prev,
        { role: 'user', content: `[Voice: ${res.data.user_text}]` },
        { role: 'ai', content: res.data.answer, audio: res.data.audio_url }
        ]);
      } catch (err) { alert('Voice processing failed.'); }
      setSending(false);
    };
    mediaRecorder.current.start();
    setIsRecording(true);
  };

  const stopRecord = () => {
    mediaRecorder.current?.stop();
    setIsRecording(false);
  };

  if (!isLoaded) return <div className="text-center p-10 text-text-muted">Please upload documents first.</div>;

  return (
    <div className="max-w-4xl mx-auto h-[70vh] flex flex-col glass-card relative bg-black/20">
      <div className="flex-1 overflow-y-auto p-10 space-y-8">
        {messages.length === 0 && (
          <EmptyState 
            icon={<MessageSquare size={64} className="text-text-dim" />}
            title="AI Knowledge Partner"
            description="Chat naturally with your documents. Ask questions, request examples, or clarify difficult concepts."
          />
        )}
        {messages.map((m, i) => (
          <motion.div 
            initial={{ opacity: 0, x: m.role === 'user' ? 20 : -20 }}
            animate={{ opacity: 1, x: 0 }}
            key={i} 
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-[85%] p-6 rounded-2xl ${m.role === 'user' ? 'bg-primary text-white shadow-lg shadow-primary-glow border-none' : 'glass-panel border-surface-border'}`}>
              <div className="text-lg leading-relaxed whitespace-pre-wrap">{m.content}</div>
              {m.audio && (
                <button 
                  onClick={() => new Audio(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${m.audio}`).play()} 
                  className="mt-4 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary bg-primary/10 px-3 py-2 rounded-lg hover:bg-primary/20 transition-all"
                >
                  <Volume2 size={14}/> Listen to Response
                </button>
              )}
            </div>
          </motion.div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="glass-panel p-4 flex items-center gap-3 italic text-text-muted">
              <Loader2 className="animate-spin text-primary" size={16}/> AI is formulating an answer...
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-6 border-t border-surface-border">
        <div className="flex items-center gap-4">
          {isRecording ? (
            <button
              onClick={stopRecord}
              className="p-4 rounded-full bg-red-500 animate-pulse text-white shadow-lg shadow-red-500/20"
              title="Stop Recording"
            >
              <Square fill="currentColor" size={24} />
            </button>
          ) : (
            <button
              onClick={startRecord}
              className="p-4 rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-all"
              title="Start Recording"
            >
              <Mic size={24} />
            </button>
          )}
          <div className="flex-1 relative">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMsg()}
              placeholder="Type your message..."
              className="w-full bg-black/30 border border-surface-border rounded-xl px-6 py-4 focus:outline-none focus:border-primary transition-all pr-16"
            />
            <button onClick={sendMsg} className="absolute right-3 top-3 p-2 text-primary hover:text-white transition-colors">
              <Send size={24} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const QuizzesTab: React.FC<{ isLoaded: boolean }> = ({ isLoaded }) => {
  const [topic, setTopic] = useState('all topics');
  const [num, setNum] = useState(5);
  const [difficulty, setDifficulty] = useState('medium');
  const [quizzes, setQuizzes] = useState<any[]>([]);
  const [flashcards, setFlashcards] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const genQuizzes = async () => {
    setLoading(true);
    try {
      const res = await generateQuiz(topic, num, difficulty);
      setQuizzes(res.data.quizzes);
    } catch (err) { alert('Quiz generation failed.'); }
    setLoading(false);
  };

  const genCards = async () => {
    setLoading(true);
    setFlashcards([]);
    try {
      const res = await getFlashcards(10);
      setFlashcards(res.data.flashcards);
    } catch (err) { alert('Flashcard generation failed.'); }
    setLoading(false);
  };

  if (!isLoaded) return <div className="text-center p-10 text-text-muted">Please upload documents first.</div>;

  return (
    <div className="grid grid-cols-2 gap-12">
      <div className="space-y-6">
        <div className="glass-card p-8">
          <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <CheckCircle className="text-primary" /> MCQs Quiz
          </h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs uppercase font-bold text-text-muted mb-2 block">Topic</label>
              <input value={topic} onChange={e => setTopic(e.target.value)} className="w-full bg-black/20 border border-surface-border p-3 rounded-lg" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs uppercase font-bold text-text-muted mb-2 block">Count</label>
                <input type="number" value={num} onChange={e => setNum(parseInt(e.target.value))} className="w-full bg-black/20 border border-surface-border p-3 rounded-lg" />
              </div>
              <div>
                <label className="text-xs uppercase font-bold text-text-muted mb-2 block">Difficulty</label>
                <select value={difficulty} onChange={e => setDifficulty(e.target.value)} className="w-full bg-black/20 border border-surface-border p-3 rounded-lg">
                  <option>easy</option>
                  <option>medium</option>
                  <option>hard</option>
                </select>
              </div>
            </div>
            <button onClick={genQuizzes} disabled={loading} className="button-primary w-full justify-center mt-4 py-4 text-lg">
              {loading ? <Loader2 className="animate-spin" /> : <Sparkles size={18} />}
              Generate Quiz
            </button>
          </div>
        </div>

        {loading && <ProcessingIndicator message="Crafting high-quality questions..." />}
        
        {!loading && quizzes.length === 0 && (
          <EmptyState 
            icon={<AlertCircle size={48} className="text-text-dim" />}
            title="No Quiz Active"
            description="Configure parameters above to start a knowledge check."
          />
        )}

        {quizzes.length > 0 && (
          <div className="space-y-6 mt-8">
            {quizzes.map((q, i) => (
              <div key={i} className="glass-card p-6 border-l-4 border-primary">
                <p className="font-bold mb-4">{q.question}</p>
                <div className="space-y-2">
                  {Object.entries(q.options).map(([k, v]: [string, any]) => (
                    <div key={k} className={`p-3 rounded-lg border text-sm ${k === q.answer ? 'bg-primary/20 border-primary text-primary' : 'bg-white/5 border-white/10'}`}>
                      <span className="font-bold mr-2">{k}:</span> {v}
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-xs italic text-text-muted">{q.explanation}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-6">
        <div className="glass-card p-8">
          <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
            <BookOpen className="text-secondary" /> Flashcards
          </h3>
          <p className="text-text-muted mb-6">Create interactive digital flashcards to test your knowledge retention.</p>
          <button onClick={genCards} disabled={loading} className="button-primary w-full justify-center bg-gradient-to-r from-secondary to-primary border-none shadow-none py-4 text-lg">
            {loading ? <Loader2 className="animate-spin" /> : <Play size={18} />}
            Prepare Deck
          </button>
        </div>

        <div className="grid gap-4 overflow-y-auto max-h-[60vh] pr-2">
          {!loading && flashcards.length === 0 && (
            <EmptyState 
              icon={<Layout size={48} className="text-text-dim" />}
              title="Empty Deck"
              description="Click 'Prepare Cards' to generate key-concept flashcards."
            />
          )}
          {flashcards.map((f, i) => (
            <motion.div
              whileHover={{ scale: 1.02 }}
              key={i}
              className="glass-card p-6 flex flex-col group cursor-pointer relative"
            >
              <div className="text-xs font-bold text-secondary mb-3 uppercase tracking-widest">Flashcard</div>
              <div className="text-lg font-semibold mb-2">{f.question}</div>
              <div className="h-0 group-hover:h-auto overflow-hidden group-hover:mt-4 transition-all duration-500 opacity-0 group-hover:opacity-100 flex flex-col border-t border-white/5 pt-0 group-hover:pt-4">
                <div className="text-xs font-bold text-text-muted uppercase tracking-widest mb-1">Answer</div>
                <div className="text-md text-text-main/80 leading-relaxed">{f.answer}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

const StudyTab: React.FC<{ isLoaded: boolean }> = ({ isLoaded }) => {
  const [mm, setMm] = useState<any>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoNotes, setVideoNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const genMm = async () => {
    setLoading(true);
    setMm(null);
    try {
      const res = await getMindMap();
      setMm(res.data.mindmap);
    } catch (err) { alert('MindMap failed.'); }
    setLoading(false);
  };

  const processVid = async () => {
    if (!videoFile) return;
    setLoading(true);
    setVideoNotes('');
    try {
      const res = await videoToNotes(videoFile);
      setVideoNotes(res.data.notes);
    } catch (err) { alert('Video processing failed.'); }
    setLoading(false);
  };

  if (!isLoaded) return <NoDocsPlaceholder />;

  return (
    <div className="grid grid-cols-2 gap-12">
      <div className="space-y-6">
        <div className="glass-card p-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2"><MapIcon size={24} className="text-primary" /> Concept Mapping</h2>
          <p className="text-text-muted mb-6">Visualize the structure of your study material with an AI-generated mind map.</p>
          <button onClick={genMm} className="button-primary w-full justify-center py-4">Rebuild Concept Map</button>
        </div>
        <div className="glass-card p-6 bg-black/40 min-h-[500px] overflow-auto border-t-0 rounded-t-none">
          {loading && <ProcessingIndicator message="Analyzing structural hierarchies..." />}
          {mm ? (
            <div className="p-4">
              <MindMapNode node={mm} depth={0} />
            </div>
          ) : !loading && (
            <EmptyState 
              icon={<MapIcon size={48} className="text-text-dim" />}
              title="No Concept Map"
              description="Construct a visual intelligence map to see how your study topics connect."
            />
          )}
        </div>
      </div>

      <div className="space-y-6">
        <div className="glass-card p-8">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2"><Play size={24} className="text-red-500" /> Video to Notes</h2>
          <p className="text-text-muted mb-4">Upload a lecture video (.mp4) and get detailed study notes automatically.</p>
          <div className="space-y-4">
            <input type="file" accept="video/mp4" onChange={e => setVideoFile(e.target.files?.[0] || null)} className="w-full text-sm" />
            <button onClick={processVid} disabled={!videoFile || loading} className="button-primary w-full justify-center py-4">
              {loading ? <Loader2 className="animate-spin" /> : 'Launch Video Processing'}
            </button>
          </div>
        </div>
        <div className="glass-card p-8 prose prose-invert overflow-auto max-h-[500px] border-t-0 rounded-t-none">
          {loading && <ProcessingIndicator message="Transcribing and analyzing video..." />}
          {videoNotes ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{videoNotes}</ReactMarkdown>
          ) : !loading && (
            <EmptyState 
              icon={<Play size={48} className="text-text-dim" />}
              title="Ready for Transcription"
              description="Upload a video to see detailed notes here."
            />
          )}
        </div>
      </div>
    </div>
  );
};

const InterviewTab: React.FC<{ isLoaded: boolean }> = ({ isLoaded }) => {
  const [session, setSession] = useState<string | null>(null);
  const [question, setQuestion] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [status, setStatus] = useState('Not started');
  const [scoreInfo, setScoreInfo] = useState({ last: 0, avg: 0, feedback: '' });
  const [isAnswering, setIsAnswering] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [loading, setLoading] = useState(false);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);

  const start = async () => {
    setLoading(true);
    try {
      const res = await startInterview();
      setSession(res.data.session_id);
      setQuestion(res.data.question);
      setAudioUrl(res.data.audio_url);
      setStatus('Session Active');
      // Auto play audio
      new Audio(`http://localhost:8000${res.data.audio_url}`).play();
    } catch (err) { alert('Failed to start interview.'); }
    setLoading(false);
  };

  const startRecord = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(stream);
    audioChunks.current = [];
    mediaRecorder.current.ondataavailable = (e) => audioChunks.current.push(e.data);
    mediaRecorder.current.onstop = async () => {
      const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
      setLoading(true);
      try {
        const res = await submitInterviewAnswer(session!, audioBlob);
        setScoreInfo({ last: res.data.score, avg: res.data.average_score, feedback: res.data.feedback });
        setAudioUrl(res.data.audio_url);
        new Audio(`http://localhost:8000${res.data.audio_url}`).play();
        setShowNext(true);
      } catch (err) { alert('Evaluation failed.'); }
      setLoading(false);
    };
    mediaRecorder.current.start();
    setIsAnswering(true);
  };

  const next = async () => {
    setLoading(true);
    try {
      const res = await nextInterviewQuestion(session!);
      setQuestion(res.data.question);
      setAudioUrl(res.data.audio_url);
      new Audio(`http://localhost:8000${res.data.audio_url}`).play();
      setShowNext(false);
      setScoreInfo(p => ({ ...p, feedback: '' }));
    } catch (err) { alert('Next question failed.'); }
    setLoading(false);
  };

  if (!isLoaded) return <NoDocsPlaceholder />;

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="flex justify-between items-center bg-black/40 p-10 rounded-2xl glass-card border-primary/20">
        <div>
          <div className="text-[10px] uppercase font-bold tracking-[0.2em] text-primary mb-2">Interview Protocol</div>
          <div className="text-3xl font-bold flex items-center gap-3">
            {session ? <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"/> : <div className="w-3 h-3 bg-text-dim rounded-full"/>}
            {status}
          </div>
        </div>
        <div className="flex gap-12">
          <div className="text-center">
            <div className="text-[10px] uppercase font-bold tracking-[0.2em] text-text-dim mb-2">Performance Rank</div>
            <div className="text-4xl font-bold text-gradient">{scoreInfo.avg.toFixed(1)}<span className="text-sm font-normal text-text-dim ml-1">/10</span></div>
          </div>
          {!session && (
            <button onClick={start} disabled={loading} className="button-primary px-8 py-4 text-lg">
              {loading ? <Loader2 className="animate-spin" /> : <Mic size={24}/>}
              Begin Evaluation
            </button>
          )}
        </div>
      </div>

      {session && (
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="space-y-10">
          <div className="glass-card p-16 text-center relative overflow-hidden bg-primary/5 border-primary/20">
            <div className="absolute top-4 left-4 text-primary opacity-20"><Volume2 size={48} /></div>
            <h3 className="text-3xl font-medium leading-relaxed italic">"{question}"</h3>
            <div className="mt-8 flex justify-center gap-4">
              <button 
                onClick={() => new Audio(`http://localhost:8000${audioUrl}`).play()} 
                className="button-secondary p-4 rounded-full border-primary/20 hover:border-primary/50 text-primary"
              >
                <Volume2 size={24}/>
              </button>
            </div>
          </div>

          <AnimatePresence>
            {scoreInfo.feedback && (
              <motion.div 
                initial={{ scale: 0.95, opacity: 0 }} 
                animate={{ scale: 1, opacity: 1 }} 
                className="glass-card p-10 bg-green-500/5 border-green-500/20"
              >
                <div className="flex justify-between items-center mb-8">
                  <div className="space-y-1">
                    <h4 className="text-xl font-bold text-green-400">Expert Feedback</h4>
                    <p className="text-xs text-green-400/60 uppercase font-bold tracking-widest">AI Generated Analysis</p>
                  </div>
                  <div className="bg-green-500/20 text-green-400 border border-green-500/40 px-6 py-2 rounded-xl text-xl font-black">
                    SCORE: {scoreInfo.last}
                  </div>
                </div>
                <p className="text-lg text-text-main/90 leading-relaxed italic">"{scoreInfo.feedback}"</p>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex flex-col items-center gap-8 mt-16 pb-12">
            {!showNext ? (
              <div className="flex flex-col items-center gap-6">
                {isAnswering ? (
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={() => mediaRecorder.current?.stop()}
                    className="w-28 h-28 rounded-full flex items-center justify-center bg-red-500 shadow-lg shadow-red-500/40 text-white animate-pulse"
                  >
                    <Square size={40} fill="currentColor" />
                  </motion.button>
                ) : (
                  <motion.button
                    whileTap={{ scale: 0.9 }}
                    onClick={startRecord}
                    className="w-28 h-28 rounded-[2.5rem] flex items-center justify-center bg-primary shadow-primary-glow text-white hover:scale-105 transition-all"
                  >
                    <Mic size={48} />
                  </motion.button>
                )}
                <div className="text-center font-bold text-sm tracking-widest uppercase text-text-main">
                  {isAnswering ? 'Recording In Progress' : 'Start Your Answer'}
                </div>
              </div>
            ) : (
              <button onClick={next} disabled={loading} className="button-primary px-16 py-6 text-2xl font-black rounded-3xl">
                {loading ? <Loader2 className="animate-spin" /> : <>Continue Protocol <ChevronRight size={32}/></>}
              </button>
            )}
            <div className="text-center">
               <p className="text-text-dim text-xs">Standardized protocol active. Feedback generated via local LLM neural network.</p>
             </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

const NoDocsPlaceholder = () => (
  <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto space-y-8 animate-fade-in">
    <div className="w-24 h-24 bg-surface rounded-3xl flex items-center justify-center border border-surface-border">
      <AlertCircle className="text-text-muted" size={48} />
    </div>
    <div className="space-y-4">
      <h3 className="text-3xl font-bold text-gradient">Neural Core Inactive</h3>
      <p className="text-text-muted text-lg">Please initialize the system by uploading your study materials in the **Documents** tab. The AI cannot function without a baseline knowledge set.</p>
    </div>
    <button onClick={() => window.location.reload()} className="button-secondary">
      Refresh Core System
    </button>
  </div>
);

export default App;
