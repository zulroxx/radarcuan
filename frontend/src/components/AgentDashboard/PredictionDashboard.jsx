import { useCallback, useEffect, useState } from "react";
import {
  ArrowClockwise,
  ChartLineUp,
  CurrencyCircleDollar,
  Fire,
  RocketLaunch,
  SealCheck,
  Sparkle,
  TrendDown,
  TrendUp,
  Warning,
  WarningCircle,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const TIMEFRAMES = ["1M", "3M", "6M", "12M"];

const TIMEFRAME_LABELS = {
  "1M": "1 Bulan",
  "3M": "3 Bulan (Kuartal)",
  "6M": "6 Bulan (Semi-Tahunan)",
  "12M": "12 Bulan (Tahunan)",
};

const getConfidenceVariant = (confidence) => {
  if (confidence === "high") return "default";
  if (confidence === "medium") return "secondary";
  return "outline";
};

const getConfidenceColor = (confidence) => {
  if (confidence === "high") return "bg-emerald-500";
  if (confidence === "medium") return "bg-amber-500";
  return "bg-slate-400";
};

const getScoreColor = (score) => {
  if (score >= 80) return "text-emerald-600";
  if (score >= 65) return "text-sky-600";
  if (score >= 45) return "text-amber-600";
  return "text-red-600";
};

const getScoreBg = (score) => {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 65) return "bg-sky-500";
  if (score >= 45) return "bg-amber-500";
  return "bg-red-500";
};

const formatReturn = (value) => {
  if (value === null || value === undefined) return "N/A";
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${Number(value).toFixed(1)}%`;
};

function StatCards({ predictions }) {
  const totalPredictions = Object.values(predictions || {}).flat().length;
  const highConf = Object.values(predictions || {}).flat().filter((p) => p.confidence === "high").length;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Total Prediksi</p>
          <p className="mt-2 text-xl font-semibold text-slate-950 sm:text-2xl">{totalPredictions}</p>
          <p className="mt-1 text-xs text-slate-500">Semua timeframe</p>
        </CardContent>
      </Card>
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Confidence Tinggi</p>
          <p className="mt-2 text-xl font-semibold text-emerald-700 sm:text-2xl">{highConf}</p>
          <p className="mt-1 text-xs text-slate-500">High confidence</p>
        </CardContent>
      </Card>
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Model AI</p>
          <p className="mt-2 text-sm font-semibold text-sky-700 sm:text-base">Mistral AI</p>
          <p className="mt-1 text-xs text-slate-500">LLM Agent</p>
        </CardContent>
      </Card>
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Sektor Dianalisis</p>
          <p className="mt-2 text-xl font-semibold text-slate-950 sm:text-2xl">12</p>
          <p className="mt-1 text-xs text-slate-500">IDX sektoral</p>
        </CardContent>
      </Card>
    </div>
  );
}

function AgentInsight({ predictions, activeTimeframe }) {
  const topPick = (predictions?.[activeTimeframe] || [])[0];

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 sm:p-4">
      <div className="flex items-start gap-3">
        <Sparkle className="mt-0.5 hidden h-5 w-5 shrink-0 text-emerald-700 sm:block" weight="fill" />
        <div className="min-w-0 space-y-2">
          <p className="text-xs font-semibold text-emerald-950 sm:text-sm">
            Insight AI Agent — {TIMEFRAME_LABELS[activeTimeframe]}
          </p>
          {topPick ? (
            <p className="text-xs leading-6 text-emerald-800 sm:text-sm">
              Sektor <strong>{topPick.sector}</strong> diprediksi menjadi yang terkuat dengan return{" "}
              {formatReturn(topPick.predicted_return)}. {topPick.rationale}
            </p>
          ) : (
            <p className="text-xs leading-6 text-emerald-800 sm:text-sm">
              Agent sedang menunggu data untuk menghasilkan prediksi.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function SectorPredictionCard({ prediction, rank, onSelect, isSelected }) {
  const barWidth = Math.max(
    5,
    Math.min(100, ((prediction.predicted_return || 0) + 20) * 2.5)
  );

  return (
    <Card
      className={`cursor-pointer border transition-all duration-200 hover:shadow-md ${
        isSelected
          ? "border-emerald-400 bg-emerald-50/50 ring-1 ring-emerald-400"
          : "border-slate-200 bg-white"
      }`}
      onClick={() => onSelect(prediction)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">
              {rank}
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-950">{prediction.sector}</p>
              <Badge
                className="mt-0.5 text-[10px] hover:!bg-inherit focus:!ring-0"
                variant={getConfidenceVariant(prediction.confidence)}
              >
                {prediction.confidence === "high"
                  ? "High"
                  : prediction.confidence === "medium"
                  ? "Medium"
                  : "Low"}
              </Badge>
            </div>
          </div>
          <div className="text-right">
            <p
              className={`text-lg font-bold tabular-nums ${
                (prediction.predicted_return || 0) >= 0 ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {formatReturn(prediction.predicted_return)}
            </p>
            <p className="text-[10px] text-slate-500">predicted return</p>
          </div>
        </div>

        <div className="mt-3">
          <Progress
            className="h-1.5 bg-slate-100"
            value={barWidth}
          />
        </div>

        <div className="mt-2 flex flex-wrap gap-1">
          {(prediction.key_drivers || []).slice(0, 2).map((driver) => (
            <Badge key={driver} className="bg-slate-100 text-[10px] text-slate-700 hover:!bg-inherit focus:ring-0" variant="secondary">
              {driver}
            </Badge>
          ))}
        </div>

        {isSelected && prediction.rationale && (
          <div className="mt-3 rounded-md bg-white p-2 text-xs leading-5 text-slate-600">
            {prediction.rationale}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StockRecommendationCard({ stock }) {
  return (
    <Card className="border-slate-200 bg-white">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-slate-950">{stock.ticker}</span>
              <Badge
                className={`text-[10px] hover:!bg-inherit focus:!ring-0 ${
                  stock.recommendation === "Strong Buy"
                    ? "bg-emerald-100 text-emerald-800"
                    : stock.recommendation === "Buy"
                    ? "bg-sky-100 text-sky-800"
                    : stock.recommendation === "Hold"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {stock.recommendation}
              </Badge>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-600">{stock.rationale}</p>
          </div>
          <div className="text-right">
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-bold text-white ${getScoreBg(stock.score)}`}
            >
              {stock.score}/100
            </span>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
          <MetricBadge label="PER" value={stock.key_metrics?.per} suffix="x" />
          <MetricBadge label="PBV" value={stock.key_metrics?.pbv} suffix="x" />
          <MetricBadge label="ROE" value={stock.key_metrics?.roe} suffix="%" />
          <MetricBadge label="Revenue" value={stock.key_metrics?.revenue_growth} suffix="%" />
          <MetricBadge label="Div Yield" value={stock.key_metrics?.dividend_yield} suffix="%" />
        </div>

        <div className="mt-3 flex items-center gap-2">
          <Badge
            className={`text-[10px] hover:!bg-inherit focus:!ring-0 ${
              stock.news_sentiment === "positif"
                ? "bg-emerald-100 text-emerald-700"
                : stock.news_sentiment === "netral"
                ? "bg-slate-100 text-slate-600"
                : "bg-red-100 text-red-700"
            }`}
          >
            {stock.news_sentiment === "positif" ? "Berita Positif" : stock.news_sentiment === "netral" ? "Berita Netral" : "Berita Negatif"}
          </Badge>
          {(stock.risks || []).slice(0, 1).map((risk) => (
            <span key={risk} className="text-[10px] text-slate-500">
              ⚠ {risk}
            </span>
          ))}
        </div>

        {stock.key_headline && stock.key_headline !== "Tidak ada berita terbaru" && (
          <div className="mt-2 rounded bg-slate-50 p-2 text-[10px] italic leading-5 text-slate-500">
            "{stock.key_headline}"
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricBadge({ label, value, suffix }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="rounded bg-slate-50 p-1.5 text-center">
      <p className="text-[10px] text-slate-500">{label}</p>
      <p className="text-xs font-semibold text-slate-800">
        {Number(value).toFixed(1)}{suffix}
      </p>
    </div>
  );
}

function LoadingState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <ArrowClockwise className="h-8 w-8 animate-spin text-emerald-500" />
      <p className="mt-4 text-sm text-slate-600">{message}</p>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <WarningCircle className="h-10 w-10 text-red-400" />
      <p className="mt-3 text-sm font-medium text-slate-700">Gagal memuat prediksi</p>
      <p className="mt-1 text-xs text-slate-500">{message}</p>
      <Button className="mt-4" onClick={onRetry} variant="outline">
        <ArrowClockwise className="mr-2 h-4 w-4" />
        Coba Lagi
      </Button>
    </div>
  );
}

const LS_PRED_KEY = "ihsg_sector_preds";
const LS_STOCK_PREFIX = "ihsg_stock_recs_";
const PRED_CACHE_TTL = 3600000;
const STOCK_CACHE_TTL = 1800000;

function lsGet(key, ttl) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const item = JSON.parse(raw);
    if (Date.now() - item.ts > ttl) {
      localStorage.removeItem(key);
      return null;
    }
    return item.data;
  } catch { return null }
}

function lsSet(key, data) {
  try { localStorage.setItem(key, JSON.stringify({ ts: Date.now(), data })) }
  catch { /* quota exceeded */ }
}

function initCachedPredictions() {
  const cached = lsGet(LS_PRED_KEY, PRED_CACHE_TTL);
  return cached?.predictions || {};
}

function initCachedGeneratedAt() {
  const cached = lsGet(LS_PRED_KEY, PRED_CACHE_TTL);
  return cached?.generated_at || null;
}

export default function PredictionDashboard() {
  const [predictions, setPredictions] = useState(initCachedPredictions);
  const [generatedAt, setGeneratedAt] = useState(initCachedGeneratedAt);
  const [activeTimeframe, setActiveTimeframe] = useState("1M");
  const [selectedSector, setSelectedSector] = useState(null);
  const [stockRecs, setStockRecs] = useState([]);
  const [loading, setLoading] = useState(() => Object.keys(initCachedPredictions()).length === 0);
  const [stockLoading, setStockLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPredictions = useCallback(async ({ refresh = false } = {}) => {
    if (!refresh) {
      const cached = lsGet(LS_PRED_KEY, PRED_CACHE_TTL);
      if (cached) {
        setPredictions(cached.predictions || {});
        setGeneratedAt(cached.generated_at);
        return;
      }
    }
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE}/sector/predictions`, {
        params: { refresh },
      });
      if (response.data.success) {
        const data = { predictions: response.data.predictions || {}, generated_at: response.data.generated_at };
        setPredictions(data.predictions);
        setGeneratedAt(data.generated_at);
        lsSet(LS_PRED_KEY, data);
        toast.success("Prediksi sektor berhasil dimuat.");
      } else {
        setError("Gagal memuat prediksi sektor");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Terjadi kesalahan jaringan";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (Object.keys(predictions).length === 0) fetchPredictions();
  }, [fetchPredictions, predictions]);

  useEffect(() => {
    function scheduleNext() {
      const now = new Date();
      const wibOffset = 7 * 60;
      const nowUtcMin = now.getUTCHours() * 60 + now.getUTCMinutes();
      const nowWibMin = (nowUtcMin + wibOffset) % (24 * 60);
      const openMin = 9 * 60;
      const closeMin = 15 * 60;
      let nextEventMin = nowWibMin < openMin ? openMin : nowWibMin < closeMin ? closeMin : openMin + 24 * 60;
      const diffMs = (nextEventMin - nowWibMin) * 60 * 1000;
      return setTimeout(() => {
        fetchPredictions({ refresh: true });
        scheduleNext();
      }, diffMs);
    }
    const timer = scheduleNext();
    return () => clearTimeout(timer);
  }, [fetchPredictions]);

  const handleSectorSelect = useCallback(async (prediction) => {
    setSelectedSector(prediction);
    const cacheKey = LS_STOCK_PREFIX + prediction.sector;
    const cached = lsGet(cacheKey, STOCK_CACHE_TTL);
    if (cached) {
      setStockRecs(cached);
      return;
    }
    setStockLoading(true);
    setStockRecs([]);
    try {
      const response = await axios.get(
        `${API_BASE}/sector/${encodeURIComponent(prediction.sector)}/stocks`,
        { params: { limit: 10 } }
      );
      if (response.data.success) {
        const recs = response.data.recommendations || [];
        setStockRecs(recs);
        lsSet(cacheKey, recs);
        toast.success(`Rekomendasi saham sektor ${prediction.sector} dimuat.`);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Gagal memuat rekomendasi";
      toast.error(msg);
    } finally {
      setStockLoading(false);
    }
  }, []);

  const currentPredictions = predictions?.[activeTimeframe] || [];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-600">
          AI Prediction Agent
        </p>
        <h2 className="mt-2 text-lg font-semibold text-slate-950 sm:text-xl">
          Prediksi Sektor & Rekomendasi Saham
        </h2>
        <p className="mt-1 text-xs leading-6 text-slate-600 sm:text-sm">
          Agent menganalisis data fundamental sektor dan sentimen berita
          menggunakan Mistral AI untuk memprediksi sektor dengan potensi cuan tertinggi.
        </p>
      </div>

      <div className="flex items-center justify-between gap-2">
        <Tabs
          className="w-full"
          value={activeTimeframe}
          onValueChange={(v) => {
            setActiveTimeframe(v);
            setSelectedSector(null);
            setStockRecs([]);
          }}
        >
          <TabsList>
            {TIMEFRAMES.map((tf) => (
              <TabsTrigger key={tf} value={tf}>
                {tf === "1M" && <Fire className="mr-1.5 h-3.5 w-3.5" />}
                {tf === "3M" && <ChartLineUp className="mr-1.5 h-3.5 w-3.5" />}
                {tf === "6M" && <TrendUp className="mr-1.5 h-3.5 w-3.5" />}
                {tf === "12M" && <RocketLaunch className="mr-1.5 h-3.5 w-3.5" />}
                {TIMEFRAME_LABELS[tf]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <StatCards predictions={predictions} />

      <AgentInsight activeTimeframe={activeTimeframe} predictions={predictions} />

      {loading ? (
        <LoadingState message="AI agent sedang menganalisis data sektor via Mistral AI..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetchPredictions({ refresh: true })} />
      ) : currentPredictions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Warning className="h-10 w-10 text-amber-400" />
          <p className="mt-3 text-sm font-medium text-slate-700">
            Belum ada prediksi untuk timeframe {TIMEFRAME_LABELS[activeTimeframe]}
          </p>
          <p className="mt-4 text-xs text-slate-400">Refresh otomatis setiap pukul 09:00 dan 15:00 WIB.</p>
        </div>
      ) : (
        <>
          <div>
            <h3 className="mb-3 text-sm font-semibold text-slate-950">
              Top Sektor — {TIMEFRAME_LABELS[activeTimeframe]}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {currentPredictions.map((pred, idx) => (
                <SectorPredictionCard
                  isSelected={selectedSector?.sector === pred.sector}
                  key={pred.sector}
                  onSelect={handleSectorSelect}
                  prediction={pred}
                  rank={idx + 1}
                />
              ))}
            </div>
          </div>

          {selectedSector && (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <h3 className="text-sm font-semibold text-slate-950">
                  Rekomendasi Saham — {selectedSector.sector}
                </h3>
                <Badge className="bg-emerald-100 text-emerald-800 hover:!bg-emerald-100 focus:!ring-0">
                  Prediksi {formatReturn(selectedSector.predicted_return)}
                </Badge>
              </div>

              {stockLoading ? (
                <LoadingState message="Agent sedang menganalisis fundamental saham..." />
              ) : stockRecs.length === 0 ? (
                <Card className="border-slate-200 bg-white">
                  <CardContent className="flex flex-col items-center py-10">
                    <p className="text-sm text-slate-600">
                      Belum ada rekomendasi saham untuk sektor ini.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-3">
                  {stockRecs.map((stock) => (
                    <StockRecommendationCard key={stock.ticker} stock={stock} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      <div className="flex items-center justify-center gap-3 text-[10px] text-slate-400">
        <span>Data diperbarui setiap 4 jam sekali</span>
        <span className="text-slate-300">|</span>
        <span>
          Terakhir diperbarui:{" "}
          {generatedAt
            ? new Date(generatedAt).toLocaleString("id-ID")
            : "-"}
        </span>
      </div>
    </div>
  );
}
