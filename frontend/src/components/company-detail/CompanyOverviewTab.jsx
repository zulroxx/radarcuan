import { ShieldCheck, AlertTriangle } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import DeferredChart from "@/components/company-detail/DeferredChart";
import { BAR_RADIUS } from "@/components/company-detail/constants";
import { formatCurrency, formatPercent, formatRatio, toneClasses } from "@/lib/screener";

function buildBenchmarkCards(company, benchmark) {
  return [
    { label: "PER", companyValue: company.per, sectorValue: benchmark.per, formatter: formatRatio, betterDirection: "lower" },
    { label: "PBV", companyValue: company.pbv, sectorValue: benchmark.pbv, formatter: formatRatio, betterDirection: "lower" },
    { label: "ROE", companyValue: company.roe, sectorValue: benchmark.roe, formatter: formatPercent, betterDirection: "higher" },
    { label: "Div. Yield", companyValue: company.dividendYield, sectorValue: benchmark.dividendYield, formatter: formatPercent, betterDirection: "higher" },
  ];
}

function getCompareTone(companyValue, sectorValue, betterDirection) {
  const isBetter = betterDirection === "higher" ? companyValue >= sectorValue : companyValue <= sectorValue;
  return isBetter ? "good" : "warning";
}

function BenchmarkCard({ item }) {
  const tone = getCompareTone(item.companyValue, item.sectorValue, item.betterDirection);

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3" data-testid={`company-detail-benchmark-${item.label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-foreground">{item.label}</p>
        <Badge className={`rounded-md border px-2 py-0.5 text-[10px] font-medium ${toneClasses[tone]}`} variant="outline">
          {tone === "good" ? "Di atas benchmark" : "Di bawah benchmark"}
        </Badge>
      </div>
      <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-muted-foreground">Emiten</p>
          <p className="font-semibold text-foreground">{item.formatter(item.companyValue)}</p>
        </div>
        <div>
          <p className="text-muted-foreground">Rata-rata sektor</p>
          <p className="font-semibold text-foreground">{item.formatter(item.sectorValue)}</p>
        </div>
      </div>
    </div>
  );
}

function ListCard({ icon: Icon, items, testIdPrefix, title, toneClass }) {
  return (
    <Card className="border-border bg-card" data-testid={`${testIdPrefix}-card`}>
      <CardHeader>
        <CardTitle className="text-base text-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={item} className="flex items-start gap-3 text-sm text-muted-foreground" data-testid={`${testIdPrefix}-${index + 1}`}>
              <Icon className={`mt-0.5 h-4 w-4 ${toneClass}`} />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function CompanyOverviewTab({ active, company, sectorBenchmark }) {
  const benchmarkCards = buildBenchmarkCards(company, sectorBenchmark);
  const hasQuarterlyData = company.revenueNetIncomeQuarters && company.revenueNetIncomeQuarters.length > 0;
  const hasStrengths = company.strengths && company.strengths.length > 0;
  const hasRisks = company.risks && company.risks.length > 0;

  return (
    <div className="space-y-4" data-testid="company-detail-tab-content-overview">
      <div className="grid gap-4 lg:grid-cols-1 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-border bg-card" data-testid="company-detail-financials-card">
          <CardHeader>
            <CardTitle className="text-base text-foreground">Mini Financials</CardTitle>
            <p className="text-sm text-muted-foreground" data-testid="company-detail-financials-description">Visualisasi revenue versus net income dalam 4 kuartal terakhir.</p>
          </CardHeader>
          <CardContent>
            {hasQuarterlyData ? (
              <DeferredChart active={active} className="h-[260px] w-full" testId="company-detail-financials-chart">
                {({ height, width }) => (
                  <BarChart data={company.revenueNetIncomeQuarters} height={height} width={width}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                    <XAxis dataKey="quarter" stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
                    <YAxis stroke="hsl(var(--muted-foreground))" tickFormatter={(value) => `${value / 1000}T`} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(value) => [formatCurrency(value), "Nilai"]} />
                    <Legend />
                  <Bar dataKey="revenue" fill="hsl(var(--chart-1))" name="Revenue" radius={BAR_RADIUS} />
                  <Bar dataKey="netIncome" fill="hsl(var(--chart-2))" name="Net Income" radius={BAR_RADIUS} />
                  </BarChart>
                )}
              </DeferredChart>
            ) : (
              <p className="text-sm text-muted-foreground">Data kuartalan belum tersedia untuk saham ini.</p>
            )}
          </CardContent>
        </Card>

        <Card className="border-border bg-card" data-testid="company-detail-benchmark-card">
          <CardHeader>
            <CardTitle className="text-base text-foreground">Benchmark vs sektor</CardTitle>
            <p className="text-sm text-muted-foreground" data-testid="company-detail-benchmark-description">Perbandingan sederhana dengan rata-rata {company.industry} ({sectorBenchmark.peerCount} emiten).</p>
          </CardHeader>
          <CardContent className="space-y-3">
            {benchmarkCards.map((item) => <BenchmarkCard item={item} key={item.label} />)}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {hasStrengths ? (
          <ListCard icon={ShieldCheck} items={company.strengths} testIdPrefix="company-detail-strength" title="Key highlights" toneClass="text-cuan" />
        ) : (
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-base text-foreground">Key highlights</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Data kekuatan belum tersedia.</p>
            </CardContent>
          </Card>
        )}
        {hasRisks ? (
          <ListCard icon={AlertTriangle} items={company.risks} testIdPrefix="company-detail-risk" title="Risiko utama" toneClass="text-loss" />
        ) : (
          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-base text-foreground">Risiko utama</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Data risiko belum tersedia.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
