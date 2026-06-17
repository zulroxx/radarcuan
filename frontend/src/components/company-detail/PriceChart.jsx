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
    <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-lg">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-slate-900">
        Rp{new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(p.close)}
      </p>
      <div className="mt-1.5 space-y-0.5 text-[11px] text-slate-500">
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

  const textColor = "#64748b";
  const gridColor = "#e2e8f0";
  const areaColor = "#059669";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              period === p.value
                ? "bg-emerald-100 text-emerald-700"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
            onClick={() => setPeriod(p.value)}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex h-[300px] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-500" />
        </div>
      ) : prices.length === 0 ? (
        <div className="flex h-[300px] items-center justify-center text-sm text-slate-400">
          Data harga tidak tersedia
        </div>
      ) : (
        <div className="h-[300px]">
          <ResponsiveContainer height="100%" width="100%">
            <AreaChart data={prices} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${ticker}`} x1="0" x2="0" y1="0" y2="1">
                  <stop offset="5%" stopColor={areaColor} stopOpacity={0.3} />
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