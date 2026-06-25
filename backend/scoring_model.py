"""Weighted scoring model combining technical, fundamental, and macro factors."""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default weights — configurable
WEIGHTS = {
    "technical": 0.30,
    "fundamental": 0.40,
    "macro_sector_fit": 0.15,
    "valuation": 0.15,
}

SECTOR_MACRO_MAP = {
    "Keuangan": {
        "favorable_when": [
            ("bi_rate", "menurun", -1),
            ("fed_rate", "menurun", -1),
            ("gdp", "positif", 1),
            ("us_10y_yield", "menurun", -1),
            ("bond_yield", "menurun", -1),
            ("inflation", "stabil", 1),
            ("sp500", "positif", 1),
            ("foreign_flow", "positif", 1),
        ],
        "unfavorable_when": [
            ("bi_rate", "meningkat", 1),
            ("fed_rate", "meningkat", 1),
        ],
    },
    "Teknologi": {
        "favorable_when": [
            ("sp500", "positif", 1),
            ("nikkei", "positif", 1),
            ("us_10y_yield", "menurun", -1),
            ("foreign_flow", "positif", 1),
        ],
        "unfavorable_when": [
            ("us_10y_yield", "meningkat", 1),
            ("fed_rate", "meningkat", 1),
        ],
    },
    "Energi": {
        "favorable_when": [
            ("oil_price", "meningkat", 1),
            ("coal_price", "meningkat", 1),
            ("usd_idr", "melemah", 1),
        ],
        "unfavorable_when": [
            ("oil_price", "menurun", -1),
            ("coal_price", "menurun", -1),
        ],
    },
    "Bahan Baku": {
        "favorable_when": [
            ("coal_price", "meningkat", 1),
            ("cpo_price", "meningkat", 1),
            ("hsi", "positif", 1),
            ("usd_idr", "melemah", 1),
        ],
        "unfavorable_when": [
            ("coal_price", "menurun", -1),
            ("cpo_price", "menurun", -1),
            ("hsi", "negatif", -1),
        ],
    },
    "Konsumer Non-Primer": {
        "favorable_when": [
            ("inflation", "stabil", 1),
            ("bi_rate", "menurun", -1),
            ("gdp", "positif", 1),
        ],
        "unfavorable_when": [
            ("inflation", "meningkat", -1),
            ("bi_rate", "meningkat", 1),
        ],
    },
    "Konsumer": {
        "favorable_when": [
            ("inflation", "menurun", 1),
            ("gdp", "positif", 1),
        ],
        "unfavorable_when": [
            ("inflation", "meningkat", -1),
        ],
    },
    "Infrastruktur": {
        "favorable_when": [
            ("bi_rate", "menurun", -1),
            ("gdp", "positif", 1),
            ("bond_yield", "menurun", -1),
        ],
        "unfavorable_when": [
            ("bi_rate", "meningkat", 1),
        ],
    },
    "Transportasi & Logistik": {
        "favorable_when": [
            ("oil_price", "menurun", -1),
            ("gdp", "positif", 1),
            ("inflation", "stabil", 1),
        ],
        "unfavorable_when": [
            ("oil_price", "meningkat", 1),
        ],
    },
    "Kesehatan": {
        "favorable_when": [
            ("gdp", "positif", 1),
            ("inflation", "stabil", 1),
        ],
        "unfavorable_when": [],
    },
    "Telekomunikasi": {
        "favorable_when": [
            ("bi_rate", "menurun", -1),
            ("inflation", "stabil", 1),
        ],
        "unfavorable_when": [
            ("bi_rate", "meningkat", 1),
        ],
    },
    "Industri": {
        "favorable_when": [
            ("gdp", "positif", 1),
            ("usd_idr", "stabil", 1),
            ("oil_price", "stabil", 1),
        ],
        "unfavorable_when": [
            ("usd_idr", "melemah", -1),
            ("oil_price", "meningkat", 1),
        ],
    },
    "Distribusi": {
        "favorable_when": [
            ("gdp", "positif", 1),
            ("inflation", "stabil", 1),
        ],
        "unfavorable_when": [
            ("inflation", "meningkat", -1),
        ],
    },
    "Jasa & Perdagangan": {
        "favorable_when": [
            ("gdp", "positif", 1),
            ("inflation", "stabil", 1),
            ("usd_idr", "stabil", 1),
        ],
        "unfavorable_when": [
            ("inflation", "meningkat", -1),
            ("usd_idr", "melemah", -1),
        ],
    },
    "Lainnya": {
        "favorable_when": [
            ("gdp", "positif", 1),
            ("sp500", "positif", 1),
        ],
        "unfavorable_when": [],
    },
}


def score_technical(stock: Dict[str, Any]) -> float:
    """Extract the existing technical/valuation score from TradingView analysis."""
    analysis = stock.get("analysis", {})
    inv_score = analysis.get("investmentScore")
    if inv_score is not None:
        return float(inv_score)

    rec = stock.get("recommendation_score", 0.5)
    return float(rec) * 100


def score_valuation(stock: Dict[str, Any]) -> float:
    """Score based on valuation metrics (PER, PBV)."""
    score = 50.0
    count = 0

    per = stock.get("per")
    if per is not None and per > 0:
        if per < 8:
            score += 30
        elif per < 12:
            score += 20
        elif per < 18:
            score += 10
        elif per < 25:
            score += 0
        elif per < 35:
            score -= 10
        else:
            score -= 20
        count += 1

    pbv = stock.get("pbv")
    if pbv is not None and pbv > 0:
        if pbv < 1:
            score += 25
        elif pbv < 1.5:
            score += 15
        elif pbv < 3:
            score += 5
        elif pbv < 5:
            score -= 5
        else:
            score -= 15
        count += 1

    if count == 0:
        return 50.0

    return max(0, min(100, score))


def score_macro_sector_fit(
    sector: str, macro_indicators: List[Dict[str, Any]]
) -> float:
    """Score how well a sector fits current macro conditions (0-100)."""
    sector_rules = SECTOR_MACRO_MAP.get(sector)
    if not sector_rules or not macro_indicators:
        return 50.0

    macro_by_id = {ind["id"]: ind for ind in macro_indicators}
    score = 50.0
    total_weight = 0

    for ind_id, expected_trend, weight in sector_rules.get(
        "favorable_when", []
    ):
        indicator = macro_by_id.get(ind_id)
        if indicator:
            actual_trend = indicator.get("trend", "netral")
            if actual_trend == expected_trend:
                score += 10 * abs(weight)
            total_weight += abs(weight)

    for ind_id, expected_trend, weight in sector_rules.get(
        "unfavorable_when", []
    ):
        indicator = macro_by_id.get(ind_id)
        if indicator:
            actual_trend = indicator.get("trend", "netral")
            if actual_trend == expected_trend:
                score -= 15 * abs(weight)
            total_weight += abs(weight)

    if total_weight == 0:
        return 50.0

    return max(0, min(100, score))


def calculate_combined_score(
    stock: Dict[str, Any],
    sector: str,
    macro_indicators: List[Dict[str, Any]],
    fundamental_score: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Calculate combined score using weighted model."""
    w = weights or WEIGHTS
    tech = score_technical(stock)
    val = score_valuation(stock)
    macro = score_macro_sector_fit(sector, macro_indicators)
    fund = fundamental_score if fundamental_score is not None else 50.0

    combined = (
        tech * w["technical"]
        + fund * w["fundamental"]
        + macro * w["macro_sector_fit"]
        + val * w["valuation"]
    )

    return {
        "combined_score": round(combined, 1),
        "technical_score": round(tech, 1),
        "fundamental_score": round(fund, 1),
        "valuation_score": round(val, 1),
        "macro_sector_fit": round(macro, 1),
        "weights": w,
    }


def get_weighted_sector_score(
    sector_averages: Dict[str, Any],
    macro_indicators: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate a combined score for an entire sector."""
    tech = sector_averages.get("avg_score", 50.0)
    fund_rev = sector_averages.get("avg_revenue_growth")
    fund_eps = sector_averages.get("avg_eps_growth")
    fund_roe = sector_averages.get("avg_roe")
    der = sector_averages.get("avg_debt_to_equity")

    # Simple fundamental score from sector averages
    fund_score = 50.0
    count = 0
    if fund_rev is not None:
        fund_score += max(-20, min(20, fund_rev))
        count += 1
    if fund_eps is not None:
        fund_score += max(-20, min(20, fund_eps))
        count += 1
    if fund_roe is not None:
        if fund_roe > 20:
            fund_score += 15
        elif fund_roe > 15:
            fund_score += 10
        elif fund_roe > 10:
            fund_score += 5
        count += 1
    if der is not None:
        if der < 0.5:
            fund_score += 10
        elif der < 1.0:
            fund_score += 5
        elif der > 2.0:
            fund_score -= 10
        count += 1
    if count > 0:
        fund_score = max(0, min(100, fund_score))

    per = sector_averages.get("avg_per")
    val_score = 50.0
    if per is not None and per > 0:
        if per < 10:
            val_score = 75
        elif per < 15:
            val_score = 65
        elif per < 20:
            val_score = 50
        elif per < 30:
            val_score = 35
        else:
            val_score = 20

    sector_name = sector_averages.get("sector", "")
    macro_score = score_macro_sector_fit(sector_name, macro_indicators)

    w = WEIGHTS
    combined = (
        tech * w["technical"]
        + fund_score * w["fundamental"]
        + macro_score * w["macro_sector_fit"]
        + val_score * w["valuation"]
    )

    return {
        "combined_score": round(combined, 1),
        "technical_score": round(tech, 1),
        "fundamental_score": round(fund_score, 1),
        "valuation_score": round(val_score, 1),
        "macro_sector_fit": round(macro_score, 1),
    }
