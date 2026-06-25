import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from agent_status import update_agent_status
from fine_tuning.dataset_logger import log_llm_call


logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "agent_cache"
CACHE_DIR.mkdir(exist_ok=True)
NEWS_CACHE_FILE = CACHE_DIR / "news_flow.json"
CACHE_TTL_SECONDS = 14400  # 4 jam (hemat API, semua user share cache)
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen/qwen3-32b")


NEWS_FLOW_URL = "https://id.tradingview.com/news-flow/Sfb1cF3y?market=bond,economic,futures,index,stock"
NEWS_PAGE_URL = "https://www.tradingview.com/news/"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_cached_news() -> Optional[Dict[str, Any]]:
    if not NEWS_CACHE_FILE.exists():
        return None
    try:
        with open(NEWS_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached.get('cached_at', ''))
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return cached
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def save_cache(data: Dict[str, Any]) -> None:
    cache = {'cached_at': now_iso(), **data}
    with open(NEWS_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


_TITLE_CLEAN_RE = re.compile(
    r'^(?:\d+\s*(?:min(?:ute)?s?|hrs?|hours?|days?|d)\s*ago|yesterday|today|'
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})\s*'
    r'(TradingView|Reuters|Dow\s*Jones|CNBC|Bloomberg|MarketWatch)?\s*',
    re.IGNORECASE
)
_PROVIDER_PREFIX_RE = re.compile(
    r'^(TradingView|Reuters|Dow\s*Jones|CNBC|Bloomberg|MarketWatch)\s*',
    re.IGNORECASE
)


def _clean_title(raw: str) -> str:
    cleaned = _TITLE_CLEAN_RE.sub('', raw)
    cleaned = _PROVIDER_PREFIX_RE.sub('', cleaned)
    return cleaned.strip()


def fetch_news_from_tradingview() -> List[Dict[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        resp = requests.get(NEWS_PAGE_URL, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        articles = []
        seen = set()

        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if not text or len(text) < 30:
                continue
            if not re.search(r'(TradingView|Reuters|Dow Jones|CNBC|Bloomberg|MarketWatch)', str(link.parent if link.parent else '')):
                if not any(kw in text.lower() for kw in ['stock', 'market', 'fed', 'price', 'trade', 'ipo', 'bond', 'gold', 'oil', 'dollar', 'equity', 'inflation', 'gdp']):
                    continue
            if text in seen:
                continue
            seen.add(text)

            time_tag = link.find_previous('time')
            published = time_tag.get('datetime') if time_tag else None
            if not published:
                published_match = re.search(r'(\d+)\s*(minute|hour|day|min|hr|d)\s*ago', text.lower())
                if published_match:
                    published = published_match.group(0)

            provider_span = link.find_previous('span')
            provider = provider_span.get_text(strip=True) if provider_span else 'TradingView'
            if not provider or len(provider) > 30:
                provider = 'TradingView'

            articles.append({
                "title": _clean_title(text),
                "url": href if href.startswith('http') else f"https://www.tradingview.com{href}",
                "provider": provider,
                "published": published or now_iso(),
            })
            if len(articles) >= 50:
                break

        if articles:
            return articles

        all_text = soup.get_text()
        lines = [l.strip() for l in all_text.split('\n') if l.strip() and len(l.strip()) > 40]
        for line in lines[:50]:
            if line in seen:
                continue
            seen.add(line)
            articles.append({
                "title": _clean_title(line),
                "url": NEWS_FLOW_URL,
                "provider": "TradingView",
                "published": now_iso(),
            })

        return articles[:50]

    except Exception as e:
        logger.warning(f"Gagal fetch news: {e}")
        return []

from prompt_utils import OUTPUT_RULES_NEWS

SYSTEM_PROMPT = OUTPUT_RULES_NEWS + """

Anda adalah analis pasar saham Indonesia. Tugas Anda menganalisis berita-berita terbaru dan memberikan output dalam JSON.

Analisis harus mencakup:
1. Ringkasan dampak berita untuk perdagangan 1 hari ke depan
2. Ringkasan berita terbaru yang paling penting
3. Sektor-sektor yang diuntungkan oleh berita tersebut (minimal 1, maksimal 5)
4. Sektor-sektor yang perlu waspada (minimal 1, maksimal 5)
5. Indikator kunci yang perlu dipantau (minimal 3, maksimal 7)
6. Rekomendasi umum untuk investor

Output JSON:
{
  "ringkasan_1hari": "string — paragraf singkat dampak berita untuk 1 hari ke depan",
  "ringkasan_terbaru": "string — ringkasan berita terbaru yang paling penting",
  "sektor_diuntungkan": [
    {
      "sektor": "Nama sektor IDX",
      "alasan": "Penjelasan spesifik mengapa sektor ini diuntungkan",
      "sentimen": "positif/sangat positif",
      "subsektor": "Sub-sektor spesifik jika ada"
    }
  ],
  "sektor_digdaya_waspada": [
    {
      "sektor": "Nama sektor",
      "alasan": "Penjelasan mengapa sektor ini perlu diwaspadai"
    }
  ],
  "indikator_kunci": [
    {
      "nama": "Nama indikator (Inflasi/Suku Bunga/Nilai Tukar/Harga Komoditas)",
      "kondisi": "kondisi saat ini",
      "dampak": "dampak ke IHSG"
    }
  ],
  "rekomendasi_umum": "string — rekomendasi umum untuk investor"
}

Jika berita terbatas, tetap berikan analisis berdasarkan kondisi makroekonomi Indonesia terkini.
Hanya output JSON, tanpa markdown, tanpa teks lain di luar JSON."""


def _normalize_analysis(result: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(result)

    out["sektor_diuntungkan"] = [
        (
            {"sektor": s, "alasan": f"{s} diuntungkan oleh sentimen positif dari berita terbaru", "sentimen": "positif", "subsektor": ""}
            if isinstance(s, str)
            else {
                "sektor": s.get("sektor", ""),
                "alasan": s.get("alasan", "").strip() or f"{s.get('sektor', 'Sektor')} diuntungkan oleh berita ekonomi terbaru",
                "sentimen": s.get("sentimen", "positif"),
                "subsektor": s.get("subsektor", ""),
            }
        )
        for s in (result.get("sektor_diuntungkan") or [])
        if (isinstance(s, str) and s) or (not isinstance(s, str) and s.get("sektor"))
    ]

    out["sektor_digdaya_waspada"] = [
        (
            {"sektor": s, "alasan": f"{s} perlu diwaspadai karena faktor ekonomi makro saat ini"}
            if isinstance(s, str)
            else {
                "sektor": s.get("sektor", ""),
                "alasan": s.get("alasan", "").strip() or f"{s.get('sektor', 'Sektor')} perlu diwaspadai karena kondisi pasar",
            }
        )
        for s in (result.get("sektor_digdaya_waspada") or [])
        if (isinstance(s, str) and s) or (not isinstance(s, str) and s.get("sektor"))
    ]

    out["indikator_kunci"] = [
        {
            "nama": ind.get("nama") or ind.get("indikator", ""),
            "kondisi": ind.get("kondisi", "").strip() or ind.get("dampak", ""),
            "dampak": ind.get("dampak", "").strip() or "Berpengaruh ke IHSG",
        }
        for ind in (result.get("indikator_kunci") or [])
        if isinstance(ind, dict) and (ind.get("nama") or ind.get("indikator"))
    ]

    return out


def analyze_news(news_items: List[Dict[str, str]]) -> Dict[str, Any]:
    if not news_items:
        result = error_result()
        result["_model"] = "fallback-default"
        return _ensure_minimum_analysis(result)

    used_model = "unknown"

    # Primary: OpenRouter Cohere
    from llm_client import get_llm_client, llm_chat_complete
    try:
        import os
        primary_model = os.environ.get("LLM_MODEL", "cohere/north-mini-code:free")
        client = get_llm_client()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"news_items": news_items[:15]}, ensure_ascii=False, indent=2)},
        ]
        resp = llm_chat_complete(client, primary_model, messages, temperature=0.2, max_tokens=16000)
        content = resp.choices[0].message.content
        if content:
            log_llm_call(
                agent_type="news_analysis",
                prompt=json.dumps({"news_items": news_items[:15]}, ensure_ascii=False),
                response=content,
                model=primary_model,
                metadata={"n_news": len(news_items), "provider": "openrouter_cohere"},
            )
            result = parse_json_response(content)
            # Validate against news analyst schema
            from response_validator import validate_response
            if not validate_response("ihsg-news-analyst", result):
                logger.warning("OpenRouter payload failed schema validation – falling back to Mistral")
                raise ValueError("validation failed")
            used_model = primary_model
            update_agent_status("news_flow", "ok")
            try:
                result = _ensure_minimum_analysis(_normalize_analysis(result))
                result["_model"] = used_model
                return result
            except Exception as e:
                logger.warning(f"Normalize primary LLM gagal ({e})")
                result = error_result()
                result["_model"] = used_model
                return _ensure_minimum_analysis(result)
    except Exception as e:
        logger.warning(f"OpenRouter/Cohere gagal ({e}), fallback ke Mistral...")

    # Fallback: Mistral Agent
    try:
        from mistral_agent_manager import MistralAgentManager
        manager = MistralAgentManager()
        response = manager.run(
            "news_flow",
            inputs={"news_items": news_items[:15]},
        )
        content = response.get("content", "")
        if content:
            log_llm_call(
                agent_type="news_analysis",
                prompt=json.dumps({"news_items": news_items[:15]}, ensure_ascii=False),
                response=content,
                model="mistral-agent-news",
                metadata={"n_news": len(news_items), "provider": "mistral"},
            )
            result = parse_json_response(content)
            used_model = "mistral-agent-news"
            update_agent_status("news_flow", "ok")
            try:
                result = _ensure_minimum_analysis(_normalize_analysis(result))
                result["_model"] = used_model
                return result
            except Exception as e:
                logger.warning(f"Normalize Mistral gagal ({e})")
    except Exception as e:
        logger.warning(f"Mistral agent gagal ({e})")

    logger.warning("Semua LLM gagal, gunakan hasil default")
    update_agent_status("news_flow", "error", "Semua LLM gagal")
    result = error_result()
    result["_model"] = used_model
    return _ensure_minimum_analysis(result)


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

    # Manual brace matching as fallback
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
    """Repair truncated JSON strings.
    Handles unbalanced braces/brackets and trailing commas.
    Returns a JSON-compatible string that can be parsed safely.
    """
    # Close any open triple-quoted string
    def _close_triple_quotes(s: str) -> str:
        triple_dq = '"' * 3
        triple_sq = "'" * 3
        if s.count(triple_dq) % 2 != 0:
            s += triple_dq
        if s.count(triple_sq) % 2 != 0:
            s += triple_sq
        return s

    json_str = _close_triple_quotes(json_str)
    # Ensure normal double-quote strings are closed
    if json_str.count('"') % 2 != 0:
        json_str += '"'
    # Balance braces and brackets
    ob = json_str.count('{') - json_str.count('}')
    ab = json_str.count('[') - json_str.count(']')
    if ob > 0:
        json_str += '}' * ob
    if ab > 0:
        json_str += ']' * ab
    # Remove stray commas before a closing } or ]
    import re
    json_str = re.sub(r',\s*(?=[}\]])', '', json_str)
    return json_str


def parse_json_response(content: str) -> Dict[str, Any]:
    json_str = _extract_first_json(content)
    for attempt in range(4):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            if attempt == 0:
                try:
                    return _json_decoder.decode(json_str)
                except json.JSONDecodeError:
                    import re
                    json_str = re.sub(r',\s*\}', '}', json_str)
                    json_str = re.sub(r',\s*\]', ']', json_str)
            elif attempt in (1, 2):
                json_str = _repair_json(json_str)
            else:
                raise


def _macro_fallback_indicators() -> List[Dict[str, str]]:
    try:
        from macro_agent import BASE_MACRO_DATA
        items = []
        for m in BASE_MACRO_DATA:
            label = m.get("label", m.get("id", ""))
            value = m.get("value") or m.get("defaultValue", "-")
            trend = m.get("trend", "stabil")
            dampak = m.get("impact", "Berpengaruh ke IHSG")
            items.append({
                "nama": f"{label} ({value})",
                "kondisi": trend.capitalize(),
                "dampak": dampak,
            })
        return items[:7]
    except Exception:
        return [
            {"nama": "BI Rate (5.75%)", "kondisi": "Menurun", "dampak": "Suku bunga rendah mendorong sektor perbankan, properti, konsumer"},
            {"nama": "Inflasi (2.48%)", "kondisi": "Terkendali", "dampak": "Inflasi rendah menguntungkan sektor konsumer dan ritel"},
            {"nama": "USD/IDR (16,325)", "kondisi": "Melemah", "dampak": "Rupiah melemah menguntungkan sektor eksportir"},
        ]


def _ensure_minimum_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(analysis)
    had_error = "Gagal" in out.get("ringkasan_1hari", "") or "Tidak ada" in out.get("ringkasan_1hari", "")
    filled_any = False

    if not out.get("sektor_diuntungkan"):
        out["sektor_diuntungkan"] = [
            {"sektor": "Energi", "alasan": "Didukung harga komoditas dan permintaan global yang stabil", "sentimen": "positif", "subsektor": ""},
            {"sektor": "Keuangan", "alasan": "Stabilitas moneter dan pertumbuhan kredit yang positif", "sentimen": "positif", "subsektor": ""},
        ]
        filled_any = True
    if not out.get("sektor_digdaya_waspada"):
        out["sektor_digdaya_waspada"] = [
            {"sektor": "Infrastruktur", "alasan": "Tertekan oleh kenaikan biaya bahan baku dan ketidakpastian anggaran"},
            {"sektor": "Konsumer Non-Primer", "alasan": "Daya beli masyarakat masih terbatas di tengah tekanan ekonomi global"},
        ]
        filled_any = True
    if not out.get("indikator_kunci"):
        out["indikator_kunci"] = _macro_fallback_indicators()
        filled_any = True

    if filled_any or had_error:
        ringkasan_1hari = out.get("ringkasan_1hari", "")
        if not ringkasan_1hari or "Gagal" in ringkasan_1hari or "Tidak ada" in ringkasan_1hari:
            out["ringkasan_1hari"] = "Data analysis masih dikumpulkan. Berikut data cadangan berdasarkan kondisi makroekonomi terkini."
        ringkasan_terbaru = out.get("ringkasan_terbaru", "")
        if not ringkasan_terbaru or "Gagal" in ringkasan_terbaru or "Tidak ada" in ringkasan_terbaru:
            out["ringkasan_terbaru"] = "Belum ada berita terbaru yang signifikan. Data di bawah adalah indikator makroekonomi umum."
        rekomendasi = out.get("rekomendasi_umum", "")
        if not rekomendasi or "tidak tersedia" in rekomendasi.lower():
            out["rekomendasi_umum"] = "Tetap diversifikasi portofolio dengan kombinasi sektor defensif dan siklikal sesuai profil risiko."
    return out


def error_result() -> Dict[str, Any]:
    return {
        "ringkasan_1hari": "Gagal menganalisis berita.",
        "ringkasan_terbaru": "Gagal menganalisis berita terbaru.",
        "sektor_diuntungkan": [],
        "sektor_digdaya_waspada": [],
        "indikator_kunci": [],
        "rekomendasi_umum": "Analisis AI tidak tersedia saat ini.",
    }


def get_news_analysis(refresh: bool = False) -> Dict[str, Any]:
    cached = load_cached_news()
    if not refresh and cached:
        return cached

    logger.info("Fetching news from TradingView...")
    news_items = fetch_news_from_tradingview()
    logger.info(f"Got {len(news_items)} news items")

    analysis = analyze_news(news_items)

    is_error = (
        "Gagal" in analysis.get("ringkasan_1hari", "")
        or "Tidak ada" in analysis.get("ringkasan_1hari", "")
    )
    if is_error:
        logger.warning("News analysis failed, preserving existing cache if available")
        if cached:
            return cached
        # Only save error result if no prior cache exists

    used_model = analysis.pop("_model", LLM_MODEL) if isinstance(analysis, dict) else LLM_MODEL
    result = {
        "news": news_items[:30],
        "analysis": analysis,
        "total_news": len(news_items),
        "generated_at": now_iso(),
        "model": used_model,
    }
    if not is_error:
        save_cache(result)
    return result
