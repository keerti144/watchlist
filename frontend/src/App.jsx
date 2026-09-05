import React, { useState } from 'react';
import { useWatchlistPolling } from './hooks/useWatchlistPolling';
import { SummaryBanner } from './components/SummaryBanner';
import { TimeTravelBar } from './components/TimeTravelBar';
import { WatchlistControls } from './components/WatchlistControls';
import { WatchlistTable } from './components/WatchlistTable';
import { Activity, AlertTriangle, RefreshCw, Cpu, LogOut, LogIn, UserPlus } from 'lucide-react';

function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submitAuth = async (event) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const res = await fetch(`/api/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name })
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(json.detail || 'Authentication failed');
      onAuthenticated(json);
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 p-4 sm:p-6 md:p-8 flex items-center justify-center">
      <form onSubmit={submitAuth} className="glass-panel w-full max-w-md rounded-2xl p-6 shadow-2xl border border-slate-800 space-y-5">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 shadow-lg shadow-emerald-500/20">
            <Activity className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">Smart Watchlist</h1>
            <p className="text-xs text-slate-400">Sign in to your personal stock list</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-950/70 p-1 border border-slate-800">
          <button
            type="button"
            onClick={() => setMode('login')}
            className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-all ${mode === 'login' ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <LogIn className="w-4 h-4" /> Login
          </button>
          <button
            type="button"
            onClick={() => setMode('register')}
            className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium transition-all ${mode === 'register' ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <UserPlus className="w-4 h-4" /> Register
          </button>
        </div>

        {mode === 'register' && (
          <input
            type="text"
            placeholder="Display name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 text-slate-100 placeholder-slate-500 text-sm border border-slate-700/80 focus:outline-none focus:border-emerald-500/80 focus:ring-2 focus:ring-emerald-500/20"
          />
        )}

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 text-slate-100 placeholder-slate-500 text-sm border border-slate-700/80 focus:outline-none focus:border-emerald-500/80 focus:ring-2 focus:ring-emerald-500/20"
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={6}
          required
          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 text-slate-100 placeholder-slate-500 text-sm border border-slate-700/80 focus:outline-none focus:border-emerald-500/80 focus:ring-2 focus:ring-emerald-500/20"
        />

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded-xl px-3 py-2">{error}</p>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-slate-950 hover:bg-emerald-400 disabled:opacity-60 transition-all"
        >
          {isSubmitting ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create Account'}
        </button>
      </form>
    </div>
  );
}

function AuthenticatedApp({ auth, onLogout }) {
  const {
    isPolling,
    setIsPolling,
    asOf,
    setAsOf,
    sortMode,
    setSortMode,
    data,
    watchlistSymbols,
    isLoading,
    isError,
    errorMessage,
    addSymbol,
    removeSymbol,
    updateSessionNow,
    refreshAll
  } = useWatchlistPolling(auth.user.id, auth.access_token);

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 p-4 sm:p-6 md:p-8 selection:bg-emerald-500 selection:text-slate-950">
      <div className="max-w-7xl mx-auto space-y-6">

        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 shadow-lg shadow-emerald-500/20">
              <Activity className="w-6 h-6 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                  Context-Aware Smart Watchlist
                </h1>
                <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-[11px] font-mono font-semibold">
                  GROWW HACKATHON
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Adaptive EWMA baseline tracking & 5-factor real-time attention scoring
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end sm:self-center text-xs font-mono">
            <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <span>User: <strong className="text-slate-100">{auth.user.name}</strong></span>
            </div>
            <button
              onClick={onLogout}
              className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-rose-300 hover:border-rose-500/40 flex items-center gap-2 transition-all"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </button>
          </div>
        </header>

        {isError && (
          <div className="bg-rose-500/15 border border-rose-500/40 rounded-2xl p-4 flex items-center justify-between gap-3 text-rose-200 shadow-xl animate-pulse-subtle">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0" />
              <div>
                <p className="text-sm font-semibold">Connection Issue</p>
                <p className="text-xs text-rose-300/80 font-mono">{errorMessage || "Unable to communicate with http://localhost:8000 backend server."}</p>
              </div>
            </div>
            <button
              onClick={refreshAll}
              className="px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/40 text-xs font-medium flex items-center gap-1.5 transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        )}

        <SummaryBanner
          data={data}
          isPolling={isPolling}
          onTogglePolling={() => setIsPolling(prev => !prev)}
          onRefresh={refreshAll}
          asOf={asOf}
        />

        <TimeTravelBar
          asOf={data.as_of}
          setAsOf={setAsOf}
          onResetSession={updateSessionNow}
          serverTime={data.server_time}
        />

        <WatchlistControls
          watchlistSymbols={watchlistSymbols}
          onAddSymbol={addSymbol}
        />

        <WatchlistTable
          items={data.items}
          sortMode={sortMode}
          setSortMode={setSortMode}
          onRemoveSymbol={removeSymbol}
          isLoading={isLoading}
        />

        <footer className="pt-6 border-t border-slate-800/60 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 font-mono gap-3">
          <p>© 2026 Context-Aware Smart Watchlist • FastAPI Backend + React Frontend</p>
          <div className="flex items-center gap-4">
            <span>50 Static NSE Symbols</span>
            <span>•</span>
            <span>SQLite Persistence</span>
          </div>
        </footer>

      </div>
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState(() => {
    try {
      const raw = localStorage.getItem('watchlist_auth');
      return raw ? JSON.parse(raw) : null;
    } catch {
      localStorage.removeItem('watchlist_auth');
      return null;
    }
  });

  const handleAuthenticated = (payload) => {
    localStorage.setItem('watchlist_auth', JSON.stringify(payload));
    setAuth(payload);
  };

  const logout = () => {
    localStorage.removeItem('watchlist_auth');
    setAuth(null);
  };

  if (!auth?.access_token || !auth?.user) {
    return <AuthPanel onAuthenticated={handleAuthenticated} />;
  }

  return <AuthenticatedApp auth={auth} onLogout={logout} />;
}
