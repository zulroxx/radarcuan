import { Star, TrendDown, TrendUp } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import useWatchlist from "@/hooks/useWatchlist";

const formatPrice = (value) => {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
};

export default function WatchlistPanel({ companies }) {
  const { watchlist, remove } = useWatchlist();
  const watchedCompanies = (companies || []).filter((c) => watchlist.includes(c.ticker));

  if (watchlist.length === 0) return null;

  return (
    <Card className="border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Star className="h-5 w-5 text-amber-400" weight="fill" />
          <CardTitle className="text-base font-semibold text-slate-800 dark:text-slate-100">Watchlist</CardTitle>
          <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300" variant="secondary">{watchlist.length}</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-slate-100 dark:divide-slate-700">
          {watchedCompanies.length === 0 ? (
            <p className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
              {watchlist.length} saham di watchlist belum tersedia di data saat ini.
            </p>
          ) : (
            watchedCompanies.map((company) => {
              const analysis = company.analysis || {};
              const score = analysis.investmentScore || 0;
              const change = company.change || 0;
              const changePositive = change >= 0;
              return (
                <div key={company.ticker} className="flex items-center justify-between px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <button
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-slate-100 dark:hover:bg-slate-700"
                      onClick={() => remove(company.ticker)}
                      title="Hapus dari watchlist"
                    >
                      <Star className="h-3.5 w-3.5 text-amber-400" weight="fill" />
                    </button>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">{company.ticker}</span>
                        <span className={`text-[10px] font-medium ${score >= 65 ? "text-emerald-600 dark:text-emerald-400" : score >= 45 ? "text-amber-600 dark:text-amber-400" : "text-red-600 dark:text-red-400"}`}>
                          {score}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-[140px]">{company.companyName}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                      Rp{formatPrice(company.price)}
                    </p>
                    <p className={`flex items-center justify-end gap-0.5 text-xs ${changePositive ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                      {changePositive ? <TrendUp className="h-3 w-3" weight="bold" /> : <TrendDown className="h-3 w-3" weight="bold" />}
                      {changePositive ? "+" : ""}{change.toFixed(2)}%
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}