import { useCallback, useEffect, useState } from "react";
import {
  ArrowClockwise,
  Article,
  ChartLineUp,
  GlobeHemisphereWest,
  Lightning,
  Newspaper,
  Scroll,
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

const LS_NEWS_KEY = "ihsg_news_analysis";
const CACHE_TTL = 14400000; // 4 jam — semua user share cache backend, hemat API

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

function formatTimeAgo(dateStr) {
  if (!dateStr) return "";
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diff = now - date;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "baru saja";
  if (mins < 60) return `${mins} menit lalu`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} jam lalu`;
  const days = Math.floor(hours / 24);
  return `${days} hari lalu`;
}

function SentimentBadge({ sentiment }) {
  if (!sentiment) return null;
  const isPos = sentiment.includes("positif");
  return (
    <Badge className={`text-[10px] hover:!bg-inherit focus:!ring-0 ${isPos ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
      {isPos ? <TrendUp className="mr-1 h-3 w-3" /> : <TrendDown className="mr-1 h-3 w-3" />}
      {sentiment}
    </Badge>
  );
}

function LoadingState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <ArrowClockwise className="h-7 w-7 animate-spin text-emerald-500" />
      <p className="mt-3 text-sm text-slate-600">{message}</p>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <WarningCircle className="h-9 w-9 text-red-400" />
      <p className="mt-2 text-sm font-medium text-slate-700">Gagal memuat berita</p>
      <p className="mt-1 text-xs text-slate-500">{message}</p>
      <Button className="mt-3" onClick={onRetry} variant="outline">
        <ArrowClockwise className="mr-2 h-4 w-4" />
        Coba Lagi
      </Button>
    </div>
  );
}

function SummaryCard({ icon: Icon, title, summary, variant = "emerald" }) {
  const colorMap = {
    emerald: { border: "border-emerald-200", bg: "bg-emerald-50", text: "text-emerald-800", icon: "text-emerald-600" },
    sky: { border: "border-sky-200", bg: "bg-sky-50", text: "text-sky-800", icon: "text-sky-600" },
    amber: { border: "border-amber-200", bg: "bg-amber-50", text: "text-amber-800", icon: "text-amber-600" },
  };
  const c = colorMap[variant] || colorMap.emerald;

  return (
    <Card className={`border ${c.border} ${c.bg} shadow-none`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {Icon && <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${c.icon}`} weight="fill" />}
          <div className="min-w-0">
            <p className="text-xs font-semibold text-slate-700">{title}</p>
            <p className={`mt-1 text-xs leading-6 ${c.text}`}>{summary}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function NewsItem({ news, index }) {
  const providerColors = {
    Reuters: "bg-blue-100 text-blue-700",
    "Dow Jones": "bg-purple-100 text-purple-700",
    CNBC: "bg-yellow-100 text-yellow-700",
    Bloomberg: "bg-orange-100 text-orange-700",
    TradingView: "bg-slate-100 text-slate-700",
    MarketWatch: "bg-cyan-100 text-cyan-700",
  };
  const provider = news.provider || "TradingView";
  const colorClass = Object.entries(providerColors).find(([key]) =>
    provider.toLowerCase().includes(key.toLowerCase())
  )?.[1] || "bg-slate-100 text-slate-700";

  return (
    <div className="flex gap-3 border-b border-slate-100 pb-3 last:border-0">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[10px] font-bold text-slate-500">
        {index}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-5 text-slate-800">{news.title}</p>
        <div className="mt-1 flex items-center gap-2">
          <Badge className={`text-[9px] hover:!bg-inherit focus:!ring-0 ${colorClass}`}>
            {provider}
          </Badge>
          <span className="text-[9px] text-slate-400">{formatTimeAgo(news.published)}</span>
        </div>
      </div>
    </div>
  );
}

function SectorGainCard({ sector }) {
  const barWidth = Math.min(100, (sector.sentimen === "sangat positif" ? 90 : 65) + Math.random() * 10);
  return (
    <Card className="border-slate-200 bg-white shadow-none">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-950">{sector.sektor}</p>
            {sector.subsektor && (
              <p className="text-[10px] text-slate-500">{sector.subsektor}</p>
            )}
          </div>
          <SentimentBadge sentiment={sector.sentimen} />
        </div>
        <Progress className="mt-2 h-1.5 bg-slate-100" value={barWidth} />
        <p className="mt-2 text-[11px] leading-5 text-slate-600">{sector.alasan}</p>
      </CardContent>
    </Card>
  );
}

function WarningSectorCard({ sector }) {
  return (
    <Card className="border-red-200 bg-red-50/30 shadow-none">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-start gap-2">
          <Warning className="mt-0.5 h-4 w-4 shrink-0 text-red-500" weight="fill" />
          <div>
            <p className="text-sm font-semibold text-slate-950">{sector.sektor}</p>
            <p className="mt-1 text-[11px] leading-5 text-slate-600">{sector.alasan}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function IndicatorCard({ indicator }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs font-semibold text-slate-950">{indicator.nama}</p>
      <p className="mt-1 text-[11px] leading-5 text-slate-600">
        <span className="font-medium text-slate-700">Kondisi: </span>{indicator.kondisi}
      </p>
      <p className="text-[11px] leading-5 text-slate-500">
        <span className="font-medium text-slate-600">Dampak: </span>{indicator.dampak}
      </p>
    </div>
  );
}

export default function NewsAnalysis() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("ringkasan");

  const fetchNews = useCallback(async ({ refresh = false } = {}) => {
    if (!refresh) {
      const cached = lsGet(LS_NEWS_KEY, CACHE_TTL);
      if (cached) {
        setData(cached);
        setLoading(false);
        return;
      }
    }
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE}/news/flow`, {
        params: { refresh },
      });
      if (response.data.success) {
        setData(response.data);
        lsSet(LS_NEWS_KEY, response.data);
        toast.success("Berita & analisis AI berhasil dimuat.");
      } else {
        setError("Gagal memuat berita");
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
    fetchNews();
  }, [fetchNews]);

  // Auto-refresh setiap 4 jam (tidak paksa refresh backend — pakai cache bersama)
  useEffect(() => {
    const interval = setInterval(() => fetchNews({ refresh: false }), CACHE_TTL);
    return () => clearInterval(interval);
  }, [fetchNews]);

  const analysis = data?.analysis || {};
  const newsList = data?.news || [];

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-600">
            AI News Intelligence
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950 sm:text-xl">
            Ringkasan Berita & Analisis Sektor
          </h2>
          <p className="mt-1 text-xs leading-6 text-slate-600 sm:text-sm">
            Agent mengumpulkan berita ekonomi global dan menganalisis dampaknya ke sektor IDX.
          </p>
        </div>
        <LoadingState message="AI agent sedang mengumpulkan & menganalisis berita terkini..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-600">
            AI News Intelligence
          </p>
          <h2 className="mt-2 text-lg font-semibold text-slate-950 sm:text-xl">
            Ringkasan Berita & Analisis Sektor
          </h2>
        </div>
        <ErrorState message={error} onRetry={() => fetchNews({ refresh: true })} />
      </div>
    );
  }

  const sectorsGain = analysis.sektor_diuntungkan || [];
  const sectorsWarn = analysis.sektor_digdaya_waspada || [];
  const indicators = analysis.indikator_kunci || [];

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-600">
          AI News Intelligence
        </p>
        <h2 className="mt-2 text-lg font-semibold text-slate-950 sm:text-xl">
          Ringkasan Berita & Analisis Sektor
        </h2>
        <p className="mt-1 text-xs leading-6 text-slate-600 sm:text-sm">
          Agent mengumpulkan berita ekonomi global dari TradingView dan menganalisis dampaknya ke sektor IDX menggunakan AI.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full sm:w-auto">
          <TabsTrigger value="ringkasan">
            <Scroll className="mr-1.5 h-3.5 w-3.5" />
            Ringkasan & Analisis
          </TabsTrigger>
          <TabsTrigger value="berita">
            <Newspaper className="mr-1.5 h-3.5 w-3.5" />
            Berita Terkini
            {newsList.length > 0 && (
              <span className="ml-1.5 rounded-full bg-sky-100 px-1.5 py-0.5 text-[9px] text-sky-700">
                {newsList.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent className="mt-4 space-y-5" value="ringkasan">
          <div className="grid gap-3 sm:grid-cols-2">
            <SummaryCard
              icon={Scroll}
              title="Ringkasan Berita Terbaru"
              summary={analysis.ringkasan_terbaru || "Tidak ada data"}
              variant="sky"
            />
            <SummaryCard
              icon={Article}
              title="Ringkasan 1 Hari Terakhir"
              summary={analysis.ringkasan_1hari || "Tidak ada data"}
              variant="emerald"
            />
          </div>

          {sectorsGain.length > 0 && (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <TrendUp className="h-4 w-4 text-emerald-600" weight="fill" />
                <h3 className="text-sm font-semibold text-slate-950">
                  Sektor yang Diuntungkan
                </h3>
                <Badge className="bg-emerald-100 text-emerald-700 hover:!bg-emerald-100 focus:!ring-0">
                  {sectorsGain.length} sektor
                </Badge>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {sectorsGain.map((s, i) => (
                  <SectorGainCard key={i} sector={s} />
                ))}
              </div>
            </div>
          )}

          {sectorsWarn.length > 0 && (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Warning className="h-4 w-4 text-amber-600" weight="fill" />
                <h3 className="text-sm font-semibold text-slate-950">
                  Sektor Perlu Diwaspadai
                </h3>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {sectorsWarn.map((s, i) => (
                  <WarningSectorCard key={i} sector={s} />
                ))}
              </div>
            </div>
          )}

          {indicators.length > 0 && (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <GlobeHemisphereWest className="h-4 w-4 text-sky-600" weight="fill" />
                <h3 className="text-sm font-semibold text-slate-950">
                  Indikator Makroekonomi Kunci
                </h3>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {indicators.map((ind, i) => (
                  <IndicatorCard key={i} indicator={ind} />
                ))}
              </div>
            </div>
          )}

          {analysis.rekomendasi_umum && (
            <div className="rounded-lg border border-sky-200 bg-sky-50 p-3 sm:p-4">
              <div className="flex items-start gap-3">
                <Sparkle className="mt-0.5 h-5 w-5 shrink-0 text-sky-600" weight="fill" />
                <div>
                  <p className="text-xs font-semibold text-slate-700">
                    Rekomendasi AI Agent
                  </p>
                  <p className="mt-1 text-xs leading-6 text-sky-800">
                    {analysis.rekomendasi_umum}
                  </p>
                </div>
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent className="mt-4 space-y-4" value="berita">
          <p className="text-xs font-semibold text-slate-700">
            {newsList.length} berita dari TradingView News Flow
          </p>

          {newsList.length === 0 ? (
            <Card className="border-slate-200 bg-white shadow-none">
              <CardContent className="flex flex-col items-center py-10">
                <p className="text-sm text-slate-600">Belum ada berita tersedia.</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-slate-200 bg-white shadow-none">
              <CardContent className="space-y-3 p-4">
                {newsList.slice(0, 20).map((news, i) => (
                  <NewsItem key={i} index={i + 1} news={news} />
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-center gap-3 text-[10px] text-slate-400">
        <span>Data diperbarui setiap 4 jam sekali</span>
        <span className="text-slate-300">|</span>
        <span>
          Terakhir diperbarui:{" "}
          {data?.generated_at
            ? new Date(data.generated_at).toLocaleString("id-ID")
            : "-"}
        </span>
      </div>
    </div>
  );
}
