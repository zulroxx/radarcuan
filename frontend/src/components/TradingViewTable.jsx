import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowsClockwise,
  CaretDown,
  CaretUp,
  ChartLineUp,
  MagnifyingGlass,
  ShieldWarning,
  Sparkle,
  TrendUp,
  WarningCircle,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "http://localhost:8000";
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

const getScoreClass = (score) => {
  if (score >= 75) return "bg-emerald-500 text-white";
  if (score >= 60) return "bg-sky-500 text-white";
  if (score >= 45) return "bg-amber-500 text-white";
  return "bg-red-500 text-white";
};

const getScoreLabel = (score) => {
  if (score >= 75) return "Menarik";
  if (score >= 60) return "Layak";
  if (score >= 45) return "Netral";
  return "Spekulatif";
};

function SummaryCards({ summary, metadata }) {
  const sourceUrl = metadata?.sourceUrl || summary?.sourceUrl;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Universe</p>
          <p className="mt-2 text-xl font-semibold text-slate-950 sm:text-2xl">{summary?.total || 0}</p>
          <p className="mt-1 text-xs text-slate-500 sm:text-sm">Saham dianalisis agent</p>
        </CardContent>
      </Card>
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Skor rata-rata</p>
          <p className="mt-2 text-xl font-semibold text-slate-950 sm:text-2xl">{summary?.averageScore || 0}/100</p>
          <p className="mt-1 text-xs text-slate-500 sm:text-sm">Gabungan valuasi, kualitas, growth</p>
        </CardContent>
      </Card>
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Pembelian kuat</p>
          <p className="mt-2 text-xl font-semibold text-emerald-700 sm:text-2xl">{summary?.strongBuyCount || 0}</p>
          <p className="mt-1 text-xs text-slate-500 sm:text-sm">Berdasarkan rating TradingView</p>
        </CardContent>
      </Card>
      <Card className="border-slate-200 bg-white shadow-none">
        <CardContent className="p-3 sm:p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Sumber</p>
          <a className="mt-2 block truncate text-xs font-semibold text-sky-700 hover:text-sky-900 sm:text-sm" href={sourceUrl} rel="noreferrer" target="_blank">
            {metadata?.screenTitle || summary?.screenTitle || "TradingView Screener"}
          </a>
          <p className="mt-1 text-xs text-slate-500">Custom screen AKYzoJyg</p>
        </CardContent>
      </Card>
    </div>
  );
}

function AgentInsight({ summary }) {
  const sectors = summary?.topSectors || [];

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 sm:p-4">
      <div className="flex items-start gap-3">
        <Sparkle className="mt-0.5 hidden h-5 w-5 shrink-0 text-emerald-700 sm:block" weight="fill" />
        <div className="min-w-0 space-y-3">
          <div>
            <p className="text-xs font-semibold text-emerald-950 sm:text-sm">Ringkasan penting AI agent</p>
            <p className="mt-1 text-xs leading-6 text-emerald-800 sm:text-sm">
              {summary?.keyInsight || "Agent sedang menunggu data TradingView untuk dianalisis."}
            </p>
          </div>
          {sectors.length ? (
            <div className="flex flex-wrap gap-1.5 sm:gap-2">
              {sectors.map((item) => (
                <Badge key={item.sector} className="bg-white text-emerald-800 hover:bg-white">
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
      <td colSpan={11} className="h-40 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <ArrowsClockwise className="h-6 w-6 animate-spin text-slate-400" />
          <p className="text-sm text-slate-500">Mengambil data TradingView dan menjalankan analisis agent...</p>
        </div>
      </td>
    </tr>
  );
}

function EmptyState({ searchQuery }) {
  return (
    <tr>
      <td colSpan={11} className="h-40 text-center">
        <p className="text-sm font-medium text-slate-700">
          {searchQuery ? "Tidak ada saham yang cocok dengan pencarian." : "Belum ada data dari TradingView."}
        </p>
      </td>
    </tr>
  );
}

function ReasonList({ title, icon: Icon, items, tone }) {
  const toneClass = tone === "risk" ? "text-amber-700" : "text-emerald-700";
  return (
    <div className="space-y-1.5">
      <div className={`flex items-center gap-1.5 text-xs font-semibold ${toneClass}`}>
        <Icon className="h-3.5 w-3.5" />
        {title}
      </div>
      <ul className="space-y-1">
        {(items || []).slice(0, 2).map((item) => (
          <li key={item} className="text-xs leading-5 text-slate-600">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

const cellClass =
  "border-b border-slate-100 px-4 py-3.5 align-top text-sm";
const stickyLeft = "sticky left-0 z-10 bg-white";
const stickyRight = "sticky right-0 z-10 bg-white";
const stickyRightAlasan = "sticky right-[100px] z-10 bg-white";

function StockRow({ item, onSelect }) {
  const analysis = item.analysis || {};
  const score = analysis.investmentScore || 0;

  return (
    <tr className="cursor-pointer border-b border-slate-100 hover:bg-slate-50/80" onClick={() => onSelect?.(item)}>
      <td className={`${cellClass} ${stickyLeft} after:pointer-events-none after:absolute after:inset-y-0 after:right-0 after:w-px after:bg-slate-200`}>
        <div className="flex items-center gap-2">
          <div className="font-mono text-sm font-semibold text-slate-950">{item.ticker}</div>
          <Badge className={`hidden px-1.5 py-0 text-[10px] font-semibold sm:inline-flex ${getScoreClass(score)}`}>{getScoreLabel(score)}</Badge>
        </div>
        <div className="mt-1 text-xs text-slate-500">{item.sector}</div>
      </td>
      <td className={`${cellClass} hidden sm:table-cell ${stickyLeft} left-[140px] after:pointer-events-none after:absolute after:inset-y-0 after:right-0 after:w-px after:bg-slate-200`}>
        <div className="text-sm font-medium text-slate-900">{item.companyName}</div>
        <div className="mt-0.5 text-xs text-slate-500">{formatMarketCap(item.marketCap)}</div>
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums text-slate-700`}>
        Rp{formatNumber(item.price, { maximumFractionDigits: 0 })}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums font-medium sm:table-cell hidden ${
        item.change >= 0 ? "text-emerald-600" : "text-red-600"
      }`}>
        {formatPercent(item.change)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums text-slate-700 sm:table-cell hidden`}>
        {formatRatio(item.per)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums text-slate-700 md:table-cell hidden`}>
        {formatRatio(item.pbv)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums text-slate-700 md:table-cell hidden`}>
        {formatPercent(item.roe)}
      </td>
      <td className={`whitespace-nowrap ${cellClass} text-right tabular-nums text-slate-700 md:table-cell hidden`}>
        {formatPercent(item.dividend_yield)}
      </td>
      <td className={`${cellClass}`}>
        <div className="flex items-center justify-end gap-2 sm:justify-start">
          <Badge className={`shrink-0 ${getScoreClass(score)}`}>{score}/100</Badge>
          <span className="hidden text-xs text-slate-500 sm:inline">{getScoreLabel(score)}</span>
        </div>
        <div className="mt-1.5 text-xs text-slate-500">{item.recommendation}</div>
      </td>
      <td className={`${cellClass} sm:table-cell hidden ${stickyRightAlasan} before:pointer-events-none before:absolute before:inset-y-0 before:left-0 before:w-px before:bg-slate-200`}>
        <ReasonList icon={TrendUp} items={analysis.investmentReasons} title="Alasan investasi" />
      </td>
      <td className={`${cellClass} lg:table-cell hidden ${stickyRight}`}>
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

  const sortableColumns = useMemo(() => [
    { key: "price", label: "Harga", align: "text-right" },
    { key: "change", label: "1D", align: "text-right" },
    { key: "per", label: "PER", align: "text-right" },
    { key: "pbv", label: "PBV", align: "text-right" },
    { key: "roe", label: "ROE", align: "text-right" },
    { key: "dividend_yield", label: "Dividen", align: "text-right" },
    { key: "score", label: "Skor", align: "" },
  ], []);

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
    <div className="space-y-4">
      <SummaryCards metadata={metadata} summary={summary} />

      <Card className="overflow-hidden border-slate-200 bg-white shadow-sm">
        <CardHeader className="space-y-4 border-b border-slate-200 bg-white/90 p-4 sm:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-600">
                TradingView AI Agent
              </p>
              <CardTitle className="mt-2 text-lg text-slate-950 sm:text-xl">
                Ringkasan investasi dari custom screener
              </CardTitle>
              <p className="mt-2 max-w-3xl text-xs leading-6 text-slate-600 sm:text-sm">
                Data diambil dari TradingView screen AKYzoJyg, lalu dinilai ulang oleh agent lokal berdasarkan rating, valuasi, profitabilitas, pertumbuhan, dividen, leverage, dan momentum.
              </p>
              <p className="mt-1.5 text-[10px] text-slate-400">Data diperbarui otomatis setiap pukul 09:00 dan 15:00 WIB.</p>
            </div>
            </div>
          <AgentInsight summary={summary} />
        </CardHeader>

        <CardContent className="p-0">
          <div className="flex items-center gap-2 border-b border-slate-200 p-3 sm:p-4">
            <MagnifyingGlass className="h-4 w-4 shrink-0 text-slate-400" />
            <Input
              className="border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Cari ticker, nama perusahaan, atau sektor..."
              value={searchQuery}
            />
            {searchQuery ? (
              <span className="shrink-0 whitespace-nowrap text-xs text-slate-500">
                {filteredData.length} dari {data.length}
              </span>
            ) : null}
          </div>

          {error && !loading ? (
            <div className="flex items-center gap-2 border-b border-slate-200 bg-red-50 p-4 text-sm text-red-700">
              <WarningCircle className="h-4 w-4" />
              {error}
            </div>
          ) : null}

          <div className="overflow-auto max-h-[calc(100vh-320px)]">
            <table className="w-full caption-bottom text-sm">
              <thead className="sticky top-0 z-20 [&_tr]:border-b-0">
                <tr>
                  <th className={`sticky left-0 z-30 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 after:pointer-events-none after:absolute after:inset-y-0 after:right-0 after:w-px after:bg-slate-200`}>
                    Ticker
                  </th>
                  <th className={`sticky left-[140px] z-30 hidden bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 sm:table-cell after:pointer-events-none after:absolute after:inset-y-0 after:right-0 after:w-px after:bg-slate-200`}>
                    Perusahaan
                  </th>
                  {sortableColumns.map((col) => {
                    const isActive = sort.key === col.key;
                    return (
                      <th
                        key={col.key}
                        className={`${col.align} cursor-pointer select-none whitespace-nowrap bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 transition-colors hover:bg-slate-100 ${
                          col.key === "score" ? "" : "hidden sm:table-cell"
                        } ${["pbv", "roe", "dividend_yield"].includes(col.key) ? "hidden md:table-cell" : ""}`}
                        onClick={() => handleSort(col.key)}
                      >
                        <span className="inline-flex items-center gap-1">
                          {col.label}
                          {isActive ? (
                            sort.dir === "asc" ? (
                              <CaretUp className="h-3 w-3 text-emerald-600" weight="fill" />
                            ) : (
                              <CaretDown className="h-3 w-3 text-emerald-600" weight="fill" />
                            )
                          ) : (
                            <CaretUp className="h-3 w-3 text-slate-300" weight="fill" />
                          )}
                        </span>
                      </th>
                    );
                  })}
                  <th className={`sticky right-[100px] z-30 hidden bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 sm:table-cell before:pointer-events-none before:absolute before:inset-y-0 before:left-0 before:w-px before:bg-slate-200`}>
                    <span className="inline-flex items-center gap-1">
                      <ChartLineUp className="h-3.5 w-3.5" />
                      Alasan
                    </span>
                  </th>
                  <th className={`sticky right-0 z-30 hidden bg-slate-50 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 lg:table-cell`}>
                    Risiko
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <LoadingState />
                ) : filteredData.length ? (
                  filteredData.map((item) => <StockRow item={item} key={item.symbol || item.ticker} onSelect={onSelectCompany} />)
                ) : (
                  <EmptyState searchQuery={searchQuery} />
                )}
              </tbody>
            </table>
          </div>

          {lastUpdated && !loading ? (
            <div className="border-t border-slate-200 px-3 py-2 text-xs text-slate-500 sm:px-4">
              Terakhir diperbarui: {new Date(lastUpdated).toLocaleString("id-ID")}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
