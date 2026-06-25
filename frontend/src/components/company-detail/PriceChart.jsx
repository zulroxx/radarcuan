import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import axios from "axios";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_BASE = `${BACKEND_URL}/api`;

const PERIODS = [
  { value: "1mo", label: "1 Bulan" },
  { value: "3mo", label: "3 Bulan" },
  { value: "6mo", label: "6 Bulan" },
  { value: "1y", label: "1 Tahun" },
  { value: "ytd", label: "YTD" },
  { value: "max", label: "Max" },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">
        Rp{new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(p.close)}
      </p>
      <div className="mt-1.5 space-y-0.5 text-[11px] text-muted-foreground">
        <p>O: Rp{new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(p.open)}</p>
        <p>H: Rp{new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(p.high)}</p>
        <p>L: Rp{new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0 }).format(p.low)}</p>
        <p>Vol: {new Intl.NumberFormat("id-ID", { notation: "compact" }).format(p.volume)}</p>
      </div>
    </div>
  );
}

function formatXAxis(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

function formatYAxis(value) {
  if (value >= 1000) return `${(value / 1000).toFixed(0)}K`;
  return value.toFixed(0);
}

export default function PriceChart({ ticker }) {
  const [prices, setPrices] = useState([]);
  const [period, setPeriod] = useState("3mo");
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!ticker) return;
    setLoading(true);
    try {
      const resp = await axios.get(`${API_BASE}/stocks/${ticker}/history?period=${period}`);
      if (resp.data.success) {
        setPrices(resp.data.prices || []);
      }
    } catch {
      setPrices([]);
    } finally {
      setLoading(false);
    }
  }, [ticker, period]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const textColor = "hsl(var(--muted-foreground))";
  const gridColor = "hsl(var(--border))";
  const areaColor = "hsl(var(--chart-2))";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              period === p.value
                ? "bg-foreground text-background"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
            onClick={() => setPeriod(p.value)}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-[300px] items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-foreground" />
        </div>
      ) : prices.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-muted-foreground">
          Data harga tidak tersedia
        </div>
      ) : (
        <div className="h-[300px]">
          <ResponsiveContainer height="100%" width="100%">
            <AreaChart data={prices} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${ticker}`} x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor={areaColor} stopOpacity={0.2} />
                  <stop offset="95%" stopColor={areaColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={gridColor} strokeDasharray="3 3" vertical={false} />
              <XAxis
                axisLine={false}
                dataKey="date"
                fontSize={11}
                minTickGap={40}
                stroke={textColor}
                tickFormatter={formatXAxis}
                tickLine={false}
              />
              <YAxis
                axisLine={false}
                domain={["auto", "auto"]}
                fontSize={11}
                stroke={textColor}
                tickFormatter={formatYAxis}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: gridColor, strokeDasharray: "3 3" }} />
              <Area
                animationDuration={300}
                dataKey="close"
                fill={`url(#gradient-${ticker})`}
                stroke={areaColor}
                strokeWidth={2}
                type="monotone"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
