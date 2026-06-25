import { ArrowSquareOut, CaretDown, CaretUp } from "@phosphor-icons/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { columns, formatCurrency, formatPercent, formatRatio } from "@/lib/screener";

const renderMetric = (key, value) => {
  if (key === "price") return formatCurrency(value);
  if (["roe", "npm", "dividendYield"].includes(key)) return formatPercent(value);
  if (["per", "pbv", "der"].includes(key)) return formatRatio(value);
  return value;
};

function SortIcon({ direction, isActive }) {
  if (!isActive) {
    return null;
  }

  if (direction === "asc") {
    return <CaretUp className="h-3.5 w-3.5" />;
  }

  return <CaretDown className="h-3.5 w-3.5" />;
}

function ResultsHeader({ companies }) {
  return (
    <CardHeader className="flex flex-col gap-4 border-b border-border bg-card/90 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground" data-testid="results-table-kicker">Hasil Screener</p>
        <CardTitle className="mt-2 text-xl text-foreground" data-testid="results-table-title">Daftar emiten yang lolos filter</CardTitle>
      </div>
      <div className="rounded-full border border-border bg-muted/50 px-4 py-2 text-sm text-muted-foreground" data-testid="results-table-count">
        {companies.length} saham ditemukan
      </div>
    </CardHeader>
  );
}

function ResultsRow({ company, onSelectCompany }) {
  return (
    <TableRow
      className="cursor-pointer border-border hover:bg-muted/30"
      data-testid={`results-row-${company.stockCode.toLowerCase()}`}
      onClick={() => onSelectCompany(company)}
    >
      {columns.map((column) => {
        const isPositive = (column.key === "dividendYield" && company[column.key] >= 4) || (column.key === "roe" && company[column.key] >= 15);
        const isMonospace = column.key === "stockCode";
        const baseClass = isMonospace ? "font-mono font-semibold text-foreground" : "text-muted-foreground";
        const positiveClass = isPositive ? "text-cuan" : "";

        return (
<TableCell
             className={`px-4 py-4 ${baseClass} ${positiveClass}`}
             data-testid={`results-cell-${company.stockCode.toLowerCase()}-${column.key}`}
             key={column.key}
           >
            <div className="flex items-center gap-2">
              <span>{renderMetric(column.key, company[column.key])}</span>
              {column.key === "companyName" ? <ArrowSquareOut className="h-3.5 w-3.5 text-muted-foreground" /> : null}
            </div>
          </TableCell>
        );
      })}
    </TableRow>
  );
}

function EmptyState() {
  return (
    <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 px-6 py-10 text-center" data-testid="results-empty-state">
      <p className="text-lg font-semibold text-foreground">Belum ada saham yang cocok.</p>
      <p className="max-w-md text-sm leading-6 text-muted-foreground">Coba longgarkan filter PER, PBV, atau ROE agar lebih banyak emiten tampil di hasil screener.</p>
    </div>
  );
}

export default function ResultsTable({ companies, sortConfig, onSort, onSelectCompany }) {
  return (
    <Card className="overflow-hidden border-border bg-card shadow-sm" data-testid="results-table-card">
      <ResultsHeader companies={companies} />
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table data-testid="results-table">
            <TableHeader>
              <TableRow>
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    className="bg-muted/50 px-4 py-3"
                  >
                    <button
                      className="flex items-center gap-1 font-medium text-muted-foreground transition-colors hover:text-foreground"
                      data-testid={`sort-header-${column.key}`}
                      onClick={() => onSort(column.key)}
                      type="button"
                    >
                      {column.label}
                      <SortIcon direction={sortConfig.direction} isActive={sortConfig.key === column.key} />
                    </button>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {companies.map((company) => <ResultsRow company={company} key={company.stockCode} onSelectCompany={onSelectCompany} />)}
            </TableBody>
          </Table>
        </div>
        {!companies.length ? <EmptyState /> : null}
      </CardContent>
    </Card>
  );
}