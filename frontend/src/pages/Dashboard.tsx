import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { AlertTriangle, Flame, Thermometer, Zap, X, Loader2 } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { alarmsApi, energyApi, agentApi } from '../services/apiClient';
import type { DiagnoseResponse } from '../types/api';

function KpiCard({
  icon: Icon, label, value, unit, trend,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string; value: string | number; unit?: string; trend?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <Icon className="h-5 w-5 text-slate-500" />
        {trend && <span className="text-xs text-slate-400">{trend}</span>}
      </div>
      <div className="mt-3">
        <div className="text-2xl font-semibold text-slate-900">
          {value}
          {unit && <span className="ml-1 text-sm font-normal text-slate-500">{unit}</span>}
        </div>
        <div className="text-sm text-slate-500">{label}</div>
      </div>
    </div>
  );
}

function DiagnosticModal({
  alarmId,
  isPending,
  error,
  data,
  onClose,
}: {
  alarmId: string;
  isPending: boolean;
  error: Error | null;
  data: DiagnoseResponse | undefined;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 className="font-semibold text-slate-900">Diagnostic IA — {alarmId}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[70vh] overflow-y-auto p-5">
          {isPending && (
            <div className="flex items-center gap-2 text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyse en cours…
            </div>
          )}
          {error && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              Erreur : {String(error)}
            </div>
          )}
          {data && (
            <div className="space-y-4">
              {data.safety_alert && (
                <div className="rounded-md bg-red-50 p-3 text-sm font-medium text-red-700">
                  ⚠️ Alerte sécurité détectée
                </div>
              )}
              <div className="prose prose-sm max-w-none text-slate-700">
                <ReactMarkdown>{data.raw_response}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function Dashboard() {
  const [diagAlarm, setDiagAlarm] = useState<string | null>(null);

  const diagMutation = useMutation({
    mutationFn: (alarmId: string) =>
      agentApi.diagnose({
        alarm_code: alarmId,
        alarm_label: alarmId,
        alarm_timestamp: new Date().toISOString(),
        equipment_name: 'Équipement GTB',
        equipment_type: 'boiler',
        site_name: 'Bâtiment AER Le Kremlin-Bicêtre',
        context: {},
      }),
  });

  const { data: actionPlan = [] } = useQuery({
    queryKey: ['action-plan'],
    queryFn: () => alarmsApi.dailyActionPlan(10),
    refetchInterval: 60_000,
  });

  const { data: energy } = useQuery({
    queryKey: ['energy-analysis'],
    queryFn: () => energyApi.analysis(30),
  });

  const tempData = Array.from({ length: 24 }, (_, i) => ({
    h: `${i}h`,
    ext: parseFloat((8 + Math.sin(i / 4) * 4).toFixed(1)),
    amb: parseFloat((20 + Math.sin(i / 6) * 1.5).toFixed(1)),
    consigne: 21,
  }));

  function openDiagnostic(alarmId: string) {
    setDiagAlarm(alarmId);
    diagMutation.mutate(alarmId);
  }

  function closeDiagnostic() {
    setDiagAlarm(null);
    diagMutation.reset();
  }

  return (
    <div className="space-y-6 p-6">
      {diagAlarm && (
        <DiagnosticModal
          alarmId={diagAlarm}
          isPending={diagMutation.isPending}
          error={diagMutation.error}
          data={diagMutation.data}
          onClose={closeDiagnostic}
        />
      )}

      <header>
        <h1 className="text-2xl font-bold text-slate-900">Tableau de bord</h1>
        <p className="text-sm text-slate-500">Vue temps réel du site — Coach IA GTB</p>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <KpiCard icon={Thermometer} label="Température moyenne" value="20.4" unit="°C" trend="+0.2 vs hier" />
        <KpiCard
          icon={Flame}
          label="Consommation 30j"
          value={energy ? energy.total_kwh.toFixed(0) : '—'}
          unit="kWh"
          trend={energy ? `${energy.deviation_pct.toFixed(1)}% vs baseline` : '0.0% vs baseline'}
        />
        <KpiCard icon={AlertTriangle} label="Alarmes actives" value={actionPlan.length} trend="Top priorité ci-dessous" />
        <KpiCard
          icon={Zap}
          label="DJU (30j)"
          value={energy ? energy.degree_days.toFixed(0) : '65'}
          unit="DJU"
        />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-200 px-4 py-3">
          <h2 className="font-semibold text-slate-900">📋 Plan d'action du jour</h2>
          <p className="text-xs text-slate-500">
            Alarmes priorisées par criticité × énergie × fréquence × persistance
          </p>
        </header>
        <ul className="divide-y divide-slate-100">
          {actionPlan.length === 0 && (
            <li className="px-4 py-6 text-center text-sm text-slate-500">
              Aucune alarme à traiter — bonne journée !
            </li>
          )}
          {actionPlan.map((alarm) => (
            <li key={alarm.alarm_id} className="flex items-center justify-between px-4 py-3 hover:bg-slate-50">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm font-semibold text-slate-700">#{alarm.rank}</span>
                <div>
                  <div className="font-medium text-slate-900">{alarm.alarm_id}</div>
                  <div className="text-xs text-slate-500">
                    Score : {alarm.score} · crit {alarm.breakdown.criticality} · énergie {alarm.breakdown.energy} · fréq {alarm.breakdown.frequency}
                  </div>
                </div>
              </div>
              <button
                onClick={() => openDiagnostic(alarm.alarm_id)}
                className="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 active:bg-blue-800"
              >
                Diagnostiquer
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 font-semibold text-slate-900">🌡️ Températures (24h)</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={tempData}>
            <XAxis dataKey="h" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip />
            <Line type="monotone" dataKey="ext" stroke="#0ea5e9" name="Extérieur" />
            <Line type="monotone" dataKey="amb" stroke="#f97316" name="Ambiante" />
            <Line type="monotone" dataKey="consigne" stroke="#10b981" strokeDasharray="4 4" name="Consigne" />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}
