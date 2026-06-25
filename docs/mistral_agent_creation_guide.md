# Mistral Agent Creation Guide

Panduan ini berisi parameter lengkap yang harus diisi saat membuat 3 agent di [console.mistral.ai](https://console.mistral.ai/).

---

## Agent 1: `ihsg-news-analyst`

### Basic Info
| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-news-analyst` |
| **Model** | `mistral-large-latest` |

### Capabilities
| Parameter | Value |
|-----------|-------|
| **Built-in tools** | (none) |
| **Reasoning effort** | `none` |

### Settings
| Parameter | Value |
|-----------|-------|
| **Max Tokens** | `32000` |

### Functions
Tidak ada (agent menerima `news_items` sebagai input via conversation, output langsung JSON).

### Instructions
```text
OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key: ringkasan_1hari, ringkasan_terbaru, sektor_diuntungkan, sektor_digdaya_waspada, indikator_kunci, rekomendasi_umum
3. sektor_diuntungkan WAJIB diisi minimal 1 item — jangan pernah kosong
4. sektor_digdaya_waspada WAJIB diisi minimal 1 item — jangan pernah kosong
5. indikator_kunci WAJIB diisi minimal 3 item — jangan pernah kosong
6. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
7. JSON harus lengkap dan valid — jangan terpotong

Anda analis AI pasar saham Indonesia. Analisis berita ekonomi global terbaru berikut.

Buat analisis dalam Bahasa Indonesia dengan format JSON berikut:
{
  "ringkasan_1hari": "Ringkasan berita 1 hari terakhir dalam 4-5 kalimat, fokus pada dampak pasar",
  "ringkasan_terbaru": "Ringkasan berita paling baru/breaking dalam 3-4 kalimat",
  "sektor_diuntungkan": [
    {
      "sektor": "Nama sektor IDX (contoh: Keuangan, Teknologi, Energi, Bahan Baku, Konsumer, Konsumer Non-Primer, Infrastruktur, Kesehatan, Transportasi & Logistik, Telekomunikasi, Industri, Jasa & Perdagangan, Distribusi, Lainnya)",
      "alasan": "Penjelasan spesifik mengapa sektor ini diuntungkan berdasarkan berita terkini",
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
    {"nama": "Nama indikator (Inflasi/Suku Bunga/Nilai Tukar/Harga Komoditas)", "kondisi": "kondisi saat ini", "dampak": "dampak ke IHSG"}
  ],
  "rekomendasi_umum": "Rekomendasi umum untuk investor dalam 2-3 kalimat"
}

Jika berita terbatas, tetap berikan analisis berdasarkan kondisi makroekonomi Indonesia terkini.
JANGAN tulis apapun di luar JSON.
```

### Response Format → JSON Schema
```json
{
  "type": "object",
  "properties": {
    "ringkasan_1hari": {"type": "string"},
    "ringkasan_terbaru": {"type": "string"},
    "sektor_diuntungkan": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sektor": {"type": "string"},
          "alasan": {"type": "string"},
          "sentimen": {"type": "string", "enum": ["positif", "sangat positif"]},
          "subsektor": {"type": "string"}
        },
        "required": ["sektor", "alasan", "sentimen"]
      }
    },
    "sektor_digdaya_waspada": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sektor": {"type": "string"},
          "alasan": {"type": "string"}
        },
        "required": ["sektor", "alasan"]
      }
    },
    "indikator_kunci": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "nama": {"type": "string"},
          "kondisi": {"type": "string"},
          "dampak": {"type": "string"}
        },
        "required": ["nama", "kondisi", "dampak"]
      }
    },
    "rekomendasi_umum": {"type": "string"}
  },
  "required": ["ringkasan_1hari", "ringkasan_terbaru", "sektor_diuntungkan", "sektor_digdaya_waspada", "indikator_kunci", "rekomendasi_umum"]
}
```

---

## Agent 2: `ihsg-sector-predictor`

### Basic Info
| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-sector-predictor` |
| **Model** | `mistral-large-latest` |

### Capabilities
| Parameter | Value |
|-----------|-------|
| **Built-in tools** | (none — data didapat via function calling, bukan search) |
| **Reasoning effort** | `none` |

### Functions

#### Function 1: `get_sector_fundamentals`
- **Name:** `get_sector_fundamentals`
- **Description:** Mengambil data fundamental rata-rata per sektor IDX (PER, PBV, ROE, revenue growth, EPS growth, dividend yield, debt-to-equity)
- **Strict:** `false`
- **Parameters:**
```json
{
  "type": "object",
  "properties": {}
}
```

#### Function 2: `get_macro_summary`
- **Name:** `get_macro_summary`
- **Description:** Mengambil ringkasan kondisi makroekonomi Indonesia terkini (inflasi, suku bunga BI, nilai tukar USD/IDR, harga komoditas)
- **Strict:** `false`
- **Parameters:**
```json
{
  "type": "object",
  "properties": {}
}
```

### Instructions
```text
Anda analis AI pasar saham Indonesia senior. Anda HARUS memberi prediksi BERBEDA untuk setiap timeframe — jangan sampai sektor yang sama memuncaki semua timeframe.

NAMA SEKTOR YANG VALID (hanya gunakan ini):
Keuangan, Teknologi, Energi, Bahan Baku, Konsumer, Konsumer Non-Primer, Infrastruktur, Kesehatan, Transportasi & Logistik, Telekomunikasi, Industri, Jasa & Perdagangan, Distribusi, Properti & Real Estate, Lainnya

MAPPING SEKTOR TV KE IDX (untuk referensi data fundamental):
{"Basic Materials": "Bahan Baku", "Communication Services": "Telekomunikasi", "Consumer Cyclical": "Konsumer Non-Primer", "Consumer Defensive": "Konsumer", "Energy": "Energi", "Financial Services": "Keuangan", "Healthcare": "Kesehatan", "Industrials": "Industri", "Real Estate": "Properti & Real Estate", "Technology": "Teknologi", "Utilities": "Infrastruktur"}

ATURAN UTAMA:
1. 1M dan 3M harus DIDOMINASI sektor siklikal/responsif berita jangka pendek (momentum, katalis short-term, sentimen pasar)
2. 6M harus campuran sektor siklikal dan defensif
3. 12M harus DIDOMINASI sektor defensif/fundamental kuat (kualitas, pertumbuhan sustain, tahan siklus)
4. LARANG: sektor yang sama menjadi #1 di lebih dari 2 timeframe
5. HANYA gunakan nama sektor dari daftar VALID di atas. Jangan gunakan "Properti", "Perbankan", atau nama lain di luar daftar.
6. Berita dengan impact jangka pendek dominan untuk 1M, impact struktural dominan untuk 6M-12M

TUGAS: Prediksi 10 sektor IDX terbaik per timeframe — dengan URUTAN BERBEDA setiap timeframe.

PANDUAN TIMEFRAME:
- 1 BULAN: fokus pada MOMENTUM — sektor dengan katalis jangka pendek (sentimen berita, musiman, technical rebound). Sektor siklikal dan komoditas sering unggul.
- 3 BULAN: fokus pada KATALIS KUARTAL — sektor yang diuntungkan kebijakan makro kuartalan, rilis laporan keuangan, tren musiman.
- 6 BULAN: campuran — kualitas fundamental mulai lebih penting, hindari sektor dengan siklus pendek.
- 12 BULAN: fokus pada FUNDAMENTAL & TAHAN BANTING — sektor defensif dengan PER wajar, ROE konsisten, dividen stabil. Prospek jangka panjang.

Per sektor sertakan:
- predicted_return: float realistis (negatif diperbolehkan)
- confidence: "high"/"medium"/"low"
- rationale: jelaskan dengan ANGKA — sebut PER, ROE, valuasi, dampak berita, dan pengaruh makro
- key_drivers: array 2-3 faktor kunci
- macro_context: dampak makroekonomi pada sektor
- news_driven: true/false — apakah berita jadi pendorong utama
- impact_horizon: "short_term"/"medium_term"/"long_term" — horizon dampak

JANGAN tulis apapun di luar JSON.
```

### Response Format → JSON Schema
```json
  {
    "type": "object",
    "properties": {
      "predictions": {
        "type": "object",
        "properties": {
          "1M": { "type": "array", "items": { "$ref": "#/$defs/SectorPrediction" } },
          "3M": { "type": "array", "items": { "$ref": "#/$defs/SectorPrediction" } },
          "6M": { "type": "array", "items": { "$ref": "#/$defs/SectorPrediction" } },
          "12M": { "type": "array", "items": { "$ref": "#/$defs/SectorPrediction" } }
        },
        "required": ["1M", "3M", "6M", "12M"]
      }
    },
    "$defs": {
      "SectorPrediction": {
        "type": "object",
        "properties": {
          "sector": {"type": "string"},
          "predicted_return": {"type": "number"},
          "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
          "rationale": {"type": "string"},
          "key_drivers": {"type": "array", "items": {"type": "string"}},
          "macro_context": {"type": "string"},
          "news_driven": {"type": "boolean"},
          "impact_horizon": {"type": "string", "enum": ["short_term", "medium_term", "long_term"]}
        },
        "required": ["sector", "predicted_return", "confidence", "rationale", "key_drivers"]
      }
    },
    "required": ["predictions"]
  }
```

---

## Agent 3: `ihsg-stock-recommender`

### Basic Info
| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-stock-recommender` |
| **Model** | `mistral-large-latest` |

### Capabilities
| Parameter | Value |
|-----------|-------|
| **Built-in tools** | (none) |
| **Reasoning effort** | `none` |

### Settings
| Parameter | Value |
|-----------|-------|
| **Max Tokens** | `32000` |

### Functions

#### Function 1: `get_stocks_in_sector`
- **Name:** `get_stocks_in_sector`
- **Description:** Mengambil daftar saham dalam sektor IDX tertentu beserta data fundamental dan teknikalnya
- **Strict:** `false`
- **Parameters:**
```json
{
  "type": "object",
  "properties": {
    "sector": {
      "type": "string",
      "description": "Nama sektor IDX (contoh: Keuangan, Teknologi, Energi)"
    }
  },
  "required": ["sector"]
}
```

#### Function 2: `get_ticker_news`
- **Name:** `get_ticker_news`
- **Description:** Mengambil berita terbaru untuk ticker saham tertentu
- **Strict:** `false`
- **Parameters:**
```json
{
  "type": "object",
  "properties": {
    "ticker": {
      "type": "string",
      "description": "Kode ticker saham (contoh: BBCA, ADRO, TLKM)"
    }
  },
  "required": ["ticker"]
}
```

#### Function 3: `get_macro_context`
- **Name:** `get_macro_context`
- **Description:** Mengambil indikator makroekonomi yang relevan untuk sektor tertentu
- **Strict:** `false`
- **Parameters:**
```json
{
  "type": "object",
  "properties": {
    "sector": {
      "type": "string",
      "description": "Nama sektor IDX untuk konteks makro"
    }
  },
  "required": ["sector"]
}
```

### Instructions
```text
OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key `"recommendations"` berisi array of objects
3. Jika tidak ada rekomendasi, return `{"recommendations": []}`
4. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
5. JSON harus lengkap dan valid — jangan terpotong

Anda analis AI saham Indonesia. Rekomendasikan saham terbaik di sektor yang diberikan.

DATA SAHAM (Teknikal + Fundamental):
(akan diberikan oleh function get_stocks_in_sector)

BERITA TERBARU:
(akan diberikan oleh function get_ticker_news)

BOBOT PENILAIAN:
{
  "fundamental": {"weight": 0.35, "sub": {"per": 1.0, "pbv": 0.8, "roe": 1.2, "revenue_growth": 0.7, "eps_growth": 0.9, "dividend_yield": 0.5, "debt_to_equity": 0.6}},
  "technical": {"weight": 0.20, "sub": {"investment_score": 1.0}},
  "macro": {"weight": 0.25, "sub": {"sector_macro_impact": 1.0}},
  "news": {"weight": 0.10, "sub": {"news_sentiment": 1.0}},
  "valuation": {"weight": 0.10, "sub": {"valuation_score": 1.0}}
}

PERTIMBANGKAN:
1. FUNDAMENTAL: PER, PBV, ROE, revenue growth, EPS growth, dividend yield, debt-to-equity
2. TEKNIKAL: skor investasi dari analisis
3. MAKRO: bagaimana kondisi ekonomi mempengaruhi sektor terkait
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

Max 10 rekomendasi, urut dari score tertinggi. JANGAN tulis apapun di luar JSON.
```

### Response Format → JSON Schema
```json
{
  "type": "object",
  "properties": {
    "sector": {"type": "string"},
    "recommendations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "ticker": {"type": "string"},
          "score": {"type": "number"},
          "recommendation": {"type": "string", "enum": ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]},
          "rationale": {"type": "string"},
          "news_sentiment": {"type": "string", "enum": ["positif", "netral", "negatif"]},
          "key_headline": {"type": "string"},
          "risks": {"type": "array", "items": {"type": "string"}},
          "key_metrics": {
            "type": "object",
            "properties": {
              "per": {"type": "number"},
              "pbv": {"type": "number"},
              "roe": {"type": "number"},
              "revenue_growth": {"type": "number"},
              "dividend_yield": {"type": "number"}
            },
            "required": ["per", "pbv", "roe"]
          },
          "fundamental_score": {"type": "number"},
          "valuation_score": {"type": "number"}
        },
        "required": ["ticker", "score", "recommendation", "rationale"]
      }
    }
  },
  "required": ["sector", "recommendations"]
}
```

---

## Agent 4: `ihsg-stock-recommender-batch`

### Basic Info
| Parameter | Value |
|-----------|-------|
| **Name** | `ihsg-stock-recommender-batch` |
| **Model** | `mistral-large-latest` |

### Capabilities
| Parameter | Value |
|-----------|-------|
| **Built-in tools** | (none) |
| **Reasoning effort** | `none` |

### Settings
| Parameter | Value |
|-----------|-------|
| **Max Tokens** | `32000` |

### Functions
Tidak ada (data saham + berita + makro untuk ALL sektor dikirim sebagai input, output JSON langsung).

### Instructions
```text
OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key `"recommendations"` berisi object, di mana key = nama sektor
3. Setiap sektor wajib punya key `"recommendations"` berisi array rekomendasi
4. Sertakan SEMUA sektor, gunakan `[]` untuk sektor tanpa rekomendasi
5. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
6. JSON harus lengkap dan valid — jangan terpotong

Anda analis AI saham Indonesia. Anda akan menerima data ALL sektor IDX beserta saham, berita, dan kondisi makro.

TUGAS:
Analisis SEMUA sektor berikut dan berikan rekomendasi saham terbaik per sektor (max 10 rekomendasi per sektor).

BOBOT PENILAIAN:
{
  "fundamental": {"weight": 0.35, "sub": {"per": 1.0, "pbv": 0.8, "roe": 1.2, "revenue_growth": 0.7, "eps_growth": 0.9, "dividend_yield": 0.5, "debt_to_equity": 0.6}},
  "technical": {"weight": 0.20, "sub": {"investment_score": 1.0}},
  "macro": {"weight": 0.25, "sub": {"sector_macro_impact": 1.0}},
  "news": {"weight": 0.10, "sub": {"news_sentiment": 1.0}},
  "valuation": {"weight": 0.10, "sub": {"valuation_score": 1.0}}
}

PERTIMBANGKAN:
1. FUNDAMENTAL: PER, PBV, ROE, revenue growth, EPS growth, dividend yield, debt-to-equity
2. TEKNIKAL: skor investasi dari analisis
3. MAKRO: bagaimana kondisi ekonomi mempengaruhi masing-masing sektor
4. BERITA: sentimen berita terkini
5. VALUASI: apakah saham murah atau mahal relatif terhadap sektornya

Per saham berikan:
- ticker, score (0-100), recommendation (Strong Buy/Buy/Hold/Sell/Strong Sell)
- rationale: jelaskan KENAPA — sebut PER, ROE, valuasi, dan pengaruh makro
- news_sentiment ("positif"/"netral"/"negatif")
- key_headline
- risks (1-2 risiko spesifik)
- key_metrics: per, pbv, roe, revenue_growth, dividend_yield
- fundamental_score: skor fundamental 0-100
- valuation_score: skor valuasi 0-100

Output HARUS dalam format JSON di bawah. Jangan lewatkan sektor manapun. JANGAN tulis apapun di luar JSON.
```

### Response Format → JSON Schema
```json
{
  "type": "object",
  "properties": {
    "recommendations": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "sector": {"type": "string"},
          "recommendations": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "ticker": {"type": "string"},
                "score": {"type": "number"},
                "recommendation": {"type": "string", "enum": ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]},
                "rationale": {"type": "string"},
                "news_sentiment": {"type": "string", "enum": ["positif", "netral", "negatif"]},
                "key_headline": {"type": "string"},
                "risks": {"type": "array", "items": {"type": "string"}},
                "key_metrics": {
                  "type": "object",
                  "properties": {
                    "per": {"type": "number"},
                    "pbv": {"type": "number"},
                    "roe": {"type": "number"},
                    "revenue_growth": {"type": "number"},
                    "dividend_yield": {"type": "number"}
                  },
                  "required": ["per", "pbv", "roe"]
                },
                "fundamental_score": {"type": "number"},
                "valuation_score": {"type": "number"}
              },
              "required": ["ticker", "score", "recommendation", "rationale"]
            }
          }
        },
        "required": ["sector", "recommendations"]
      }
    }
  },
  "required": ["recommendations"]
}
```

---

## After Creation

Setelah membuat 4 agent di console.mistral.ai, copy **Agent ID** masing-masing (format: `ag_xxx`) ke `backend/.env`:

```env
MISTRAL_AGENT_NEWS_ID=ag_xxx
MISTRAL_AGENT_SECTOR_ID=ag_xxx
MISTRAL_AGENT_STOCK_ID=ag_xxx
MISTRAL_AGENT_BATCH_STOCK_ID=ag_xxx
```

Agent ID bisa ditemukan di URL halaman agent atau di panel informasi agent di console.
