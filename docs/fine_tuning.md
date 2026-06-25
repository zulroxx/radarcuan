# Fine-Tuning Pipeline — IHSG AI Agents

## Overview

Fine-tuning memungkinkan anda menyesuaikan model Mistral AI dengan data spesifik pasar saham Indonesia, sehingga prediksi sektor dan rekomendasi saham menjadi lebih akurat.

### Agents yang Didukung

| Agent | Tipe | File |
|-------|------|------|
| Sector Prediction | `sector_prediction` | `backend/sector_predictor_agent.py` |
| Stock Recommendation | `stock_recommendation` | `backend/stock_recommender_agent.py` |
| News Analysis | `news_analysis` | `backend/news_flow_agent.py` |

---

## Arsitektur

```
backend/fine_tuning/
├── __init__.py
├── config.py                  # Konfigurasi path & env vars
├── dataset_logger.py          # Thread-safe JSONL logger
├── prepare_dataset.py         # Filter rating positif → format Mistral
├── train.py                   # Upload + trigger Mistral fine-tuning API
└── evaluate.py                # Bandingkan base vs fine-tuned model
└── dataset/
    ├── raw/                   # Raw LLM logs (append harian)
    ├── prepared/              # Training-ready datasets
    └── seed/                  # Seed/example data (optional)

backend/agent_cache/
└── ratings.json              # Rating dari user (file fallback)
```

Alur data:

```
LLM Call → dataset_logger.py → raw/train_YYYY-MM-DD.jsonl
                                        ↓
                                  prepare_dataset.py  ← agent_cache/ratings.json
                                        ↓
                                  prepared/ft_dataset_*.jsonl
                                        ↓
                                  train.py → Mistral Fine-tuning API
                                        ↓
                                  FINETUNED_MODEL_ID → agents
```

---

## Tahap 1: Data Collection

Setiap kali agent memanggil LLM, dataset_logger mencatat prompt + response ke file JSONL.

### Format Log

```jsonl
{
  "prompt": "...",
  "response": "...",
  "agent_type": "sector_prediction",
  "model": "mistral-medium-latest",
  "timestamp": "2026-06-17T00:00:00+00:00",
  "metadata": {
    "n_sectors": 12,
    "has_macro": true,
    "has_news": true
  }
}
```

### Konfigurasi

| Env Variable | Default | Deskripsi |
|-------------|---------|-----------|
| `FINETUNE_LOG_ENABLED` | `true` | Aktifkan/nonaktifkan logging |
| `FINETUNE_LOG_BATCH_SIZE` | `10` | Flush buffer setiap N entry |

---

## Tahap 2: Feedback Collection

User dapat memberikan rating 👍/👎 pada output agent melalui frontend.

### Rating UI di Frontend

| Halaman | Lokasi Rating |
|---------|---------------|
| `PredictionDashboard.jsx` | Setiap kartu prediksi sektor + setiap kartu rekomendasi saham |
| `NewsAnalysis.jsx` | Kartu ringkasan berita (ringkasan_1hari, ringkasan_terbaru) + rekomendasi umum |

Komponen: `frontend/src/components/ui/RatingButtons.jsx`

### Endpoint API Rating

| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| POST | `/api/feedback/rating` | Public | Submit rating (1 = 👍, -1 = 👎) |
| GET | `/api/feedback/ratings` | Public | List semua ratings + agregat |
| GET | `/api/feedback/ratings/stats` | Public | Statistik per agent type |

### Format Rating

```json
{
  "id": "uuid",
  "agent_type": "sector_prediction",
  "target_id": "Energi",
  "rating": 1,
  "sector": "Energi",
  "ticker": null,
  "created_at": "2026-06-17T00:00:00+00:00"
}
```

Rating disimpan ke `agent_cache/ratings.json` (fallback) atau MongoDB collection `agent_ratings`.

---

## Tahap 3: Training Pipeline

### 3a. Prepare Dataset

Filter data berdasarkan rating positif, konversi ke format Mistral, split train/validation.

```bash
cd backend
python -m fine_tuning.prepare_dataset
```

Output:

```json
{
  "success": true,
  "dataset_name": "ft_dataset_20260617_120000",
  "total_raw": 150,
  "total_filtered": 120,
  "total_formatted": 120,
  "train_count": 96,
  "val_count": 24
}
```

**Fallback:** Jika belum ada rating positif, semua raw log akan digunakan.

### 3b. Train (Mistral Fine-tuning API)

Upload file ke Mistral dan trigger fine-tuning job.

```bash
# Dry run — test konfigurasi tanpa kirim API
python -m fine_tuning.train --dry-run

# Real training (butuh LLM_API_KEY)
python -m fine_tuning.train
```

**Parameter training:**

| Env Variable | Default | Deskripsi |
|-------------|---------|-----------|
| `FINETUNE_BASE_MODEL` | `mistral-medium-latest` | Base model |
| `FINETUNE_STEPS` | `100` | Jumlah training steps |
| `FINETUNE_LEARNING_RATE` | `0.0001` | Learning rate |

Output sukses:

```json
{
  "id": "ft-abc123",
  "status": "SUCCESS",
  "model": "ft:mistral-medium-latest:ihsg:20260617"
}
```

### 3c. Evaluasi

Bandingkan base model vs fine-tuned model pada validation set:

```bash
python -m fine_tuning.evaluate
```

Output:

```json
{
  "base_model": { "json_validity_rate": 85.0, "sector_name_accuracy": 92.3, ... },
  "finetuned_model": { "json_validity_rate": 95.0, "sector_name_accuracy": 98.7, ... },
  "improvement": { "json_validity_rate": 10.0, "sector_name_accuracy": 6.4, ... }
}
```

Metrik yang diukur:
- **JSON Validity Rate** — persentase response yang valid JSON
- **Sector Name Accuracy** — persentase nama sektor yang sesuai daftar IDX
- **Recommendation Valid Rate** — persentase rekomendasi yang valid (Strong Buy/Buy/Hold/Sell/Strong Sell)
- **Avg Tokens Per Call** — efisiensi token (semakin rendah semakin hemat)

---

## Tahap 4: Deployment

### 4a. Endpoint Monitoring

Endpoint publik untuk mengecek status fine-tuning:

| Method | Endpoint | Auth | Deskripsi |
|--------|----------|------|-----------|
| GET | `/api/fine-tune/stats` | Public | Dataset stats + model info |
| GET | `/api/admin/fine-tune/status` | Admin | Detail status (raw logs, prepared datasets, ratings) |
| POST | `/api/admin/fine-tune/train` | Admin | Trigger training (`?dry_run=true` untuk test) |

Contoh response `/api/fine-tune/stats`:

```json
{
  "stats": {
    "raw_log_files": 3,
    "raw_log_entries": 250,
    "prepared_datasets": [{ "name": "ft_dataset_20260617_120000", "entries": 96 }],
    "ratings_total": 45,
    "ratings_upvotes": 38
  },
  "model": {
    "base_model": "mistral-medium-latest",
    "fine_tuned_model": "ft:mistral-medium-latest:ihsg:20260617",
    "fine_tune_enabled": true,
    "traffic_percent": 50
  }
}
```

### 4b. Frontend Model Indicator

**PredictionDashboard.jsx** — badge "Fine-tuned" / "Base" muncul di kartu Model AI pada StatCards, menampilkan nama model aktif dan persentase traffic.

**NewsAnalysis.jsx** — nama model aktif ditampilkan di footer, dengan label "(FT)" jika menggunakan fine-tuned model.

### 4c. Aktifkan Fine-tuned Model

Set di `.env`:

```env
FINETUNE_ENABLED=true
FINETUNED_MODEL_ID=ft:mistral-medium-latest:ihsg:20260617
FINETUNE_TRAFFIC_PERCENT=100
```

### 4d. A/B Testing

Gunakan `FINETUNE_TRAFFIC_PERCENT` untuk gradual rollout:

| Nilai | Perilaku |
|-------|----------|
| `0` | 100% base model |
| `25` | 25% fine-tuned, 75% base |
| `50` | 50% masing-masing |
| `75` | 75% fine-tuned, 25% base |
| `100` | 100% fine-tuned model |

### 4e. Model Selection Logic

```python
def _get_active_model() -> str:
    if FINETUNE_ENABLED and FINETUNED_MODEL_ID:
        if FINETUNE_TRAFFIC_PERCENT >= 100:
            return FINETUNED_MODEL_ID
        if FINETUNE_TRAFFIC_PERCENT > 0 and random <= TRAFFIC_PERCENT:
            return FINETUNED_MODEL_ID
    return LLM_MODEL
```

### 4f. Trigger Training via API

```bash
# Dry run — test tanpa biaya
curl -X POST "http://localhost:8000/api/admin/fine-tune/train?token=ihsg-admin-token&dry_run=true"

# Real training
curl -X POST "http://localhost:8000/api/admin/fine-tune/train?token=ihsg-admin-token"
```

---

## Environment Variables (Lengkap)

```env
# LLM
LLM_API_KEY=
LLM_BASE_URL=https://api.mistral.ai
LLM_MODEL=mistral-medium-latest

# Fine-tuning
FINETUNE_LOG_ENABLED=true
FINETUNE_LOG_BATCH_SIZE=10
FINETUNE_ENABLED=false
FINETUNED_MODEL_ID=
FINETUNE_BASE_MODEL=mistral-medium-latest
FINETUNE_STEPS=100
FINETUNE_LEARNING_RATE=0.0001
FINETUNE_TRAFFIC_PERCENT=0
```

---

## File yang Dimodifikasi

### Backend
| File | Perubahan |
|------|-----------|
| `fine_tuning/config.py` | Konfigurasi path + env vars |
| `fine_tuning/dataset_logger.py` | Thread-safe buffered JSONL logger |
| `fine_tuning/prepare_dataset.py` | Filter rating → format Mistral → split |
| `fine_tuning/train.py` | Upload + trigger Mistral fine-tuning |
| `fine_tuning/evaluate.py` | Evaluasi perbandingan model |
| `server.py` | Rating endpoints + fine-tune management endpoints |
| `sector_predictor_agent.py` | Logging + `_get_active_model()` A/B |
| `stock_recommender_agent.py` | Logging + `_get_active_model()` A/B |
| `news_flow_agent.py` | Logging + `_get_active_model()` A/B |
| `.env.example` | 8 env vars fine-tuning |

### Frontend
| File | Perubahan |
|------|-----------|
| `ui/RatingButtons.jsx` | Komponen thumbs up/down reusable |
| `AgentDashboard/PredictionDashboard.jsx` | Rating per sektor/saham + model indicator badge |
| `AgentDashboard/NewsAnalysis.jsx` | Rating per ringkasan + model indicator footer |

---

## Quick Start

```bash
# 1. Jalankan server, kumpulkan interaksi user + rating
cd backend && python -m uvicorn server:app --reload

# 2. Cek status dataset
curl http://localhost:8000/api/fine-tune/stats

# 3. Prepare dataset
python -m fine_tuning.prepare_dataset

# 4. Training (dry-run dulu)
python -m fine_tuning.train --dry-run
# Real:
python -m fine_tuning.train

# 5. Set model di .env setelah training selesai
FINETUNE_ENABLED=true
FINETUNED_MODEL_ID=ft:mistral-medium-latest:ihsg:20260617
FINETUNE_TRAFFIC_PERCENT=50

# 6. Evaluasi perbandingan
python -m fine_tuning.evaluate
```

---

## Referensi

- [Mistral Fine-tuning API Docs](https://docs.mistral.ai/capabilities/finetuning/)
- [Mistral API Reference](https://docs.mistral.ai/api/)
