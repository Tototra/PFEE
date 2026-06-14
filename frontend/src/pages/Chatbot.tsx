// Interface conversationnelle du Coach IA.
// 4 rubriques : Dépannage, Analyse, Énergie, Plan d'action.
// Streaming des réponses via SSE.

import { Send, Wrench, BarChart3, Zap, ClipboardList } from 'lucide-react';
import { useState } from 'react';
import { agentApi } from '../services/apiClient';
import type { ChatMessage, ChatRubric } from '../types/api';

const RUBRICS: Array<{ id: ChatRubric; label: string; icon: React.ComponentType<{ className?: string }> }> = [
  { id: 'depannage', label: 'Dépannage', icon: Wrench },
  { id: 'analyse', label: 'Analyse', icon: BarChart3 },
  { id: 'energie', label: 'Énergie', icon: Zap },
  { id: 'plan_action', label: "Plan d'action", icon: ClipboardList },
];

const SYSTEM_PROMPTS: Record<ChatRubric, string> = {
  depannage:
    "Tu es un expert CVC. Aide l'utilisateur à diagnostiquer un dysfonctionnement avec questions de clarification ciblées.",
  analyse:
    "Tu es un analyste GTB. Aide l'utilisateur à interpréter les données de supervision avec rigueur.",
  energie:
    "Tu es un expert en performance énergétique du bâtiment. Suggère des optimisations sans dégrader le confort.",
  plan_action:
    "Tu es un coach d'exploitation. Aide l'utilisateur à prioriser ses actions de la journée.",
};

export function Chatbot() {
  const [rubric, setRubric] = useState<ChatRubric>('depannage');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { role: 'user', content: input };
    const newMessages: ChatMessage[] = [
      { role: 'system', content: SYSTEM_PROMPTS[rubric] },
      ...messages,
      userMsg,
    ];
    setMessages([...messages, userMsg]);
    setInput('');
    setLoading(true);
    setStreaming('');

    let accumulator = '';
    try {
      await agentApi.chatStream(
        newMessages,
        (chunk) => {
          accumulator += chunk;
          setStreaming(accumulator);
        },
        rubric,
      );
      setMessages((prev) => [...prev, { role: 'assistant', content: accumulator }]);
      setStreaming('');
    } catch (e) {
      console.error(e);
      setStreaming('');
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '⚠️ Erreur de communication avec l\'IA.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-bold text-slate-900">Coach IA — Chat</h1>
        <p className="text-sm text-slate-500">
          Choisissez une rubrique pour orienter l'expertise du coach
        </p>
      </header>

      {/* Sélecteur de rubrique */}
      <div className="mb-4 flex gap-2">
        {RUBRICS.map((r) => {
          const Icon = r.icon;
          const active = rubric === r.id;
          return (
            <button
              key={r.id}
              onClick={() => setRubric(r.id)}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition ${
                active
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
              }`}
            >
              <Icon className="h-4 w-4" />
              {r.label}
            </button>
          );
        })}
      </div>

      {/* Historique de chat */}
      <div className="flex-1 space-y-4 overflow-y-auto rounded-lg border border-slate-200 bg-white p-4">
        {messages.length === 0 && (
          <p className="text-center text-sm text-slate-500">
            Posez votre question — par exemple : « Alarme de surchauffe chaudière #12, que faire ? »
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-900'
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans text-sm">{m.content}</pre>
            </div>
          </div>
        ))}
        {streaming && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg bg-slate-100 px-4 py-2 text-slate-900">
              <pre className="whitespace-pre-wrap font-sans text-sm">{streaming}</pre>
              <span className="ml-1 animate-pulse">▌</span>
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="mt-4 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Votre question…"
          rows={2}
          className="flex-1 resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          {loading ? '…' : 'Envoyer'}
        </button>
      </div>
    </div>
  );
}
