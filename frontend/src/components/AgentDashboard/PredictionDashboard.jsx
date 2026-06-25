import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowClockwise,
  ChartLineUp,
  ClockClockwise,
  Fire,
  Newspaper,
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
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import RatingButtons from "@/components/ui/RatingButtons";
import StatCardGrid from "@/components/ui/stat-card-grid";
import useTickerNews from "@/hooks/useTickerNews";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const TIMEFRAMES = ["1M", "3M", "6M", "12M"];

const TIMEFRAME_LABELS = {
  "1M": "1 Bulan",
  "3M": "3 Bulan",
  "6M": "6 Bulan",
  "12M": "12 Bulan",
};

const getConfidenceVariant = (confidence) => {
  if (confidence === "high") return "default";
  if (confidence === "medium") return "secondary";
  return "outline";
};

const getScoreColor = (score) => {
  if (score >= 80) return "text-cuan";
  if (score >= 65) return "text-chart-1";
  if (score >= 45) return "text-amber-600";
  return "text-loss";
};

const getScoreBg = (score) => {
  if (score >= 80) return "bg-cuan";
  if (score >= 65) return "bg-chart-1";
  if (score >= 45) return "bg-amber-500";
  return "bg-loss/80";
};

const getValuasiBadge = (text) => {
  if (!text) return "secondary";
  const t = text.toLowerCase();
  if (t === "murah" || t === "undervalued" || t === "aset murah" || t === "valuasi murah" || t === "valuasi rendah") return "success";
  if (t === "wajar" || t === "fair value" || t === "valuasi masih rasional" || t === "strong buy") return "default";
  if (t === "buy") return "success";
  if (t === "hold") return "outline";
  if (t === "sell" || t === "mahal" || t === "overvalued" || t === "mahal/perlu cek" || t === "valuasi mahal" || t === "valuasi premium") return "destructive";
  return "secondary";
};

const formatReturn = (value) => {
  if (value === null || value === undefined) return "N/A";
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${Number(value).toFixed(1)}%`;
};

function AgentInsight({ predictions, activeTimeframe }) {
  const topPick = (predictions?.[activeTimeframe] || [])[0];

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3 sm:p-4">
      <div className="flex items-start gap-3">
        <Sparkle className="mt-0.5 hidden h-4 w-4 shrink-0 text-foreground sm:block" />
        <div className="min-w-0 space-y-2">
          <p className="text-xs font-semibold text-foreground sm:text-sm">
            Insight AI Agent — {TIMEFRAME_LABELS[activeTimeframe]}
          </p>
          {topPick ? (
            <p className="text-xs leading-5 text-muted-foreground sm:text-sm">
              Sektor <strong className="text-foreground">{topPick.sector}</strong> diprediksi menjadi yang terkuat dengan return{" "}
              <strong className={topPick.predicted_return >= 0 ? "text-cuan" : "text-loss"}>{formatReturn(topPick.predicted_return)}</strong>. {topPick.rationale}
            </p>
          ) : (
            <p className="text-xs leading-5 text-muted-foreground sm:text-sm">
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
      className={`cursor-pointer border transition-all duration-200 ${
        isSelected
          ? "border-ring bg-muted/30 ring-1 ring-ring"
          : "border-border bg-card hover:border-muted-foreground/30"
      }`}
      onClick={() => onSelect(prediction)}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
              {rank}
            </span>
            <div>
              <p className="text-sm font-semibold text-foreground">{prediction.sector}</p>
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
                (prediction.predicted_return || 0) >= 0 ? "text-cuan" : "text-loss"
              }`}
            >
              {formatReturn(prediction.predicted_return)}
            </p>
            <p className="text-[10px] text-muted-foreground">predicted return</p>
          </div>
        </div>

        <div className="mt-3">
          <Progress
            className="h-1.5 bg-muted"
            value={barWidth}
          />
        </div>

        <div className="mt-2 flex flex-wrap gap-1">
          {(prediction.key_drivers || []).slice(0, 2).map((driver) => (
            <Badge key={driver} className="bg-muted text-[10px] text-muted-foreground hover:!bg-inherit focus:ring-0" variant="secondary">
              {driver}
            </Badge>
          ))}
        </div>

        <div className="mt-2 flex justify-end" onClick={(e) => e.stopPropagation()}>
          <RatingButtons
            agentType="sector_prediction"
            targetId={prediction.sector}
            sector={prediction.sector}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function ScoreBar({ label, value, color }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 text-[10px] text-muted-foreground">{label}</span>
      <div className="h-1.5 flex-1 rounded-full bg-muted">
        <div className={`h-full rounded-full ${color || "bg-muted-foreground/30"}`} style={{ width: `${Math.max(2, Math.min(100, value))}%` }} />
      </div>
      <span className="w-8 text-right text-[10px] font-medium text-foreground">{Math.round(value)}</span>
    </div>
  );
}

function computeScore(value, thresholds) {
  if (value === null || value === undefined) return null;
  for (const [min, score] of thresholds) {
    if (value >= min) return score;
  }
  return thresholds.at(-1)[1];
}
function computeScoreLow(value, thresholds) {
  if (value === null || value === undefined) return null;
  for (const [max, score] of thresholds) {
    if (value <= max) return score;
  }
  return thresholds.at(-1)[1];
}

function computeFundamentalScore(s) {
  const scores = [
    computeScore(s.roe, [[20, 100], [15, 80], [10, 60], [5, 40], [-Infinity, 20]]),
    computeScore(s.revenue_growth, [[20, 100], [10, 80], [5, 60], [0, 40], [-Infinity, 20]]),
    computeScore(s.eps_growth, [[20, 100], [10, 80], [5, 60], [0, 40], [-Infinity, 20]]),
    computeScore(s.dividend_yield, [[5, 100], [3, 80], [1, 60], [0.5, 40], [-Infinity, 20]]),
    computeScoreLow(s.debt_to_equity, [[0.5, 100], [1, 80], [2, 60], [3, 40], [Infinity, 20]]),
  ].filter(v => v !== null);
  return scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
}

function computeValuationScore(s) {
  const scores = [
    computeScoreLow(s.per, [[5, 100], [10, 80], [15, 60], [25, 40], [Infinity, 20]]),
    computeScoreLow(s.pbv, [[1, 100], [1.5, 80], [3, 60], [5, 40], [Infinity, 20]]),
  ].filter(v => v !== null);
  return scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;
}

function StockRecommendationCard({ stock }) {
  const scoring = stock.scoring || {};
  const recText = stock.recommendation || stock.valuation || "-";
  const recBadge = getValuasiBadge(recText);
  const fundScore = stock.fundamental_score ?? scoring.fundamental_score ?? computeFundamentalScore(stock);
  const valScore = stock.valuation_score ?? scoring.valuation_score ?? computeValuationScore(stock);
  const { newsMap, loading, fetchNews } = useTickerNews();
  useEffect(() => { fetchNews(stock.ticker); }, [fetchNews, stock.ticker]);

  return (
    <Card className="border-border bg-card">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-foreground">{stock.ticker}</span>
              <Badge variant={recBadge}>{recText}</Badge>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{stock.rationale || stock.reason}</p>
          </div>
          <div className="text-right">
            <span
              className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-bold text-background ${getScoreBg(stock.score ?? stock.investment_score ?? 0)}`}
            >
              {(stock.score ?? stock.investment_score ?? 0)}/100
            </span>
          </div>
        </div>

        {(stock.fundamental_score || stock.valuation_score || scoring.combined_score || stock.investment_score || fundScore || valScore) && (
          <div className="mt-3 rounded-md bg-muted/50 p-2">
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Skor Detail</p>
            {stock.investment_score && !stock.fundamental_score && !fundScore && (
              <ScoreBar label="Skor Investasi" value={stock.investment_score} color="bg-cuan" />
            )}
            <ScoreBar label="Fundamental" value={fundScore} color="bg-cuan" />
            {scoring.technical_score != null && <ScoreBar label="Teknikal" value={scoring.technical_score} color="bg-chart-1" />}
            <ScoreBar label="Valuasi" value={valScore} color="bg-chart-4" />
            {scoring.macro_sector_fit != null && <ScoreBar label="Makro Fit" value={scoring.macro_sector_fit} color="bg-amber-500" />}
            {scoring.combined_score && (
              <div className="mt-1 flex items-center gap-2 border-t border-border pt-1">
                <span className="w-24 text-[10px] font-semibold text-foreground">Skor Gabungan</span>
                <span className={`text-xs font-bold ${getScoreColor(scoring.combined_score)}`}>{Math.round(scoring.combined_score)}/100</span>
              </div>
            )}
          </div>
        )}

        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5">
          <MetricBadge label="PER" value={stock.per ?? stock.key_metrics?.per} suffix="x" />
          <MetricBadge label="PBV" value={stock.pbv ?? stock.key_metrics?.pbv} suffix="x" />
          <MetricBadge label="ROE" value={stock.roe ?? stock.key_metrics?.roe} suffix="%" />
          <MetricBadge label="Revenue" value={stock.revenue_growth ?? stock.key_metrics?.revenue_growth} suffix="%" />
          <MetricBadge label="Div Yield" value={stock.dividend_yield ?? stock.key_metrics?.dividend_yield} suffix="%" />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {stock.news_sentiment && (
            <Badge
              variant={stock.news_sentiment === "positif" ? "success" : stock.news_sentiment === "netral" ? "secondary" : "danger"}
              className="text-[10px]"
            >
              {stock.news_sentiment === "positif" ? "Berita Positif" : stock.news_sentiment === "netral" ? "Berita Netral" : "Berita Negatif"}
            </Badge>
          )}
          {(stock.risks || []).slice(0, 1).map((risk) => (
            <span key={risk} className="text-[10px] text-muted-foreground">
              ⚠ {risk}
            </span>
          ))}
          {/* {stock.valuation && !stock.news_sentiment && (
            <Badge variant="outline" className="text-[10px]">
              {stock.valuation}
            </Badge>
          )} */}
        </div>

        {stock.key_headline && stock.key_headline !== "Tidak ada berita terbaru" && (
          <div className="mt-2 rounded bg-muted/30 p-2 text-[10px] italic leading-5 text-muted-foreground">
            &ldquo;{stock.key_headline}&rdquo;
          </div>
        )}

        <div className="mt-2 flex items-center justify-end">
          <RatingButtons
            agentType="stock_recommendation"
            targetId={stock.ticker}
            sector={stock.sector}
            ticker={stock.ticker}
          />
        </div>

        {newsMap[stock.ticker]?.length > 0 && (
          <div className="mt-2 space-y-1.5 border-t border-border pt-2">
            <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
              <Newspaper size={11} weight="bold" />
              Berita Terbaru
            </div>
            {newsMap[stock.ticker].slice(0, 4).map((article, i) => (
              <div key={i} className="rounded bg-muted/30 px-2 py-1.5">
                <p className="text-[11px] leading-4 text-foreground">{article.title}</p>
                {article.publisher && (
                  <p className="mt-0.5 text-[9px] text-muted-foreground">{article.publisher}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricBadge({ label, value, suffix }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="rounded-md bg-muted/50 p-1.5 text-center">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="text-xs font-semibold text-foreground">
        {Number(value).toFixed(1)}{suffix}
      </p>
    </div>
  );
}

function LoadingState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <ArrowClockwise className="h-6 w-6 animate-spin text-muted-foreground" />
      <p className="mt-3 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <WarningCircle className="h-8 w-8 text-loss" />
      <p className="mt-3 text-sm font-medium text-foreground">Gagal memuat prediksi</p>
      <p className="mt-1 text-xs text-muted-foreground">{message}</p>
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
  const [isStockModalOpen, setIsStockModalOpen] = useState(false);
  const [loading, setLoading] = useState(() => Object.keys(initCachedPredictions()).length === 0);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockProcessing, setStockProcessing] = useState(null);
  const stockRetryRef = useRef(null);
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
    fetchPredictions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      if (stockRetryRef.current) clearTimeout(stockRetryRef.current);
    };
  }, []);

  const handleSectorSelect = useCallback(async (prediction) => {
    setSelectedSector(prediction);
    setIsStockModalOpen(true);
    setStockProcessing(null);
    if (stockRetryRef.current) clearTimeout(stockRetryRef.current);

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
        setStockProcessing(null);
        lsSet(cacheKey, recs);
        toast.success(`Rekomendasi saham sektor ${prediction.sector} dimuat.`);
      } else if (response.data.processing) {
        setStockProcessing({
          estimated_seconds: response.data.estimated_seconds_remaining || 300,
          run_id: response.data.run_id,
        });
        toast.info(response.data.message || "Data masih diproses...");
        stockRetryRef.current = setTimeout(() => {
          handleSectorSelect(prediction);
        }, 30000);
      } else {
        setStockProcessing(null);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Gagal memuat rekomendasi";
      toast.error(msg);
    } finally {
      setStockLoading(false);
    }
  }, []);

  const currentPredictions = predictions?.[activeTimeframe] || [];
  const statItems = useMemo(() => {
    const totalPredictions = Object.values(predictions || {}).flat().length;
    const highConf = Object.values(predictions || {}).flat().filter((p) => p.confidence === "high").length;
    return [
      { label: "Total Prediksi", value: totalPredictions, description: "Semua timeframe", icon: ChartLineUp },
      { label: "Confidence Tinggi", value: highConf, description: "High confidence", icon: SealCheck },
      { label: "Sektor Dianalisis", value: 12, description: "IDX sektoral", icon: Sparkle },
    ];
  }, [predictions]);

  return (
    <div className="space-y-5">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
          AI Prediction Agent
        </p>
        <h2 className="mt-1.5 text-lg font-semibold text-foreground sm:text-xl">
          Prediksi Sektor & Rekomendasi Saham
        </h2>
        <p className="mt-1 text-xs leading-5 text-muted-foreground sm:text-sm">
          Agent menganalisis data fundamental sektor + kondisi makroekonomi global
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
          <TabsList className="overflow-x-auto w-full flex-nowrap justify-start scrollbar-none">
            {TIMEFRAMES.map((tf) => (
              <TabsTrigger key={tf} value={tf} className="shrink-0">
                {tf === "1M" && <Fire className="mr-1 h-3 w-3 hidden sm:inline-block" />}
                {tf === "3M" && <ChartLineUp className="mr-1 h-3 w-3 hidden sm:inline-block" />}
                {tf === "6M" && <TrendUp className="mr-1 h-3 w-3 hidden sm:inline-block" />}
                {tf === "12M" && <RocketLaunch className="mr-1 h-3 w-3 hidden sm:inline-block" />}
                {TIMEFRAME_LABELS[tf]}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>

      <StatCardGrid items={statItems} columns={3} />

      <AgentInsight activeTimeframe={activeTimeframe} predictions={predictions} />

      {loading ? (
        <LoadingState message="AI agent sedang menganalisis data sektor via Mistral AI..." />
      ) : error ? (
        <ErrorState message={error} onRetry={() => fetchPredictions({ refresh: true })} />
      ) : currentPredictions.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Warning className="h-8 w-8 text-amber-400" />
          <p className="mt-3 text-sm font-medium text-foreground">
            AI Agent Belum Siap
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Data prediksi sektor akan tersedia setelah jadwal generate berikutnya.
            Admin dapat memicu generate manual melalui panel Admin.
          </p>
        </div>
      ) : (
        <>
          <div>
            <h3 className="mb-3 text-sm font-semibold text-foreground">
              Top Sektor — {TIMEFRAME_LABELS[activeTimeframe]}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {currentPredictions.map((pred, idx) => (
                <SectorPredictionCard
                  isSelected={selectedSector?.sector === pred.sector && isStockModalOpen}
                  key={pred.sector}
                  onSelect={handleSectorSelect}
                  prediction={pred}
                  rank={idx + 1}
                />
              ))}
            </div>
          </div>
        </>
      )}

      <div className="flex items-center justify-center gap-3 text-[10px] text-muted-foreground">
        <span>Data diperbarui setiap 4 jam sekali</span>
        <span className="text-border">|</span>
        <span>
          Terakhir diperbarui:{" "}
          {generatedAt
            ? new Date(generatedAt).toLocaleString("id-ID")
            : "-"}
        </span>
      </div>

      <Dialog open={isStockModalOpen} onOpenChange={setIsStockModalOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Rekomendasi Saham — {selectedSector?.sector}</DialogTitle>
            <DialogDescription className="sr-only">
              Daftar rekomendasi saham untuk sektor {selectedSector?.sector}
            </DialogDescription>
          </DialogHeader>

          {stockLoading ? (
            <LoadingState message="Agent sedang menganalisis fundamental saham..." />
          ) : stockProcessing ? (
            <Card className="border-amber-500/20 bg-amber-500/5">
              <CardContent className="flex flex-col items-center py-8 text-center">
                <ClockClockwise className="mb-3 h-8 w-8 text-amber-500" />
                <p className="text-sm font-medium text-amber-600">
                  Batch Agent Sedang Memproses
                </p>
                <p className="mt-2 text-xs text-amber-600/80 max-w-md">
                  Sistem sedang menyusun rekomendasi saham untuk seluruh sektor secara bersamaan.
                  Halaman akan refresh otomatis saat data tersedia.
                </p>
                <div className="mt-4 flex items-center gap-2 text-xs text-amber-600/80">
                  <ArrowClockwise className="h-3 w-3 animate-spin" />
                  Estimasi selesai: ~{Math.ceil(stockProcessing.estimated_seconds / 60)} menit
                </div>
                <p className="mt-1 text-[10px] text-amber-500/60">
                  Run ID: {stockProcessing.run_id}
                </p>
              </CardContent>
            </Card>
          ) : stockRecs.length === 0 ? (
            <Card className="border-border bg-card">
              <CardContent className="flex flex-col items-center py-10">
                <p className="text-sm text-muted-foreground">
                  Belum ada rekomendasi saham untuk sektor ini.
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Rekomendasi akan tersedia setelah scheduler batch selesai dijalankan.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="flex-1 overflow-y-auto pr-2 -mr-2">
              <div className="grid gap-3">
                {stockRecs.map((stock) => (
                  <StockRecommendationCard key={stock.ticker} stock={stock} />
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
