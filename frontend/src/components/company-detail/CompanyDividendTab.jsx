import { Bar, BarChart, CartesianGrid, Cell, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DeferredChart from "@/components/company-detail/DeferredChart";
import { BAR_RADIUS, COMPANY_DETAIL_TABLE_CELL_CLASS } from "@/components/company-detail/constants";
import { formatPercent } from "@/lib/screener";

function getYieldFill(yieldValue) {
  return yieldValue >= 5 ? "#10B981" : "#94A3B8";
}

export default function CompanyDividendTab({ active, company }) {
  const hasDividendHistory = company.dividendHistory && company.dividendHistory.length > 0;
  
  if (!hasDividendHistory) {
    return (
      <div className="space-y-4" data-testid="company-detail-tab-content-dividend">
        <Card className="border-slate-200 bg-white">
          <CardHeader>
            <CardTitle className="text-lg text-slate-950">Riwayat dividen</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-500">Data riwayat dividen belum tersedia untuk saham ini.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="company-detail-tab-content-dividend">
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-[1fr_1fr]">
        <Card className="border-slate-200 bg-white" data-testid="company-detail-dividend-history-card">
          <CardHeader>
            <CardTitle className="text-lg text-slate-950">Riwayat dividen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-auto rounded-2xl border border-slate-200">
              <table className="w-full min-w-[520px]">
                <thead className="bg-slate-50">
                  <tr>
                    <th className={COMPANY_DETAIL_TABLE_CELL_CLASS}>Tahun</th>
                    <th className={COMPANY_DETAIL_TABLE_CELL_CLASS}>DPS</th>
                    <th className={COMPANY_DETAIL_TABLE_CELL_CLASS}>Payout Ratio</th>
                    <th className={COMPANY_DETAIL_TABLE_CELL_CLASS}>Yield</th>
                  </tr>
                </thead>
                <tbody>
                  {company.dividendHistory.map((row) => (
                    <tr key={row.year} data-testid={`company-detail-dividend-row-${row.year}`}>
                      <td className={COMPANY_DETAIL_TABLE_CELL_CLASS}>{row.year}</td>
                      <td className={COMPANY_DETAIL_TABLE_CELL_CLASS}>Rp{row.dividendPerShare.toLocaleString("id-ID")}</td>
                      <td className={COMPANY_DETAIL_TABLE_CELL_CLASS}>{formatPercent(row.payoutRatio)}</td>
                      <td className={COMPANY_DETAIL_TABLE_CELL_CLASS}>{formatPercent(row.yield)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white" data-testid="company-detail-dividend-chart-card">
          <CardHeader>
            <CardTitle className="text-lg text-slate-950">Payout & yield trend</CardTitle>
          </CardHeader>
          <CardContent>
            <DeferredChart active={active} className="h-[300px] w-full" testId="company-detail-dividend-chart">
              {({ height, width }) => (
                <BarChart data={company.dividendHistory} height={height} width={width}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="year" stroke="#64748B" tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748B" tickLine={false} axisLine={false} />
                  <Tooltip formatter={(value, name) => [formatPercent(value), name === "payoutRatio" ? "Payout Ratio" : "Yield"]} />
                  <Legend />
                  <Bar dataKey="payoutRatio" fill="#0F172A" name="Payout Ratio" radius={BAR_RADIUS} />
                  <Bar dataKey="yield" name="Yield" radius={BAR_RADIUS}>
                    {company.dividendHistory.map((entry) => (
                      <Cell key={entry.year} fill={getYieldFill(entry.yield)} />
                    ))}
                  </Bar>
                </BarChart>
              )}
            </DeferredChart>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}