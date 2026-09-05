import { useState, useEffect, useCallback, useRef } from 'react';

export function useWatchlistPolling(userId = 'default_user', authToken = null) {
  const [isPolling, setIsPolling] = useState(true);
  const [asOf, setAsOf] = useState(null);
  const [sortMode, setSortMode] = useState('attention');
  const [data, setData] = useState({
    summary: 'Loading market insights...',
    items: [],
    as_of: null,
    server_time: Date.now() / 1000,
  });
  const [watchlistSymbols, setWatchlistSymbols] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [lastFetchTime, setLastFetchTime] = useState(Date.now());

  const prevPricesRef = useRef({});

  const authHeaders = useCallback((headers = {}) => ({
    ...headers,
    ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
  }), [authToken]);

  const fetchWatchlist = useCallback(async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`/api/watchlist?user_id=${encodeURIComponent(userId)}`, {
        headers: authHeaders()
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch watchlist`);
      const json = await res.json();
      setWatchlistSymbols(json.symbols || []);
      setIsError(false);
    } catch (err) {
      console.error('Fetch watchlist error:', err);
      setIsError(true);
      setErrorMessage(err.message || 'Connection error to backend server');
    }
  }, [userId, authToken, authHeaders]);

  const fetchInsights = useCallback(async () => {
    if (!authToken) return;
    try {
      let url = `/api/watchlist/insights?user_id=${encodeURIComponent(userId)}&sort=${sortMode}`;
      if (asOf !== null) {
        url += `&as_of=${asOf}`;
      }

      const res = await fetch(url, {
        headers: authHeaders()
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Engine calculation error`);
      const json = await res.json();

      const newItems = (json.items || []).map(item => {
        const prevPrice = prevPricesRef.current[item.symbol];
        let flash = null;
        if (prevPrice !== undefined && prevPrice !== item.current_price) {
          flash = item.current_price > prevPrice ? 'green' : 'red';
        }
        prevPricesRef.current[item.symbol] = item.current_price;
        return { ...item, flash };
      });

      setData({
        summary: json.summary || 'Trading stably within normal baseline.',
        items: newItems,
        as_of: json.as_of,
        server_time: json.server_time,
      });

      setIsError(false);
      setErrorMessage('');
      setLastFetchTime(Date.now());
    } catch (err) {
      console.error('Fetch insights error:', err);
      setIsError(true);
      setErrorMessage(err.message || 'Failed to communicate with backend engine');
    } finally {
      setIsLoading(false);
    }
  }, [userId, sortMode, asOf, authToken, authHeaders]);

  const refreshAll = useCallback(async () => {
    await fetchWatchlist();
    await fetchInsights();
  }, [fetchWatchlist, fetchInsights]);

  useEffect(() => {
    fetchWatchlist();
    fetchInsights();

    if (!isPolling) return;

    const intervalId = setInterval(() => {
      fetchInsights();
    }, 2500);

    return () => clearInterval(intervalId);
  }, [isPolling, fetchWatchlist, fetchInsights]);

  const addSymbol = async (symbol) => {
    const symUpper = symbol.toUpperCase().trim();
    setWatchlistSymbols(prev => [...new Set([...prev, symUpper])]);

    try {
      const res = await fetch('/api/watchlist/add', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ user_id: userId, symbol: symUpper })
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to add symbol');
      }
      await refreshAll();
    } catch (err) {
      alert(err.message);
      await fetchWatchlist();
    }
  };

  const removeSymbol = async (symbol) => {
    const symUpper = symbol.toUpperCase();
    setWatchlistSymbols(prev => prev.filter(s => s !== symUpper));
    setData(prev => ({
      ...prev,
      items: prev.items.filter(item => item.symbol !== symUpper)
    }));

    try {
      const res = await fetch('/api/watchlist/remove', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ user_id: userId, symbol: symUpper })
      });
      if (!res.ok) throw new Error('Failed to remove symbol');
      await refreshAll();
    } catch (err) {
      console.error(err);
      await refreshAll();
    }
  };

  const updateSessionNow = async () => {
    try {
      const res = await fetch('/api/session/update', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ user_id: userId })
      });
      if (res.ok) {
        const json = await res.json();
        setAsOf(json.last_viewed_at);
        await fetchInsights();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return {
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
    lastFetchTime,
    addSymbol,
    removeSymbol,
    updateSessionNow,
    refreshAll
  };
}
