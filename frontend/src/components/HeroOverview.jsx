import { Card, CardContent } from "@/components/ui/card";
import { SCREENER } from "@/constants/testIds";

export default function HeroOverview({ formattedUpdatedAt, statCards, tvUpdatedAt }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800" data-testid="hero-overview-card">
      <div className="grid gap-6 p-5 lg:grid-cols-[1.3fr_0.7fr] lg:p-8">
        <div className="space-y-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-600 dark:text-emerald-400">TradingView-powered workflow</p>
          <h2 className="max-w-3xl text-xl font-semibold tracking-tight text-slate-950 dark:text-slate-50 sm:text-2xl lg:text-3xl">Agent membaca screener, lalu merangkum saham yang paling layak diriset.</h2>
          <p className="max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-400">
            Data diambil dari custom TradingView screener, lalu diperkaya dengan skor investasi, alasan utama, dan risiko yang perlu dicek sebelum membeli.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex w-fit items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400" data-testid={SCREENER.updatedAt}>
              Data referensi: {formattedUpdatedAt}
            </div>
            {tvUpdatedAt ? (
              <div className="inline-flex w-fit items-center rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5 text-xs text-sky-700 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-400">
                Data TradingView: {new Date(tvUpdatedAt).toLocaleString("id-ID", { dateStyle: "full", timeStyle: "short" })}
              </div>
            ) : (
              <div className="inline-flex w-fit items-center rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500">
                Data TradingView: memuat...
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3" data-testid={SCREENER.topStats}>
          {statCards.map((stat) => (
            <Card key={stat.label} className="border-slate-200 bg-white shadow-none dark:border-slate-700 dark:bg-slate-800 dark:shadow-none" data-testid={`hero-stat-${stat.label.toLowerCase().replace(/\s+/g, "-")}`}>
              <CardContent className="flex items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-slate-500 dark:text-slate-400">{stat.label}</p>
                  <p className="mt-1.5 text-xl font-semibold text-slate-950 dark:text-slate-50 sm:text-2xl">{stat.value}</p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{stat.description}</p>
                </div>
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 sm:h-10 sm:w-10">
                  <stat.icon className="h-4 w-4 sm:h-5 sm:w-5" weight="duotone" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
