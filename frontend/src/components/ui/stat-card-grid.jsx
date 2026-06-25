import { Card, CardContent } from "@/components/ui/card";

function StatCard({ icon: Icon, label, value, description, trend, trendValue }) {
  const trendIsUp = trend === "up" || (trend === "auto" && trendValue >= 0);
  const trendIsDown = trend === "down" || (trend === "auto" && trendValue < 0);

  return (
    <Card className="border-border">
      <CardContent className="flex items-center justify-between gap-3 p-3 sm:p-4">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <p className="mt-0.5 text-xl font-semibold text-foreground sm:text-2xl">
            {value}
          </p>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/50">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

function StatLinkCard({ icon: Icon, label, value, href, description }) {
  return (
    <Card className="border-border">
      <CardContent className="flex items-center justify-between gap-3 p-3 sm:p-4">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {label}
          </p>
          <a
            className="mt-0.5 block truncate text-sm font-semibold text-foreground hover:text-primary"
            href={href}
            rel="noreferrer"
            target="_blank"
          >
            {value}
          </a>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/50">
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function StatCardGrid({ items, columns = 4 }) {
  if (!items || items.length === 0) return null;

  const colClass = {
    2: "grid-cols-2",
    3: "grid-cols-2 sm:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-5",
  };

  return (
    <div className={`grid gap-3 ${colClass[columns] || colClass[4]}`}>
      {items.map((item) => {
        if (item.href) {
          return <StatLinkCard key={item.label} {...item} />;
        }
        return <StatCard key={item.label} {...item} />;
      })}
    </div>
  );
}
