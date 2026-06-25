import { Building2, Sparkle } from "lucide-react";
import { SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, toneClasses } from "@/lib/screener";

export default function CompanyDetailHeader({ company, insightBadges }) {
  return (
    <div className="border-b border-border bg-card p-4 sm:p-5">
      <SheetHeader className="space-y-3 text-left">
        <div className="flex items-start gap-3 sm:gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-foreground text-sm font-semibold text-background sm:h-12 sm:w-12 sm:text-base" data-testid="company-detail-logo">{company.logoText}</div>
          <div className="min-w-0 space-y-1.5">
            <div className="inline-flex w-fit rounded-md border border-border bg-muted/50 px-2 py-0.5 text-[11px] font-medium text-muted-foreground" data-testid="company-detail-code">{company.stockCode}</div>
            <SheetTitle className="text-base font-semibold text-foreground sm:text-lg" data-testid="company-detail-name">{company.companyName}</SheetTitle>
            <SheetDescription className="text-sm leading-5 text-muted-foreground" data-testid="company-detail-industry-description">{company.industryDescription}</SheetDescription>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground" data-testid="company-detail-industry-row">
          <Building2 className="h-4 w-4" />
          <span>{company.industry}</span>
          <span className="text-border">•</span>
          <span className="font-medium text-foreground" data-testid="company-detail-price">{formatCurrency(company.price)}</span>
        </div>

        <div className="flex flex-wrap gap-1.5" data-testid="company-detail-insight-badges">
          {insightBadges.map((insight) => (
            <Badge key={insight.label} className={`rounded-md border px-2 py-0.5 text-xs font-medium ${toneClasses[insight.tone]}`} data-testid={`company-detail-insight-${insight.label.toLowerCase().replace(/\s+/g, "-")}`} variant="outline">
              {insight.label}
            </Badge>
          ))}
        </div>

        <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm leading-5 text-muted-foreground" data-testid="company-detail-analyst-angle">
          <span className="font-semibold text-foreground">Analyst angle:</span> {company.analystAngle}
        </div>
      </SheetHeader>
    </div>
  );
}
