export function adaptTVCompany(item) {
  const analysis = item.analysis || {};
  return {
    stockCode: item.ticker || item.symbol?.replace("IDX:", "") || "",
    companyName: item.companyName || "",
    industry: item.sector || "IHSG",
    industryDescription: item.sector ? `Sektor ${item.sector}` : "Sektor IHSG",
    price: item.price || 0,
    per: item.per || 0,
    pbv: item.pbv || 0,
    roe: item.roe || 0,
    npm: item.roa || 0,
    der: item.debt_to_equity || 0,
    dividendYield: item.dividend_yield || 0,
    regularDividend: (item.dividend_yield || 0) > 0,
    logoText: (item.companyName || "?").charAt(0).toUpperCase(),
    analystAngle: analysis.summary || analysis.investmentReasons?.[0] || "Data analis tidak tersedia.",
    strengths: analysis.investmentReasons || [],
    risks: analysis.risks || [],
    annualFinancials: null,
    valuationSummary: null,
    dividendHistory: null,
    revenueNetIncomeQuarters: null,
    ratioTrend: null,
    keyFinancialMetrics: null,
  };
}

export function adaptTVCompanies(data) {
  return (data || []).map(adaptTVCompany);
}
