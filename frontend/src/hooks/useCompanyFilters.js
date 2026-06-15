import { useCallback, useMemo, useState } from "react";
import { defaultFilters, filterCompanies, getAverages, quickFilters, sortCompanies } from "@/lib/screener";

const initialSortConfig = {
  key: "roe",
  direction: "desc",
};

export default function useCompanyFilters(companies) {
  const [filters, setFilters] = useState(defaultFilters);
  const [sortConfig, setSortConfig] = useState(initialSortConfig);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [activeQuickFilter, setActiveQuickFilter] = useState("");

  const filteredCompanies = useMemo(
    () => filterCompanies(companies, filters),
    [companies, filters],
  );

  const sortedCompanies = useMemo(
    () => sortCompanies(filteredCompanies, sortConfig),
    [filteredCompanies, sortConfig],
  );

  const averages = useMemo(
    () => getAverages(sortedCompanies),
    [sortedCompanies],
  );

  const handleSort = useCallback((key) => {
    setSortConfig((current) => {
      const isSameKey = current.key === key;
      return {
        key,
        direction: isSameKey && current.direction === "desc" ? "asc" : "desc",
      };
    });
  }, []);

  const handleFilterChange = useCallback((key, value) => {
    setActiveQuickFilter("");
    setFilters((current) => ({ ...current, [key]: value }));
  }, []);

  const handleQuickFilter = useCallback((key) => {
    setActiveQuickFilter(key);
    setFilters(quickFilters[key].values);
  }, []);

  const handleReset = useCallback(() => {
    setActiveQuickFilter("");
    setFilters(defaultFilters);
  }, []);

  const closeCompanySheet = useCallback((open) => {
    if (!open) {
      setSelectedCompany(null);
    }
  }, []);

  return {
    filters,
    sortConfig,
    selectedCompany,
    activeQuickFilter,
    filteredCompanies,
    sortedCompanies,
    averages,
    setSelectedCompany,
    handleSort,
    handleFilterChange,
    handleQuickFilter,
    handleReset,
    closeCompanySheet,
  };
}