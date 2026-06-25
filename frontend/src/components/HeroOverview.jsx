import StatCardGrid from "@/components/ui/stat-card-grid";
import { SCREENER } from "@/constants/testIds";

export default function HeroOverview({ formattedUpdatedAt, statCards, tvUpdatedAt }) {
  return (
    <section className="rounded-lg border border-border bg-card" data-testid="hero-overview-card">
      <div className="grid gap-4 p-4 lg:grid-cols-[1.3fr_0.7fr] lg:p-5">
        <div className="space-y-2.5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            TradingView-powered workflow
          </p>
          <h2 className="max-w-3xl text-base font-semibold tracking-tight text-foreground sm:text-lg lg:text-xl">
            Agent membaca screener, lalu merangkum saham yang paling layak diriset.
          </h2>
          <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
            Data diambil dari custom TradingView screener, lalu diperkaya dengan skor investasi, alasan utama, dan risiko yang perlu dicek sebelum membeli.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex w-fit items-center rounded-md border border-border bg-muted/50 px-2.5 py-1 text-xs text-muted-foreground" data-testid={SCREENER.updatedAt}>
              Data referensi: {formattedUpdatedAt}
            </div>
            {tvUpdatedAt ? (
              <div className="inline-flex w-fit items-center rounded-md border border-border bg-muted/50 px-2.5 py-1 text-xs text-muted-foreground">
                Data TradingView: {new Date(tvUpdatedAt).toLocaleString("id-ID", { dateStyle: "full", timeStyle: "short" })}
              </div>
            ) : (
              <div className="inline-flex w-fit items-center rounded-md border border-border bg-muted/50 px-2.5 py-1 text-xs text-muted-foreground">
                Data TradingView: memuat...
              </div>
            )}
          </div>
        </div>

        <div data-testid={SCREENER.topStats}>
          <StatCardGrid items={statCards} columns={2} />
        </div>
      </div>
    </section>
  );
}
