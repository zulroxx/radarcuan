import { useCallback, useEffect, useRef, useState } from "react";

const AGENT_LABELS = {
  tradingview: "Memperbarui data TradingView...",
  macro: "Memproses indikator makroekonomi...",
  news: "Menambang berita pasar terkini...",
  sector_predictions: "Memprediksi pergerakan sektor...",
  stock_recommendations: "Menyusun rekomendasi saham...",
  order_book: "Mengumpulkan data order book...",
};

const FALLBACK_STATES = [
  "Menganalisis data pasar saham...",
  "Menyinkronkan data antar agent...",
  "Mengkalibrasi model analisis...",
];

const POLL_MS = 15000;
const TYPE_SPEED_MS = 45;
const PAUSE_MS = 1800;
const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

export default function ProcessingStatus() {
  const [processing, setProcessing] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [phraseIdx, setPhraseIdx] = useState(0);
  const [typed, setTyped] = useState("");
  const [phase, setPhase] = useState("typing");
  const mountedRef = useRef(true);
  const pollTimer = useRef(null);
  const animTimer = useRef(null);
  const scheduleNextRef = useRef(null);
  const latestTypedRef = useRef("");
  const latestPhaseRef = useRef("typing");
  const latestAgentRef = useRef(null);
  const latestPhraseIdxRef = useRef(0);

  latestTypedRef.current = typed;
  latestPhaseRef.current = phase;
  latestAgentRef.current = currentAgent;
  latestPhraseIdxRef.current = phraseIdx;

  useEffect(() => {
    mountedRef.current = true;
    const poll = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);
        const res = await fetch(`${API_BASE}/processing-status`, { signal: controller.signal });
        clearTimeout(timeout);
        const data = await res.json();
        if (!mountedRef.current) return;
        setProcessing(data.processing ?? false);
        if (data.agents) {
          const running = Object.entries(data.agents).find(
            ([, info]) => info.status === "running"
          );
          const agent = running ? running[0] : null;
          if (agent !== latestAgentRef.current) {
            setCurrentAgent(agent);
            setTyped("");
            setPhase("typing");
          }
        }
      } catch {}
    };
    poll();
    pollTimer.current = setInterval(poll, POLL_MS);
    return () => {
      mountedRef.current = false;
      clearInterval(pollTimer.current);
      clearTimeout(animTimer.current);
    };
  }, []);

  const getCurrentPhrase = useCallback(() => {
    if (currentAgent && AGENT_LABELS[currentAgent]) {
      return AGENT_LABELS[currentAgent];
    }
    return FALLBACK_STATES[phraseIdx % FALLBACK_STATES.length];
  }, [currentAgent, phraseIdx]);

  scheduleNextRef.current = () => {
    const phrase = getCurrentPhrase();
    const curTypedLen = latestTypedRef.current.length;
    const curPhase = latestPhaseRef.current;
    if (curPhase === "typing" && curTypedLen < phrase.length) {
      animTimer.current = setTimeout(() => {
        if (mountedRef.current) {
          setTyped(phrase.slice(0, curTypedLen + 1));
          setTimeout(() => {
            if (scheduleNextRef.current) scheduleNextRef.current();
          }, 0);
        }
      }, TYPE_SPEED_MS);
    } else if (curPhase === "typing") {
      setPhase("pausing");
      animTimer.current = setTimeout(() => {
        if (mountedRef.current) {
          setPhase("erasing");
          setTyped("");
          setTimeout(() => {
            if (scheduleNextRef.current) scheduleNextRef.current();
          }, 0);
        }
      }, PAUSE_MS);
    } else if (curPhase === "pausing") {
    } else {
      setPhase("typing");
      if (!latestAgentRef.current || !AGENT_LABELS[latestAgentRef.current]) {
        setPhraseIdx((p) => (p + 1) % FALLBACK_STATES.length);
      }
      setTimeout(() => {
        if (scheduleNextRef.current) scheduleNextRef.current();
      }, 50);
    }
  };

  useEffect(() => {
    if (!processing) {
      setTyped("");
      setPhraseIdx(0);
      setPhase("typing");
      setCurrentAgent(null);
      return;
    }
    if (scheduleNextRef.current) scheduleNextRef.current();
    return () => clearTimeout(animTimer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processing, currentAgent]);

  if (!processing) return null;

  return (
    <div className="group relative shrink-0">
      <div className="flex items-center gap-1.5 rounded-md border border-border bg-muted/70 px-2 py-1 text-[10px] font-medium text-muted-foreground backdrop-blur-sm transition-colors hover:bg-muted">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-foreground/40" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-foreground/60" />
        </span>
        <span className="min-w-[4rem] truncate">{typed || <span className="opacity-40">·</span>}</span>
      </div>

      <div className="invisible absolute right-0 top-full z-50 mt-2 w-72 rounded-lg border border-border bg-card p-4 shadow-sm opacity-0 transition-all group-hover:visible group-hover:opacity-100">
        <div className="mb-2 flex items-center gap-2 border-b border-border pb-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-foreground/40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-foreground/60" />
          </span>
          <p className="text-xs font-semibold text-foreground">AI Agent Sedang Memproses</p>
        </div>

        <div className="mb-3 flex items-center gap-3 rounded-md bg-muted/30 px-3 py-2">
          <div className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground">
              {typed || <span className="opacity-40">{'\u00a0'}</span>}
              {phase === "typing" && typed.length > 0 && (
                <span className="ml-0.5 animate-pulse text-foreground">{'\u258c'}</span>
              )}
            </p>
          </div>
        </div>

        <p className="mb-1 text-[11px] leading-relaxed text-muted-foreground">
          {currentAgent && AGENT_LABELS[currentAgent]
            ? `Mengupdate: ${AGENT_LABELS[currentAgent].replace("...", "")}`
            : "Data akan tersedia setelah semua tahapan analisis selesai."}
        </p>

        <div className="mt-2 border-t border-border pt-2">
          <p className="text-[10px] text-muted-foreground/60">
            Polling every {POLL_MS / 1000}s &middot; auto-hides when complete
          </p>
        </div>
      </div>
    </div>
  );
}
