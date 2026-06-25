import { useCallback, useRef, useState } from "react";
import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

export default function useTickerNews() {
  const [newsMap, setNewsMap] = useState({});
  const [loading, setLoading] = useState({});
  const loadingRef = useRef({});
  const fetchedRef = useRef({});

  const fetchNews = useCallback(async (ticker) => {
    if (loadingRef.current[ticker] || fetchedRef.current[ticker]) return;
    fetchedRef.current[ticker] = true;
    loadingRef.current[ticker] = true;
    setLoading((prev) => ({ ...prev, [ticker]: true }));
    try {
      const res = await axios.get(`${API_BASE}/stocks/${ticker}/news`, {
        params: { max_articles: 5 },
      });
      if (res.data.success) {
        setNewsMap((prev) => ({ ...prev, [ticker]: res.data.news }));
      } else {
        setNewsMap((prev) => ({ ...prev, [ticker]: [] }));
      }
    } catch {
      setNewsMap((prev) => ({ ...prev, [ticker]: [] }));
    } finally {
      loadingRef.current[ticker] = false;
      setLoading((prev) => ({ ...prev, [ticker]: false }));
    }
  }, []);

  const clearNews = useCallback((ticker) => {
    setNewsMap((prev) => {
      const next = { ...prev };
      delete next[ticker];
      return next;
    });
  }, []);

  return { newsMap, loading, fetchNews, clearNews };
}
