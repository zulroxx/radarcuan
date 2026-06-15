export const defaultFilters = {
  perMax: 25,
  pbvMax: 3,
  roeMin: 10,
  npmMin: 5,
  derMax: 1.5,
  dividendOnly: false,
  dividendYieldMin: 0,
};

export const quickFilters = {
  value: {
    label: "Value Investing (Murah)",
    values: { perMax: 15, pbvMax: 2, roeMin: 10, npmMin: 6, derMax: 1.2, dividendOnly: false, dividendYieldMin: 0 },
  },
  growth: {
    label: "Growth Stock (Tumbuh)",
    values: { perMax: 35, pbvMax: 5, roeMin: 15, npmMin: 10, derMax: 1.6, dividendOnly: false, dividendYieldMin: 0 },
  },
  dividend: {
    label: "Dividend Hunters",
    values: { perMax: 20, pbvMax: 3, roeMin: 10, npmMin: 8, derMax: 1.5, dividendOnly: true, dividendYieldMin: 4 },
  },
};

export const columns = [
  { key: "stockCode", label: "Stock Code" },
  { key: "companyName", label: "Company Name", hiddenMobile: "hidden sm:table-cell" },
  { key: "industry", label: "Industry", hiddenMobile: "hidden md:table-cell" },
  { key: "price", label: "Price (EOD)" },
  { key: "per", label: "PER" },
  { key: "pbv", label: "PBV", hiddenMobile: "hidden sm:table-cell" },
  { key: "roe", label: "ROE", hiddenMobile: "hidden sm:table-cell" },
  { key: "npm", label: "NPM", hiddenMobile: "hidden md:table-cell" },
  { key: "der", label: "DER", hiddenMobile: "hidden md:table-cell" },
  { key: "dividendYield", label: "Div. Yield" },
];

export const filterCompanies = (companies, filters) =>
  companies.filter((company) => matchesAllFilters(company, filters));

function matchesValuationFilter(company, filters) {
  return company.per <= filters.perMax && company.pbv <= filters.pbvMax;
}

function matchesQualityFilter(company, filters) {
  return company.roe >= filters.roeMin && company.npm >= filters.npmMin && company.der <= filters.derMax;
}

function matchesDividendFilter(company, filters) {
  const yieldMatches = company.dividendYield >= filters.dividendYieldMin;
  const dividendRuleMatches = !filters.dividendOnly || company.regularDividend;
  return yieldMatches && dividendRuleMatches;
}

function matchesAllFilters(company, filters) {
  return matchesValuationFilter(company, filters)
    && matchesQualityFilter(company, filters)
    && matchesDividendFilter(company, filters);
}

export const sortCompanies = (companies, sortConfig) => {
  const sorted = [...companies].sort((left, right) => {
    const leftValue = left[sortConfig.key];
    const rightValue = right[sortConfig.key];

    if (typeof leftValue === "number" && typeof rightValue === "number") {
      return sortConfig.direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
    }

    if (sortConfig.direction === "asc") {
      return String(leftValue).localeCompare(String(rightValue), "id");
    }

    return String(rightValue).localeCompare(String(leftValue), "id");
  });

  return sorted;
};

export const formatCurrency = (value) => `Rp${Number(value).toLocaleString("id-ID")}`;

export const formatPercent = (value) => `${Number(value).toFixed(1)}%`;

export const formatRatio = (value) => `${Number(value).toFixed(1)}x`;

export const formatCompactCurrency = (value) => {
  const numericValue = Number(value);
  if (Math.abs(numericValue) >= 1000) {
    return `Rp${(numericValue / 1000).toFixed(1)}T`;
  }
  return `Rp${numericValue.toLocaleString("id-ID")}M`;
};

export const getAverages = (companies) => {
  if (!companies.length) {
    return { avgRoe: 0, avgDividendYield: 0 };
  }

  const totals = companies.reduce(
    (acc, company) => ({
      avgRoe: acc.avgRoe + company.roe,
      avgDividendYield: acc.avgDividendYield + company.dividendYield,
    }),
    { avgRoe: 0, avgDividendYield: 0 },
  );

  return {
    avgRoe: totals.avgRoe / companies.length,
    avgDividendYield: totals.avgDividendYield / companies.length,
  };
};

export const getSectorBenchmark = (companies, selectedCompany) => {
  const peers = companies.filter((company) => company.industry === selectedCompany.industry);
  const base = peers.length ? peers : [selectedCompany];
  const totals = base.reduce(
    (acc, company) => ({
      per: acc.per + company.per,
      pbv: acc.pbv + company.pbv,
      roe: acc.roe + company.roe,
      dividendYield: acc.dividendYield + company.dividendYield,
    }),
    { per: 0, pbv: 0, roe: 0, dividendYield: 0 },
  );

  return {
    peerCount: base.length,
    per: totals.per / base.length,
    pbv: totals.pbv / base.length,
    roe: totals.roe / base.length,
    dividendYield: totals.dividendYield / base.length,
  };
};

export const getMetricTone = (metric, value) => {
  if (metric === "per") return getLowerBetterTone(value, 12, 20);
  if (metric === "pbv") return getLowerBetterTone(value, 2, 4);
  if (metric === "roe") return getHigherBetterTone(value, 18, 12);
  if (metric === "dividendYield") return getHigherBetterTone(value, 5, 2);
  if (metric === "der") return getLowerBetterTone(value, 0.8, 1.5);
  return "neutral";
};

function getLowerBetterTone(value, goodThreshold, neutralThreshold) {
  if (value <= goodThreshold) {
    return "good";
  }

  if (value <= neutralThreshold) {
    return "neutral";
  }

  return "warning";
}

function getHigherBetterTone(value, goodThreshold, neutralThreshold) {
  if (value >= goodThreshold) {
    return "good";
  }

  if (value >= neutralThreshold) {
    return "neutral";
  }

  return "warning";
}

export const toneClasses = {
  good: "border-emerald-200 bg-emerald-50 text-emerald-700",
  neutral: "border-slate-200 bg-slate-100 text-slate-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
};

export const getCompanyInsights = (company, sectorBenchmark) => {
  return buildInsightRules(sectorBenchmark)
    .filter((rule) => rule.predicate(company))
    .map((rule) => ({ label: rule.label, tone: rule.tone }))
    .slice(0, 4);
};

function buildInsightRules(sectorBenchmark) {
  return [
    {
      label: "Murah vs sektor",
      tone: "good",
      predicate: (company) => company.per < sectorBenchmark.per && company.pbv < sectorBenchmark.pbv,
    },
    {
      label: "Profitabilitas sehat",
      tone: "good",
      predicate: (company) => company.roe > 18 && company.der <= 1,
    },
    {
      label: "Dividend play",
      tone: "good",
      predicate: (company) => company.dividendYield >= 5 && company.regularDividend,
    },
    {
      label: "Valuasi premium",
      tone: "warning",
      predicate: (company) => company.per > 25 || company.pbv > 5,
    },
    {
      label: "Perlu disiplin risiko",
      tone: "warning",
      predicate: (company) => company.der > 1.2 || company.npm < 5,
    },
    {
      label: "Bukan fokus dividen",
      tone: "neutral",
      predicate: (company) => !company.regularDividend,
    },
  ];
}