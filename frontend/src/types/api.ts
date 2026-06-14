// Types partagés frontend ↔ backend
// Doivent rester alignés avec les Pydantic models du backend (app/api/v1).

export interface Site {
  id: string;
  name: string;
  code: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string;
  supervision_vendor: string;
}

export interface Point {
  id: string;
  site_id: string;
  equipment_id: string | null;
  external_id: string;
  name: string;
  point_type: string;
  unit: string | null;
  is_active: boolean;
}

export interface Measurement {
  timestamp: string;
  value: number;
  quality: string;
}

export interface Alarm {
  alarm_id: string;
  code: string;
  label: string;
  equipment_name: string;
  criticality: '1_info' | '2_low' | '3_medium' | '4_high' | '5_critical';
  triggered_at: string;
  is_active: boolean;
}

export interface PrioritizedAlarm {
  alarm_id: string;
  rank: number;
  score: number;
  breakdown: {
    criticality: number;
    energy: number;
    frequency: number;
    persistence: number;
    occupancy: number;
  };
}

export interface DiagnoseRequest {
  alarm_code: string;
  alarm_label: string;
  alarm_timestamp: string;
  equipment_name: string;
  equipment_type: string;
  site_name: string;
  recent_measurements?: Record<string, unknown>[];
  weather_current?: Record<string, unknown> | null;
  related_alarms?: Record<string, unknown>[];
}

export interface DiagnoseResponse {
  summary: string;
  raw_response: string;
  sources: Array<{
    source: string;
    score: number;
    snippet: string;
  }>;
  confidence: number;
  latency_ms: number;
  model: string;
  safety_alert: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export type ChatRubric = 'depannage' | 'analyse' | 'energie' | 'plan_action';

export interface EnergyAnalysis {
  period_start: string;
  period_end: string;
  total_kwh: number;
  baseline_kwh: number;
  deviation_pct: number;
  degree_days: number;
  drift_detected: boolean;
}
