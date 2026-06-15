import { useEffect, useMemo, useState } from "react";
import { getCompanyInsights, getSectorBenchmark } from "@/lib/screener";

export default function useCompanyDetailState({ company, companies, open }) {
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    if (open && company) {
      setActiveTab("overview");
    }
  }, [company?.stockCode, open, setActiveTab]);

  const sectorBenchmark = useMemo(() => {
    if (!company) {
      return null;
    }

    return getSectorBenchmark(companies, company);
  }, [companies, company]);

  const insightBadges = useMemo(() => {
    if (!company || !sectorBenchmark) {
      return [];
    }

    return getCompanyInsights(company, sectorBenchmark);
  }, [company, sectorBenchmark]);

  return {
    activeTab,
    setActiveTab,
    sectorBenchmark,
    insightBadges,
  };
}