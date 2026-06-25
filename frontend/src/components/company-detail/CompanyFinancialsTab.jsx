import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { COMPANY_DETAIL_TABLE_CELL_CLASS } from "@/components/company-detail/constants";
import { formatCompactCurrency } from "@/lib/screener";

function DataTable({ columns, rows, testIdPrefix }) {
  return (
    <div className="overflow-auto rounded-lg border border-border">
      <table className="w-full min-w-[520px]">
        <thead className="bg-muted/50">
          <tr>
            {columns.map((column) => (
              <th className={COMPANY_DETAIL_TABLE_CELL_CLASS} key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year} data-testid={`${testIdPrefix}-${row.year}`}>
              {columns.map((column) => (
                <td className={COMPANY_DETAIL_TABLE_CELL_CLASS} key={column.key}>{column.render(row[column.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const incomeColumns = [
  { key: "year", label: "Tahun", render: (value) => value },
  { key: "revenue", label: "Revenue", render: (value) => formatCompactCurrency(value) },
  { key: "ebitda", label: "EBITDA", render: (value) => formatCompactCurrency(value) },
  { key: "netIncome", label: "Net Income", render: (value) => formatCompactCurrency(value) },
];

const balanceColumns = [
  { key: "year", label: "Tahun", render: (value) => value },
  { key: "assets", label: "Assets", render: (value) => formatCompactCurrency(value) },
  { key: "liabilities", label: "Liabilities", render: (value) => formatCompactCurrency(value) },
  { key: "equity", label: "Equity", render: (value) => formatCompactCurrency(value) },
  { key: "cash", label: "Cash", render: (value) => formatCompactCurrency(value) },
];

const cashFlowColumns = [
  { key: "year", label: "Tahun", render: (value) => value },
  { key: "operatingCashFlow", label: "OCF", render: (value) => formatCompactCurrency(value) },
  { key: "capex", label: "Capex", render: (value) => formatCompactCurrency(value) },
  { key: "freeCashFlow", label: "FCF", render: (value) => formatCompactCurrency(value) },
];

export default function CompanyFinancialsTab({ company }) {
  const hasFinancials = company.annualFinancials && company.annualFinancials.balanceSheet;
  
  if (!hasFinancials) {
    return (
      <div className="space-y-4" data-testid="company-detail-tab-content-financials">
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-lg text-foreground">Laporan keuangan ringkas</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">Data keuangan belum tersedia untuk saham ini.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="company-detail-tab-content-financials">
      <Card className="border-border bg-card" data-testid="company-detail-income-table-card">
        <CardHeader>
          <CardTitle className="text-lg text-foreground">Laporan keuangan ringkas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div>
            <p className="mb-3 text-sm font-medium text-foreground">Income Statement</p>
            <DataTable columns={incomeColumns} rows={company.annualFinancials.incomeStatement} testIdPrefix="company-detail-income-row" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-2">
            <div>
              <p className="mb-3 text-sm font-medium text-foreground">Balance Sheet</p>
              <DataTable columns={balanceColumns} rows={company.annualFinancials.balanceSheet} testIdPrefix="company-detail-balance-row" />
            </div>
            <div>
              <p className="mb-3 text-sm font-medium text-foreground">Cash Flow</p>
              <DataTable columns={cashFlowColumns} rows={company.annualFinancials.cashFlow} testIdPrefix="company-detail-cashflow-row" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}