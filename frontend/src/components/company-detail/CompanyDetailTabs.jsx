import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CompanyOverviewTab from "@/components/company-detail/CompanyOverviewTab";
import CompanyFinancialsTab from "@/components/company-detail/CompanyFinancialsTab";
import CompanyDividendTab from "@/components/company-detail/CompanyDividendTab";
import CompanyValuationTab from "@/components/company-detail/CompanyValuationTab";
import PriceChart from "@/components/company-detail/PriceChart";

export default function CompanyDetailTabs({ activeTab, company, onTabChange, open, sectorBenchmark }) {
  return (
    <Tabs className="space-y-4" onValueChange={onTabChange} value={activeTab}>
      <TabsList className="h-auto w-full flex-wrap justify-start gap-1 rounded-xl border border-slate-200 bg-slate-50/50 p-1 sm:w-auto">
        <TabsTrigger className="rounded-lg px-3 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm sm:px-4 sm:py-2 sm:text-sm" data-testid="company-detail-tab-overview" value="overview">Overview</TabsTrigger>
        <TabsTrigger className="rounded-lg px-3 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm sm:px-4 sm:py-2 sm:text-sm" data-testid="company-detail-tab-financials" value="financials">Financials</TabsTrigger>
        <TabsTrigger className="rounded-lg px-3 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm sm:px-4 sm:py-2 sm:text-sm" data-testid="company-detail-tab-dividend" value="dividend">Dividend</TabsTrigger>
        <TabsTrigger className="rounded-lg px-3 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm sm:px-4 sm:py-2 sm:text-sm" data-testid="company-detail-tab-valuation" value="valuation">Valuation</TabsTrigger>
        <TabsTrigger className="rounded-lg px-3 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:shadow-sm sm:px-4 sm:py-2 sm:text-sm" value="chart">Chart</TabsTrigger>
      </TabsList>

      <TabsContent value="overview">
        <CompanyOverviewTab active={open && activeTab === "overview"} company={company} sectorBenchmark={sectorBenchmark} />
      </TabsContent>
      <TabsContent value="financials">
        <CompanyFinancialsTab company={company} />
      </TabsContent>
      <TabsContent value="dividend">
        <CompanyDividendTab active={open && activeTab === "dividend"} company={company} />
      </TabsContent>
      <TabsContent value="valuation">
        <CompanyValuationTab active={open && activeTab === "valuation"} company={company} />
      </TabsContent>
      <TabsContent value="chart">
        <PriceChart ticker={company.stockCode} />
      </TabsContent>
    </Tabs>
  );
}