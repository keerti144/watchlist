import React, { useState } from 'react';
import { 
  TrendingUp, TrendingDown, Flame, AlertTriangle, Trash2, 
  ArrowUpDown, ShieldAlert, Zap, Layers, Newspaper, ExternalLink
} from 'lucide-react';

export function WatchlistTable({ items, sortMode, setSortMode, onRemoveSymbol, isLoading }) {
  const [expandedNews, setExpandedNews] = useState(null);

  const renderTagPill = (tag) => {
    let style = 'bg-slate-800 text-slate-300 border-slate-700';
    let icon = null;

    if (tag.includes('UNUSUAL_VOLUME') || tag.includes('VOL_SURGE')) {
      style = 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      icon = <Flame className="w-3 h-3 text-amber-400" />;
    } else if (tag === 'CIRCUIT_ALERT') {
      style = 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-bold animate-pulse-subtle';
      icon = <ShieldAlert className="w-3 h-3 text-rose-400" />;
    } else if (tag.includes('VWAP_CROSS')) {
      style = 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30';
      icon = <Zap className="w-3 h-3 text-indigo-400" />;
    } else if (tag === 'EWMA_DRIFT') {
      style = 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      icon = <Layers className="w-3 h-3 text-purple-400" />;
    } else if (tag === 'HIGH_VOLATILITY') {
      style = 'bg-red-500/15 text-red-300 border-red-500/30';
      icon = <AlertTriangle className="w-3 h-3 text-red-400" />;
    }

    return (
      <span
        key={tag}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono border font-medium ${style}`}
      >
        {icon}
        <span>{tag}</span>
      </span>
    );
  };

  const getAttentionColor = (score) => {
    if (score >= 70) return 'text-rose-200';
    if (score >= 40) return 'text-amber-200';
    return 'text-emerald-200';
  };

  const renderModeBadge = (mode) => {
    const normalizedMode = mode === 'live' ? 'live' : 'replay';
    const style = normalizedMode === 'live'
      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/35'
      : 'bg-cyan-500/15 text-cyan-300 border-cyan-500/35';

    return (
      <span
        className={`px-1.5 py-0.5 rounded text-[10px] border font-mono font-semibold ${style}`}
        title={normalizedMode === 'live' ? 'Streaming exchange quotes' : 'Off-hours replay simulation'}
      >
        {normalizedMode.toUpperCase()}
      </span>
    );
  };

  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl border border-slate-800">
      <div className="px-5 py-4 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-slate-200 flex items-center gap-2">
          <span>Smart Watchlist Insights</span>
          <span className="text-xs font-mono font-normal text-slate-400">({items.length} stocks)</span>
        </h3>

        <div className="flex items-center gap-1.5 text-xs font-mono">
          <span className="text-slate-500 mr-1 hidden sm:inline flex items-center gap-1">
            <ArrowUpDown className="w-3.5 h-3.5" /> Sort:
          </span>
          {[
            { id: 'attention', label: 'Attention Score' },
            { id: 'delta', label: 'Session Delta' },
            { id: 'symbol', label: 'Symbol' },
          ].map(s => (
            <button
              key={s.id}
              onClick={() => setSortMode(s.id)}
              className={`px-3 py-1.5 rounded-xl font-medium transition-all ${
                sortMode === s.id
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                  : 'bg-slate-800/80 text-slate-400 hover:bg-slate-700/80 border border-slate-700/60'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-sm">
          <thead>
            <tr className="bg-slate-950/80 text-slate-400 text-xs font-mono uppercase tracking-wider border-b border-slate-800">
              <th className="py-3.5 px-4 font-semibold">Stock Symbol</th>
              <th className="py-3.5 px-4 font-semibold text-right">Price</th>
              <th className="py-3.5 px-4 font-semibold text-right">Session %</th>
              <th className="py-3.5 px-4 font-semibold text-right">VWAP</th>
              <th className="py-3.5 px-4 font-semibold text-right">Volume (z-σ)</th>
              <th className="py-3.5 px-4 font-semibold text-right">EWMA Dev</th>
              <th className="py-3.5 px-4 font-semibold">Attention Score</th>
              <th className="py-3.5 px-4 font-semibold">Anomaly Tags & Live News</th>
              <th className="py-3.5 px-4 font-semibold text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {isLoading && items.length === 0 ? (
              <tr>
                <td colSpan="9" className="py-12 text-center text-slate-500 font-mono">
                  Loading real-time market data & news feeds...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan="9" className="py-12 text-center text-slate-500 font-mono">
                  Watchlist is empty. Search and add stocks above.
                </td>
              </tr>
            ) : (
              items.map(item => {
                const delta = item.session_delta_pct ?? item.delta_pct ?? 0;
                const price = item.current_price || 0;
                const vwap = item.vwap || 0;
                const volume = item.volume || 0;
                const zScore = item.volume_zscore ?? item.vol_ratio ?? 0;
                const ewmaDev = item.ewma_deviation ?? 0;
                const score = item.attention_score || 0;
                const tags = item.anomaly_tags || item.tags || [];
                const news = item.news || [];
                const isStale = item.is_stale;
                const isPositive = delta >= 0;
                const dataMode = item.data_mode || 'replay';

                const flashClass = item.flash === 'green' 
                  ? 'animate-flash-green' 
                  : item.flash === 'red' 
                  ? 'animate-flash-red' 
                  : '';

                const isNewsOpen = expandedNews === item.symbol;

                return (
                  <React.Fragment key={item.symbol}>
                    <tr
                      className={`transition-colors hover:bg-slate-800/40 ${flashClass} ${
                        isStale ? 'opacity-55 bg-slate-900/60' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-100 flex items-center gap-2">
                        <span>{item.symbol}</span>
                        {renderModeBadge(dataMode)}
                        {isStale && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700" title="Tick age > 60s">
                            STALE
                          </span>
                        )}
                        {news.length > 0 && (
                          <button
                            onClick={() => setExpandedNews(isNewsOpen ? null : item.symbol)}
                            className={`p-1 rounded-md transition-colors ${
                              isNewsOpen ? 'bg-indigo-500/30 text-indigo-300' : 'text-slate-500 hover:text-indigo-400 hover:bg-slate-800'
                            }`}
                            title={`Click to view ${news.length} news headlines`}
                          >
                            <Newspaper className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-right font-semibold text-slate-100">
                        Rs. {price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>

                      <td className="py-3.5 px-4 font-mono text-right">
                        <span className={`inline-flex items-center gap-1 font-semibold px-2 py-0.5 rounded-md ${
                          isPositive 
                            ? 'text-emerald-400 bg-emerald-500/10' 
                            : 'text-rose-400 bg-rose-500/10'
                        }`}>
                          {isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                          {isPositive ? '+' : ''}{delta.toFixed(2)}%
                        </span>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-right text-slate-300">
                        <div className="flex flex-col items-end">
                          <span>Rs. {vwap.toFixed(2)}</span>
                          {item.vwap_crossed && (
                            <span className={`text-[10px] font-semibold ${item.vwap_cross_type === 'BULLISH' ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {item.vwap_cross_type} CROSS
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-right">
                        <div className="flex flex-col items-end">
                          <span className="text-slate-200">{volume.toLocaleString('en-IN')}</span>
                          <span className={`text-xs ${zScore >= 2.0 ? 'text-amber-400 font-bold' : 'text-slate-400'}`}>
                            {zScore > 0 ? '+' : ''}{zScore.toFixed(2)}σ
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 font-mono text-right">
                        <span className={`font-medium ${
                          Math.abs(ewmaDev) >= 2.5 ? 'text-purple-400 font-bold' : 'text-slate-300'
                        }`}>
                          {ewmaDev > 0 ? '+' : ''}{ewmaDev.toFixed(2)}σ
                        </span>
                      </td>

                      <td className="py-3.5 px-4 min-w-[140px]">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/50">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                score >= 70 ? 'bg-gradient-to-r from-amber-500 to-rose-500' :
                                score >= 40 ? 'bg-gradient-to-r from-amber-400 to-amber-500' :
                                'bg-gradient-to-r from-emerald-500 to-teal-400'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(5, score))}%` }}
                            />
                          </div>
                          <span className={`font-mono text-xs font-bold w-10 text-right ${getAttentionColor(score)}`}>
                            {score.toFixed(1)}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1 items-center max-w-xs">
                          {tags.length > 0 ? (
                            tags.map(tag => renderTagPill(tag))
                          ) : (
                            <span className="text-slate-600 text-xs font-mono">—</span>
                          )}

                          {news.length > 0 && (
                            <button
                              onClick={() => setExpandedNews(isNewsOpen ? null : item.symbol)}
                              className="text-[11px] font-mono text-indigo-400 hover:underline flex items-center gap-1 ml-1"
                            >
                              <Newspaper className="w-3 h-3" />
                              {news.length} News
                            </button>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={() => onRemoveSymbol(item.symbol)}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title={`Remove ${item.symbol} from Watchlist`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>

                    {/* Expandable News Row */}
                    {isNewsOpen && news.length > 0 && (
                      <tr className="bg-slate-900/90 border-b border-slate-800">
                        <td colSpan="9" className="p-4">
                          <div className="space-y-2 max-w-4xl mx-auto">
                            <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 font-mono uppercase tracking-wider">
                              <Newspaper className="w-4 h-4" />
                              <span>Live Market News for {item.symbol}</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                              {news.map((n, i) => (
                                <a
                                  key={i}
                                  href={n.link || '#'}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="block p-3 rounded-xl bg-slate-950/80 hover:bg-slate-800/80 border border-slate-800/80 hover:border-indigo-500/40 transition-all group"
                                >
                                  <p className="text-xs font-medium text-slate-200 group-hover:text-indigo-300 line-clamp-2 leading-relaxed">
                                    {n.title}
                                  </p>
                                  <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2 font-mono">
                                    <span>{n.publisher || 'Yahoo Finance'}</span>
                                    <ExternalLink className="w-3 h-3 group-hover:text-indigo-400" />
                                  </div>
                                </a>
                              ))}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
