# Mistral AI Agent Migration Guide

## Arsitektur

```
┌─────────────────────────────────────────────────┐
│                  Server (Python)                  │
│                                                    │
│  mistral_agent_manager.py                          │
│  ┌─────────────────────────────────────────────┐   │
│  │ MistralAgentManager                          │   │
│  │  • run(agent_key, inputs) → content          │   │
│  │  • handle function calls from agent          │   │
│  │  • fallback ke llm_client.py                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                    │
│  Agent Modules (masih ada fallback):                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │ news_flow    │  │ sector_pred. │  │ stock_rec│ │
│  │ → Mistral    │  │ → Mistral    │  │ → Mistral│ │
│  │ → llm_client │  │ → llm_client │  │ → llm_cl │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│                                                    │
│  Data Agents (no LLM):                             │
│  ┌──────────────┐  ┌─────────────────┐             │
│  │ macro_agent  │  │ tradingview_ag.  │             │
│  └──────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────┘
```

## Setup Agent di Mistral Console

Buat 3 agent di [console.mistral.ai](https://console.mistral.ai/chat)

### 1. Agent: `ihsg-news-analyst`

| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-news-analyst` |
| **Model** | `mistral-large-latest` |
| **Instructions** | _"Anda analis AI pasar saham Indonesia. Analisis berita ekonomi global dan dampaknya ke sektor IHSG. Output JSON: ringkasan_1hari, ringkasan_terbaru, sektor_diuntungkan[], sektor_digdaya_waspada[], indikator_kunci[], rekomendasi_umum."_ |
| **Tools** | `web_search_premium` |
| **Response Format** | JSON |

### 2. Agent: `ihsg-sector-predictor`

| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-sector-predictor` |
| **Model** | `mistral-large-latest` |
| **Instructions** | System prompt prediksi sektor (lengkap, lihat `sector_predictor_agent.py:build_prompt()`) |
| **Tools** | `web_search_premium` + Function `get_sector_fundamentals()`, `get_macro_summary()` |
| **Response Format** | JSON Schema |

### 3. Agent: `ihsg-stock-recommender`

| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-stock-recommender` |
| **Model** | `mistral-large-latest` |
| **Instructions** | System prompt rekomendasi saham (lihat `stock_recommender_agent.py:build_prompt()`) |
| **Tools** | Function `get_stocks_in_sector()`, `get_ticker_news()`, `get_macro_context()` |
| **Response Format** | JSON Schema |

## Set Agent ID di .env

```env
MISTRAL_API_KEY=your_api_key_here
MISTRAL_AGENT_NEWS_ID=ag_xxx
MISTRAL_AGENT_SECTOR_ID=ag_xxx
MISTRAL_AGENT_STOCK_ID=ag_xxx
```

## Cara Kerja `MistralAgentManager`

```python
from mistral_agent_manager import MistralAgentManager

manager = MistralAgentManager()

# Kirim tugas ke agent
response = manager.run("news", inputs={"news_items": [...]})
# atau
response = manager.run("sector_predictor", inputs={"sector_data": {...}})
# atau
response = manager.run("stock_recommender", inputs={"sector": "Keuangan", "stocks": [...]})

print(response["content"])      # Final output dari agent
print(response["tool_calls"])   # Daftar function calls yang dieksekusi
```

### Function Calling Flow

1. Agent memutuskan untuk memanggil function (misal `get_macro_summary`)
2. `MistralAgentManager._execute_function()` menjalankan function di Python
3. Hasil dikembalikan ke agent via `conversations.append()` dengan `FunctionResultEntry`
4. Agent melanjutkan reasoning hingga menghasilkan final output

## Fallback Mechanism

Jika Mistral API key tidak dikonfigurasi atau agent gagal:

```python
# news_flow_agent.py
try:
    manager = MistralAgentManager()
    response = manager.run("news", inputs=...)
except Exception:
    # Fallback ke OpenAI-compatible client (llm_client.py)
    client = get_llm_client()
    response = llm_chat_complete(client, ...)
```

## Frontend Playground

Di `/admin` tab **Playground**, pilih mode:

- **Chat Completion** — bebas atur model, capability, tools, response format
- **Agent** — pilih salah satu pre-created agent (News, Sector Predictor, Stock Recommender)

## Contoh API Call

```python
import requests

response = requests.post(
    "http://localhost:8000/api/admin/playground?token=xxx",
    json={
        "agent_key": "news",
        "instructions": "",
        "messages": [{"role": "user", "content": "Analisa kondisi pasar saham Indonesia terkini"}],
        "response_format": None,
    }
)
print(response.json()["content"])
```
