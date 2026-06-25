# Plan: Migrasi `ihsg-news-analyst` dari Mistral ke Google Gemini

## Ringkasan
Ganti LLM untuk analisis berita dari Mistral Agent (`ihsg-news-analyst`) ke Google Gemini API menggunakan SDK `google-genai` (v2.x, yang terbaru). Model: `gemini-2.0-flash-lite` (atau bisa dikonfigurasi via env var).

---

## 1. `backend/requirements.txt` — Tambah dependency

```
google-genai>=2.0.0
```

---

## 2. File Baru: `backend/gemini_client.py`

Module wrapper untuk Google Gen AI SDK. Fungsi utama:

```python
import os
import logging
from typing import Optional

# Google Gen AI SDK baru (bukan google-generativeai yang deprecated)
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

_client: Optional[genai.Client] = None

def get_gemini_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

def analyze_news_with_gemini(news_items: list, system_prompt: str) -> Optional[str]:
    """
    Kirim news_items ke Gemini dan return raw JSON string response.
    Handle rate limit / error.
    """
    try:
        client = get_gemini_client()
        # Gabungkan system prompt + news items
        contents = system_prompt + "\n\nBerita:\n" + json.dumps(news_items, ensure_ascii=False, indent=2)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=8192,
            ),
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None

def reset_client():
    """Force re-init client (misal API key berubah)."""
    global _client
    _client = None
```

---

## 3. `backend/news_flow_agent.py` — Modifikasi `analyze_news()`

**Sebelum:**
```python
def analyze_news(news_items):
    # Primary: Mistral Agent
    try:
        from mistral_agent_manager import MistralAgentManager
        manager = MistralAgentManager()
        response = manager.run("news", inputs={"news_items": news_items[:15]})
        content = response.get("content", "")
        if content:
            log_llm_call(...)
            result = parse_json_response(content)
            return result
    except Exception as e:
        logger.warning(f"Mistral agent gagal ({e}), fallback ke LLM client...")
    
    # Mistral gagal -> error_result()
    return error_result()
```

**Sesudah:**
```python
def analyze_news(news_items):
    # Primary: Google Gemini
    gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_api_key:
        try:
            from gemini_client import analyze_news_with_gemini
            
            SYSTEM_PROMPT = """Anda adalah analis pasar saham Indonesia. Analisis berita berikut dan berikan output JSON dengan format:
{
  "ringkasan_1hari": "Ringkasan dampak berita untuk 1 hari ke depan...",
  "ringkasan_terbaru": "Ringkasan berita terbaru yang paling penting...",
  "sektor_diuntungkan": ["Nama Sektor", ...],
  "sektor_digdaya_waspada": ["Nama Sektor", ...],
  "indikator_kunci": [{"indikator": "...", "dampak": "positif/negatif/netral"}],
  "rekomendasi_umum": "Rekomendasi umum untuk investor..."
}
Hanya output JSON, tanpa markdown atau teks lain."""

            content = analyze_news_with_gemini(news_items[:15], SYSTEM_PROMPT)
            if content:
                log_llm_call(
                    agent_type="news_analysis",
                    prompt=json.dumps({"news_items": news_items[:15]}, ensure_ascii=False),
                    response=content,
                    model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite"),
                    metadata={"n_news": len(news_items), "provider": "gemini"},
                )
                result = parse_json_response(content)
                update_agent_status("news", "ok")
                return result
        except Exception as e:
            logger.warning(f"Gemini gagal ({e}), fallback ke Mistral...")

    # Fallback: Mistral Agent (existing code)
    try:
        from mistral_agent_manager import MistralAgentManager
        ...
    except Exception as e:
        logger.warning(f"Semua LLM gagal ({e})")

    return error_result()
```

### Perubahan Spesifik:

a) Tambah env var check `GEMINI_API_KEY` — jika tidak diset, skip Gemini langsung ke Mistral

b) **System prompt**: Langsung di-hardcode di `news_flow_agent.py` (seperti instruction Mistral agent). Ini perlu disesuaikan dengan instruksi yang ada di Mistral Console agent `ihsg-news-analyst`.

c) Update `log_llm_call`: `model` → nilai dari `GEMINI_MODEL`, `metadata` tambah `"provider": "gemini"`

d) Update `LLM_MODEL` fallback: Jika Gemini dipakai, `LLM_MODEL` (untuk response ke frontend) pakai `GEMINI_MODEL`

---

## 4. `.env` — Variable Lingkungan Baru

```
# Google Gemini (untuk news analysis)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite
```

---

## 5. Catatan Rate Limit

| Limit | Nilai | Kebutuhan (4 jam scheduler) | Aman? |
|-------|-------|---------------------------|-------|
| Requests per day | 1.500 | 6 (scheduler) + manual trigger | ✅ Sangat aman |
| Tokens per minute | 1.000.000 | ~10.000 per call | ✅ Sangat aman |

---

## 6. Output yang Sama

Gemini akan menghasilkan JSON dengan format identik dengan Mistral:

```json
{
  "ringkasan_1hari": "...",
  "ringkasan_terbaru": "...",
  "sektor_diuntungkan": [...],
  "sektor_digdaya_waspada": [...],
  "indikator_kunci": [...],
  "rekomendasi_umum": "..."
}
```

Parser `parse_json_response()` yang sudah ada tetap bisa dipakai karena formatnya sama.

---

## 7. Fallback Chain

```
Gemini API (primary)
  ↓ gagal
Mistral Agent (fallback 1 — kode existing)
  ↓ gagal
error_result() (fallback final — kode existing)
```

---

## 8. Verifikasi

1. Install `pip install google-genai`
2. Set `GEMINI_API_KEY` di `.env`
3. Restart backend
4. Cek log: "Gemini API success" / "Gemini gagal, fallback ke Mistral"
5. Panggil `GET /api/news/flow` → pastikan response sukses dengan format JSON yang sama
6. Test: hapus `GEMINI_API_KEY` → pastikan fallback ke Mistral berjalan
