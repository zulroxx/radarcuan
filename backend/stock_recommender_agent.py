import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yfinance as yf
from dotenv import load_dotenv
from mistralai.client import Mistral

logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "agent_cache"
CACHE_DIR.mkdir(exist_ok=True)
STOCK_CACHE_FILE = CACHE_DIR / "stock_recommendations.json"
CACHE_TTL_SECONDS = 3600
TV_CACHE_FILE = ROOT_DIR / "tradingview_cache.json"

LLM_MODEL = os.environ.get("LLM_MODEL", "mistral-small-latest")

TV_TO_IDX_SECTOR = {
    "Electronic Technology": "Teknologi",
    "Technology Services": "Teknologi",
    "Health Technology": "Kesehatan",
    "Health Services": "Kesehatan",
    "Communications": "Telekomunikasi",
    "Finance": "Keuangan",
    "Perbankan": "Perbankan",
    "Banking": "Perbankan",
    "Consumer Non-Durables": "Konsumer Non-Primer",
    "Consumer Durables": "Konsumer",
    "Energy Minerals": "Energi",
    "Non-Energy Minerals": "Bahan Baku",
    "Utilities": "Infrastruktur",
    "Transportation": "Transportasi & Logistik",
    "Retail Trade": "Konsumer",
    "Commercial Services": "Jasa & Perdagangan",
    "Producer Manufacturing": "Industri",
    "Process Industries": "Bahan Baku",
    "Distribution Services": "Distribusi",
    "Industrial Services": "Industri",
    "Consumer Services": "Konsumer Non-Primer",
    "Miscellaneous": "Lainnya",
}

IDX_TO_TV_SECTORS: Dict[str, List[str]] = {}
for tv_name, idx_name in TV_TO_IDX_SECTOR.items():
    if idx_name not in IDX_TO_TV_SECTORS:
        IDX_TO_TV_SECTORS[idx_name] = []
    IDX_TO_TV_SECTORS[idx_name].append(tv_name)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_idn_market_open() -> bool:
    now = datetime.now(timezone(timedelta(hours=7)))
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour < 15


def load_cached_recommendations(sector: str, limit: int) -> Optional[Dict[str, Any]]:
    if not STOCK_CACHE_FILE.exists():
        return None
    try:
        with open(STOCK_CACHE_FILE, 'r', encoding='utf-8') as f:
            all_cache: Dict = json.load(f)
        entry = all_cache.get(sector)
        if not entry:
            return None
        cached_time = datetime.fromisoformat(entry.get('generated_at', ''))
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if is_idn_market_open():
            if age < CACHE_TTL_SECONDS and entry.get("limit", 0) >= limit:
                return entry
        else:
            if entry.get("limit", 0) >= limit:
                return entry
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def save_cache(sector: str, data: Dict[str, Any]) -> None:
    try:
        all_cache: Dict = {}
        if STOCK_CACHE_FILE.exists():
            with open(STOCK_CACHE_FILE, 'r', encoding='utf-8') as f:
                all_cache = json.load(f)
        all_cache[sector] = data
        with open(STOCK_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Gagal menyimpan cache: {e}")


def get_llm_client() -> Mistral:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY tidak ditemukan")
    return Mistral(api_key=api_key, server_url=os.environ.get("LLM_BASE_URL", "https://api.mistral.ai"))


def load_tv_records_from_cache() -> Optional[List[Dict[str, Any]]]:
    if not TV_CACHE_FILE.exists():
        return None
    try:
        with open(TV_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        return cached.get('data', [])
    except (json.JSONDecodeError, KeyError):
        return None


def get_stocks_in_sector(sector_name: str) -> List[Dict[str, Any]]:
    records = load_tv_records_from_cache()
    if not records:
        try:
            backend_dir = Path(__file__).parent
            import sys
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            from tradingview_agent import fetch_and_analyze_tradingview_screen
            records, _, _ = fetch_and_analyze_tradingview_screen(limit=500)
        except Exception as e:
            logger.warning(f"Gagal fetch TV: {e}")
            return []

    tv_sector_names = IDX_TO_TV_SECTORS.get(sector_name, [sector_name])
    tv_names_lower = {s.lower() for s in tv_sector_names}
    stocks = [r for r in records if (r.get("sector") or "").lower() in tv_names_lower]
    stocks.sort(key=lambda x: (x.get("analysis") or {}).get("investmentScore", 0) or 0, reverse=True)
    return stocks


def fetch_news_batch(stocks: List[Dict[str, Any]], max_stocks: int = 5, max_articles: int = 2) -> Dict[str, List[Dict[str, str]]]:
    news_map: Dict[str, List[Dict[str, str]]] = {}
    for stock in stocks[:max_stocks]:
        ticker = stock.get("ticker", "")
        if not ticker:
            continue
        try:
            yf_ticker = yf.Ticker(f"{ticker}.JK" if not ticker.endswith(".JK") else ticker)
            raw_news = getattr(yf_ticker, "news", []) or []
            articles = [{"title": a.get("title", ""), "publisher": a.get("publisher", "")} 
                       for a in raw_news[:max_articles]]
            news_map[ticker] = articles
        except Exception:
            news_map[ticker] = []
    return news_map


def build_prompt(sector_name: str, stocks: List[Dict[str, Any]], news_data: Dict[str, List[Dict[str, str]]],
                 sector_prediction: Optional[Dict[str, Any]] = None) -> str:
    stocks_simple = []
    for s in stocks[:15]:
        analysis = s.get("analysis") or {}
        stocks_simple.append({
            "ticker": s.get("ticker"), "companyName": s.get("companyName"), "price": s.get("price"),
            "per": s.get("per"), "pbv": s.get("pbv"), "roe": s.get("roe"),
            "revenue_growth": s.get("revenue_growth"), "eps_growth": s.get("eps_growth"),
            "dividend_yield": s.get("dividend_yield"), "debt_to_equity": s.get("debt_to_equity"),
            "investment_score": analysis.get("investmentScore"), "valuation": s.get("valuation"),
        })
    stocks_json = json.dumps(stocks_simple, ensure_ascii=False, indent=2)
    news_json = json.dumps(news_data, ensure_ascii=False, indent=2)

    sector_ctx = ""
    if sector_prediction:
        sector_ctx = f"\nPREDIKSI SEKTOR: {json.dumps(sector_prediction, ensure_ascii=False)}\n"

    # Macro context for sector
    macro_context = ""
    try:
        from macro_agent import get_sector_macro_context
        macro_indicators = get_sector_macro_context(sector_name)
        if macro_indicators:
            macro_context = "\nKONDISI MAKRO TERKAIT SEKTOR INI:\n"
            for ind in macro_indicators:
                macro_context += f"- {ind['label']}: {ind['value']} (trend: {ind.get('trend', 'netral')}) — {ind.get('impact', '')}\n"
    except Exception:
        pass

    from scoring_model import WEIGHTS
    weights_str = json.dumps(WEIGHTS, indent=2)

    return f"""Anda analis AI saham Indonesia. Rekomendasikan saham terbaik di sektor {sector_name}.
{sector_ctx}
{macro_context}
DATA SAHAM (Teknikal + Fundamental):
{stocks_json}

BERITA TERBARU:
{news_json}

BOBOT PENILAIAN:
{weights_str}

PERTIMBANGKAN:
1. FUNDAMENTAL: PER, PBV, ROE, revenue growth, EPS growth, dividend yield, debt-to-equity
2. TEKNIKAL: skor investasi dari analisis
3. MAKRO: bagaimana kondisi ekonomi mempengaruhi sektor {sector_name}
4. BERITA: sentimen berita terkini
5. VALUASI: apakah saham murah atau mahal relatif terhadap sektor

Per saham berikan:
- ticker, score (0-100), recommendation (Strong Buy/Buy/Hold/Sell/Strong Sell)
- rationale: jelaskan KENAPA — sebut PER, ROE, valuasi, dan pengaruh makro
- news_sentiment ("positif"/"netral"/"negatif")
- key_headline
- risks (1-2 risiko spesifik)
- key_metrics: per, pbv, roe, revenue_growth, dividend_yield
- fundamental_score: skor fundamental 0-100
- valuation_score: skor valuasi 0-100

RESPON JSON:
{{"sector":"{sector_name}","recommendations":[{{"ticker":"BBCA","score":85,"recommendation":"Strong Buy","rationale":"PER 14x menarik dengan ROE 23% dan BI rate turun mendukung margin bunga","news_sentiment":"positif","key_headline":"BBCA laba naik 12%","risks":["Kredit macet"],"key_metrics":{{"per":14,"pbv":2.8,"roe":23,"revenue_growth":12,"dividend_yield":4.2}},"fundamental_score":82,"valuation_score":70}}]}}
Max 10 rekomendasi, urut dari score tertinggi. JANGAN tulis apapun di luar JSON."""


def parse_llm_response(content: str) -> Dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(line for line in lines if not line.startswith("```"))
    content = content.strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("JSON tidak ditemukan")
    json_str = content[start:end+1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        import re
        json_str = re.sub(r',\s*\}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        return json.loads(json_str)


def recommend_stocks(sector_name: str, limit: int = 10, refresh: bool = False,
                     sector_prediction: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not refresh:
        cached = load_cached_recommendations(sector_name, limit)
        if cached:
            return cached

    logger.info(f"Recommending stocks for {sector_name} (enhanced)...")

    stocks = get_stocks_in_sector(sector_name)
    if not stocks:
        return {"sector": sector_name, "recommendations": [],
                "message": f"Tidak ada data saham untuk sektor {sector_name}.", "generated_at": now_iso()}

    news_data = fetch_news_batch(stocks)
    prompt = build_prompt(sector_name, stocks, news_data, sector_prediction)

    client = get_llm_client()
    response = client.chat.complete(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=16000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    parsed = parse_llm_response(content)

    result = {
        "sector": sector_name,
        "recommendations": (parsed.get("recommendations", []) or [])[:limit],
        "generated_at": now_iso(),
        "model": LLM_MODEL,
        "limit": limit,
        "method": "enhanced_fundamental_macro",
    }
    save_cache(sector_name, result)
    return result
