import { useCallback, useEffect, useRef, useState } from"react";
import {
 ArrowUp,
 ArrowDown,
 Scroll,
 Sparkle,
 Clock,
 CurrencyCircleDollar,
 PiggyBank,
 TrendUp,
 Coins,
} from"@phosphor-icons/react";
import axios from"axios";
import { Badge } from"@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from"@/components/ui/card";
import { toast } from"@/components/ui/sonner";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const TIMEFRAMES = ["1M", "3M", "6M", "12M"];

const TIMEFRAME_LABELS = {
 "1M": "1 Bulan",
 "3M": "3 Bulan (Kuartal)",
 "6M": "6 Bulan (Semi-Tahunan)",
 "12M": "12 Bulan (Tahunan)",
};

const formatPrice = (value) => {
 if (value === null || value === undefined) return"-";
 return new Intl.NumberFormat("id-ID", {
 style: "decimal",
 minimumFractionDigits: 0,
 maximumFractionDigits: 2,
 }).format(value);
};

const formatReturn = (value) => {
 if (value === null || value === undefined) return"-";
 const prefix = value >= 0 ? "+" : "";
 return `${prefix}${Number(value).toFixed(2)}%`;
};

const getReturnColor = (value) => {
 if (value === null || value === undefined) return "text-slate-500 dark:text-slate-400";
 if (value >= 5) return "text-emerald-600 dark:text-emerald-400";
 if (value >= 0) return "text-emerald-500 dark:text-emerald-400";
 if (value >= -5) return "text-red-500 dark:text-red-400";
 return "text-red-600 dark:text-red-400";
};

const round = (value, decimals) => Number(value.toFixed(decimals));

const getConfidenceBadge = (confidence) => {
 const variants = { high: "default", medium: "secondary", low: "outline" };
 return variants[confidence] || "outline";
};

const SHARES_PER_ORDER = 100;

const LS_ORDER_KEY = "ihsg_order_book";
const CACHE_TTL = 3600000;
const POLL_INTERVAL = 8000;
const POLL_TIMEOUT = 300000;

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

function PreparingState({ message, subMessage }) {
 const [dots, setDots] = useState("");
 useEffect(() => {
 const interval = setInterval(() => {
 setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
 }, 800);
 return () => clearInterval(interval);
 }, []);

 return (
 <div className="flex flex-col items-center justify-center py-20">
 <div className="relative mb-8">
 <div className="h-20 w-20 animate-pulse rounded-full bg-emerald-100 dark:bg-emerald-950" />
 <div className="absolute inset-0 flex items-center justify-center">
 <div className="h-12 w-12 animate-spin rounded-full border-4 border-emerald-200 dark:border-emerald-800 border-t-emerald-500" />
 </div>
 <div className="absolute -right-2 -top-1">
 <Sparkle className="h-6 w-6 animate-bounce text-emerald-400"weight="fill" />
 </div>
 </div>
 <p className="text-lg font-semibold text-slate-800 dark:text-slate-200">
 {message || "Menyiapkan data order book"}
 <span className="inline-block w-6 text-left">{dots}</span>
 </p>
 <p className="mt-2 max-w-sm text-center text-sm leading-6 text-slate-500 dark:text-slate-400">
 {subMessage || "Sistem sedang mengumpulkan data prediksi sektor dan harga saham."}
 </p>
 <div className="mt-8 flex gap-2">
 {[0, 1, 2, 3, 4].map((i) => (
 <div
 key={i}
 className="h-2 w-2 animate-pulse rounded-full bg-emerald-400"
 style={{ animationDelay: `${i * 0.3}s` }}
 />
 ))}
 </div>
 </div>
 );
}

function StatCards({ simulations, generatedAt }) {
 const totalOrders = simulations.reduce((sum, s) => sum + s.stocks.length, 0);
 const openOrders = simulations.reduce((sum, s) => sum + s.stocks.filter((st) => st.status === "open").length, 0);
 const closedOrders = totalOrders - openOrders;

 return (
 <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
 <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-800 dark:shadow-none">
 <CardContent className="p-3 sm:p-4">
 <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Total Order</p>
 <p className="mt-2 text-xl font-semibold text-slate-950 dark:text-slate-50 sm:text-2xl">{totalOrders}</p>
 <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Semua timeframe</p>
 </CardContent>
 </Card>
 <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-800 dark:shadow-none">
 <CardContent className="p-3 sm:p-4">
 <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Open</p>
 <p className="mt-2 text-xl font-semibold text-emerald-700 dark:text-emerald-400 sm:text-2xl">{openOrders}</p>
 <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Menunggu close</p>
 </CardContent>
 </Card>
 <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-800 dark:shadow-none">
 <CardContent className="p-3 sm:p-4">
 <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Closed</p>
 <p className="mt-2 text-xl font-semibold text-sky-700 dark:text-sky-400 sm:text-2xl">{closedOrders}</p>
 <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Selesai</p>
 </CardContent>
 </Card>
 <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-800 dark:shadow-none">
 <CardContent className="p-3 sm:p-4">
 <p className="text-xs uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Terakhir</p>
 <p className="mt-2 text-xs font-semibold text-slate-700 dark:text-slate-300 sm:text-sm">
 {generatedAt ? new Date(generatedAt).toLocaleString("id-ID", { dateStyle: "full", timeStyle: "short" }) : "-"}
 </p>
 <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Update sistem</p>
 </CardContent>
 </Card>
 </div>
 );
}

function PortfolioSummary({ simulations }) {
 const totalInvested = simulations.reduce((sum, s) => {
 return sum + s.stocks.reduce((sub, st) => sub + (st.buy_price || 0) * SHARES_PER_ORDER, 0);
 }, 0);

 const currentValue = simulations.reduce((sum, s) => {
 return sum + s.stocks.reduce((sub, st) => {
 if (st.status === "closed" && st.actual_sell_price != null) {
 return sub + st.actual_sell_price * SHARES_PER_ORDER;
 }
 return sub + (st.current_price || st.buy_price || 0) * SHARES_PER_ORDER;
 }, 0);
 }, 0);

 const totalEstimated = simulations.reduce((sum, s) => {
 return sum + s.stocks.reduce((sub, st) => {
 if (st.buy_price && st.estimated_sell_price) {
 return sub + (st.estimated_sell_price - st.buy_price) * SHARES_PER_ORDER;
 }
 return sub;
 }, 0);
 }, 0);

 const totalActual = simulations.reduce((sum, s) => {
 return sum + s.stocks.reduce((sub, st) => {
 const sellPrice = st.status === "closed" ? st.actual_sell_price : st.current_price;
 if (st.buy_price && sellPrice) {
 return sub + (sellPrice - st.buy_price) * SHARES_PER_ORDER;
 }
 return sub;
 }, 0);
 }, 0);

 const totalReturnPct = totalInvested > 0 ? (totalActual / totalInvested) * 100 : 0;
 const predReturnPct = totalInvested > 0 ? (totalEstimated / totalInvested) * 100 : 0;
 const investedFormatted = new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(totalInvested);
 const valueFormatted = new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(currentValue);
 const actualFormatted = new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(totalActual);

 return (
 <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50/80 to-white shadow-sm dark:border-emerald-800 dark:from-emerald-950/50 dark:to-slate-800">
 <CardHeader className="pb-3">
 <div className="flex items-center gap-2">
 <PiggyBank className="h-5 w-5 text-emerald-600 dark:text-emerald-400"weight="duotone" />
 <CardTitle className="text-base font-semibold text-slate-800 dark:text-slate-200">Ringkasan Portofolio</CardTitle>
 </div>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
 <div>
 <p className="flex items-center gap-1 text-xs uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
 <Coins className="h-3 w-3"weight="duotone" />
 Modal Awal
 </p>
 <p className="mt-1 text-lg font-bold text-slate-800 dark:text-slate-200">Rp {investedFormatted}</p>
 <p className="text-[10px] text-slate-400 dark:text-slate-500">{SHARES_PER_ORDER} lembar/order</p>
 </div>
 <div>
 <p className="flex items-center gap-1 text-xs uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
 <TrendUp className="h-3 w-3"weight="duotone" />
 Prediksi Return
 </p>
 <p className="mt-1 text-lg font-bold text-emerald-600 dark:text-emerald-400">
 {totalEstimated >= 0 ? "+" : ""}Rp {new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(totalEstimated)}
 </p>
 <p className={`text-[10px] font-semibold ${predReturnPct >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
 {predReturnPct >= 0 ? "+" : ""}{predReturnPct.toFixed(2)}%
 </p>
 </div>
 <div>
 <p className="flex items-center gap-1 text-xs uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
 <CurrencyCircleDollar className="h-3 w-3"weight="duotone" />
 Aktual Return
 </p>
 <p className={`mt-1 text-lg font-bold ${totalActual >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
 {totalActual >= 0 ? "+" : ""}Rp {actualFormatted}
 </p>
 <p className={`text-[10px] font-semibold ${totalReturnPct >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
 {totalReturnPct >= 0 ? "+" : ""}{totalReturnPct.toFixed(2)}%
 </p>
 </div>
 <div>
 <p className="flex items-center gap-1 text-xs uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
 <Coins className="h-3 w-3"weight="duotone" />
 Nilai Investasi
 </p>
 <p className="mt-1 text-lg font-bold text-slate-800 dark:text-slate-200">Rp {valueFormatted}</p>
 <p className={`text-[10px] font-semibold ${(currentValue - totalInvested) >= 0 ? "text-emerald-500 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
 {(currentValue - totalInvested) >= 0 ? "+" : ""}Rp {new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(currentValue - totalInvested)}
 </p>
 </div>
 </div>
 </CardContent>
 </Card>
 );
}

function TimeframeCard({ simulation }) {
 const { timeframe, sector, stocks } = simulation;

 return (
 <Card className="overflow-hidden border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
 <CardHeader className="border-b border-slate-100 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 pb-3">
 <div className="flex flex-wrap items-center justify-between gap-2">
 <div className="flex items-center gap-2">
 <Clock className="h-5 w-5 text-slate-400 dark:text-slate-500"weight="duotone" />
 <CardTitle className="text-base font-semibold text-slate-800 dark:text-slate-200">
 {TIMEFRAME_LABELS[timeframe]}
 </CardTitle>
 </div>
 <div className="flex items-center gap-2">
 <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-400 hover:bg-emerald-100"variant="secondary">
 #{sector.rank} {sector.name}
 </Badge>
 <Badge variant={getConfidenceBadge(sector.confidence)}>
 {sector.confidence || "N/A"}
 </Badge>
 </div>
 </div>
 {sector.rationale && (
 <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400 line-clamp-2">{sector.rationale}</p>
 )}
 </CardHeader>
 <CardContent className="p-0">
 <div className="overflow-x-auto">
 <table className="w-full caption-bottom text-sm">
 <thead>
 <tr className="border-b border-slate-100 text-xs font-medium uppercase tracking-[0.08em] dark:border-slate-700 text-slate-500 dark:text-slate-400">
 <th className="px-4 py-3 text-left">Ticker</th>
 <th className="px-4 py-3 text-left">Rekomendasi</th>
 <th className="px-4 py-3 text-left">Buy Date</th>
 <th className="px-4 py-3 text-left">Sell Date</th>
 <th className="px-4 py-3 text-right">Buy Price</th>
 <th className="px-4 py-3 text-right">Est. Sell</th>
 <th className="px-4 py-3 text-right">Actual Sell</th>
 <th className="px-4 py-3 text-right">Est. Return</th>
 <th className="px-4 py-3 text-right">Actual Return</th>
 <th className="px-4 py-3 text-center">Status</th>
 </tr>
 </thead>
 <tbody>
 {stocks.map((stock) => (
 <tr key={stock.ticker} className="border-b border-slate-50 transition-colors dark:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-700/50 :bg-slate-700/50 :bg-slate-700/50">
 <td className="px-4 py-3">
 <span className="font-semibold text-slate-800 dark:text-slate-200">{stock.ticker}</span>
 {stock.company_name && (
 <p className="text-xs text-slate-400 dark:text-slate-500 truncate max-w-[120px]">{stock.company_name}</p>
 )}
 </td>
 <td className="px-4 py-3">
 <Badge
 className={
 stock.recommendation?.includes("Strong Buy")
 ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-400"
 : stock.recommendation === "Buy"
 ? "bg-sky-100 text-sky-700 dark:bg-sky-900 dark:text-sky-400"
 : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
 }
 variant="secondary"
 >
 {stock.recommendation || "-"}
 </Badge>
 </td>
 <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{stock.buy_date}</td>
 <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">{stock.sell_date}</td>
 <td className="px-4 py-3 text-right font-medium text-slate-800 dark:text-slate-200">
 {formatPrice(stock.buy_price)}
 </td>
 <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-400">
 {formatPrice(stock.estimated_sell_price)}
 </td>
 <td className="px-4 py-3 text-right font-medium text-slate-800 dark:text-slate-200">
 {formatPrice(stock.actual_sell_price)}
 </td>
 <td className={`px-4 py-3 text-right font-semibold ${getReturnColor(stock.predicted_return_pct)}`}>
 {formatReturn(stock.predicted_return_pct)}
 </td>
 <td className={`px-4 py-3 text-right font-semibold ${getReturnColor(stock.actual_return_pct)}`}>
 <span className="flex items-center justify-end gap-1">
 {stock.actual_return_pct !== null && stock.actual_return_pct !== undefined && (
 stock.actual_return_pct >= 0
 ? <ArrowUp className="h-3 w-3 text-emerald-500 dark:text-emerald-400"weight="bold" />
 : <ArrowDown className="h-3 w-3 text-red-500 dark:text-red-400"weight="bold" />
 )}
 {formatReturn(stock.actual_return_pct)}
 </span>
 </td>
 <td className="px-4 py-3 text-center">
 <Badge
 className={
 stock.status === "closed"
 ? "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
 : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-400"
 }
 variant="secondary"
 >
 {stock.status === "closed" ? "Closed" : "Open"}
 </Badge>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </CardContent>
 </Card>
 );
}

export default function OrderBook() {
 const [simulations, setSimulations] = useState(() => lsGet(LS_ORDER_KEY, CACHE_TTL) || []);
 const [generatedAt, setGeneratedAt] = useState(null);
 const [loading, setLoading] = useState(() => !lsGet(LS_ORDER_KEY, CACHE_TTL));
 const [preparing, setPreparing] = useState(false);
 const [priceUpdating, setPriceUpdating] = useState(false);
 const pollingRef = useRef(null);
 const priceIntervalRef = useRef(null);
 const buyPriceMapRef = useRef({});

 const triggerCacheRefresh = useCallback(async () => {
 try {
 await axios.post(`${API_BASE}/admin/refresh-cache?token=ihsg-admin-token`);
 } catch {
 // scheduler may already be running
 }
 }, []);

 const startPolling = useCallback(() => {
 if (pollingRef.current) return;
 setPreparing(true);

 let timedOut = false;
 const timeoutId = setTimeout(() => {
 timedOut = true;
 setPreparing(false);
 setLoading(false);
 pollingRef.current = null;
 }, POLL_TIMEOUT);

 const poll = async () => {
 if (timedOut) return;
 try {
 const resp = await axios.get(`${API_BASE}/order-book/simulation`);
 if (resp.data.success) {
 const sims = resp.data.simulations || [];
 if (sims.length > 0) {
 clearTimeout(timeoutId);
 setPreparing(false);
 setLoading(false);
 setSimulations(sims);
 setGeneratedAt(resp.data.generated_at);
 lsSet(LS_ORDER_KEY, sims);
 pollingRef.current = null;
 return;
 }
 }
 } catch {
 // keep polling
 }
 pollingRef.current = setTimeout(poll, POLL_INTERVAL);
 };

 pollingRef.current = setTimeout(poll, POLL_INTERVAL);
 return () => {
 clearTimeout(timeoutId);
 if (pollingRef.current) {
 clearTimeout(pollingRef.current);
 pollingRef.current = null;
 }
 };
 }, []);

 const mergePrices = useCallback((newSims) => {
 const map = buyPriceMapRef.current;
 return newSims.map((sim) => ({
 ...sim,
 stocks: sim.stocks.map((stock) => {
 const key = `${sim.timeframe}_${stock.ticker}`;
 const savedBuy = map[key];
 const buyPrice = savedBuy || stock.buy_price;
 if (!savedBuy) map[key] = stock.buy_price;
 const currentPrice = stock.current_price || stock.buy_price;
 const actualReturn = buyPrice && currentPrice
 ? round((currentPrice - buyPrice) / buyPrice * 100, 2)
 : stock.actual_return_pct;
 return {
 ...stock,
 buy_price: buyPrice,
 current_price: currentPrice,
 actual_return_pct: actualReturn,
 };
 }),
 }));
 }, []);

 const fetchSimulations = useCallback(async () => {
 const cached = lsGet(LS_ORDER_KEY, CACHE_TTL);
 if (cached) {
 const merged = mergePrices(cached);
 setSimulations(merged);
 setLoading(false);
 return;
 }

 setLoading(true);
 try {
 const response = await axios.get(`${API_BASE}/order-book/simulation`);
 if (response.data.success) {
 const sims = response.data.simulations || [];
 if (sims.length > 0) {
 const merged = mergePrices(sims);
 setSimulations(merged);
 setGeneratedAt(response.data.generated_at);
 lsSet(LS_ORDER_KEY, merged);
 } else {
 triggerCacheRefresh();
 startPolling();
 }
 } else {
 triggerCacheRefresh();
 startPolling();
 }
 } catch {
 triggerCacheRefresh();
 startPolling();
 } finally {
 setLoading(false);
 }
 }, [triggerCacheRefresh, startPolling, mergePrices]);

 const refreshPrices = useCallback(async () => {
 setPriceUpdating(true);
 try {
 const resp = await axios.get(`${API_BASE}/order-book/simulation?refresh=true`);
 if (resp.data.success) {
 const sims = resp.data.simulations || [];
 if (sims.length > 0) {
 const merged = mergePrices(sims);
 setSimulations(merged);
 setGeneratedAt(resp.data.generated_at);
 lsSet(LS_ORDER_KEY, merged);
 }
 }
 } catch {
 // silent fail — keep showing stale prices
 } finally {
 setPriceUpdating(false);
 }
 }, [mergePrices]);

 useEffect(() => {
 fetchSimulations();

 return () => {
 if (pollingRef.current) {
 clearTimeout(pollingRef.current);
 pollingRef.current = null;
 }
 if (priceIntervalRef.current) {
 clearInterval(priceIntervalRef.current);
 priceIntervalRef.current = null;
 }
 };
 }, [fetchSimulations]);

 useEffect(() => {
 if (simulations.length > 0) {
 const immediate = setTimeout(refreshPrices, 2000);
 priceIntervalRef.current = setInterval(refreshPrices, 300000);
 return () => {
 clearTimeout(immediate);
 if (priceIntervalRef.current) {
 clearInterval(priceIntervalRef.current);
 priceIntervalRef.current = null;
 }
 };
 }
  }, [simulations, refreshPrices]);

 if (preparing) {
 return (
 <div className="space-y-6">
 <div className="flex items-center gap-2">
 <Scroll className="h-6 w-6 text-emerald-500 dark:text-emerald-400"weight="duotone" />
 <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Order Book Simulation</h2>
 </div>
 <PreparingState
 message="Menyiapkan data order book"
 subMessage="Sistem sedang mengumpulkan prediksi sektor, rekomendasi saham, dan harga pasar. Ini akan memakan waktu beberapa saat."
 />
 </div>
 );
 }

 if (loading) {
 return (
 <div className="space-y-6">
 <div className="flex items-center gap-2">
 <Scroll className="h-6 w-6 text-emerald-500 dark:text-emerald-400"weight="duotone" />
 <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Order Book Simulation</h2>
 </div>
 <div className="flex items-center justify-center py-20">
 <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 dark:border-emerald-800 border-t-emerald-500" />
 </div>
 </div>
 );
 }

 return (
 <div className="space-y-6">
 <div className="flex items-center justify-between gap-2">
 <div className="flex items-center gap-2">
 <Scroll className="h-6 w-6 text-emerald-500 dark:text-emerald-400"weight="duotone" />
 <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Order Book Simulation</h2>
 </div>
 {priceUpdating && (
 <div className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500">
 <div className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-emerald-300 border-t-emerald-500" />
 Memperbarui harga...
 </div>
 )}
 </div>

 <StatCards simulations={simulations} generatedAt={generatedAt} />

 {simulations.length > 0 && <PortfolioSummary simulations={simulations} />}

 {simulations.length === 0 ? (
 <Card className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-800 dark:shadow-none">
 <CardContent className="flex flex-col items-center justify-center py-16">
 <CurrencyCircleDollar className="mb-4 h-12 w-12 text-slate-300"weight="duotone" />
 <p className="text-sm text-slate-500 dark:text-slate-400">Belum ada data simulasi. Jalankan scheduler terlebih dahulu.</p>
 </CardContent>
 </Card>
 ) : (
 <div className="space-y-4">
 {simulations.map((sim) => (
 <TimeframeCard key={sim.timeframe} simulation={sim} />
 ))}
 </div>
 )}
 </div>
 );
}