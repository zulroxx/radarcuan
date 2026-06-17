import { useCallback, useState } from "react";
import FilterSidebar from "@/components/FilterSidebar";
import HeroOverview from "@/components/HeroOverview";
import InvestmentSummary from "@/components/InvestmentSummary";
import TradingViewTable from "@/components/TradingViewTable";
import WatchlistPanel from "@/components/WatchlistPanel";
import useScreenerData from "@/hooks/useScreenerData";

const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || "http://localhost:8000").replace(/\/+$/, "");

export default function ScreenerLayout(props) {
  const [tvUpdatedAt, setTvUpdatedAt] = useState(null);
  const [tvData, setTvData] = useState([]);
  const waitlist = useScreenerData(`${BACKEND_URL}/api`);

  const handleDataUpdate = useCallback((payload) => {
    if (payload?.updatedAt) setTvUpdatedAt(payload.updatedAt);
    if (payload?.data) {
      setTvData(payload.data);
      props.onTvDataUpdate?.(payload.data);
    }
  }, [props]);

  return (
    <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="space-y-6">
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
        <FilterSidebar
          waitlistForm={waitlist.waitlistForm}
          onWaitlistChange={waitlist.handleWaitlistChange}
          onWaitlistSubmit={waitlist.submitWaitlist}
          waitlistLoading={waitlist.waitlistLoading}
        />
      </div>
    </main>
  );
}
