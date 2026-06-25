import { Star, TrendDown, TrendUp } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useWatchlist } from "@/lib/watchlist-context";

const formatPrice = (value) => {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("id-ID", { style: "decimal", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
};

function WatchlistItem({ company, onRemove }) {
  const analysis = company.analysis || {};
  const score = analysis.investmentScore || 0;
  const change = company.change || 0;
  const changePositive = change >= 0;

  return (
    <div className="flex items-center justify-between px-3 py-2">
      <div className="flex items-center gap-2">
        <button
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded hover:bg-muted"
          onClick={() => onRemove(company.ticker)}
          title="Hapus dari watchlist"
        >
          <Star className="h-3.5 w-3.5 text-amber-400" weight="fill" />
        </button>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-foreground">{company.ticker}</span>
            <span className={`text-[10px] font-medium ${score >= 65 ? "text-cuan" : score >= 45 ? "text-amber-500" : "text-loss"}`}>
              {score}
            </span>
          </div>
          <p className="text-[11px] text-muted-foreground truncate max-w-[140px]">{company.companyName}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-foreground">
          Rp{formatPrice(company.price)}
        </p>
        <p className={`flex items-center justify-end gap-0.5 text-xs ${changePositive ? "text-cuan" : "text-loss"}`}>
          {changePositive ? <TrendUp className="h-3 w-3" weight="bold" /> : <TrendDown className="h-3 w-3" weight="bold" />}
          {changePositive ? "+" : ""}{change.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

export default function WatchlistPanel({ companies }) {
  const { watchlist, remove } = useWatchlist();
  const watchedCompanies = (companies || []).filter((c) => watchlist.includes(c.ticker));

  if (watchlist.length === 0) return null;

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Star className="h-4 w-4 text-amber-400" weight="fill" />
          <CardTitle className="text-sm font-semibold text-foreground">Watchlist</CardTitle>
          <Badge className="bg-amber-500/10 text-amber-600" variant="secondary">{watchlist.length}</Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {watchedCompanies.length === 0 ? (
            <p className="px-3 py-2 text-xs text-muted-foreground">
              {watchlist.length} saham di watchlist belum tersedia di data saat ini.
            </p>
          ) : (
            watchedCompanies.map((company) => (
              <WatchlistItem key={company.ticker} company={company} onRemove={remove} />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
