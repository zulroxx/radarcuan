import { useCallback, useState } from "react";

const LS_KEY = "radarcuan_watchlist";

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch { /* ignore */ }
  return [];
}

function saveWatchlist(tickers) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(tickers));
  } catch { /* quota */ }
}

export default function useWatchlist() {
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

  return { watchlist, add, remove, toggle, isWatched };
}