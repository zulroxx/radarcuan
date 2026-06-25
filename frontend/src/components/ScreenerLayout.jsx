import { useCallback, useState } from "react";
import FilterSidebar from "@/components/FilterSidebar";
import HeroOverview from "@/components/HeroOverview";
import InvestmentSummary from "@/components/InvestmentSummary";
import TradingViewTable from "@/components/TradingViewTable";
import WatchlistPanel from "@/components/WatchlistPanel";
import { WatchlistProvider } from "@/lib/watchlist-context";

export default function ScreenerLayout(props) {
  const [tvUpdatedAt, setTvUpdatedAt] = useState(null);
  const [tvData, setTvData] = useState([]);

  const handleDataUpdate = useCallback((payload) => {
    if (payload?.updatedAt) setTvUpdatedAt(payload.updatedAt);
    if (payload?.data) {
      setTvData(payload.data);
      props.onTvDataUpdate?.(payload.data);
    }
  }, [props]);

  return (
    <WatchlistProvider>
      <main className="mx-auto max-w-[1600px] px-4 py-5 sm:px-6 lg:px-8">
        <div className="space-y-5">
          <HeroOverview
            formattedUpdatedAt={props.formattedUpdatedAt}
            statCards={props.statCards}
            tvUpdatedAt={tvUpdatedAt}
          />
          <InvestmentSummary companies={tvData} />
          <TradingViewTable
            onDataUpdate={handleDataUpdate}
            onSelectCompany={props.onSelectCompany}
          />
          <WatchlistPanel companies={tvData} />
          <FilterSidebar />
        </div>
      </main>
    </WatchlistProvider>
  );
}
