import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

from agent_status import update_agent_status


TRADINGVIEW_SCREEN_URL = "https://www.tradingview.com/screener/AKYzoJyg/"
TRADINGVIEW_SCAN_URL = "https://scanner.tradingview.com/indonesia/scan"

TV_COLUMNS = [
    "name",
    "description",
    "close",
    "change",
    "volume",
    "market_cap_basic",
    "price_earnings_ttm",
    "price_book_fq",
    "earnings_per_share_basic_ttm",
    "earnings_per_share_diluted_yoy_growth_ttm",
    "dividends_yield_current",
    "sector",
    "Recommend.All",
    "return_on_equity_fq",
    "return_on_assets_fq",
    "debt_to_equity_fq",
    "total_revenue_yoy_growth_ttm",
    "Perf.YTD",
    "beta_1_year",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_json_object(text: str, start_index: int) -> str:
    brace_start = text.index("{", start_index)
    depth = 0
    in_string = False
    escape = False

    for index in range(brace_start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start : index + 1]

    raise ValueError("Tidak dapat membaca konfigurasi screener TradingView.")


def fetch_screen_config() -> Dict[str, Any]:
    try:
        response = requests.get(
            TRADINGVIEW_SCREEN_URL,
            timeout=25,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        marker = "window.initData.screen_data"
        marker_index = response.text.find(marker)
        if marker_index == -1:
            raise ValueError("Konfigurasi screener TradingView tidak ditemukan.")
        return json.loads(_extract_json_object(response.text, marker_index))
    except Exception as e:
        update_agent_status("tradingview", "error", str(e))
        raise


def _has_value_filter(filter_item: Dict[str, Any]) -> bool:
    right = filter_item.get("right") or {}
    if "value" in right:
        return right.get("value") is not None
    if "values" in right:
        return bool(right.get("values"))
    if "left" in right or "right" in right:
        return right.get("left") is not None or right.get("right") is not None
    return False


def _format_filter_id(filter_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    column = ((filter_item.get("left") or {}).get("column") or {})
    column_id = column.get("id")
    if not column_id or not _has_value_filter(filter_item):
        return None
    return filter_item


def build_scan_payload(screen_config: Dict[str, Any], limit: int) -> Dict[str, Any]:
    markets = (screen_config.get("market_settings") or {}).get("markets") or ["indonesia"]
    filters = [
        filter_item
        for filter_item in (_format_filter_id(item) for item in screen_config.get("filters", []))
        if filter_item
    ]

    payload: Dict[str, Any] = {
        "markets": markets,
        "symbols": {"query": {"types": ["stock"]}, "tickers": []},
        "columns": TV_COLUMNS,
        "sort": {"sortBy": "Recommend.All", "sortOrder": "desc"},
        "range": [0, limit],
    }

    if filters:
        payload["filter"] = filters

    return payload


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric != numeric:
        return None
    return numeric


def _fmt_number(value: Optional[float], suffix: str = "", digits: int = 1) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}{suffix}"


def analyst_rating_label(value: Optional[float]) -> str:
    if value is None:
        return "Belum ada rating"
    if value >= 0.5:
        return "Pembelian kuat"
    if value >= 0.15:
        return "Beli"
    if value > -0.15:
        return "Netral"
    if value > -0.5:
        return "Jual"
    return "Jual kuat"


def valuation_label(per: Optional[float], pbv: Optional[float]) -> str:
    if per is not None and 0 < per <= 12 and (pbv is None or pbv <= 1.8):
        return "Murah"
    if per is not None and per <= 25 and (pbv is None or pbv <= 4):
        return "Wajar"
    if pbv is not None and pbv <= 1.2 and (per is None or per <= 30):
        return "Aset murah"
    return "Mahal/Perlu cek"


def _score_range(value: Optional[float], good: float, weak: float, higher_better: bool = True) -> int:
    if value is None:
        return 4
    if higher_better:
        if value >= good:
            return 10
        if value <= weak:
            return 1
        return round(1 + 9 * ((value - weak) / (good - weak)))
    if value <= good:
        return 10
    if value >= weak:
        return 1
    return round(1 + 9 * ((weak - value) / (weak - good)))


def analyze_stock(row: Dict[str, Any]) -> Dict[str, Any]:
    per = row["per"]
    pbv = row["pbv"]
    roe = row["roe"]
    debt_to_equity = row["debt_to_equity"]
    dividend_yield = row["dividend_yield"]
    revenue_growth = row["revenue_growth"]
    eps_growth = row["eps_growth"]
    ytd = row["performance_ytd"]
    recommendation = row["recommendation_score"]
    beta = row["beta"]

    score_parts = [
        _score_range(recommendation, 0.5, -0.5),
        _score_range(per, 10, 35, higher_better=False),
        _score_range(pbv, 1.2, 6, higher_better=False),
        _score_range(roe, 18, 3),
        _score_range(revenue_growth, 15, -10),
        _score_range(eps_growth, 15, -20),
        _score_range(dividend_yield, 5, 0),
        _score_range(debt_to_equity, 0.5, 2.5, higher_better=False),
        _score_range(ytd, 20, -30),
    ]
    investment_score = round(sum(score_parts) / len(score_parts) * 10)

    reasons: List[str] = []
    risks: List[str] = []

    if recommendation is not None and recommendation >= 0.5:
        reasons.append("Konsensus teknikal/analis TradingView berada di area pembelian kuat.")
    elif recommendation is not None and recommendation >= 0.15:
        reasons.append("Sinyal TradingView condong beli, memberi dukungan awal untuk dipantau.")

    if per is not None and 0 < per <= 15:
        reasons.append(f"PER {per:.1f}x masih relatif rendah untuk kandidat value.")
    elif per is not None and per > 35:
        risks.append(f"PER {per:.1f}x tinggi, sehingga margin of safety perlu diuji lagi.")

    if pbv is not None and pbv <= 1.5:
        reasons.append(f"PBV {pbv:.1f}x menunjukkan harga belum terlalu mahal terhadap nilai buku.")
    elif pbv is not None and pbv > 5:
        risks.append(f"PBV {pbv:.1f}x mahal, rawan koreksi jika ekspektasi turun.")

    if roe is not None and roe >= 15:
        reasons.append(f"ROE {roe:.1f}% menandakan profitabilitas modal kuat.")
    elif roe is not None and roe < 5:
        risks.append(f"ROE {roe:.1f}% rendah, kualitas laba perlu dicek.")

    if revenue_growth is not None and revenue_growth >= 10:
        reasons.append(f"Pertumbuhan pendapatan TTM {revenue_growth:.1f}% memberi dukungan fundamental.")
    elif revenue_growth is not None and revenue_growth < 0:
        risks.append(f"Pendapatan TTM turun {abs(revenue_growth):.1f}%, perlu cek penyebabnya.")

    if dividend_yield is not None and dividend_yield >= 4:
        reasons.append(f"Dividend yield {dividend_yield:.1f}% menarik untuk investor income.")

    if debt_to_equity is not None and debt_to_equity <= 0.7:
        reasons.append("Leverage rendah, memberi ruang lebih baik saat siklus melemah.")
    elif debt_to_equity is not None and debt_to_equity > 2:
        risks.append("Leverage tinggi, sensitif terhadap bunga dan pelemahan arus kas.")

    if beta is not None and beta > 1.5:
        risks.append(f"Beta {beta:.1f}x menandakan volatilitas lebih tinggi dari pasar.")

    if not reasons:
        reasons.append("Belum ada kombinasi metrik yang cukup kuat; cocok hanya untuk watchlist awal.")
    if not risks:
        risks.append("Tetap validasi laporan keuangan, likuiditas, dan katalis terbaru sebelum membeli.")

    if investment_score >= 75:
        verdict = "Menarik untuk riset lanjut"
    elif investment_score >= 60:
        verdict = "Layak dipantau"
    elif investment_score >= 45:
        verdict = "Netral, tunggu konfirmasi"
    else:
        verdict = "Spekulatif/berisiko"

    summary = (
        f"{row['ticker']} mendapat skor {investment_score}/100. "
        f"Faktor utama: {reasons[0]} Risiko utama: {risks[0]}"
    )

    return {
        "investmentScore": investment_score,
        "verdict": verdict,
        "summary": summary,
        "investmentReasons": reasons[:4],
        "risks": risks[:3],
    }


def normalize_scan_row(symbol: str, values: List[Any]) -> Dict[str, Any]:
    raw = dict(zip(TV_COLUMNS, values))
    ticker = raw.get("name") or symbol.replace("IDX:", "")
    per = _num(raw.get("price_earnings_ttm"))
    pbv = _num(raw.get("price_book_fq"))
    roe = _num(raw.get("return_on_equity_fq"))
    row = {
        "symbol": symbol,
        "ticker": ticker,
        "companyName": raw.get("description") or ticker,
        "price": _num(raw.get("close")),
        "change": _num(raw.get("change")),
        "volume": _num(raw.get("volume")),
        "marketCap": _num(raw.get("market_cap_basic")),
        "per": per,
        "pbv": pbv,
        "eps": _num(raw.get("earnings_per_share_basic_ttm")),
        "eps_growth": _num(raw.get("earnings_per_share_diluted_yoy_growth_ttm")),
        "dividend_yield": _num(raw.get("dividends_yield_current")),
        "sector": raw.get("sector") or "Tidak diklasifikasi",
        "recommendation_score": _num(raw.get("Recommend.All")),
        "recommendation": analyst_rating_label(_num(raw.get("Recommend.All"))),
        "roe": roe,
        "roa": _num(raw.get("return_on_assets_fq")),
        "debt_to_equity": _num(raw.get("debt_to_equity_fq")),
        "revenue_growth": _num(raw.get("total_revenue_yoy_growth_ttm")),
        "performance_ytd": _num(raw.get("Perf.YTD")),
        "beta": _num(raw.get("beta_1_year")),
        "valuation": valuation_label(per, pbv),
    }
    row["analysis"] = analyze_stock(row)

    row.update(
        {
            "Ticker": row["ticker"],
            "Nama Perusahaan": row["companyName"],
            "Harga": _fmt_number(row["price"], digits=0),
            "Perubahan %": _fmt_number(row["change"], "%"),
            "Volume": _fmt_number(row["volume"], digits=0),
            "Market Cap": _fmt_number(row["marketCap"], digits=0),
            "P/E": _fmt_number(row["per"], "x"),
            "EPS": _fmt_number(row["eps"]),
            "Rekomendasi Analis": row["recommendation"],
            "Dividen Yield": _fmt_number(row["dividend_yield"], "%"),
            "Valuasi": row["valuation"],
        }
    )
    return row


def build_market_summary(rows: List[Dict[str, Any]], screen_config: Dict[str, Any]) -> Dict[str, Any]:
    total = len(rows)
    if not total:
        return {
            "screenTitle": screen_config.get("title", "TradingView Screener"),
            "sourceUrl": TRADINGVIEW_SCREEN_URL,
            "total": 0,
            "averageScore": 0,
            "strongBuyCount": 0,
            "topSectors": [],
            "keyInsight": "Belum ada data yang dapat dianalisis.",
        }

    average_score = round(sum(row["analysis"]["investmentScore"] for row in rows) / total)
    strong_buy_count = sum(1 for row in rows if row["recommendation"] == "Pembelian kuat")

    sector_counts: Dict[str, int] = {}
    for row in rows:
        sector_counts[row["sector"]] = sector_counts.get(row["sector"], 0) + 1
    top_sectors = [
        {"sector": sector, "count": count}
        for sector, count in sorted(sector_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    top_pick = rows[0]
    key_insight = (
        f"{top_pick['ticker']} menjadi kandidat teratas dengan skor "
        f"{top_pick['analysis']['investmentScore']}/100 dan status "
        f"{top_pick['analysis']['verdict'].lower()}."
    )

    return {
        "screenTitle": screen_config.get("title", "TradingView Screener"),
        "sourceUrl": TRADINGVIEW_SCREEN_URL,
        "total": total,
        "averageScore": average_score,
        "strongBuyCount": strong_buy_count,
        "topSectors": top_sectors,
        "keyInsight": key_insight,
    }


def fetch_and_analyze_tradingview_screen(limit: int = 500) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    screen_config = fetch_screen_config()
    time.sleep(1.0)
    payload = build_scan_payload(screen_config, limit)
    response = requests.post(
        TRADINGVIEW_SCAN_URL,
        json=payload,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Origin": "https://www.tradingview.com",
            "Referer": TRADINGVIEW_SCREEN_URL,
        },
    )
    response.raise_for_status()
    scan_result = response.json()
    rows = [
        normalize_scan_row(item.get("s", ""), item.get("d", []))
        for item in scan_result.get("data", [])
    ]
    rows.sort(
        key=lambda row: (
            row["analysis"]["investmentScore"],
            row["recommendation_score"] if row["recommendation_score"] is not None else -9,
            row["marketCap"] if row["marketCap"] is not None else 0,
        ),
        reverse=True,
    )
    summary = build_market_summary(rows, screen_config)
    metadata = {
        "sourceUrl": TRADINGVIEW_SCREEN_URL,
        "screenId": screen_config.get("id"),
        "screenTitle": screen_config.get("title"),
        "totalAvailable": scan_result.get("totalCount", len(rows)),
        "fetchedAt": now_iso(),
    }
    update_agent_status("tradingview", "ok")
    return rows, summary, metadata
