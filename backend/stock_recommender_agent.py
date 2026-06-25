import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yfinance as yf
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from agent_status import update_agent_status
from fine_tuning.dataset_logger import log_llm_call
from rate_limiter import sync_rate_delay
from sector_constants import TV_TO_IDX_SECTOR, IDX_TO_TV_SECTORS

ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "agent_cache"
CACHE_DIR.mkdir(exist_ok=True)

logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

yf.set_tz_cache_location(str(CACHE_DIR / "yfinance_tz"))
(CACHE_DIR / "yfinance_tz").mkdir(parents=True, exist_ok=True)

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)
STOCK_CACHE_FILE = CACHE_DIR / "stock_recommendations.json"
from cache_config import CACHE_TTL

CACHE_TTL_SECONDS = CACHE_TTL["stock_recommendations"]
TV_CACHE_FILE = ROOT_DIR / "tradingview_cache.json"

LLM_MODEL = os.environ.get("LLM_MODEL", "qwen/qwen3-32b")

_CEREBRAS_BATCH_SYSTEM_PROMPT = """You are an expert stock analyst for the Indonesian Stock Exchange (IDX).

Your task is to analyze all sector data provided below and recommend the best stocks from each sector based on fundamentals, valuation, news sentiment, and growth prospects.

OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key `"recommendations"` berisi object, di mana key = nama sektor
3. Setiap sektor wajib punya key `"recommendations"` berisi array rekomendasi
4. Sertakan SEMUA sektor, gunakan `[]` untuk sektor tanpa rekomendasi
5. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
6. JSON harus lengkap dan valid — jangan terpotong

Each recommendation object MUST have these exact fields:
- ticker: string (e.g. "BBCA")
- companyName: string
- price: number or null
- per: number or null (price-to-earnings ratio)
- pbv: number or null (price-to-book value)
- roe: number or null (return on equity)
- revenue_growth: number or null
- eps_growth: number or null
- dividend_yield: number or null
- debt_to_equity: number or null
- investment_score: number (0-100)
- valuation: string ("Undervalued", "Fair Value", or "Overvalued")
- reason: string (reason for recommendation in Bahasa Indonesia)"""


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


def fetch_news_tradingview(ticker: str, max_articles: int = 5) -> List[Dict[str, str]]:
    try:
        clean = ticker.replace(".JK", "")
        url = f"https://www.tradingview.com/symbols/IDX-{clean}/news/"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]
            if not text or len(text) < 40:
                continue
            provider_span = link.find_previous("span")
            provider = provider_span.get_text(strip=True) if provider_span else ""
            if provider and len(provider) > 30:
                provider = ""
            articles.append({
                "title": text,
                "publisher": provider or "TradingView",
            })
            if len(articles) >= max_articles:
                break
        return articles
    except Exception:
        return []


def fetch_news_batch(stocks: List[Dict[str, Any]], max_stocks: int = 5, max_articles: int = 2) -> Dict[str, List[Dict[str, str]]]:
    news_map: Dict[str, List[Dict[str, str]]] = {}
    for i, stock in enumerate(stocks[:max_stocks]):
        ticker = stock.get("ticker", "")
        if not ticker:
            continue
        # Try TradingView first
        articles = fetch_news_tradingview(ticker, max_articles)
        # Fallback to yfinance
        if not articles:
            try:
                yf_ticker = yf.Ticker(f"{ticker}.JK" if not ticker.endswith(".JK") else ticker)
                raw_news = getattr(yf_ticker, "news", []) or []
                articles = [{"title": a.get("title", ""), "publisher": a.get("publisher", "")} 
                           for a in raw_news[:max_articles]]
            except Exception:
                articles = []
        news_map[ticker] = articles
        if i < len(stocks[:max_stocks]) - 1:
            sync_rate_delay(0.5)
    return news_map


_json_decoder = json.JSONDecoder(strict=False)


def _extract_first_json(text: str) -> str:
    """Extract first complete JSON object/array from text, handling nested brackets."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(line for line in lines if not line.startswith("```"))
    text = text.strip()

    try:
        obj, end = _json_decoder.raw_decode(text)
        return text[:end]
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        return text

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{' or ch == '[':
            depth += 1
        elif ch == '}' or ch == ']':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return text[start:]


def _repair_json(json_str: str) -> str:
    """Fix common JSON truncation: unterminated strings + missing closing brackets."""
    if json_str.count('"') % 2 != 0:
        json_str += '"'
    ob = json_str.count('{') - json_str.count('}')
    ab = json_str.count('[') - json_str.count(']')
    if ob > 0:
        json_str += '}' * ob
    if ab > 0:
        json_str += ']' * ab
    return json_str


def parse_llm_response(content: str) -> Dict[str, Any]:
    if not content or not content.strip():
        raise ValueError("Empty response from LLM")
    json_str = _extract_first_json(content)
    if not json_str:
        raise ValueError("No JSON found in response")

    # First, try standard parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Second, try _json_decoder.decode (more lenient) + clean trailing commas
    try:
        return _json_decoder.decode(json_str)
    except json.JSONDecodeError:
        import re
        json_str = re.sub(r',\s*\}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)

    # Third, try raw_decode — recovers a valid JSON prefix from truncated text
    try:
        obj, end = _json_decoder.raw_decode(json_str)
        logger.info("raw_decode recovered valid JSON prefix (len=%d)", end)
        return obj
    except json.JSONDecodeError:
        pass

    # Last resort: repair truncated JSON (add missing quotes/brackets) and retry
    json_str = _repair_json(json_str)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            obj, end = _json_decoder.raw_decode(json_str)
            logger.info("raw_decode (after repair) recovered valid JSON prefix (len=%d)", end)
            return obj
        except json.JSONDecodeError:
            raise


def recommend_stocks(sector_name: str, limit: int = 10, refresh: bool = False,
                     sector_prediction: Optional[Dict[str, Any]] = None,
                     use_mistral: bool = True) -> Dict[str, Any]:
    if not refresh:
        cached = load_cached_recommendations(sector_name, limit)
        if cached:
            return cached

    logger.info(f"Recommending stocks for {sector_name}...")

    stocks = get_stocks_in_sector(sector_name)
    if not stocks:
        logger.warning(f"Tidak ada data saham untuk sektor {sector_name}, skip LLM call")
        update_agent_status("stock_recommendations", "ok")
        return {"sector": sector_name, "recommendations": [],
                "message": f"Tidak ada data saham untuk sektor {sector_name}.", "generated_at": now_iso()}

    news_data = fetch_news_batch(stocks)
    content = None
    used_mistral = False

    # Try Mistral agent (only if use_mistral=True)
    if use_mistral:
        try:
            from mistral_agent_manager import MistralAgentManager
            manager = MistralAgentManager()
            inputs = {
                "sector": sector_name,
                "stocks": [
                    {
                        "ticker": s.get("ticker"),
                        "companyName": s.get("companyName"),
                        "price": s.get("price"),
                        "per": s.get("per"),
                        "pbv": s.get("pbv"),
                        "roe": s.get("roe"),
                        "revenue_growth": s.get("revenue_growth"),
                        "eps_growth": s.get("eps_growth"),
                        "dividend_yield": s.get("dividend_yield"),
                        "debt_to_equity": s.get("debt_to_equity"),
                        "investment_score": (s.get("analysis") or {}).get("investmentScore"),
                        "valuation": s.get("valuation"),
                    }
                    for s in stocks[:10]
                ],
                "news": news_data,
                "sector_prediction": sector_prediction,
            }
            response = manager.run(
                "stock_recommender", inputs=inputs,
                max_function_calls=15, timeout_ms=120000,
            )
            content = response.get("content")
            if content:
                try:
                    parsed = parse_llm_response(content)
                    used_mistral = True
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.error(
                        "Mistral agent returned invalid JSON for %s: %s\n"
                        "len=%d last_200=%s",
                        sector_name, e,
                        len(content), content[-200:]
                    )
                    content = None  # force fallback
        except Exception as e:
            logger.warning(f"Mistral agent gagal ({e}), fallback ke LLM client...")

    # Mistral agent gagal, gunakan hasil kosong
    if not content:
        logger.warning("Mistral agent gagal untuk %s, fallback ke hasil kosong", sector_name)
        update_agent_status("stock_recommendations", "error", "Mistral agent failed")
        return {
            "sector": sector_name,
            "recommendations": [],
            "generated_at": now_iso(),
            "model": LLM_MODEL,
            "limit": limit,
            "method": "enhanced_fundamental_macro",
        }

    log_llm_call(
        agent_type="stock_recommendation",
        prompt=content[:500] + "...",
        response=content,
        model="mistral-agent-stock" if used_mistral else LLM_MODEL,
        metadata={
            "sector": sector_name,
            "n_stocks": len(stocks),
            "n_news": len(news_data),
            "has_sector_prediction": sector_prediction is not None,
        },
    )

    if isinstance(parsed, list):
        recommendations = parsed[:limit]
    elif isinstance(parsed, dict):
        recommendations = (parsed.get("recommendations", []) or [])[:limit]
    else:
        logger.warning("LLM returned non-dict for %s (type=%s), returning empty", sector_name, type(parsed).__name__)
        update_agent_status("stock_recommendations", "error", f"LLM returned {type(parsed).__name__}")
        return {
            "sector": sector_name,
            "recommendations": [],
            "generated_at": now_iso(),
            "model": LLM_MODEL,
            "limit": limit,
            "method": "enhanced_fundamental_macro",
        }

    result = {
        "sector": sector_name,
        "recommendations": recommendations,
        "generated_at": now_iso(),
        "model": LLM_MODEL,
        "limit": limit,
        "method": "enhanced_fundamental_macro",
    }
    save_cache(sector_name, result)
    update_agent_status("stock_recommendations", "ok")
    return result


def recommend_stocks_batch(sectors: List[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Generate stock recommendations for ALL sectors in one batch LLM call.

    Primary: Cerebras (gpt-oss-120b) via chat completions.
    Fallback 1: Mistral batch agent (tanpa function calling).
    Fallback 2: Per-sector via recommend_stocks().
    """
    if sectors is None:
        from sector_constants import IDX_SECTORS
        sectors = IDX_SECTORS

    logger.info("Batch recommending stocks for %d sectors...", len(sectors))

    # Collect data for all sectors
    all_sectors_data = {}
    for sector in sectors:
        stocks = get_stocks_in_sector(sector)
        if not stocks:
            continue
        news_data = fetch_news_batch(stocks)
        stocks_simple = [
            {
                "ticker": s.get("ticker"),
                "companyName": s.get("companyName"),
                "price": s.get("price"),
                "per": s.get("per"),
                "pbv": s.get("pbv"),
                "roe": s.get("roe"),
                "revenue_growth": s.get("revenue_growth"),
                "eps_growth": s.get("eps_growth"),
                "dividend_yield": s.get("dividend_yield"),
                "debt_to_equity": s.get("debt_to_equity"),
                "investment_score": (s.get("analysis") or {}).get("investmentScore"),
                "valuation": s.get("valuation"),
            }
            for s in stocks[:10]
        ]
        all_sectors_data[sector] = {
            "stocks": stocks_simple,
            "news": news_data,
        }

    if not all_sectors_data:
        logger.warning("No stock data found for any sector")
        return {"success": False, "error": "No stock data", "stored": 0}

    content = None
    used_cerebras = False
    used_mistral = False

    # --- Try Cerebras (primary) ---
    try:
        from cerebras_client import is_available, generate_batch
        if is_available():
            system_prompt = _CEREBRAS_BATCH_SYSTEM_PROMPT
            user_text = json.dumps({
                "all_sectors": all_sectors_data,
                "max_recommendations_per_sector": limit,
            }, ensure_ascii=False)
            result = generate_batch(system_prompt, user_text)
            if result is not None:
                content = result
                content_len = len(content)
                logger.info("Cerebras batch success: content_len=%s, preview=%s",
                            content_len, content[:200])
                try:
                    parsed = parse_llm_response(content)
                    used_cerebras = True
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.error("Cerebras batch returned invalid JSON: %s (len=%d, last_200=%s)",
                                 e, content_len, content[-200:])
                    content = None
            else:
                logger.warning("Cerebras returned None (rate limited), falling back to Mistral...")
        else:
            logger.info("Cerebras not configured (CEREBRAS_API_KEY missing), using Mistral...")
    except Exception as e:
        logger.warning("Cerebras batch failed: %s, falling back to Mistral...", e, exc_info=True)

    # --- Try Mistral batch agent (fallback 1) ---
    if not content:
        try:
            from mistral_agent_manager import MistralAgentManager
            manager = MistralAgentManager()
            if "batch_stock" in manager.available_agents:
                inputs = {
                    "all_sectors": all_sectors_data,
                    "max_recommendations_per_sector": limit,
                }
                response = manager.run(
                    "batch_stock", inputs=inputs,
                    max_function_calls=5, timeout_ms=240000,
                )
                content = response.get("content")
                content_len = len(content) if content else 0
                logger.info("Batch Mistral response: content_len=%s, preview=%s",
                            content_len, (content[:200] if content else "None"))
                if content:
                    try:
                        parsed = parse_llm_response(content)
                        used_mistral = True
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        logger.error("Batch Mistral returned invalid JSON: %s (len=%d, preview=%s)",
                                     e, content_len, content[-200:])
                        content = None
        except Exception as e:
            logger.warning("Batch Mistral agent gagal: %s", e, exc_info=True)

    stored = 0
    sector_results: Dict[str, Dict[str, Any]] = {}

    # Parse batch response and save per-sector caches
    if content:
        if not isinstance(parsed, dict):
            logger.warning("Batch LLM returned non-dict (type=%s), falling back", type(parsed).__name__)
            content = None
        else:
            batch_recs = parsed.get("recommendations", {})
            if isinstance(batch_recs, dict):
                model_tag = "cerebras-llama-4-scout" if used_cerebras else "mistral-agent-batch-stock"
                method_tag = "batch_cerebras" if used_cerebras else "batch_mistral"
                for sector, sector_data in batch_recs.items():
                    recs = (sector_data.get("recommendations", []) or [])[:limit]
                    if recs:
                        result = {
                            "sector": sector,
                            "recommendations": recs,
                            "generated_at": now_iso(),
                            "model": model_tag,
                            "limit": limit,
                            "method": method_tag,
                        }
                        save_cache(sector, result)
                        sector_results[sector] = result
                        stored += 1
                logger.info("Batch %s: %d/%d sectors stored", method_tag, stored, len(sectors))
                update_agent_status("stock_recommendations", "ok" if stored else "error")
                return {"success": stored > 0, "stored": stored, "method": method_tag, "sector_results": sector_results}

    # All batch LLMs failed, fallback per-sector via Mistral
    logger.info("All batch LLMs failed/empty, fallback per-sector via Mistral...")
    for i, sector in enumerate(sectors):
        if i > 0:
            sync_rate_delay(2.0)
        try:
            result = recommend_stocks(sector_name=sector, limit=limit, refresh=True, use_mistral=True)
            if result.get("recommendations"):
                sector_results[sector] = result
                stored += 1
        except Exception as e:
            logger.error("Fallback Mistral gagal untuk %s: %s", sector, e)

    update_agent_status("stock_recommendations", "ok" if stored else "error")
    return {"success": stored > 0, "stored": stored, "method": "per_sector_mistral_fallback", "sector_results": sector_results}
