import React from 'react';
import { Flame, Clock, RefreshCw, Radio, AlertTriangle } from 'lucide-react';

export function SummaryBanner({ data, isPolling, onTogglePolling, onRefresh, asOf }) {
  const { summary, items, server_time } = data;
  
  const effectiveAsOf = asOf || (data.as_of);
  const elapsedSec = server_time && effectiveAsOf ? Math.max(0, server_time - effectiveAsOf) : 3600;

  const formatElapsed = (seconds) => {
    if (seconds < 60) return `${Math.floor(seconds)}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h ago`;
    return `${(seconds / 86400).toFixed(1)}d ago (Long Absence Fallback)`;
  };

  const anomalousCount = items.filter(item => {
    const tags = item.anomaly_tags || item.tags || [];
    return tags.length > 0 || (item.attention_score || 0) >= 40;
  }).length;

  const isLongAbsence = items.some(item => item.is_long_absence);

  return (
    <div className={`relative overflow-hidden rounded-2xl transition-all duration-300 ${
      anomalousCount > 0
        ? 'glass-panel-glow border-amber-500/30'
        : 'glass-panel'
    } p-5 md:p-6 mb-6 shadow-xl`}>
      <div className="absolute -right-12 -top-12 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -left-12 -bottom-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-2 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2.5 text-xs">
            <button
              onClick={onTogglePolling}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full font-medium transition-all ${
                isPolling
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25'
                  : 'bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25'
              }`}
              title={isPolling ? "Click to Pause Polling" : "Click to Resume Polling"}
            >
              <Radio className={`w-3.5 h-3.5 ${isPolling ? 'animate-pulse text-emerald-400' : ''}`} />
              <span>{isPolling ? 'LIVE ENGINE POLLING' : 'POLLING PAUSED'}</span>
            </button>

            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>Baseline: {formatElapsed(elapsedSec)}</span>
            </div>

            {anomalousCount > 0 ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/40 font-semibold animate-pulse-subtle">
                <Flame className="w-3.5 h-3.5 text-amber-400" />
                <span>{anomalousCount} Stock{anomalousCount > 1 ? 's' : ''} Require Attention</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 text-slate-400 border border-slate-700/50">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>All Normal</span>
              </div>
            )}

            {isLongAbsence && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/40 font-semibold">
                <AlertTriangle className="w-3.5 h-3.5 text-purple-400" />
                <span>30d+ Historical Fallback Active</span>
              </div>
            )}
          </div>

          <h2 className="text-lg md:text-xl font-medium text-slate-100 leading-snug tracking-tight">
            {summary}
          </h2>
        </div>

        <div className="flex items-center gap-2 self-end md:self-center">
          <button
            onClick={onRefresh}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 text-slate-200 text-sm font-medium border border-slate-700/80 transition-all shadow-md active:scale-95"
            title="Refresh Insights Now"
          >
            <RefreshCw className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>
    </div>
  );
}
