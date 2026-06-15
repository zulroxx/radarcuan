import { useCallback, useState } from "react";
import HeroOverview from "@/components/HeroOverview";
import TradingViewTable from "@/components/TradingViewTable";

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
    <main className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div className="space-y-6">
        <HeroOverview
          formattedUpdatedAt={props.formattedUpdatedAt}
          statCards={props.statCards}
          tvUpdatedAt={tvUpdatedAt}
        />
        <TradingViewTable
          onDataUpdate={handleDataUpdate}
          onSelectCompany={props.onSelectCompany}
        />
      </div>
    </main>
  );
}
