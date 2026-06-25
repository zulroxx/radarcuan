import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowsClockwise,
  CaretDown,
  CaretUp,
  ChartLineUp,
  MagnifyingGlass,
  ShieldWarning,
  Sparkle,
  Star,
  TrendUp,
  WarningCircle,
} from "@phosphor-icons/react";
import axios from "axios";
import { useWatchlist } from "@/lib/watchlist-context";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import StatCardGrid from "@/components/ui/stat-card-grid";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const formatNumber = (value, options = {}) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return Number(value).toLocaleString("id-ID", options);
};

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return `${Number(value).toFixed(1)}%`;
};

const formatRatio = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return `${Number(value).toFixed(1)}x`;
};

const formatMarketCap = (value) => {
  if (!value) return "N/A";
  if (Math.abs(value) >= 1_000_000_000_000) return `Rp${(value / 1_000_000_000_000).toFixed(1)}T`;
  if (Math.abs(value) >= 1_000_000_000) return `Rp${(value / 1_000_000_000).toFixed(1)}M`;
  return `Rp${formatNumber(value, { maximumFractionDigits: 0 })}`;
};

const getScoreVariant = (score) => {
  if (score >= 75) return "default";
  if (score >= 60) return "secondary";
  if (score >= 45) return "outline";
  return "destructive";
};

const getScoreLabel = (score) => {
  if (score >= 75) return "Menarik";
  if (score >= 60) return "Layak";
  if (score >= 45) return "Netral";
  return "Spekulatif";
};

function SummaryCards({ summary, metadata }) {
  const sourceUrl = metadata?.sourceUrl || summary?.sourceUrl;
  const items = [
    { label: "Universe", value: summary?.total || 0, description: "Saham dianalisis agent", icon: ChartLineUp },
    { label: "Skor rata-rata", value: `${summary?.averageScore || 0}/100`, description: "Gabungan valuasi, kualitas, growth", icon: Sparkle },
    { label: "Pembelian kuat", value: summary?.strongBuyCount || 0, description: "Berdasarkan rating TradingView", icon: TrendUp },
    {
      label: "Sumber",
      value: metadata?.screenTitle || summary?.screenTitle || "TradingView Screener",
      description: "Custom screen AKYzoJyg",
      icon: ChartLineUp,
      ...(sourceUrl ? { href: sourceUrl } : {}),
    },
  ];

  return <StatCardGrid items={items} columns={4} />;
}

function AgentInsight({ summary }) {
  const sectors = summary?.topSectors || [];

  return (
    <div className="rounded-md border border-border bg-muted/30 p-3">
      <div className="flex items-start gap-3">
        <Sparkle className="mt-0.5 hidden h-4 w-4 shrink-0 text-foreground sm:block" />
        <div className="min-w-0 space-y-2">
          <div>
            <p className="text-xs font-semibold text-foreground">Ringkasan penting AI agent</p>
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
              {summary?.keyInsight || "Agent sedang menunggu data TradingView untuk dianalisis."}
            </p>
          </div>
          {sectors.length ? (
            <div className="flex flex-wrap gap-1.5">
              {sectors.map((item) => (
                <Badge key={item.sector} className="bg-muted text-muted-foreground hover:bg-muted/80" variant="secondary">
                  {item.sector}: {item.count}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <tr>
      <td colSpan={11} className="h-32 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <ArrowsClockwise className="h-5 w-5 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Mengambil data TradingView dan menjalankan analisis agent...</p>
        </div>
      </td>
    </tr>
  );
}

function EmptyState({ searchQuery }) {
  return (
    <tr>
      <td colSpan={11} className="h-32 text-center">
        <p className="text-sm font-medium text-muted-foreground">
          {searchQuery ? "Tidak ada saham yang cocok dengan pencarian." : "Belum ada data dari TradingView."}
        </p>
      </td>
    </tr>
  );
}

function ReasonList({ title, icon: Icon, items, tone }) {
  return (
    <div className="space-y-1">
      <div className={`flex items-center gap-1.5 text-[11px] font-semibold ${tone === "risk" ? "text-loss" : "text-cuan"}`}>
        <Icon className="h-3 w-3" />
        {title}
      </div>
      <ul className="space-y-0.5">
        {(items || []).slice(0, 2).map((item) => (
          <li key={item} className="text-[11px] leading-5 text-muted-foreground">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

const cellClass =
  "border-b border-border px-3 py-2.5 align-top text-sm";
const stickyLeft = "lg:sticky lg:left-0 z-10 bg-card";
const stickyRight = "lg:sticky lg:right-0 z-10 bg-card";
const stickyRightAlasan = "lg:sticky lg:right-[100px] z-10 bg-card";

function StockRow({ item, onSelect, isWatched, onToggleWatch }) {
  const analysis = item.analysis || {};
  const score = analysis.investmentScore || 0;
  const watched = isWatched?.(item.ticker);

  return (
    <tr className="cursor-pointer border-b border-border hover:bg-muted/30" onClick={() => onSelect?.(item)}>
      <td className={`${cellClass} ${stickyLeft} lg:after:pointer-events-none lg:after:absolute lg:after:inset-y-0 lg:after:right-0 lg:after:w-px lg:after:bg-border`}>
        <div className="flex items-center gap-2">
          <button
            className="-ml-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-muted"
            onClick={(e) => { e.stopPropagation(); onToggleWatch?.(item.ticker); }}
            title={watched ? "Hapus dari watchlist" : "Tambah ke watchlist"}
          >
            <Star className={`h-3.5 w-3.5 ${watched ? "text-amber-400" : "text-muted-foreground/40"}`} weight={watched ? "fill" : "regular"} />
          </button>
          <div className="font-mono text-sm font-semibold text-foreground">{item.ticker}</div>
          <Badge className="px-1.5 py-0 text-[10px]" variant={getScoreVariant(score)}>{getScoreLabel(score)}</Badge>
        </div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">{item.sector}</div>
      </td>
      <td className={`${cellClass} ${stickyLeft} lg:left-[132px] lg:after:pointer-events-none lg:after:absolute lg:after:inset-y-0 lg:after:right-0 lg:after:w-px lg:after:bg-border`}>
        <div className="text-sm font-medium text-foreground">{item.companyName}</div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">{formatMarketCap(item.marketCap)}</div>
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right font-mono tabular-nums text-foreground`}>
        Rp{formatNumber(item.price, { maximumFractionDigits: 0 })}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums font-mono font-medium ${
         item.change >= 0 ? "text-cuan" : "text-loss"
       }`}>
        {formatPercent(item.change)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums font-mono text-muted-foreground`}>
        {formatRatio(item.per)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums font-mono text-muted-foreground`}>
        {formatRatio(item.pbv)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums font-mono text-muted-foreground`}>
        {formatPercent(item.roe)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums font-mono text-muted-foreground`}>
        {formatPercent(item.dividend_yield)}
      </td>
      <td className={`${cellClass}`}>
        <div className="flex items-center justify-end gap-2 sm:justify-start">
          <Badge variant={getScoreVariant(score)}>{score}/100</Badge>
          <span className="hidden text-xs text-muted-foreground sm:inline">{getScoreLabel(score)}</span>
        </div>
        <div className="mt-1 text-xs text-muted-foreground">{item.recommendation}</div>
      </td>
      <td className={`${cellClass} ${stickyRightAlasan} lg:before:pointer-events-none lg:before:absolute lg:before:inset-y-0 lg:before:left-0 lg:before:w-px lg:before:bg-border`}>
        <ReasonList icon={TrendUp} items={analysis.investmentReasons} title="Alasan investasi" />
      </td>
      <td className={`${cellClass} ${stickyRight}`}>
        <ReasonList icon={ShieldWarning} items={analysis.risks} title="Risiko utama" tone="risk" />
      </td>
    </tr>
  );
}

export default function TradingViewTable({ onDataUpdate, onSelectCompany }) {
  const [data, setData] = useState([]);
  const [summary, setSummary] = useState({});
  const [metadata, setMetadata] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [sort, setSort] = useState({ key: null, dir: "asc" });
  const mounted = useRef(false);

  const sortableColumns = useMemo(() => [
    { key: "price", label: "Harga", align: "text-right" },
    { key: "change", label: "1D", align: "text-right" },
    { key: "per", label: "PER", align: "text-right" },
    { key: "pbv", label: "PBV", align: "text-right" },
    { key: "roe", label: "ROE", align: "text-right" },
    { key: "dividend_yield", label: "Dividen", align: "text-right" },
    { key: "score", label: "Skor", align: "" },
  ], []);

  const { isWatched, toggle: toggleWatch } = useWatchlist();

  const handleSort = useCallback((key) => {
    setSort((prev) => {
      if (prev.key === key) {
        return { key, dir: prev.dir === "asc" ? "desc" : "asc" };
      }
      return { key, dir: "asc" };
    });
  }, []);

  const fetchData = async ({ refresh = false } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE}/tradingview/summary`, {
        params: { refresh, limit: 500 },
      });
      if (response.data.success) {
        setData(response.data.data || []);
        setSummary(response.data.analysis_summary || {});
        setMetadata(response.data.metadata || {});
        const updatedAt = response.data.updated_at || response.data.metadata?.fetchedAt || new Date().toISOString();
        setLastUpdated(updatedAt);
        onDataUpdate?.({ updatedAt, data: response.data.data || [], summary: response.data.analysis_summary || {} });
        toast.success(response.data.from_cache ? "Analisis TradingView dimuat dari cache." : "Data TradingView berhasil dianalisis.");
      } else {
        setError(response.data.message || "Gagal mengambil data");
        toast.error(response.data.message || "Gagal mengambil data");
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || "Terjadi kesalahan jaringan";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        fetchData({ refresh: true });
        scheduleNext();
      }, diffMs);
    }
    const timer = scheduleNext();
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredData = useMemo(() => {
    let result = data;
    const query = searchQuery.toLowerCase().trim();
    if (query) {
      result = data.filter((item) => {
        return (
          (item.ticker || "").toLowerCase().includes(query)
          || (item.companyName || "").toLowerCase().includes(query)
          || (item.sector || "").toLowerCase().includes(query)
        );
      });
    }

    if (sort.key) {
      result = [...result].sort((a, b) => {
        const getVal = (item) => {
          if (sort.key === "score") return item.analysis?.investmentScore ?? 0;
          return item[sort.key] ?? 0;
        };
        const va = getVal(a);
        const vb = getVal(b);
        const cmp = typeof va === "number" ? va - vb : String(va).localeCompare(String(vb));
        return sort.dir === "asc" ? cmp : -cmp;
      });
    }

    return result;
  }, [data, searchQuery, sort.key, sort.dir]);

  return (
    <div className="space-y-3">
      <SummaryCards metadata={metadata} summary={summary} />

      <Card className="overflow-hidden border-border bg-card">
        <CardHeader className="space-y-3 border-b border-border bg-card p-3 sm:p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                TradingView AI Agent
              </p>
              <CardTitle className="mt-1.5 text-base text-foreground sm:text-lg">
                Ringkasan investasi dari custom screener
              </CardTitle>
              <p className="mt-1.5 max-w-3xl text-xs leading-5 text-muted-foreground sm:text-sm">
                Data diambil dari TradingView screen AKYzoJyg, lalu dinilai ulang oleh agent lokal berdasarkan rating, valuasi, profitabilitas, pertumbuhan, dividen, leverage, dan momentum.
              </p>
              <p className="mt-1 text-[10px] text-muted-foreground/60">Data diperbarui otomatis setiap pukul 09:00 dan 15:00 WIB.</p>
            </div>
          </div>
          <AgentInsight summary={summary} />
        </CardHeader>

        <CardContent className="p-0">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2 sm:px-4">
            <MagnifyingGlass className="h-4 w-4 shrink-0 text-muted-foreground" />
            <Input
              className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Cari ticker, nama perusahaan, atau sektor..."
              value={searchQuery}
            />
            {searchQuery ? (
              <span className="shrink-0 whitespace-nowrap text-xs text-muted-foreground">
                {filteredData.length} dari {data.length}
              </span>
            ) : null}
          </div>

          {error && !loading ? (
            <div className="flex items-center gap-2 border-b border-border bg-destructive/5 p-3 text-sm text-destructive">
              <WarningCircle className="h-4 w-4" />
              {error}
            </div>
          ) : null}

          <div className="overflow-auto max-h-[calc(100vh-320px)]">
            <table className="w-full min-w-[900px] caption-bottom text-sm">
              <thead className="sticky top-0 z-20 [&_tr]:border-b-0">
                <tr>
                  <th className={`lg:sticky lg:left-0 z-30 bg-muted/50 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground lg:after:pointer-events-none lg:after:absolute lg:after:inset-y-0 lg:after:right-0 lg:after:w-px lg:after:bg-border`}>
                    Ticker
                  </th>
                  <th className={`lg:sticky lg:left-[132px] z-30 bg-muted/50 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground lg:after:pointer-events-none lg:after:absolute lg:after:inset-y-0 lg:after:right-0 lg:after:w-px lg:after:bg-border`}>
                    Perusahaan
                  </th>
                  {sortableColumns.map((col) => {
                    const isActive = sort.key === col.key;
                    return (
                      <th
                        key={col.key}
                        className={`${col.align} cursor-pointer select-none whitespace-nowrap bg-muted/50 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:bg-muted`}
                        onClick={() => handleSort(col.key)}
                      >
                        <span className="inline-flex items-center gap-1">
                          {col.label}
                          {isActive ? (
                            sort.dir === "asc" ? (
                              <CaretUp className="h-3 w-3 text-foreground" weight="fill" />
                            ) : (
                              <CaretDown className="h-3 w-3 text-foreground" weight="fill" />
                            )
                          ) : (
                            <CaretUp className="h-3 w-3 text-muted-foreground/30" weight="fill" />
                          )}
                        </span>
                      </th>
                    );
                  })}
                  <th className={`lg:sticky lg:right-[100px] z-30 bg-muted/50 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground lg:before:pointer-events-none lg:before:absolute lg:before:inset-y-0 lg:before:left-0 lg:before:w-px lg:before:bg-border`}>
                    <span className="inline-flex items-center gap-1">
                      <ChartLineUp className="h-3.5 w-3.5" />
                      Alasan
                    </span>
                  </th>
                  <th className={`lg:sticky lg:right-0 z-30 bg-muted/50 px-3 py-2.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground`}>
                    Risiko
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <LoadingState />
                ) : filteredData.length ? (
                  filteredData.map((item) => <StockRow item={item} key={item.symbol || item.ticker} onSelect={onSelectCompany} isWatched={isWatched} onToggleWatch={toggleWatch} />)
                ) : (
                  <EmptyState searchQuery={searchQuery} />
                )}
              </tbody>
            </table>
          </div>

          {lastUpdated && !loading ? (
            <div className="border-t border-border px-3 py-2 text-xs text-muted-foreground sm:px-4">
              Terakhir diperbarui: {new Date(lastUpdated).toLocaleString("id-ID")}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
