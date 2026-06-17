import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

ROOT_DIR = Path(__file__).parent
MACRO_CACHE_FILE = ROOT_DIR / "agent_cache" / "macro_data.json"
MACRO_CACHE_TTL = 3600

logger = logging.getLogger(__name__)

BASE_MACRO_DATA: List[Dict[str, Any]] = [
    # === Domestic Monetary Policy ===
    {
        "id": "bi_rate",
        "label": "BI Rate",
        "category": "Moneter Domestik",
        "unit": "%",
        "defaultValue": "5.75",
        "change": -0.25,
        "description": "Suku bunga acuan BI 7-Day RR",
        "source": "Bank Indonesia",
        "updated_at": None,
        "impact": "Suku bunga rendah mendorong sektor perbankan, properti, konsumer",
        "trend": "menurun",
    },
    {
        "id": "inflation",
        "label": "Inflasi (IHK)",
        "category": "Moneter Domestik",
        "unit": "%",
        "defaultValue": "2.48",
        "change": -0.12,
        "description": "YoY — Indeks Harga Konsumen",
        "source": "BPS",
        "updated_at": None,
        "impact": "Inflasi rendah menguntungkan sektor konsumer dan ritel",
        "trend": "stabil",
    },
    {
        "id": "gdp",
        "label": "PDB",
        "category": "Pertumbuhan Ekonomi",
        "unit": "%",
        "defaultValue": "5.03",
        "change": 0.08,
        "description": "Pertumbuhan YoY kuartal terakhir",
        "source": "BPS",
        "updated_at": None,
        "impact": "PDB tumbuh mendorong seluruh sektor secara umum",
        "trend": "positif",
    },
    {
        "id": "bond_yield",
        "label": "10Y Bond Yield",
        "category": "Moneter Domestik",
        "unit": "%",
        "defaultValue": "6.85",
        "change": 0.15,
        "description": "Yield obligasi pemerintah 10 tahun",
        "source": "Bloomberg / Reuters",
        "updated_at": None,
        "impact": "Yield tinggi membuat saham kurang menarik (risk-free rate naik)",
        "trend": "meningkat",
    },
    # === Exchange Rate & Commodities ===
    {
        "id": "usd_idr",
        "label": "USD/IDR",
        "category": "Nilai Tukar & Komoditas",
        "unit": "",
        "defaultValue": "16325",
        "change": None,
        "description": "Nilai tukar Rupiah terhadap USD",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "Rupiah melemah menguntungkan sektor eksportir (batu bara, CPO, tekstil)",
        "trend": "melemah",
    },
    {
        "id": "oil_price",
        "label": "Harga Minyak",
        "category": "Nilai Tukar & Komoditas",
        "unit": "USD",
        "defaultValue": "78.40",
        "change": None,
        "description": "Brent crude oil / barel",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "Minyak tinggi menguntungkan energi, merugikan transportasi & manufaktur",
        "trend": "volatil",
    },
    {
        "id": "coal_price",
        "label": "Harga Batubara",
        "category": "Nilai Tukar & Komoditas",
        "unit": "USD",
        "defaultValue": "142.50",
        "change": None,
        "description": "Newcastle coal / ton (estimasi)",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "Batubara tinggi langsung mendorong sektor energi",
        "trend": "stabil",
    },
    {
        "id": "cpo_price",
        "label": "Harga CPO",
        "category": "Nilai Tukar & Komoditas",
        "unit": "IDR",
        "defaultValue": "12850",
        "change": None,
        "description": "Crude Palm Oil / kg (estimasi)",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "CPO tinggi menguntungkan perkebunan dan agrikultur",
        "trend": "stabil",
    },
    # === Global Central Banks ===
    {
        "id": "fed_rate",
        "label": "Fed Rate",
        "category": "Kebijakan Global",
        "unit": "%",
        "defaultValue": "4.50",
        "change": -0.25,
        "description": "Suku bunga acuan Federal Reserve AS",
        "source": "Federal Reserve",
        "updated_at": None,
        "impact": "Fed Rate turun meredakan tekanan di pasar emerging market termasuk Indonesia",
        "trend": "menurun",
    },
    {
        "id": "us_inflation",
        "label": "Inflasi AS",
        "category": "Kebijakan Global",
        "unit": "%",
        "defaultValue": "3.10",
        "change": -0.20,
        "description": "YoY CPI AS — indikator inflasi global",
        "source": "US BLS",
        "updated_at": None,
        "impact": "Inflasi AS turun memberi ruang The Fed menurunkan suku bunga",
        "trend": "menurun",
    },
    {
        "id": "us_10y_yield",
        "label": "US 10Y Treasury",
        "category": "Kebijakan Global",
        "unit": "%",
        "defaultValue": "4.20",
        "change": -0.10,
        "description": "Yield obligasi AS 10 tahun — acuan global risk-free rate",
        "source": "US Treasury",
        "updated_at": None,
        "impact": "Yield AS turun mendorong aliran modal ke emerging market",
        "trend": "menurun",
    },
    # === Global Indices ===
    {
        "id": "sp500",
        "label": "S&P 500",
        "category": "Indeks Global",
        "unit": "",
        "defaultValue": "5420.5",
        "change": None,
        "description": "Indeks saham AS — sentimen risk appetite global",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "S&P 1300 naik menandakan risk-on global, positif untuk emerging market",
        "trend": "positif",
    },
    {
        "id": "nikkei",
        "label": "Nikkei 225",
        "category": "Indeks Global",
        "unit": "",
        "defaultValue": "38450",
        "change": None,
        "description": "Indeks saham Jepang — barometer Asia",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "Nikkei naik menandakan sentimen positif di Asia",
        "trend": "positif",
    },
    {
        "id": "hsi",
        "label": "HSI",
        "category": "Indeks Global",
        "unit": "",
        "defaultValue": "18400",
        "change": None,
        "description": "Hang Seng Index — sentimen ekonomi China",
        "source": "Yahoo Finance",
        "updated_at": None,
        "impact": "HSI naik mengindikasikan permintaan China menguat, positif untuk komoditas",
        "trend": "positif",
    },
    # === Capital Flow ===
    {
        "id": "foreign_flow",
        "label": "Foreign Flow",
        "category": "Aliran Modal",
        "unit": "T",
        "defaultValue": "2.8",
        "change": None,
        "description": "Net buy asing minggu ini (IDR)",
        "source": "KSEI / RTI",
        "updated_at": None,
        "impact": "Asing net buy menandakan kepercayaan investor global terhadap Indonesia",
        "trend": "positif",
    },
    {
        "id": "reserves",
        "label": "Cadangan Devisa",
        "category": "Aliran Modal",
        "unit": "B",
        "defaultValue": "146.2",
        "change": 3.1,
        "description": "Posisi akhir bulan lalu (USD)",
        "source": "Bank Indonesia",
        "updated_at": None,
        "impact": "Cadangan devisa tinggi memberi stabilitas nilai tukar",
        "trend": "positif",
    },
]

YFINANCE_TICKERS = {
    "usd_idr": "IDR=X",
    "ihsg": "^JKSE",
    "oil_price": "BZ=F",
    "sp500": "^GSPC",
    "nikkei": "^N225",
    "hsi": "^HSI",
}

SECTOR_MACRO_SENSITIVITY = {
    "Perbankan": ["bi_rate", "fed_rate", "gdp", "bond_yield", "us_10y_yield"],
    "Keuangan": ["bi_rate", "fed_rate", "bond_yield", "sp500"],
    "Teknologi": ["sp500", "nikkei", "us_10y_yield", "foreign_flow"],
    "Kesehatan": ["gdp", "inflation"],
    "Telekomunikasi": ["bi_rate", "inflation"],
    "Energi": ["oil_price", "coal_price", "usd_idr", "hsi"],
    "Bahan Baku": ["coal_price", "cpo_price", "usd_idr", "hsi"],
    "Infrastruktur": ["bi_rate", "gdp", "bond_yield"],
    "Transportasi & Logistik": ["oil_price", "gdp", "inflation"],
    "Konsumer Non-Primer": ["inflation", "bi_rate", "gdp"],
    "Konsumer": ["inflation", "gdp", "bi_rate"],
    "Industri": ["gdp", "usd_idr", "oil_price"],
    "Distribusi": ["gdp", "inflation"],
    "Jasa & Perdagangan": ["gdp", "inflation", "usd_idr"],
    "Lainnya": ["gdp", "sp500"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_cache() -> Optional[Dict[str, Any]]:
    if not MACRO_CACHE_FILE.exists():
        return None
    try:
        with open(MACRO_CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached.get("cached_at", ""))
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if age < MACRO_CACHE_TTL:
            return cached
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def save_cache(indicators: List[Dict[str, Any]]) -> None:
    cache_data = {
        "cached_at": now_iso(),
        "indicators": indicators,
    }
    MACRO_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MACRO_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)


def fetch_live_data() -> Dict[str, Optional[float]]:
    results: Dict[str, Optional[float]] = {}
    for key, ticker in YFINANCE_TICKERS.items():
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period="1d")
            if not hist.empty:
                price = hist["Close"].iloc[-1]
                if key == "usd_idr":
                    results[key] = round(float(price), 0)
                elif key == "oil_price":
                    results[key] = round(float(price), 2)
                elif key in ("ihsg", "sp500", "nikkei", "hsi"):
                    results[key] = round(float(price), 1)
            else:
                info = tk.info
                if info and "regularMarketPrice" in info:
                    price = info["regularMarketPrice"]
                    if price:
                        results[key] = round(float(price), 2)
        except Exception as e:
            logger.warning(f"Gagal mengambil data yfinance untuk {key}: {e}")
    return results


async def fetch_live_data_async() -> Dict[str, Optional[float]]:
    """Parallel async version of fetch_live_data — 5-10x faster."""

    async def fetch_one(key: str, ticker: str) -> Tuple[str, Optional[float]]:
        try:
            tk = await asyncio.to_thread(yf.Ticker, ticker)
            hist = await asyncio.to_thread(lambda: tk.history(period="1d"))
            if not hist.empty:
                price = hist["Close"].iloc[-1]
                if key == "usd_idr":
                    return key, round(float(price), 0)
                elif key == "oil_price":
                    return key, round(float(price), 2)
                elif key in ("ihsg", "sp500", "nikkei", "hsi"):
                    return key, round(float(price), 1)
            else:
                info = await asyncio.to_thread(lambda: tk.info)
                if info and "regularMarketPrice" in info:
                    price = info["regularMarketPrice"]
                    if price:
                        return key, round(float(price), 2)
        except Exception as e:
            logger.warning(f"Gagal fetch yfinance async {key}: {e}")
        return key, None

    tasks = [fetch_one(key, ticker) for key, ticker in YFINANCE_TICKERS.items()]
    results_list = await asyncio.gather(*tasks)
    return dict(results_list)


def get_macro_indicators(refresh: bool = False) -> Dict[str, Any]:
    if not refresh:
        cached = load_cache()
        if cached:
            return {
                "indicators": cached["indicators"],
                "cached_at": cached["cached_at"],
                "from_cache": True,
            }

    live = fetch_live_data()
    timestamp = now_iso()

    indicators = []
    for item in BASE_MACRO_DATA:
        indicator = dict(item)
        ind_id = indicator["id"]

        if ind_id in live and live[ind_id] is not None:
            live_val = live[ind_id]
            default_val = float(indicator["defaultValue"].replace(",", ""))
            if default_val != 0:
                indicator["change"] = round(
                    ((live_val - default_val) / default_val) * 100, 2
                )
            indicator["liveValue"] = live_val

            if ind_id in ("usd_idr",):
                indicator["value"] = f"{live_val:,.0f}"
            elif ind_id in ("ihsg", "sp500"):
                indicator["value"] = f"{live_val:,.1f}"
            elif ind_id in ("nikkei", "hsi"):
                indicator["value"] = f"{live_val:,.0f}"
            elif ind_id == "oil_price":
                indicator["value"] = f"${live_val:.2f}"
            else:
                indicator["value"] = str(live_val)
        else:
            indicator["value"] = indicator["defaultValue"]

        indicator["updated_at"] = timestamp
        indicators.append(indicator)

    save_cache(indicators)

    return {
        "indicators": indicators,
        "cached_at": timestamp,
        "from_cache": False,
        "total": len(indicators),
    }


async def get_macro_indicators_async(refresh: bool = False) -> Dict[str, Any]:
    """Async version with parallel yfinance calls."""
    if not refresh:
        cached = load_cache()
        if cached:
            return {
                "indicators": cached["indicators"],
                "cached_at": cached["cached_at"],
                "from_cache": True,
            }

    live = await fetch_live_data_async()
    timestamp = now_iso()

    indicators = []
    for item in BASE_MACRO_DATA:
        indicator = dict(item)
        ind_id = indicator["id"]

        if ind_id in live and live[ind_id] is not None:
            live_val = live[ind_id]
            default_val = float(indicator["defaultValue"].replace(",", ""))
            if default_val != 0:
                indicator["change"] = round(
                    ((live_val - default_val) / default_val) * 100, 2
                )
            indicator["liveValue"] = live_val

            if ind_id in ("usd_idr",):
                indicator["value"] = f"{live_val:,.0f}"
            elif ind_id in ("ihsg", "sp500"):
                indicator["value"] = f"{live_val:,.1f}"
            elif ind_id in ("nikkei", "hsi"):
                indicator["value"] = f"{live_val:,.0f}"
            elif ind_id == "oil_price":
                indicator["value"] = f"${live_val:.2f}"
            else:
                indicator["value"] = str(live_val)
        else:
            indicator["value"] = indicator["defaultValue"]

        indicator["updated_at"] = timestamp
        indicators.append(indicator)

    save_cache(indicators)

    return {
        "indicators": indicators,
        "cached_at": timestamp,
        "from_cache": False,
        "total": len(indicators),
    }


def get_macro_summary() -> str:
    """Return a concise macro summary text for LLM prompts."""
    data = get_macro_indicators()
    lines = []
    for ind in data["indicators"]:
        trend = ind.get("trend", "netral")
        impact = ind.get("impact", "")
        lines.append(f"- {ind['label']}: {ind['value']} ({trend}) — {impact}")
    return "\n".join(lines)


def get_sector_macro_context(sector: str) -> List[Dict[str, Any]]:
    """Get relevant macro indicators for a specific sector."""
    data = get_macro_indicators()
    relevant_ids = SECTOR_MACRO_SENSITIVITY.get(sector, [])
    return [ind for ind in data["indicators"] if ind["id"] in relevant_ids]
