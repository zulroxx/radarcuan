import { Activity, BadgeDollarSign, ChartBar, Landmark, ShieldCheck, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCompactCurrency, formatCurrency, formatPercent, formatRatio, getMetricTone, toneClasses } from "@/lib/screener";

function buildMetricCards(company) {
  return [
    { label: "PER", value: formatRatio(company.per), icon: TrendingUp, tone: getMetricTone("per", company.per) },
    { label: "ROE", value: formatPercent(company.roe), icon: Activity, tone: getMetricTone("roe", company.roe) },
    { label: "Dividend Yield", value: formatPercent(company.dividendYield), icon: ChartBar, tone: getMetricTone("dividendYield", company.dividendYield) },
    { label: "DER", value: formatRatio(company.der), icon: ShieldCheck, tone: getMetricTone("der", company.der) },
  ];
}

function buildFinancialCards(company) {
  // Handle missing financial data gracefully (for TradingView data)
  const hasFinancials = company.annualFinancials && company.annualFinancials.balanceSheet;
  const latestBalance = hasFinancials ? company.annualFinancials.balanceSheet.at(-1) : null;
  const latestCashFlow = hasFinancials ? company.annualFinancials.cashFlow.at(-1) : null;
  const valuation = company.valuationSummary || {};

  return [
    { label: "Aset 2024", value: hasFinancials ? formatCompactCurrency(latestBalance.assets) : "N/A", icon: Landmark },
    { label: "Kas 2024", value: hasFinancials ? formatCompactCurrency(latestBalance.cash) : "N/A", icon: BadgeDollarSign },
    { label: "Free Cash Flow", value: hasFinancials ? formatCompactCurrency(latestCashFlow.freeCashFlow) : "N/A", icon: ChartBar },
    { label: "Margin of Safety", value: valuation.marginOfSafetyPrice ? formatCurrency(valuation.marginOfSafetyPrice) : "N/A", icon: TrendingUp },
  ];
}

function MetricCard({ item }) {
  let badgeLabel = "Netral";
  if (item.tone === "good") {
    badgeLabel = "Positif";
  } else if (item.tone === "warning") {
    badgeLabel = "Perlu perhatian";
  }

  return (
    <Card className="border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid={`company-detail-metric-${item.label.toLowerCase().replace(/\s+/g, "-")}`}>
      <CardContent className="flex items-center justify-between gap-4 p-4 sm:p-5">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400">{item.label}</p>
          <p className="mt-1.5 text-xl font-semibold text-slate-950 sm:text-2xl dark:text-slate-50">{item.value}</p>
          <Badge className={`mt-2 rounded-md border px-2 py-0.5 text-[10px] font-medium ${toneClasses[item.tone]}`} data-testid={`company-detail-metric-tone-${item.label.toLowerCase().replace(/\s+/g, "-")}`} variant="outline">
            {badgeLabel}
          </Badge>
        </div>
        <item.icon className="h-7 w-7 shrink-0 text-emerald-500 sm:h-8 sm:w-8" />
      </CardContent>
    </Card>
  );
}

function HighlightCard({ item }) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900" data-testid={`company-detail-highlight-${item.label.toLowerCase().replace(/\s+/g, "-")}`}>
      <CardContent className="flex items-center justify-between gap-4 p-4 sm:p-5">
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400">{item.label}</p>
          <p className="mt-1.5 text-base font-semibold text-slate-950 sm:text-xl dark:text-slate-50">{item.value}</p>
        </div>
        <item.icon className="h-7 w-7 shrink-0 text-slate-400 sm:h-8 sm:w-8 dark:text-slate-500" />
      </CardContent>
    </Card>
  );
}

export default function CompanyMetricGrid({ company }) {
  const metricCards = buildMetricCards(company);
  const financialCards = buildFinancialCards(company);

  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-4">
        {metricCards.map((item) => <MetricCard item={item} key={item.label} />)}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-2 md:gap-4 xl:grid-cols-4">
        {financialCards.map((item) => <HighlightCard item={item} key={item.label} />)}
      </div>
    </>
  );
}