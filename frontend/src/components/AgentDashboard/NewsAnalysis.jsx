import { useCallback, useEffect, useState } from "react";
import {
  Article,
  ArrowSquareOut,
  ChartLineUp,
  GlobeHemisphereWest,
  Lightning,
  Newspaper,
  Scroll,
  Sparkle,
  TrendDown,
  TrendUp,
  Warning,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import RatingButtons from "@/components/ui/RatingButtons";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const LS_NEWS_KEY = "ihsg_news_analysis";
const CACHE_TTL = 14400000;

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
    <Badge className={`text-[10px] hover:!bg-inherit focus:!ring-0 ${isPos ? "bg-cuan/10 text-cuan" : "bg-loss/10 text-loss"}`}>
      {isPos ? <TrendUp className="mr-1 h-3 w-3" /> : <TrendDown className="mr-1 h-3 w-3" />}
      {sentiment}
    </Badge>
  );
}

function SummaryCard({ icon: Icon, title, summary, variant = "emerald", ratingTarget }) {
  const colorMap = {
    emerald: { border: "border-cuan/20", bg: "bg-cuan/5", icon: "text-cuan" },
    sky: { border: "border-chart-1/20", bg: "bg-chart-1/5", icon: "text-chart-1" },
    amber: { border: "border-amber-500/20", bg: "bg-amber-500/5", icon: "text-amber-600" },
  };
  const c = colorMap[variant] || colorMap.emerald;

  return (
    <Card className={`border ${c.border} ${c.bg} shadow-none`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {Icon && <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${c.icon}`} weight="fill" />}
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-foreground">{title}</p>
             <p className="mt-1 text-xs leading-6 text-muted-foreground">{summary}</p>
          </div>
        </div>
        {ratingTarget && (
          <div className="mt-2 flex justify-end">
            <RatingButtons agentType="news_analysis" targetId={ratingTarget} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function NewsItem({ news, index }) {
  const providerColors = {
    Reuters: "bg-chart-1/10 text-chart-1",
    "Dow Jones": "bg-chart-3/10 text-chart-3",
    CNBC: "bg-chart-5/10 text-chart-5",
    Bloomberg: "bg-chart-4/10 text-chart-4",
    TradingView: "bg-muted text-muted-foreground",
    MarketWatch: "bg-cuan/10 text-cuan",
  };
  const provider = news.provider || "TradingView";
  const colorClass = Object.entries(providerColors).find(([key]) =>
    provider.toLowerCase().includes(key.toLowerCase())
  )?.[1] || "bg-muted text-muted-foreground";

  const url = news.url && news.url.startsWith("http") ? news.url : null;

  return (
    <div className="flex gap-3 border-b border-border pb-3 last:border-0">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground">
        {index}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-5 text-foreground">{news.title}</p>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
          <Badge className={`text-[9px] hover:!bg-inherit focus:!ring-0 ${colorClass}`}>
            {provider}
          </Badge>
          <span className="text-[9px] text-muted-foreground">{formatTimeAgo(news.published)}</span>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-0.5 text-[9px] text-chart-1 hover:text-chart-1/80 hover:underline"
            >
              <ArrowSquareOut className="h-3 w-3" weight="bold" />
              Buka
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

function SectorGainCard({ sector }) {
  const hash = [...(sector.sektor || "")].reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const offset = hash % 11;
  const barWidth = Math.min(100, (sector.sentimen === "sangat positif" ? 85 : 60) + offset);
  return (
    <Card className="border-border bg-card shadow-none">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">{sector.sektor}</p>
            {sector.subsektor && (
              <p className="text-[10px] text-muted-foreground">{sector.subsektor}</p>
            )}
          </div>
          <SentimentBadge sentiment={sector.sentimen} />
        </div>
        <Progress className="mt-2 h-1.5 bg-muted" value={barWidth} />
        <p className="mt-2 text-[11px] leading-5 text-muted-foreground">{sector.alasan}</p>
      </CardContent>
    </Card>
  );
}

function WarningSectorCard({ sector }) {
  return (
    <Card className="border-loss/20 bg-loss/5 shadow-none">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-start gap-2">
          <Warning className="mt-0.5 h-4 w-4 shrink-0 text-loss" weight="fill" />
          <div>
            <p className="text-sm font-semibold text-foreground">{sector.sektor}</p>
            <p className="mt-1 text-[11px] leading-5 text-muted-foreground">{sector.alasan}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function IndicatorCard({ indicator }) {
  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <p className="text-xs font-semibold text-foreground">{indicator.nama}</p>
      <p className="mt-1 text-[11px] leading-5 text-muted-foreground">
        <span className="font-medium text-foreground">Kondisi: </span>{indicator.kondisi}
      </p>
      <p className="text-[11px] leading-5 text-muted-foreground">
        <span className="font-medium text-foreground">Dampak: </span>{indicator.dampak}
      </p>
    </div>
  );
}

function SkeletonSummary() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {[1, 2].map((i) => (
        <Card key={i} className="border-border bg-card shadow-none">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="h-5 w-5 animate-pulse rounded bg-muted" />
              <div className="min-w-0 flex-1">
                <div className="h-3 w-32 animate-pulse rounded bg-muted" />
                <div className="mt-2 space-y-1.5">
                  <div className="h-2 w-full animate-pulse rounded bg-muted/50" />
                  <div className="h-2 w-3/4 animate-pulse rounded bg-muted/50" />
                  <div className="h-2 w-5/6 animate-pulse rounded bg-muted/50" />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function NewsAnalysis() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notReady, setNotReady] = useState(false);
  const [activeTab, setActiveTab] = useState("ringkasan");
  const [modelInfo, setModelInfo] = useState(null);

  const fetchNews = useCallback(async () => {
    const cached = lsGet(LS_NEWS_KEY, CACHE_TTL);
    const cachedError = cached?.analysis?.ringkasan_1hari?.startsWith("Gagal") || cached?.analysis?.ringkasan_1hari?.startsWith("Tidak ada");
    if (cached && !cachedError) {
      setData(cached);
      setLoading(false);
      return;
    }
    if (cached && cachedError) {
      localStorage.removeItem(LS_NEWS_KEY);
    }

    setLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/news/flow`);
      if (response.data.success) {
        setData(response.data);
        const hasError = response.data.analysis?.ringkasan_1hari?.startsWith("Gagal") || response.data.analysis?.ringkasan_1hari?.startsWith("Tidak ada");
        if (!hasError) lsSet(LS_NEWS_KEY, response.data);
        try {
          const mResp = await axios.get(`${API_BASE}/fine-tune/stats`);
          if (mResp.data.success) setModelInfo(mResp.data.model);
        } catch { }
      } else {
        setNotReady(true);
      }
    } catch {
      setNotReady(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  const analysis = data?.analysis || {};
  const newsList = data?.news || [];
  const hasAnalysisError =
    analysis.ringkasan_1hari?.startsWith("Gagal") ||
    analysis.ringkasan_1hari?.startsWith("Tidak ada") ||
    analysis.ringkasan_1hari === "Data analysis masih dikumpulkan" ||
    !data?.analysis;

  const header = (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-chart-1">
        AI News Intelligence
      </p>
      <h2 className="mt-2 text-lg font-semibold text-foreground sm:text-xl">
        Ringkasan Berita & Analisis Sektor
      </h2>
      <p className="mt-1 text-xs leading-6 text-muted-foreground sm:text-sm">
        Agent mengumpulkan berita ekonomi global dari TradingView dan menganalisis dampaknya ke sektor IDX menggunakan AI.
      </p>
    </div>
  );

  if (loading) {
    return (
      <div className="space-y-6">
        {header}
        <SkeletonSummary />
      </div>
    );
  }

  if (notReady || !data) {
    return (
      <div className="space-y-6">
        {header}
        <div className="flex flex-col items-center justify-center py-16">
          <Warning className="h-10 w-10 text-amber-500" />
          <p className="mt-3 text-sm font-medium text-foreground">
            AI Agent Belum Siap
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Data analisis berita akan tersedia setelah jadwal generate berikutnya.
            Admin dapat memicu generate manual melalui panel Admin.
          </p>
        </div>
      </div>
    );
  }

  const sectorsGain = (analysis.sektor_diuntungkan || []).map((s) =>
    typeof s === "string" ? { sektor: s, alasan: "", sentimen: "positif", subsektor: "" } : s
  );
  const sectorsWarn = (analysis.sektor_digdaya_waspada || []).map((s) =>
    typeof s === "string" ? { sektor: s, alasan: "" } : s
  );
  const indicators = (analysis.indikator_kunci || []).map((ind) => {
    if (typeof ind === "string") return { nama: ind, kondisi: "", dampak: "" };
    return { nama: ind.nama || ind.indikator || "", kondisi: ind.kondisi || "", dampak: ind.dampak || "" };
  });

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-chart-1">
          AI News Intelligence
        </p>
        <h2 className="mt-2 text-lg font-semibold text-foreground sm:text-xl">
          Ringkasan Berita & Analisis Sektor
        </h2>
        <p className="mt-1 text-xs leading-6 text-muted-foreground sm:text-sm">
          Agent mengumpulkan berita ekonomi global dari TradingView dan menganalisis dampaknya ke sektor IDX menggunakan AI.
        </p>
      </div>

      {hasAnalysisError && (
        <div className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <Warning className="h-4 w-4 shrink-0 text-amber-500" weight="fill" />
          <p className="text-xs text-amber-600">
            Analisis AI sedang mengalami gangguan. Data di bawah adalah data cadangan otomatis.
            Admin dapat melakukan refresh manual melalui panel Admin.
          </p>
        </div>
      )}

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
              <span className="ml-1.5 rounded-full bg-chart-1/10 px-1.5 py-0.5 text-[9px] text-chart-1">
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
              ratingTarget="ringkasan_terbaru"
            />
            <SummaryCard
              icon={Article}
              title="Ringkasan 1 Hari Terakhir"
              summary={analysis.ringkasan_1hari || "Tidak ada data"}
              variant="emerald"
              ratingTarget="ringkasan_1hari"
            />
          </div>

          {sectorsGain.length > 0 && (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <TrendUp className="h-4 w-4 text-cuan" weight="fill" />
                <h3 className="text-sm font-semibold text-foreground">
                  Sektor yang Diuntungkan
                </h3>
                <Badge className="bg-cuan/10 text-cuan">
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
                <h3 className="text-sm font-semibold text-foreground">
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
                <GlobeHemisphereWest className="h-4 w-4 text-chart-1" weight="fill" />
                <h3 className="text-sm font-semibold text-foreground">
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
            <div className="rounded-lg border border-chart-1/20 bg-chart-1/5 p-3 sm:p-4">
              <div className="flex items-start gap-3">
                <Sparkle className="mt-0.5 h-5 w-5 shrink-0 text-chart-1" weight="fill" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-foreground">
                    Rekomendasi AI Agent
                  </p>
                  <p className="mt-1 text-xs leading-6 text-chart-1">
                    {analysis.rekomendasi_umum}
                  </p>
                </div>
              </div>
              <div className="mt-2 flex justify-end">
                <RatingButtons agentType="news_analysis" targetId="rekomendasi_umum" />
              </div>
            </div>
          )}
        </TabsContent>

        <TabsContent className="mt-4 space-y-4" value="berita">
          <p className="text-xs font-semibold text-foreground">
            {newsList.length} berita dari TradingView News Flow
          </p>

          {newsList.length === 0 ? (
            <Card className="border-border bg-card shadow-none">
              <CardContent className="flex flex-col items-center py-10">
                <p className="text-sm text-muted-foreground">Belum ada berita tersedia.</p>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border bg-card shadow-none">
              <CardContent className="space-y-3 p-4">
                {newsList.slice(0, 20).map((news, i) => (
                  <NewsItem key={i} index={i + 1} news={news} />
                ))}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-center gap-3 text-[10px] text-muted-foreground">
        <span>Data diperbarui setiap 4 jam sekali</span>
        {modelInfo && (
          <>
            <span className="text-border">|</span>
            <span>
              Model:{" "}
              {modelInfo.fine_tune_enabled && modelInfo.fine_tuned_model
                ? (modelInfo.fine_tuned_model || "").split(":").slice(-2).join(":") + " (FT)"
                : (modelInfo.base_model || "Mistral").split("/").pop()}
            </span>
          </>
        )}
        <span className="text-border">|</span>
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
