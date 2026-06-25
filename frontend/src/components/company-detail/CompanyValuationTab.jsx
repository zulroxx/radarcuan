import { Line, LineChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DeferredChart from "@/components/company-detail/DeferredChart";
import { PER_DOT, ROE_DOT } from "@/components/company-detail/constants";
import { formatCurrency, formatPercent, formatRatio } from "@/lib/screener";

function SummaryTile({ label, testId, value }) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-4" data-testid={testId}>
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-lg font-semibold text-foreground">{value}</p>
    </div>
  );
}

export default function CompanyValuationTab({ active, company }) {
  const hasValuation = company.valuationSummary && company.valuationSummary.fairValueRange;
  const hasRatioTrend = company.ratioTrend && company.ratioTrend.length > 0;
  
  if (!hasValuation) {
    return (
      <div className="space-y-4" data-testid="company-detail-tab-content-valuation">
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-lg text-foreground">Valuation summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Data valuasi belum tersedia untuk saham ini.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="company-detail-tab-content-valuation">
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-border bg-card" data-testid="company-detail-valuation-summary-card">
          <CardHeader>
            <CardTitle className="text-lg text-foreground">Valuation summary</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <SummaryTile label="Fair value range" testId="company-detail-fair-value-range" value={`${formatCurrency(company.valuationSummary.fairValueRange[0])} - ${formatCurrency(company.valuationSummary.fairValueRange[1])}`} />
            <SummaryTile label="Earnings yield" testId="company-detail-earnings-yield" value={formatPercent(company.valuationSummary.earningsYield)} />
            <SummaryTile label="Median PER 3Y" testId="company-detail-median-per-3y" value={formatRatio(company.valuationSummary.medianPer3Y)} />
            <SummaryTile label="Revenue CAGR 3Y" testId="company-detail-revenue-cagr-3y" value={formatPercent(company.valuationSummary.revenueCagr3Y)} />
            <SummaryTile label="Payout ratio terbaru" testId="company-detail-payout-ratio-latest" value={formatPercent(company.valuationSummary.payoutRatioLatest)} />
            <SummaryTile label="FCF coverage" testId="company-detail-fcf-coverage" value={formatRatio(company.valuationSummary.fcfCoverage)} />
          </CardContent>
        </Card>

        <Card className="border-border bg-card" data-testid="company-detail-trend-card">
          <CardHeader>
            <CardTitle className="text-lg text-foreground">Key Ratio Trend</CardTitle>
            <p className="text-sm text-muted-foreground" data-testid="company-detail-trend-description">Pergerakan ROE dan PER dalam 3 tahun terakhir untuk memvalidasi konsistensi fundamental.</p>
          </CardHeader>
          <CardContent>
            {hasRatioTrend ? (
              <DeferredChart active={active} className="h-[320px] w-full" testId="company-detail-trend-chart">
                {({ height, width }) => (
                  <LineChart data={company.ratioTrend} height={height} width={width}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="year" stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                    <YAxis stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                    <Tooltip formatter={(value, name) => [name === "roe" ? formatPercent(value) : formatRatio(value), name === "roe" ? "ROE" : "PER"]} />
                    <Legend />
                    <Line dataKey="roe" dot={ROE_DOT} name="ROE" stroke="hsl(var(--cuan))" strokeWidth={3} type="monotone" />
                    <Line dataKey="per" dot={PER_DOT} name="PER" stroke="hsl(var(--foreground))" strokeWidth={3} type="monotone" />
                  </LineChart>
                )}
              </DeferredChart>
            ) : (
              <p className="text-sm text-muted-foreground">Data trend ratio belum tersedia.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}