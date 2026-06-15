import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yfinance as yf

ROOT_DIR = Path(__file__).parent
MACRO_CACHE_FILE = ROOT_DIR / "agent_cache" / "macro_data.json"
MACRO_CACHE_TTL = 3600  # 1 hour

logger = logging.getLogger(__name__)

BASE_MACRO_DATA: List[Dict[str, Any]] = [
    {
        "id": "bi_rate",
        "label": "BI Rate",
        "category": "Kebijakan Moneter",
        "unit": "%",
        "defaultValue": "5.75",
        "change": -0.25,
        "description": "Suku bunga acuan BI 7-Day RR",
        "source": "Bank Indonesia",
        "updated_at": None,
    },
    {
        "id": "inflation",
        "label": "Inflasi (IHK)",
        "category": "Kebijakan Moneter",
        "unit": "%",
        "defaultValue": "2.48",
        "change": -0.12,
        "description": "YoY — Indeks Harga Konsumen",
        "source": "BPS",
        "updated_at": None,
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
    },
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
    },
    {
        "id": "bond_yield",
        "label": "10Y Bond Yield",
        "category": "Kebijakan Moneter",
        "unit": "%",
        "defaultValue": "6.85",
        "change": 0.15,
        "description": "Yield obligasi pemerintah 10 tahun",
        "source": "Bloomberg / Reuters",
        "updated_at": None,
    },
    {
        "id": "cad",
        "label": "CAD",
        "category": "Pertumbuhan Ekonomi",
        "unit": "B",
        "defaultValue": "-2.4",
        "change": -0.3,
        "description": "Current Account Defisit (USD)",
        "source": "Bank Indonesia",
        "updated_at": None,
    },
    {
        "id": "reserves",
        "label": "Cadangan Devisa",
        "category": "Kebijakan Moneter",
        "unit": "B",
        "defaultValue": "146.2",
        "change": 3.1,
        "description": "Posisi akhir bulan lalu (USD)",
        "source": "Bank Indonesia",
        "updated_at": None,
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
    },
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
    },
    {
        "id": "ihsg",
        "label": "IHSG",
        "category": "Pertumbuhan Ekonomi",
        "unit": "",
        "defaultValue": "7125.4",
        "change": None,
        "description": "Indeks Harga Saham Gabungan",
        "source": "Yahoo Finance",
        "updated_at": None,
    },
]

YFINANCE_TICKERS = {
    "usd_idr": "IDR=X",
    "ihsg": "^JKSE",
    "oil_price": "BZ=F",
}

# Approximate tickers for coal and CPO
# Newcastle coal futures - not directly on yfinance, use MTF (Methane) or none
# CPO - use FCPO or similar


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
                    # IDR=X gives USD/IDR rate
                    results[key] = round(float(price), 0)
                elif key == "oil_price":
                    results[key] = round(float(price), 2)
                elif key == "ihsg":
                    results[key] = round(float(price), 1)
            else:
                # Try getting regular market price
                info = tk.info
                if info and "regularMarketPrice" in info:
                    price = info["regularMarketPrice"]
                    if price:
                        results[key] = round(float(price), 2)
        except Exception as e:
            logger.warning(f"Gagal mengambil data yfinance untuk {key}: {e}")
    return results


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

        if indicator["id"] in live and live[indicator["id"]] is not None:
            live_val = live[indicator["id"]]
            default_val = float(indicator["defaultValue"].replace(",", ""))
            indicator["change"] = round(
                ((live_val - default_val) / default_val) * 100, 2
            )

            if indicator["id"] == "usd_idr":
                indicator["value"] = f"{live_val:,.0f}"
            elif indicator["id"] == "ihsg":
                indicator["value"] = f"{live_val:,.1f}"
            elif indicator["id"] == "oil_price":
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
