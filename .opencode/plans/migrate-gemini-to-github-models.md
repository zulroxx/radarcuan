# Plan: Ganti Google Gemini → GitHub Models (Meta-Llama-3.3-70B)

## Ringkasan
Ganti provider LLM untuk news analysis dari Google Gemini ke GitHub Models.
GitHub Models pakai **OpenAI-compatible API** (`https://models.inference.ai.azure.com`) — `openai` SDK sudah terinstall, **tanpa dependency baru**.

---

## 1. `backend/gemini_client.py` — Replace isi file

**Hapus seluruh isi** dan ganti dengan client GitHub Models. Interface tetap sama (`is_available()`, `generate_content()`) sehingga `news_flow_agent.py` **tidak perlu diubah**.

```python
import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_MODEL = os.environ.get("GITHUB_MODEL", "Meta-Llama-3.3-70B")
GITHUB_BASE_URL = "https://models.inference.ai.azure.com"

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN tidak diset")
        _client = OpenAI(api_key=GITHUB_TOKEN, base_url=GITHUB_BASE_URL)
    return _client


def reset_client():
    global _client
    _client = None


def generate_content(system_prompt: str, user_text: str, max_retries: int = 3) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=GITHUB_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.2,
                max_tokens=8192,
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e)
            is_quota = "429" in err or "rate" in err.lower()
            if is_quota and attempt < max_retries - 1:
                delay = 10.0 * (2 ** attempt)  # 10s, 20s, 40s
                logger.warning(f"github-models rate limited (attempt {attempt+1}/{max_retries}), retry in {delay:.0f}s")
                time.sleep(delay)
            else:
                logger.error(f"github-models API error: {e}")
                return None
    return None


def is_available() -> bool:
    return bool(GITHUB_TOKEN)
```

**Perbedaan penting dari Gemini:**
- Pakai `OpenAI()` SDK (sudah terinstall) — bukan `google-genai`
- Endpoint: `https://models.inference.ai.azure.com`
- Auth: `GITHUB_TOKEN` (GitHub Personal Access Token)
- `chat.completions.create()` — standard OpenAI format
- Rate limit 15 RPM / 150 RPD (jauh di atas kebutuhan scheduler 6x/hari)

---

## 2. `backend/.env` + `backend/.env.example` — Update env vars

**Ganti:**
```env
# Google Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash-lite
```

**Menjadi:**
```env
# GitHub Models — news analysis via Meta-Llama-3.3-70B
# Buat token di https://github.com/settings/tokens (classic, no scopes needed)
GITHUB_TOKEN=
GITHUB_MODEL=Meta-Llama-3.3-70B
```

---

## 3. `backend/requirements.txt` — Hapus dependency

Hapus `google-genai>=2.0.0` (sudah tidak dipakai).
`openai` sudah ada di requirements.

---

## 4. Testing (opsional, bisa pakai curl)

```bash
curl -s -X POST "https://models.inference.ai.azure.com/chat/completions" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Meta-Llama-3.3-70B",
    "messages": [{"role": "user", "content": "Halo, balas dengan Halo juga"}],
    "max_tokens": 100
  }'
```

---

## 5. Catatan

| Aspek | Detail |
|-------|--------|
| **Token** | Buat GitHub Personal Access Token (classic) di `github.com/settings/tokens` — **tidak perlu scope apapun** |
| **Model** | `Meta-Llama-3.3-70B` — alternatif: `gpt-4o-mini`, `Mistral-large`, `Cohere-command-r+`, dll |
| **Rate limit** | 15 RPM / 150 RPD = 6 call scheduler + 144 manual trigger aman |
| **Fallback** | Tetap ke Mistral Agent (seperti sebelumnya) jika GitHub Models error |
| **Keamanan** | Data via Azure infrastructure, tidak dipakai training |

**Tidak ada perubahan di `news_flow_agent.py`** — karena interface `is_available()` dan `generate_content()` tetap sama.
