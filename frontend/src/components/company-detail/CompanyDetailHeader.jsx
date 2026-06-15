import { Building2 } from "lucide-react";
import { SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, toneClasses } from "@/lib/screener";

export default function CompanyDetailHeader({ company, insightBadges }) {
  return (
    <div className="border-b border-slate-200 bg-white p-5 sm:p-6">
      <SheetHeader className="space-y-4 text-left">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-base font-semibold text-white sm:h-14 sm:w-14 sm:text-lg" data-testid="company-detail-logo">{company.logoText}</div>
          <div className="min-w-0 space-y-1.5">
            <div className="inline-flex w-fit rounded-md border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700" data-testid="company-detail-code">{company.stockCode}</div>
            <SheetTitle className="text-lg font-semibold text-slate-950 sm:text-xl" data-testid="company-detail-name">{company.companyName}</SheetTitle>
            <SheetDescription className="text-sm leading-6 text-slate-600" data-testid="company-detail-industry-description">{company.industryDescription}</SheetDescription>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500" data-testid="company-detail-industry-row">
          <Building2 className="h-4 w-4" />
          <span>{company.industry}</span>
          <span className="text-slate-300">•</span>
          <span className="font-medium text-slate-700" data-testid="company-detail-price">{formatCurrency(company.price)}</span>
        </div>

        <div className="flex flex-wrap gap-1.5" data-testid="company-detail-insight-badges">
          {insightBadges.map((insight) => (
            <Badge key={insight.label} className={`rounded-md border px-2.5 py-0.5 text-xs font-medium ${toneClasses[insight.tone]}`} data-testid={`company-detail-insight-${insight.label.toLowerCase().replace(/\s+/g, "-")}`} variant="outline">
              {insight.label}
            </Badge>
          ))}
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-sm leading-6 text-slate-600" data-testid="company-detail-analyst-angle">
          <span className="font-semibold text-slate-950">Analyst angle:</span> {company.analystAngle}
        </div>
      </SheetHeader>
    </div>
  );
}