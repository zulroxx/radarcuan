import { Sheet, SheetContent, SheetDescription } from "@/components/ui/sheet";
import CompanyDetailHeader from "@/components/company-detail/CompanyDetailHeader";
import CompanyDetailTabs from "@/components/company-detail/CompanyDetailTabs";
import CompanyMetricGrid from "@/components/company-detail/CompanyMetricGrid";
import useCompanyDetailState from "@/hooks/useCompanyDetailState";

export default function CompanyDetailSheet({ company, companies, open, onOpenChange }) {
  const { activeTab, setActiveTab, insightBadges, sectorBenchmark } = useCompanyDetailState({ company, companies, open });

  if (!company || !sectorBenchmark) {
    return null;
  }

  return (
    <Sheet onOpenChange={onOpenChange} open={open}>
      <SheetContent className="w-full overflow-y-auto border-l border-border bg-background p-0 sm:max-w-4xl" data-testid="company-detail-sheet">
        <SheetDescription className="sr-only">Detail perusahaan {company.ticker}</SheetDescription>
        <CompanyDetailHeader company={company} insightBadges={insightBadges} />

        <div className="space-y-4 p-4 sm:p-5">
          <CompanyMetricGrid company={company} />
          <CompanyDetailTabs
            activeTab={activeTab}
            company={company}
            onTabChange={setActiveTab}
            open={open}
            sectorBenchmark={sectorBenchmark}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
}
