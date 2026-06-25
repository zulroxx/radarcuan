import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUp,
  ArrowDown,
  Scroll,
  Clock,
  CurrencyCircleDollar,
  PiggyBank,
  TrendUp,
  Coins,
  CaretUp,
  CaretDown,
  SealCheck,
} from "@phosphor-icons/react";
import axios from "axios";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import StatCardGrid from "@/components/ui/stat-card-grid";
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

const formatPrice = (value) => {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("id-ID", {
    style: "decimal",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatReturn = (value) => {
  if (value === null || value === undefined) return "-";
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${Number(value).toFixed(2)}%`;
};

const getReturnColor = (value) => {
  if (value === null || value === undefined) return "text-muted-foreground";
  if (value >= 5) return "text-cuan";
  if (value >= 0) return "text-cuan";
  if (value >= -5) return "text-loss";
  return "text-loss";
};

const round = (value, decimals) => Number(value.toFixed(decimals));

const SHARES_PER_ORDER = 100;

function groupByTimeframe(simulations) {
  const map = {};
  for (const sim of simulations) {
    const tf = sim.timeframe;
    if (!map[tf]) {
      map[tf] = {
        timeframe: tf,
        stocks: [],
      };
    }
    for (const stock of sim.stocks) {
      map[tf].stocks.push({
        ...stock,
        sector_name: stock.sector || sim.sector?.name || "-",
      });
    }
  }
  return Object.values(map);
}

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
    <div className="flex flex-col items-center justify-center py-16">
      <div className="mb-4 h-12 w-12 animate-spin rounded-full border-2 border-border border-t-foreground" />
      <p className="text-base font-semibold text-foreground">
        {message || "Menyiapkan data order book"}
        <span className="inline-block w-6 text-left">{dots}</span>
      </p>
      <p className="mt-2 max-w-sm text-center text-sm leading-6 text-muted-foreground">
        {subMessage || "Sistem sedang mengumpulkan data prediksi sektor dan harga saham."}
      </p>
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

  const totalOrders = simulations.reduce((sum, s) => sum + s.stocks.length, 0);
  const totalShares = totalOrders * SHARES_PER_ORDER;

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <PiggyBank className="h-4 w-4 text-foreground" />
          <CardTitle className="text-base font-semibold text-foreground">Ringkasan Portofolio</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="flex items-center gap-1 text-xs uppercase tracking-wider text-muted-foreground">
              <Coins className="h-3 w-3" />
              Modal Awal
            </p>
            <p className="mt-1 text-lg font-bold text-foreground">Rp {investedFormatted}</p>
            <p className="text-[10px] text-muted-foreground">{SHARES_PER_ORDER} lembar/order</p>
          </div>
          <div>
            <p className="flex items-center gap-1 text-xs uppercase tracking-wider text-muted-foreground">
              <TrendUp className="h-3 w-3" />
              Prediksi Return
            </p>
            <p className="mt-1 text-lg font-bold text-cuan">
              {totalEstimated >= 0 ? "+" : ""}Rp {new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(totalEstimated)}
            </p>
            <p className={`text-[10px] font-semibold ${predReturnPct >= 0 ? "text-cuan" : "text-loss"}`}>
              {predReturnPct >= 0 ? "+" : ""}{predReturnPct.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="flex items-center gap-1 text-xs uppercase tracking-wider text-muted-foreground">
              <CurrencyCircleDollar className="h-3 w-3" />
              Aktual Return
            </p>
            <p className={`mt-1 text-lg font-bold ${totalActual >= 0 ? "text-cuan" : "text-loss"}`}>
              {totalActual >= 0 ? "+" : ""}Rp {actualFormatted}
            </p>
            <p className={`text-[10px] font-semibold ${totalReturnPct >= 0 ? "text-cuan" : "text-loss"}`}>
              {totalReturnPct >= 0 ? "+" : ""}{totalReturnPct.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="flex items-center gap-1 text-xs uppercase tracking-wider text-muted-foreground">
              <Coins className="h-3 w-3" />
              Nilai Investasi
            </p>
            <p className="mt-1 text-lg font-bold text-foreground">Rp {valueFormatted}</p>
            <p className={`text-[10px] font-semibold ${(currentValue - totalInvested) >= 0 ? "text-cuan" : "text-loss"}`}>
              {(currentValue - totalInvested) >= 0 ? "+" : ""}Rp {new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(currentValue - totalInvested)}
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1 rounded-md border border-border bg-muted/30 px-3 py-2.5 text-xs text-muted-foreground">
          {simulations.map((s) => {
            const orders = s.stocks.length;
            if (!orders) return null;
            return (
              <span key={s.timeframe} className="text-muted-foreground">
                <span className="font-semibold text-foreground">{TIMEFRAME_LABELS[s.timeframe]}</span>
                : {orders} order ({orders * SHARES_PER_ORDER} lembar)
              </span>
            );
          })}
          <span className="font-semibold text-foreground">
            Total: {totalOrders} order ({totalShares} lembar)
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

function TimeframeCard({ simulation }) {
  const { timeframe, stocks } = simulation;
  const [sortConfig, setSortConfig] = useState({ key: null, direction: "asc" });

  const handleSort = (key) => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === "asc" ? "desc" : "asc",
    }));
  };

  const sortedStocks = useMemo(() => {
    if (!sortConfig.key) return stocks;
    return [...stocks].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === "string") {
        return sortConfig.direction === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      return sortConfig.direction === "asc" ? aVal - bVal : bVal - aVal;
    });
  }, [stocks, sortConfig]);

  const nStocks = stocks.length;
  const totalInvested = stocks.reduce(
    (sum, s) => sum + (s.buy_price || 0) * SHARES_PER_ORDER, 0,
  );
  const totalEstProfit = stocks.reduce((sum, s) => {
    if (s.buy_price && s.estimated_sell_price)
      return sum + (s.estimated_sell_price - s.buy_price) * SHARES_PER_ORDER;
    return sum;
  }, 0);
  const totalActualProfit = stocks.reduce((sum, s) => {
    const sellPrice = s.status === "closed" ? s.actual_sell_price : s.current_price;
    if (s.buy_price && sellPrice)
      return sum + (sellPrice - s.buy_price) * SHARES_PER_ORDER;
    return sum;
  }, 0);

  const avgEstReturn =
    nStocks > 0
      ? stocks.reduce((sum, s) => sum + (s.predicted_return_pct || 0), 0) / nStocks
      : 0;
  const closedStocks = stocks.filter((s) => s.status === "closed");
  const avgActualReturn =
    closedStocks.length > 0
      ? closedStocks.reduce((sum, s) => sum + (s.actual_return_pct || 0), 0) /
        closedStocks.length
      : null;
  const totalEstReturnPct = totalInvested > 0 ? (totalEstProfit / totalInvested) * 100 : 0;
  const totalActualReturnPct =
    totalInvested > 0 ? (totalActualProfit / totalInvested) * 100 : 0;

  const fmt = (v) =>
    new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(v);

  const thClass =
    "px-3 py-2.5 cursor-pointer select-none font-semibold text-muted-foreground transition-colors hover:text-foreground";

  function SortIcon({ columnKey }) {
    const { key, direction } = sortConfig;
    if (key !== columnKey) {
      return <CaretUp className="ml-1 inline-block h-3 w-3 text-muted-foreground/30" weight="fill" />;
    }
    return direction === "asc" ? (
      <CaretUp className="ml-1 inline-block h-3 w-3 text-foreground" weight="fill" />
    ) : (
      <CaretDown className="ml-1 inline-block h-3 w-3 text-foreground" weight="fill" />
    );
  }

  return (
    <Card className="overflow-hidden border-border bg-card">
      <CardHeader className="border-b border-border bg-muted/30 pb-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base font-semibold text-foreground">
            {TIMEFRAME_LABELS[timeframe]}
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 border-b border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground sm:px-4">
          <span>
            <span className="font-semibold text-foreground">{nStocks}</span>{" "}
            Saham
          </span>

          <span>
            Rerata Est.:{" "}
            <span
              className={`font-semibold ${
                avgEstReturn >= 0 ? "text-cuan" : "text-loss"
              }`}
            >
              {formatReturn(avgEstReturn)}
            </span>
          </span>
          {avgActualReturn != null && (
            <span>
              Rerata Aktual:{" "}
              <span
                className={`font-semibold ${
                  avgActualReturn >= 0 ? "text-cuan" : "text-loss"
                }`}
              >
                {formatReturn(avgActualReturn)}
              </span>
            </span>
          )}
          <span>
            Investasi:{" "}
            <span className="font-semibold text-foreground">Rp {fmt(totalInvested)}</span>
          </span>
          <span>
            Est. Profit:{" "}
            <span
              className={`font-semibold ${
                totalEstProfit >= 0 ? "text-cuan" : "text-loss"
              }`}
            >
              {totalEstProfit >= 0 ? "+" : ""}Rp {fmt(totalEstProfit)} ({totalEstReturnPct >= 0 ? "+" : ""}
              {totalEstReturnPct.toFixed(2)}%)
            </span>
          </span>
          {totalActualProfit !== 0 && (
            <span>
              Realisasi:{" "}
              <span
                className={`font-semibold ${
                  totalActualProfit >= 0 ? "text-cuan" : "text-loss"
                }`}
              >
                {totalActualProfit >= 0 ? "+" : ""}Rp {fmt(totalActualProfit)} (
                {totalActualReturnPct >= 0 ? "+" : ""}
                {totalActualReturnPct.toFixed(2)}%)
              </span>
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full caption-bottom text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wider text-muted-foreground">
                <th
                  className={`${thClass} text-left`}
                  onClick={() => handleSort("ticker")}
                >
                  Ticker<SortIcon columnKey="ticker" />
                </th>
                <th
                  className={`${thClass} text-left`}
                  onClick={() => handleSort("sector_name")}
                >
                  Sektor<SortIcon columnKey="sector_name" />
                </th>
                <th
                  className={`${thClass} text-left`}
                  onClick={() => handleSort("recommendation")}
                >
                  Rekomendasi<SortIcon columnKey="recommendation" />
                </th>
                <th
                  className={`${thClass} text-left`}
                  onClick={() => handleSort("buy_date")}
                >
                  Buy Date<SortIcon columnKey="buy_date" />
                </th>
                <th
                  className={`${thClass} text-left`}
                  onClick={() => handleSort("sell_date")}
                >
                  Sell Date<SortIcon columnKey="sell_date" />
                </th>
                <th
                  className={`${thClass} text-right`}
                  onClick={() => handleSort("buy_price")}
                >
                  Buy Price<SortIcon columnKey="buy_price" />
                </th>
                <th
                  className={`${thClass} text-right`}
                  onClick={() => handleSort("estimated_sell_price")}
                >
                  Est. Sell<SortIcon columnKey="estimated_sell_price" />
                </th>
                <th
                  className={`${thClass} text-right`}
                  onClick={() => handleSort("actual_sell_price")}
                >
                  Actual Sell<SortIcon columnKey="actual_sell_price" />
                </th>
                <th
                  className={`${thClass} text-right`}
                  onClick={() => handleSort("predicted_return_pct")}
                >
                  Est. Return<SortIcon columnKey="predicted_return_pct" />
                </th>
                <th
                  className={`${thClass} text-right`}
                  onClick={() => handleSort("actual_return_pct")}
                >
                  Actual Return<SortIcon columnKey="actual_return_pct" />
                </th>
                <th
                  className={`${thClass} text-center`}
                  onClick={() => handleSort("status")}
                >
                  Status<SortIcon columnKey="status" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedStocks.map((stock) => (
                <tr
                  key={stock.ticker}
                  className="border-b border-border transition-colors hover:bg-muted/30"
                >
                  <td className="px-3 py-2.5">
                    <span className="font-semibold text-foreground">
                      {stock.ticker}
                    </span>
                    {stock.company_name && (
                      <p className="max-w-[120px] truncate text-xs text-muted-foreground">
                        {stock.company_name}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <span className="text-xs text-muted-foreground">
                      {stock.sector_name || "-"}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <Badge
                      className="text-[10px]"
                      variant={
                        stock.recommendation?.includes("Strong Buy") ? "default" :
                        stock.recommendation === "Buy" ? "secondary" : "outline"
                      }
                    >
                      {stock.recommendation || "-"}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">
                    {stock.buy_date}
                  </td>
                  <td className="px-3 py-2.5 text-xs text-muted-foreground">
                    {stock.sell_date}
                  </td>
                  <td className="px-3 py-2.5 text-right font-medium text-foreground tabular-nums">
                    {formatPrice(stock.buy_price)}
                  </td>
                  <td className="px-3 py-2.5 text-right text-muted-foreground tabular-nums">
                    {formatPrice(stock.estimated_sell_price)}
                  </td>
                  <td className="px-3 py-2.5 text-right font-medium text-foreground tabular-nums">
                    {formatPrice(stock.actual_sell_price)}
                  </td>
                  <td
                    className={`px-3 py-2.5 text-right font-semibold tabular-nums ${getReturnColor(stock.predicted_return_pct)}`}
                  >
                    {formatReturn(stock.predicted_return_pct)}
                  </td>
                  <td
                    className={`px-3 py-2.5 text-right font-semibold tabular-nums ${getReturnColor(stock.actual_return_pct)}`}
                  >
                    <span className="flex items-center justify-end gap-1">
                      {stock.actual_return_pct !== null &&
                        stock.actual_return_pct !== undefined &&
                        (stock.actual_return_pct >= 0 ? (
                          <ArrowUp
                            className="h-3 w-3 text-cuan"
                            weight="bold"
                          />
                        ) : (
                          <ArrowDown
                            className="h-3 w-3 text-loss"
                            weight="bold"
                          />
                        ))}
                      {formatReturn(stock.actual_return_pct)}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-center">
                    <Badge
                      variant={stock.status === "closed" ? "secondary" : "default"}
                      className="text-[10px]"
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
  const [marketOpen, setMarketOpen] = useState(true);
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
        const isOpen = resp.data.market_open !== false;
        setMarketOpen(isOpen);
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
          if (!isOpen) {
            clearTimeout(timeoutId);
            setPreparing(false);
            setLoading(false);
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
      setMarketOpen(response.data.market_open !== false);
      if (response.data.success) {
        const sims = response.data.simulations || [];
        if (sims.length > 0) {
          const merged = mergePrices(sims);
          setSimulations(merged);
          setGeneratedAt(response.data.generated_at);
          lsSet(LS_ORDER_KEY, merged);
        } else if (response.data.market_open !== false) {
          triggerCacheRefresh();
          startPolling();
        }
      } else if (response.data.market_open !== false) {
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
    if (!marketOpen) {
      if (priceIntervalRef.current) {
        clearInterval(priceIntervalRef.current);
        priceIntervalRef.current = null;
      }
      return;
    }
    setPriceUpdating(true);
    try {
      const resp = await axios.get(`${API_BASE}/order-book/simulation?refresh=true`);
      setMarketOpen(resp.data.market_open !== false);
      if (!resp.data.market_open) {
        if (priceIntervalRef.current) {
          clearInterval(priceIntervalRef.current);
          priceIntervalRef.current = null;
        }
      }
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
      // silent fail
    } finally {
      setPriceUpdating(false);
    }
  }, [marketOpen, mergePrices]);

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
    if (simulations.length > 0 && marketOpen) {
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
  }, [simulations, refreshPrices, marketOpen]);

  const groupedSimulations = useMemo(() => groupByTimeframe(simulations), [simulations]);

  const statItems = useMemo(() => {
    const totalOrders = groupedSimulations.reduce((sum, s) => sum + s.stocks.length, 0);
    const openOrders = groupedSimulations.reduce((sum, s) => sum + s.stocks.filter((st) => st.status === "open").length, 0);
    const closedOrders = totalOrders - openOrders;
    return [
      { label: "Total Order", value: totalOrders, description: "Semua timeframe", icon: Scroll },
      { label: "Open", value: openOrders, description: "Menunggu close", icon: TrendUp },
      { label: "Closed", value: closedOrders, description: "Selesai", icon: SealCheck },
      {
        label: "Terakhir",
        value: generatedAt ? new Date(generatedAt).toLocaleString("id-ID", { dateStyle: "full", timeStyle: "short" }) : "-",
        description: "Update sistem",
        icon: Clock,
      },
    ];
  }, [groupedSimulations, generatedAt]);

  if (preparing) {
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-2">
          <Scroll className="h-5 w-5 text-foreground" />
          <h2 className="text-xl font-bold text-foreground">Order Book Simulation</h2>
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
      <div className="space-y-5">
        <div className="flex items-center gap-2">
          <Scroll className="h-5 w-5 text-foreground" />
          <h2 className="text-xl font-bold text-foreground">Order Book Simulation</h2>
        </div>
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-foreground" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Scroll className="h-5 w-5 text-foreground" />
          <h2 className="text-xl font-bold text-foreground">Order Book Simulation</h2>
        </div>
        {priceUpdating && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <div className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-border border-t-foreground" />
            Memperbarui harga...
          </div>
        )}
      </div>

      <StatCardGrid items={statItems} columns={4} />

      {groupedSimulations.length > 0 && <PortfolioSummary simulations={groupedSimulations} />}

      {groupedSimulations.length === 0 ? (
        <Card className="border-border bg-card">
          <CardContent className="flex flex-col items-center justify-center py-16">
            <CurrencyCircleDollar className="mb-4 h-10 w-10 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">Belum ada data simulasi. Jalankan scheduler terlebih dahulu.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {groupedSimulations.map((sim) => (
            <TimeframeCard key={sim.timeframe} simulation={sim} />
          ))}
        </div>
      )}
    </div>
  );
}
