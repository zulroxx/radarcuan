import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf
logging.getLogger("yfinance").setLevel(logging.ERROR)
_yf_tz_cache = Path(__file__).parent / "agent_cache" / "yfinance_tz"
_yf_tz_cache.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(_yf_tz_cache))

ROOT_DIR = Path(__file__).parent
FUNDAMENTAL_CACHE_DIR = ROOT_DIR / "agent_cache" / "fundamental"
FUNDAMENTAL_CACHE_TTL = 86400  # 24 hours (fundamentals don't change daily)
FINANCIAL_CACHE_TTL = 604800   # 7 days (financial statements)

logger = logging.getLogger(__name__)


def _ensure_cache_dir():
    FUNDAMENTAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(ticker: str, data_type: str) -> Path:
    return FUNDAMENTAL_CACHE_DIR / f"{ticker}_{data_type}.json"


def _load_cache(ticker: str, data_type: str, ttl: int) -> Optional[Any]:
    path = _cache_path(ticker, data_type)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        age = time.time() - cached.get("cached_at", 0)
        if age < ttl:
            return cached.get("data")
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def _save_cache(ticker: str, data_type: str, data: Any) -> None:
    _ensure_cache_dir()
    path = _cache_path(ticker, data_type)
    cache_data = {"cached_at": time.time(), "data": data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2, default=str)


def get_financial_summary(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch comprehensive financial summary for a ticker using yfinance."""
    cached = _load_cache(ticker, "financial_summary", FINANCIAL_CACHE_TTL)
    if cached:
        return cached

    try:
        tk = yf.Ticker(ticker + ".JK")

        income_stmt = tk.income_stmt
        balance_sheet = tk.balance_sheet
        cash_flow = tk.cash_flow

        if income_stmt is None or income_stmt.empty:
            return None

        summary = {}
        current_year = income_stmt.columns[0] if not income_stmt.empty else None
        prev_year = income_stmt.columns[1] if len(income_stmt.columns) > 1 else None

        def safe_val(df, col, key):
            if col is None or df is None or df.empty:
                return None
            try:
                val = df.loc[key, col]
                if pd.isna(val):
                    return None
                return float(val)
            except (KeyError, TypeError, ValueError):
                return None

        # Revenue
        rev_current = safe_val(income_stmt, current_year, "Total Revenue")
        rev_prev = safe_val(income_stmt, prev_year, "Total Revenue")
        summary["revenue"] = rev_current
        summary["revenue_prev"] = rev_prev
        if rev_current and rev_prev and rev_prev != 0:
            summary["revenue_growth_pct"] = round(
                ((rev_current - rev_prev) / abs(rev_prev)) * 100, 2
            )
        else:
            summary["revenue_growth_pct"] = None

        # Net Income
        ni_current = safe_val(income_stmt, current_year, "Net Income")
        ni_prev = safe_val(income_stmt, prev_year, "Net Income")
        summary["net_income"] = ni_current
        summary["net_income_prev"] = ni_prev
        if ni_current and ni_prev and ni_prev != 0:
            summary["net_income_growth_pct"] = round(
                ((ni_current - ni_prev) / abs(ni_prev)) * 100, 2
            )
        else:
            summary["net_income_growth_pct"] = None

        # Net Profit Margin
        if rev_current and rev_current != 0 and ni_current:
            summary["net_profit_margin"] = round(
                (ni_current / rev_current) * 100, 2
            )
        else:
            summary["net_profit_margin"] = None

        # EBITDA
        ebitda = safe_val(income_stmt, current_year, "EBITDA")
        summary["ebitda"] = ebitda
        if ebitda and rev_current and rev_current != 0:
            summary["ebitda_margin"] = round((ebitda / rev_current) * 100, 2)
        else:
            summary["ebitda_margin"] = None

        # Operating Income
        op_income = safe_val(income_stmt, current_year, "Operating Income")
        summary["operating_income"] = op_income
        if op_income and rev_current and rev_current != 0:
            summary["operating_margin"] = round(
                (op_income / rev_current) * 100, 2
            )
        else:
            summary["operating_margin"] = None

        # Balance Sheet
        if balance_sheet is not None and not balance_sheet.empty:
            bs_col = balance_sheet.columns[0]

            total_assets = safe_val(balance_sheet, bs_col, "Total Assets")
            total_debt = safe_val(balance_sheet, bs_col, "Total Debt")
            total_equity = safe_val(balance_sheet, bs_col, "Total Equity Gross Growth")
            if total_equity is None:
                total_equity = safe_val(
                    balance_sheet, bs_col, "Stockholders Equity"
                )

            cash = safe_val(
                balance_sheet, bs_col, "Cash And Cash Equivalents"
            )
            if cash is None:
                cash = safe_val(balance_sheet, bs_col, "Cash")

            current_assets = safe_val(
                balance_sheet, bs_col, "Current Assets"
            )
            current_liabilities = safe_val(
                balance_sheet, bs_col, "Current Liabilities"
            )

            summary["total_assets"] = total_assets
            summary["total_debt"] = total_debt
            summary["total_equity"] = total_equity
            summary["cash"] = cash

            if total_debt and total_equity and total_equity != 0:
                summary["debt_to_equity"] = round(
                    total_debt / total_equity, 2
                )
            else:
                summary["debt_to_equity"] = None

            if current_assets and current_liabilities and current_liabilities != 0:
                summary["current_ratio"] = round(
                    current_assets / current_liabilities, 2
                )
            else:
                summary["current_ratio"] = None

        # Cash Flow
        if cash_flow is not None and not cash_flow.empty:
            cf_col = cash_flow.columns[0]
            op_cash = safe_val(cash_flow, cf_col, "Operating Cash Flow")
            free_cash = safe_val(cash_flow, cf_col, "Free Cash Flow")
            summary["operating_cash_flow"] = op_cash
            summary["free_cash_flow"] = free_cash
            if ni_current and ni_current != 0 and op_cash:
                summary["cash_flow_quality"] = round(op_cash / ni_current, 2)
            else:
                summary["cash_flow_quality"] = None

        # Key ratios
        info = {}
        try:
            info = tk.info
        except Exception:
            pass

        if info:
            summary["market_cap"] = info.get("marketCap")
            summary["forward_pe"] = info.get("forwardPE")
            summary["trailing_pe"] = info.get("trailingPE")
            summary["price_to_book"] = info.get("priceToBook")
            summary["return_on_equity"] = info.get("returnOnEquity")
            summary["return_on_assets"] = info.get("returnOnAssets")
            summary["dividend_yield"] = info.get("dividendYield")
            summary["beta"] = info.get("beta")
            summary["fifty_two_week_high"] = info.get("fiftyTwoWeekHigh")
            summary["fifty_two_week_low"] = info.get("fiftyTwoWeekLow")
            summary["sector"] = info.get("sector")
            summary["industry"] = info.get("industry")

        summary["fetched_at"] = datetime.now(timezone.utc).isoformat()
        _save_cache(ticker, "financial_summary", summary)
        return summary

    except Exception as e:
        logger.warning(f"Gagal mengambil data fundamental untuk {ticker}: {e}")
        return None


def get_fundamental_score(summary: Optional[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    """Score a stock based on its fundamental health (0-100)."""
    if not summary:
        return 50.0, {"score": 50, "reason": "Data fundamental tidak tersedia"}

    details = {}
    total_score = 0.0
    weights = 0.0

    # Revenue Growth (weight: 20%)
    rev_growth = summary.get("revenue_growth_pct")
    if rev_growth is not None:
        if rev_growth > 20:
            sub = 95
        elif rev_growth > 10:
            sub = 80
        elif rev_growth > 5:
            sub = 65
        elif rev_growth > 0:
            sub = 50
        elif rev_growth > -10:
            sub = 30
        else:
            sub = 15
        total_score += sub * 0.20
        weights += 0.20
        details["revenue_growth"] = {"value": rev_growth, "score": sub}

    # Net Income Growth (weight: 25%)
    ni_growth = summary.get("net_income_growth_pct")
    if ni_growth is not None:
        if ni_growth > 25:
            sub = 95
        elif ni_growth > 15:
            sub = 85
        elif ni_growth > 5:
            sub = 65
        elif ni_growth > 0:
            sub = 50
        elif ni_growth > -15:
            sub = 25
        else:
            sub = 10
        total_score += sub * 0.25
        weights += 0.25
        details["net_income_growth"] = {"value": ni_growth, "score": sub}

    # Net Profit Margin (weight: 20%)
    npm = summary.get("net_profit_margin")
    if npm is not None:
        if npm > 25:
            sub = 95
        elif npm > 15:
            sub = 85
        elif npm > 10:
            sub = 70
        elif npm > 5:
            sub = 50
        elif npm > 0:
            sub = 30
        else:
            sub = 10
        total_score += sub * 0.20
        weights += 0.20
        details["net_profit_margin"] = {"value": npm, "score": sub}

    # Debt to Equity (weight: 15%)
    der = summary.get("debt_to_equity")
    if der is not None:
        if der < 0.3:
            sub = 90
        elif der < 0.5:
            sub = 80
        elif der < 1.0:
            sub = 60
        elif der < 2.0:
            sub = 40
        elif der < 4.0:
            sub = 20
        else:
            sub = 5
        total_score += sub * 0.15
        weights += 0.15
        details["debt_to_equity"] = {"value": der, "score": sub}

    # Current Ratio (weight: 10%)
    cr = summary.get("current_ratio")
    if cr is not None:
        if cr > 3.0:
            sub = 90
        elif cr > 2.0:
            sub = 80
        elif cr > 1.5:
            sub = 65
        elif cr > 1.0:
            sub = 50
        else:
            sub = 20
        total_score += sub * 0.10
        weights += 0.10
        details["current_ratio"] = {"value": cr, "score": sub}

    # Cash Flow Quality (weight: 10%)
    cfq = summary.get("cash_flow_quality")
    if cfq is not None:
        if cfq > 1.5:
            sub = 90
        elif cfq > 1.0:
            sub = 75
        elif cfq > 0.5:
            sub = 50
        else:
            sub = 20
        total_score += sub * 0.10
        weights += 0.10
        details["cash_flow_quality"] = {"value": cfq, "score": sub}

    if weights == 0:
        return 50.0, {"score": 50, "reason": "Data fundamental tidak mencukupi"}

    final_score = round(total_score / weights, 1)
    details["score"] = final_score

    return final_score, details


def get_sector_fundamental_averages(
    tickers: List[str],
) -> Dict[str, float]:
    """Calculate average fundamental metrics for a sector."""
    metrics = {
        "revenue_growth_pct": [],
        "net_income_growth_pct": [],
        "net_profit_margin": [],
        "debt_to_equity": [],
        "current_ratio": [],
    }

    for ticker in tickers[:20]:
        summary = get_financial_summary(ticker)
        if summary:
            for key in metrics:
                val = summary.get(key)
                if val is not None:
                    metrics[key].append(val)

    averages = {}
    for key, vals in metrics.items():
        if vals:
            averages[key] = round(sum(vals) / len(vals), 2)
        else:
            averages[key] = None

    return averages
