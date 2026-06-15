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
from mistralai.client import Mistral

logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "agent_cache"
CACHE_DIR.mkdir(exist_ok=True)
NEWS_CACHE_FILE = CACHE_DIR / "news_flow.json"
CACHE_TTL_SECONDS = 14400  # 4 jam (hemat API, semua user share cache)

LLM_MODEL = os.environ.get("LLM_MODEL", "mistral-small-latest")

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


def get_llm_client() -> Mistral:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY tidak ditemukan di environment variables")
    return Mistral(api_key=api_key, server_url=os.environ.get("LLM_BASE_URL", "https://api.mistral.ai"))


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
                "title": text,
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
                "title": line,
                "url": NEWS_FLOW_URL,
                "provider": "TradingView",
                "published": now_iso(),
            })

        return articles[:50]

    except Exception as e:
        logger.warning(f"Gagal fetch news: {e}")
        return []


def build_analysis_prompt(news_items: List[Dict[str, str]]) -> str:
    news_json = json.dumps(news_items[:30], ensure_ascii=False, indent=2)
    return f"""Anda analis AI pasar saham Indonesia. Analisis berita ekonomi global terbaru berikut.

BERITA TERBARU:
{news_json}

Buat analisis dalam Bahasa Indonesia dengan format JSON berikut:
{{
  "ringkasan_1hari": "Ringkasan berita 1 hari terakhir dalam 4-5 kalimat, fokus pada dampak pasar",
  "ringkasan_terbaru": "Ringkasan berita paling baru/breaking dalam 3-4 kalimat",
  "sektor_diuntungkan": [
    {{
      "sektor": "Nama sektor IDX (contoh: Perbankan, Teknologi, Energi, Bahan Baku, Konsumer, Infrastruktur, Kesehatan, Properti, Dll)",
      "alasan": "Penjelasan spesifik mengapa sektor ini diuntungkan berdasarkan berita terkini",
      "sentimen": "positif"/"sangat positif",
      "subsektor": "Sub-sektor spesifik jika ada"
    }}
  ],
  "sektor_digdaya_waspada": [
    {{
      "sektor": "Nama sektor",
      "alasan": "Penjelasan mengapa sektor ini perlu diwaspadai"
    }}
  ],
  "indikator_kunci": [
    {{"nama": "Nama indikator (Inflasi/Suku Bunga/Nilai Tukar/Harga Komoditas)", "kondisi": "kondisi saat ini", "dampak": "dampak ke IHSG"}}
  ],
  "rekomendasi_umum": "Rekomendasi umum untuk investor dalam 2-3 kalimat"
}}

Gunakan data berita yang tersedia. Jika berita terbatas, tetap berikan analisis berdasarkan kondisi makroekonomi Indonesia.
JANGAN tulis apapun di luar JSON.""" 


def analyze_news(news_items: List[Dict[str, str]]) -> Dict[str, Any]:
    if not news_items:
        return {
            "ringkasan_1hari": "Tidak ada berita yang berhasil diambil.",
            "ringkasan_terbaru": "Tidak ada berita terbaru.",
            "sektor_diuntungkan": [],
            "sektor_digdaya_waspada": [],
            "indikator_kunci": [],
            "rekomendasi_umum": "Data berita tidak tersedia.",
        }

    prompt = build_analysis_prompt(news_items)

    try:
        client = get_llm_client()
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=8000,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(line for line in lines if not line.startswith("```"))
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            result = json.loads(json_str)
            return result
        return json.loads(content)
    except Exception as e:
        logger.error(f"Gagal analisis AI: {e}")
        return {
            "ringkasan_1hari": "Gagal menganalisis berita.",
            "ringkasan_terbaru": "Gagal menganalisis berita terbaru.",
            "sektor_diuntungkan": [],
            "sektor_digdaya_waspada": [],
            "indikator_kunci": [],
            "rekomendasi_umum": "Analisis AI tidak tersedia saat ini.",
        }


def get_news_analysis(refresh: bool = False) -> Dict[str, Any]:
    if not refresh:
        cached = load_cached_news()
        if cached:
            return cached

    logger.info("Fetching news from TradingView...")
    news_items = fetch_news_from_tradingview()
    logger.info(f"Got {len(news_items)} news items")

    analysis = analyze_news(news_items)

    result = {
        "news": news_items[:30],
        "analysis": analysis,
        "total_news": len(news_items),
        "generated_at": now_iso(),
        "model": LLM_MODEL,
    }
    save_cache(result)
    return result
