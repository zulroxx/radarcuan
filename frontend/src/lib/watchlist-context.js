import { createContext, useCallback, useContext, useMemo, useState } from "react";

const LS_KEY = "radarcuan_watchlist";

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch { }
  return [];
}

function saveWatchlist(tickers) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(tickers));
  } catch { }
}

const WatchlistContext = createContext(null);

export function WatchlistProvider({ children }) {
  const [watchlist, setWatchlist] = useState(loadWatchlist);

  const add = useCallback((ticker) => {
    setWatchlist((prev) => {
      if (prev.includes(ticker)) return prev;
      const next = [...prev, ticker];
      saveWatchlist(next);
      return next;
    });
  }, []);

  const remove = useCallback((ticker) => {
    setWatchlist((prev) => {
      const next = prev.filter((t) => t !== ticker);
      saveWatchlist(next);
      return next;
    });
  }, []);

  const toggle = useCallback((ticker) => {
    setWatchlist((prev) => {
      const exists = prev.includes(ticker);
      const next = exists ? prev.filter((t) => t !== ticker) : [...prev, ticker];
      saveWatchlist(next);
      return next;
    });
  }, []);

  const isWatched = useCallback(
    (ticker) => watchlist.includes(ticker),
    [watchlist],
  );

  const value = useMemo(() => ({ watchlist, add, remove, toggle, isWatched }), [watchlist, add, remove, toggle, isWatched]);

  return (
    <WatchlistContext.Provider value={value}>
      {children}
    </WatchlistContext.Provider>
  );
}

export function useWatchlist() {
  const ctx = useContext(WatchlistContext);
  if (!ctx) throw new Error("useWatchlist must be used within WatchlistProvider");
  return ctx;
}
