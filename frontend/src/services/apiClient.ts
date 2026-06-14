// Client API centralisé.
// Toutes les requêtes passent par cette instance Axios.

import axios from 'axios';
import type {
  Alarm,
  DiagnoseRequest,
  DiagnoseResponse,
  EnergyAnalysis,
  Point,
  PrioritizedAlarm,
  Site,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Intercepteur d'erreurs global
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API Error]', error.response?.status, error.response?.data);
    return Promise.reject(error);
  },
);

// ─── Sites ────────────────────────────────────────────────────────────────────
export const sitesApi = {
  list: async (): Promise<Site[]> => {
    const { data } = await apiClient.get<Site[]>('/sites');
    return data;
  },
  get: async (id: string): Promise<Site> => {
    const { data } = await apiClient.get<Site>(`/sites/${id}`);
    return data;
  },
};

// ─── Points ──────────────────────────────────────────────────────────────────
export const pointsApi = {
  list: async (siteId?: string, pointType?: string): Promise<Point[]> => {
    const { data } = await apiClient.get<Point[]>('/points', {
      params: { site_id: siteId, point_type: pointType },
    });
    return data;
  },
  getMeasurements: async (pointId: string, hours = 24) => {
    const { data } = await apiClient.get(`/points/${pointId}/measurements`, {
      params: { hours },
    });
    return data;
  },
};

// ─── Alarmes ─────────────────────────────────────────────────────────────────
export const alarmsApi = {
  listActive: async (): Promise<Alarm[]> => {
    const { data } = await apiClient.get<Alarm[]>('/alarms/active');
    return data;
  },
  dailyActionPlan: async (topN = 10): Promise<PrioritizedAlarm[]> => {
    const { data } = await apiClient.get<PrioritizedAlarm[]>('/alarms/action-plan/daily', {
      params: { top_n: topN },
    });
    return data;
  },
};

// ─── Agent IA ────────────────────────────────────────────────────────────────
export const agentApi = {
  diagnose: async (req: DiagnoseRequest): Promise<DiagnoseResponse> => {
    const { data } = await apiClient.post<DiagnoseResponse>('/agent/diagnose', req, {
      timeout: 60000,
    });
    return data;
  },

  /** Stream du chat avec callback par chunk (SSE). */
  chatStream: async (
    messages: { role: string; content: string }[],
    onChunk: (chunk: string) => void,
    rubric?: string,
  ): Promise<void> => {
    const response = await fetch(`${API_BASE}/agent/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, rubric }),
    });
    if (!response.body) throw new Error('Pas de stream renvoyé par l\'API');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const chunk = line.slice(6);
          if (chunk === '[DONE]') return;
          onChunk(chunk);
        }
      }
    }
  },
};

// ─── Énergie ─────────────────────────────────────────────────────────────────
export const energyApi = {
  analysis: async (days = 30): Promise<EnergyAnalysis> => {
    const { data } = await apiClient.get<EnergyAnalysis>('/energy/analysis', {
      params: { days },
    });
    return data;
  },
  optimizations: async () => {
    const { data } = await apiClient.get('/energy/optimizations');
    return data;
  },
};
