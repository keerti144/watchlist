import React, { useState, useRef, useEffect } from 'react';
import { Plus, Search, CheckCircle2 } from 'lucide-react';

const NSE_SYMBOLS_LIST = [
  "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
  "BHARTIARTL", "SBIN", "KOTAKBANK", "LT", "HINDUNILVR",
  "ITC", "AXISBANK", "ASIANPAINT", "MARUTI", "SUNPHARMA",
  "TITAN", "BAJFINANCE", "ULTRACEMCO", "WIPRO", "HCLTECH",
  "ONGC", "POWERGRID", "NTPC", "COALINDIA", "TATASTEEL",
  "TATAMOTORS", "JSWSTEEL", "ADANIENT", "ADANIPORTS", "M&M",
  "BAJAJFINSV", "NESTLEIND", "GRASIM", "TECHM", "INDUSINDBK",
  "BRITANNIA", "EICHERMOT", "DIVISLAB", "CIPLA", "DRREDDY",
  "BPCL", "HEROMOTOCO", "APOLLOTYRE", "DABUR", "GODREJCP",
  "HDFCLIFE", "SBILIFE", "PIDILITIND", "BEL", "HAL"
];

export function WatchlistControls({ watchlistSymbols, onAddSymbol }) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredSymbols = query.trim() === ''
    ? NSE_SYMBOLS_LIST
    : NSE_SYMBOLS_LIST.filter(s => s.toLowerCase().includes(query.toLowerCase().trim()));

  const handleAdd = (symbol) => {
    onAddSymbol(symbol);
    setQuery('');
    setIsOpen(false);
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-5">
      <div className="relative flex-1 max-w-md" ref={dropdownRef}>
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search 50 NSE stocks (e.g. INFY, SBIN, TCS)..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-900/90 text-slate-100 placeholder-slate-500 text-sm font-medium border border-slate-700/80 focus:outline-none focus:border-emerald-500/80 focus:ring-2 focus:ring-emerald-500/20 transition-all shadow-inner"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs font-bold"
            >
              ✕
            </button>
          )}
        </div>

        {isOpen && (
          <div className="absolute z-30 left-0 right-0 mt-2 max-h-60 overflow-y-auto rounded-xl glass-panel bg-slate-900/95 border border-slate-700 shadow-2xl divide-y divide-slate-800">
            {filteredSymbols.length > 0 ? (
              filteredSymbols.map(sym => {
                const isAdded = watchlistSymbols.includes(sym);
                return (
                  <div
                    key={sym}
                    onClick={() => !isAdded && handleAdd(sym)}
                    className={`flex items-center justify-between px-4 py-2.5 text-sm cursor-pointer transition-colors ${
                      isAdded
                        ? 'bg-slate-800/40 text-slate-500 cursor-not-allowed'
                        : 'hover:bg-emerald-500/10 text-slate-200 hover:text-emerald-300'
                    }`}
                  >
                    <span className="font-mono font-semibold">{sym}</span>
                    {isAdded ? (
                      <span className="flex items-center gap-1 text-xs text-slate-500">
                        <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
                        In Watchlist
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-emerald-400 font-medium">
                        <Plus className="w-3.5 h-3.5" />
                        Add
                      </span>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-3 text-xs text-slate-400 text-center">
                No matching NSE symbols found
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between sm:justify-end gap-3 text-xs text-slate-400 font-mono">
        <div className="px-3 py-2 rounded-xl bg-slate-900/80 border border-slate-800">
          Watching: <span className="text-emerald-400 font-semibold">{watchlistSymbols.length}</span> / 50 Stocks
        </div>
      </div>
    </div>
  );
}
