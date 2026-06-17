import { useMemo } from "react";
import { Sparkle } from "@phosphor-icons/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const formatNum = (v, d = 1) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
  return Number(v).toFixed(d);
};

const formatPct = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
  return `${Number(v).toFixed(1)}%`;
};

function SectorRow({ sector }) {
  const score = sector.avgScore;
  const scoreClass = score >= 75 ? "text-emerald-600" : score >= 60 ? "text-sky-600" : score >= 45 ? "text-amber-600" : "text-red-600";
  return (
    <tr className="border-b border-slate-100 transition-colors hover:bg-slate-50/80 last:border-0">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-900">{sector.sector}</span>
        </div>
      </td>
      <td className="px-4 py-3 text-right tabular-nums text-sm font-semibold text-slate-700">{sector.count}</td>
      <td className={`px-4 py-3 text-right tabular-nums text-sm font-semibold ${scoreClass}`}>{formatNum(sector.avgScore)}</td>
      <td className="px-4 py-3 text-right tabular-nums text-sm text-slate-600">{formatNum(sector.avgPer, 1)}x</td>
      <td className="px-4 py-3 text-right tabular-nums text-sm text-slate-600">{formatNum(sector.avgPbv, 1)}x</td>
      <td className="px-4 py-3 text-right tabular-nums text-sm text-slate-600">{formatPct(sector.avgRoe)}</td>
      <td className="px-4 py-3 text-right tabular-nums text-sm text-slate-600">{formatPct(sector.avgDivYield)}</td>
    </tr>
  );
}

export default function InvestmentSummary({ companies }) {
  const sectors = useMemo(() => {
    if (!companies || companies.length === 0) return [];

    const map = {};
    for (const item of companies) {
      const sec = item.sector || "Lainnya";
      if (!map[sec]) {
        map[sec] = { sector: sec, count: 0, scoreSum: 0, perSum: 0, pbvSum: 0, roeSum: 0, divYieldSum: 0 };
      }
      map[sec].count += 1;
      const score = item.analysis?.investmentScore;
      if (score !== null && score !== undefined && !Number.isNaN(Number(score))) map[sec].scoreSum += Number(score);
      if (item.per !== null && item.per !== undefined && !Number.isNaN(Number(item.per))) map[sec].perSum += Number(item.per);
      if (item.pbv !== null && item.pbv !== undefined && !Number.isNaN(Number(item.pbv))) map[sec].pbvSum += Number(item.pbv);
      if (item.roe !== null && item.roe !== undefined && !Number.isNaN(Number(item.roe))) map[sec].roeSum += Number(item.roe);
      if (item.dividend_yield !== null && item.dividend_yield !== undefined && !Number.isNaN(Number(item.dividend_yield))) map[sec].divYieldSum += Number(item.dividend_yield);
    }

    return Object.values(map).map((s) => ({
      ...s,
      avgScore: s.count > 0 ? s.scoreSum / s.count : 0,
      avgPer: s.count > 0 ? s.perSum / s.count : 0,
      avgPbv: s.count > 0 ? s.pbvSum / s.count : 0,
      avgRoe: s.count > 0 ? s.roeSum / s.count : 0,
      avgDivYield: s.count > 0 ? s.divYieldSum / s.count : 0,
    })).sort((a, b) => b.count - a.count);
  }, [companies]);

  const totalCompanies = companies?.length || 0;

  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader className="border-b border-slate-100 p-4 sm:p-5">
        <div className="flex items-center gap-2">
          <Sparkle className="h-4 w-4 text-emerald-500" weight="fill" />
          <CardTitle className="text-sm font-semibold text-slate-900 sm:text-base">
            Ringkasan Investasi per Sektor
          </CardTitle>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {totalCompanies} saham dianalisis dari {sectors.length} sektor
        </p>
      </CardHeader>
      <CardContent className="p-0">
        {sectors.length === 0 ? (
          <div className="flex h-[200px] items-center justify-center text-sm text-slate-400">
            {totalCompanies === 0 ? "Menunggu data screener..." : "Data sektor tidak tersedia"}
          </div>
        ) : (
          <div className="h-[280px] overflow-y-auto">
            <table className="w-full caption-bottom text-sm">
              <thead className="sticky top-0 z-10 bg-white">
                <tr>
                  <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-500">Sektor</th>
                  <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-500">Emiten</th>
                  <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-500">Skor</th>
                  <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-500">PER</th>
                  <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-500">PBV</th>
                  <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-500">ROE</th>
                  <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-500">Yield</th>
                </tr>
              </thead>
              <tbody>
                {sectors.map((sec) => (
                  <SectorRow key={sec.sector} sector={sec} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
