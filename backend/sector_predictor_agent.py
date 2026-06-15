import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

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
SECTOR_CACHE_FILE = CACHE_DIR / "sector_predictions.json"
CACHE_TTL_SECONDS = 3600
TV_CACHE_FILE = ROOT_DIR / "tradingview_cache.json"
TV_CACHE_USABLE_SECONDS = 3600

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

LLM_MODEL = os.environ.get("LLM_MODEL", "mistral-small-latest")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_idn_market_open() -> bool:
    now = datetime.now(timezone(timedelta(hours=7)))
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour < 15


def load_cached_predictions() -> Optional[Dict[str, Any]]:
    if not SECTOR_CACHE_FILE.exists():
        return None
    try:
        with open(SECTOR_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached.get('cached_at', ''))
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if is_idn_market_open():
            if age < CACHE_TTL_SECONDS:
                return cached
        else:
            return cached
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def save_cache(data: Dict[str, Any]) -> None:
    cache = {'cached_at': now_iso(), **data}
    with open(SECTOR_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_llm_client() -> Mistral:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY tidak ditemukan di environment variables")
    return Mistral(api_key=api_key, server_url=os.environ.get("LLM_BASE_URL", "https://api.mistral.ai"))


def load_tv_data_from_cache() -> Optional[List[Dict[str, Any]]]:
    if not TV_CACHE_FILE.exists():
        return None
    try:
        with open(TV_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        records = cached.get('data', [])
        if not records:
            return None
        return records
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def compute_sector_averages(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    sector_data: Dict[str, Dict[str, Any]] = {}
    for r in records:
        sec = r.get("sector", "Lainnya")
        if sec not in sector_data:
            sector_data[sec] = {
                "count": 0, "avg_per": [], "avg_pbv": [], "avg_roe": [],
                "avg_revenue_growth": [], "avg_eps_growth": [], "avg_dividend_yield": [],
                "avg_debt_to_equity": [], "avg_score": [],
            }
        sd = sector_data[sec]
        sd["count"] += 1
        for k, v in [("avg_per", r.get("per")), ("avg_pbv", r.get("pbv")), ("avg_roe", r.get("roe")),
                     ("avg_revenue_growth", r.get("revenue_growth")), ("avg_eps_growth", r.get("eps_growth")),
                     ("avg_dividend_yield", r.get("dividend_yield")), ("avg_debt_to_equity", r.get("debt_to_equity"))]:
            if v is not None:
                sd[k].append(v)
        score_val = (r.get("analysis") or {}).get("investmentScore")
        if score_val is not None:
            sd["avg_score"].append(score_val)
    result = {}
    for sec, sd in sector_data.items():
        result[sec] = {
            key: round(sum(vals) / len(vals), 1) if vals else None
            for key, vals in [
                ("count", [sd["count"]]), ("avg_per", sd["avg_per"]), ("avg_pbv", sd["avg_pbv"]),
                ("avg_roe", sd["avg_roe"]), ("avg_revenue_growth", sd["avg_revenue_growth"]),
                ("avg_eps_growth", sd["avg_eps_growth"]), ("avg_dividend_yield", sd["avg_dividend_yield"]),
                ("avg_debt_to_equity", sd["avg_debt_to_equity"]), ("avg_score", sd["avg_score"]),
            ]
        }
        result[sec]["count"] = sd["count"]
    return result


def fetch_sector_data() -> Dict[str, Any]:
    records = load_tv_data_from_cache()
    if records:
        logger.info("TV data loaded from cache")
        return compute_sector_averages(records)
    logger.info("TV cache miss, fetching fresh...")
    try:
        backend_dir = Path(__file__).parent
        import sys
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from tradingview_agent import fetch_and_analyze_tradingview_screen
        records, _, _ = fetch_and_analyze_tradingview_screen(limit=500)
        if records:
            return compute_sector_averages(records)
    except Exception as e:
        logger.warning(f"TV fetch failed: {e}")
    return {}


IDX_SECTORS = sorted(set(v for v in TV_TO_IDX_SECTOR.values()))
IDX_SECTORS_STR = ", ".join(IDX_SECTORS)


def build_prompt(tv_data: Dict[str, Any]) -> str:
    mapped_data = {}
    for eng_name, metrics in tv_data.items():
        idx_name = TV_TO_IDX_SECTOR.get(eng_name, eng_name)
        if idx_name in mapped_data:
            existing = mapped_data[idx_name]
            for k in ["count", "avg_score"]:
                existing[k] = (existing.get(k, 0) or 0) + (metrics.get(k, 0) or 0)
            continue
        mapped_data[idx_name] = dict(metrics)
    tv_json = json.dumps(mapped_data, ensure_ascii=False, indent=2)

    # Macro context
    try:
        from macro_agent import get_macro_summary
        macro_summary = get_macro_summary()
    except Exception:
        macro_summary = "Data makro tidak tersedia."

    # News context — impacted sectors
    news_context = ""
    try:
        from news_flow_agent import get_news_analysis
        news_data = get_news_analysis()
        analysis = news_data.get("analysis", {})
        benefited = analysis.get("sektor_diuntungkan", [])
        cautious = analysis.get("sektor_digdaya_waspada", [])
        if benefited or cautious:
            parts = []
            if benefited:
                parts.append("SEKTOR DIUNTUNGKAN BERITA:")
                for s in benefited:
                    parts.append(f"- {s.get('sektor')}: {s.get('alasan')} (sentimen: {s.get('sentimen')})")
            if cautious:
                parts.append("SEKTOR DIWASPADAI BERITA:")
                for s in cautious:
                    parts.append(f"- {s.get('sektor')}: {s.get('alasan')}")
            news_context = "\n".join(parts)
    except Exception:
        news_context = ""

    return f"""Anda analis AI pasar saham Indonesia senior. Anda HARUS memberi prediksi BERBEDA untuk setiap timeframe — jangan sampai sektor yang sama memuncaki semua timeframe.

ATURAN UTAMA:
1. 1M dan 3M harus DIDOMINASI sektor siklikal/responsif berita jangka pendek (momentum, katalis short-term, sentimen pasar)
2. 6M harus campuran sektor siklikal dan defensif
3. 12M harus DIDOMINASI sektor defensif/fundamental kuat (kualitas, pertumbuhan sustain, tahan siklus)
4. LARANG: sektor yang sama menjadi #1 di lebih dari 2 timeframe
5. Berita dengan impact jangka pendek dominan untuk 1M, impact struktural dominan untuk 6M-12M

DATA FUNDAMENTAL SEKTOR (rata-rata):
{tv_json}

KONDISI MAKROEKONOMI:
{macro_summary}

{news_context}

TUGAS: Prediksi 10 sektor IDX terbaik per timeframe — dengan URUTAN BERBEDA setiap timeframe.

PANDUAN TIMEFRAME:
- 1 BULAN: fokus pada MOMENTUM — sektor dengan katalis jangka pendek (sentimen berita, musiman, technical rebound). Sektor siklikal dan komoditas sering unggul.
- 3 BULAN: fokus pada KATALIS KUARTAL — sektor yang diuntungkan kebijakan makro kuartalan, rilis laporan keuangan, tren musiman.
- 6 BULAN: campuran — kualitas fundamental mulai lebih penting, hindari sektor dengan siklus pendek.
- 12 BULAN: fokus pada FUNDAMENTAL & TAHAN BANTING — sektor defensif dengan PER wajar, ROE konsisten, dividen stabil. Prospek jangka panjang.

Per sektor sertakan:
- predicted_return: float realistis (negatif diperbolehkan)
- confidence: "high"/"medium"/"low"
- rationale: jelaskan dengan ANKA — sebut PER, ROE, valuasi, dampak berita, dan pengaruh makro
- key_drivers: array 2-3 faktor kunci
- macro_context: dampak makroekonomi pada sektor
- news_driven: true/false — apakah berita jadi pendorong utama
- impact_horizon: "short_term"/"medium_term"/"long_term" — horizon dampak

RESPON JSON:
{{"predictions":{{"1M":[{{"sector":"Energi","predicted_return":8.5,"confidence":"high","rationale":"Harga batubara naik 5% didorong permintaan China dan pelemahan rupiah menguntungkan eksportir. Rata-rata PER sektor 8x menarik.","key_drivers":["Harga batubara naik","Rupiah melemah","Permintaan China pulih"],"macro_context":"Kenaikan harga komoditas dan pelemahan rupiah mendorong sektor energi","news_driven":true,"impact_horizon":"short_term"}}],"3M":[],"6M":[{{"sector":"Perbankan","predicted_return":7.2,"confidence":"high","rationale":"BI rate turun 25bp mendorong ekspansi kredit. ROE rata-rata 18% dengan PER 12x masih menarik. Pertumbuhan kredit diproyeksi 10-12% dalam 6 bulan.","key_drivers":["Penurunan BI rate","Kredit tumbuh","PER menarik"],"macro_context":"Relaksasi moneter mendukung margin bunga","news_driven":false,"impact_horizon":"medium_term"}}],"12M":[]}}}}
JANGAN tulis apapun di luar JSON."""


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
    except json.JSONDecodeError as e:
        import re
        json_str = re.sub(r',\s*\}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e2:
            logger.error(f"Raw content snippet: {content[:2000]}")
            logger.error(f"After cleanup: {json_str[:2000]}")
            raise e2


def predict_sectors(refresh: bool = False) -> Dict[str, Any]:
    if not refresh:
        cached = load_cached_predictions()
        if cached:
            return cached

    logger.info("Generating sector predictions via Mistral (enhanced)...")
    tv_data = fetch_sector_data()
    prompt = build_prompt(tv_data)

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
    predictions = parsed.get("predictions", {})

    # Warn if predictions look identical across timeframes
    pred_keys = list(predictions.keys())
    for i in range(len(pred_keys)):
        for j in range(i + 1, len(pred_keys)):
            secs_i = [p.get("sector") for p in predictions.get(pred_keys[i], [])[:3]]
            secs_j = [p.get("sector") for p in predictions.get(pred_keys[j], [])[:3]]
            if secs_i == secs_j:
                logger.warning(
                    f"Top 3 sektor sama antara {pred_keys[i]} dan {pred_keys[j]}: {secs_i}"
                )

    result = {
        "predictions": predictions,
        "generated_at": now_iso(),
        "model": LLM_MODEL,
        "method": "enhanced_fundamental_macro",
    }
    save_cache(result)
    return result


def get_predictions_by_timeframe(timeframe: str = None, refresh: bool = False) -> Dict[str, Any]:
    valid = ["1M", "3M", "6M", "12M"]
    result = predict_sectors(refresh=refresh)
    predictions = result.get("predictions", {})
    if timeframe and timeframe in valid:
        result["predictions"] = {timeframe: predictions.get(timeframe, [])}
    return result
