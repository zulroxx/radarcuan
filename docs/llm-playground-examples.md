# Contoh Prompt untuk Playground Mistral AI

Dokumen ini berisi prompt yang sebenarnya dikirim ke Mistral AI oleh aplikasi IHSG Smart Screening. Cocok untuk dicoba langsung di [Mistral Playground](https://console.mistral.ai/chat/) atau via API.

## Pengaturan Umum

| Parameter | Value |
|-----------|-------|
| Model | `mistral-medium-latest` |
| Temperature | `0.3` |
| Response Format | `json_object` |
| Max Tokens | `16000` (sector predictions & stock recommendations) / `8000` (news) |

## Cara Penggunaan

Kirim sebagai satu `{"role": "user", "content": "..."}`. Jika playground mendukung system prompt, bisa ditambahkan: `"Anda adalah AI asisten analis pasar saham Indonesia yang ahli."`

---

## 1. Prediksi Sektor (Sector Predictions)

### System Prompt (opsional)

```
Anda adalah AI asisten analis pasar saham Indonesia yang ahli dalam menganalisis sektor-sektor IDX berdasarkan data fundamental, makroekonomi, dan berita.
```

### User Prompt

```
Anda analis AI pasar saham Indonesia senior. Anda HARUS memberi prediksi BERBEDA untuk setiap timeframe — jangan sampai sektor yang sama memuncaki semua timeframe.

NAMA SEKTOR YANG VALID (hanya gunakan ini):
Keuangan, Teknologi, Energi, Bahan Baku, Konsumer, Konsumer Non-Primer, Infrastruktur, Kesehatan, Transportasi & Logistik, Telekomunikasi, Industri, Jasa & Perdagangan, Distribusi, Lainnya

MAPPING SEKTOR TV KE IDX (untuk referensi data fundamental):
{"Energi": "energi", "Basic Materials": "bahan_baku", "Industrials": "industri", "Consumer Cyclicals": "konsumer_non_primer", "Consumer Non-Cyclicals": "konsumer", "Financials": "keuangan", "Infrastructure": "infrastruktur", "Healthcare": "kesehatan", "Technology": "teknologi", "Transportation & Logistics": "transportasi_logistik", "Property & Real Estate": "lainnya", "Telecommunications": "telekomunikasi", "Utilities": "infrastruktur", "Energy": "energi", "Properties": "lainnya"}

ATURAN UTAMA:
1. 1M dan 3M harus DIDOMINASI sektor siklikal/responsif berita jangka pendek (momentum, katalis short-term, sentimen pasar)
2. 6M harus campuran sektor siklikal dan defensif
3. 12M harus DIDOMINASI sektor defensif/fundamental kuat (kualitas, pertumbuhan sustain, tahan siklus)
4. LARANG: sektor yang sama menjadi #1 di lebih dari 2 timeframe
5. HANYA gunakan nama sektor dari daftar VALID di atas. Jangan gunakan "Properti", "Perbankan", atau nama lain di luar daftar.
6. Berita dengan impact jangka pendek dominan untuk 1M, impact struktural dominan untuk 6M-12M

DATA FUNDAMENTAL SEKTOR (rata-rata):
[
  {"sector": "Energi", "avg_per": 8.5, "avg_pbv": 1.2, "avg_roe": 15.3, "avg_revenue_growth": 8.2, "avg_dividend_yield": 4.5},
  {"sector": "Bahan Baku", "avg_per": 12.3, "avg_pbv": 1.8, "avg_roe": 14.1, "avg_revenue_growth": 6.5, "avg_dividend_yield": 3.2},
  {"sector": "Keuangan", "avg_per": 14.2, "avg_pbv": 2.5, "avg_roe": 18.6, "avg_revenue_growth": 10.1, "avg_dividend_yield": 4.0},
  {"sector": "Teknologi", "avg_per": 25.4, "avg_pbv": 4.2, "avg_roe": 12.8, "avg_revenue_growth": 25.3, "avg_dividend_yield": 1.0},
  {"sector": "Konsumer", "avg_per": 22.1, "avg_pbv": 3.8, "avg_roe": 16.2, "avg_revenue_growth": 7.8, "avg_dividend_yield": 2.8}
]

KONDISI MAKROEKONOMI:
- BI Rate: 5.75% (turun 25 bps)
- Inflasi: 2.8% (terkendali)
- IHSG: 7,200 (stabil)
- USD/IDR: 15,600 (melemah 0.5%)
- Pertumbuhan PDB: 5.1%
- Harga Minyak: $78/bbl

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

RESPON JSON:
{"predictions":{"1M":[{"sector":"Energi","predicted_return":8.5,"confidence":"high","rationale":"Harga batubara naik 5% didorong permintaan China dan pelemahan rupiah menguntungkan eksportir. Rata-rata PER sektor 8x menarik.","key_drivers":["Harga batubara naik","Rupiah melemah","Permintaan China pulih"],"macro_context":"Kenaikan harga komoditas dan pelemahan rupiah mendorong sektor energi","news_driven":true,"impact_horizon":"short_term"}],"3M":[{"sector":"Keuangan","predicted_return":7.2,"confidence":"high","rationale":"BI rate turun 25bp mendorong ekspansi kredit. ROE rata-rata 18% dengan PER 12x masih menarik. Pertumbuhan kredit diproyeksi 10-12% dalam 6 bulan.","key_drivers":["Penurunan BI rate","Kredit tumbuh","PER menarik"],"macro_context":"Relaksasi moneter mendukung margin bunga","news_driven":false,"impact_horizon":"medium_term"}],"6M":[{"sector":"Konsumer","predicted_return":6.5,"confidence":"medium","rationale":"Inflasi terkendali mendorong daya beli. ROE 16% stabil. Valuasi PER 22x agak mahal tapi didukung pertumbuhan konsisten.","key_drivers":["Daya beli naik","Inflasi rendah","Konsumsi kuat"],"macro_context":"Inflasi rendah dan BI rate turun mendukung sektor konsumsi","news_driven":false,"impact_horizon":"medium_term"}],"12M":[{"sector":"Kesehatan","predicted_return":10.2,"confidence":"high","rationale":"Sektor defensif dengan prospek jangka panjang kuat. Program JKN dan penuaan populasi mendorong permintaan layanan kesehatan secara struktural.","key_drivers":["Penuaan populasi","Program JKN","Permintaan struktural"],"macro_context":"Faktor demografis dan kebijakan kesehatan nasional mendukung pertumbuhan jangka panjang","news_driven":false,"impact_horizon":"long_term"}]}}
JANGAN tulis apapun di luar JSON.
```

---

## 2. Rekomendasi Saham per Sektor (Stock Recommendations)

### System Prompt (opsional)

```
Anda adalah AI asisten analis saham Indonesia yang ahli dalam merekomendasikan saham berdasarkan analisis fundamental, teknikal, makroekonomi, dan sentimen berita.
```

### User Prompt

```
Anda analis AI saham Indonesia. Rekomendasikan saham terbaik di sektor Energi.

DATA MAKRO:
BI Rate: 5.75% | Inflasi: 2.8% | IHSG: 7,200

DATA SAHAM (Teknikal + Fundamental):
[{"ticker":"ADRO","sector":"Energi","price":2850,"per":6.2,"pbv":0.9,"roe":14.5,"revenue_growth":8.1,"dividend_yield":6.5,"debt_to_equity":0.45,"investment_score":72,"subsector":"Batubara","market_cap":91200},{"ticker":"PTBA","sector":"Energi","price":3850,"per":7.1,"pbv":1.3,"roe":18.2,"revenue_growth":5.4,"dividend_yield":8.2,"debt_to_equity":0.32,"investment_score":78,"subsector":"Batubara","market_cap":44400}]

BERITA TERBARU:
[{"title":"Harga batubara menguat seiring permintaan China","date":"2026-06-18","sentiment":"positif","source":"Kontan"},{"title":"ADRO targetkan produksi 70 juta ton di 2026","date":"2026-06-17","sentiment":"positif","source":"Bisnis"}]

BOBOT PENILAIAN:
- Fundamental: 40%
- Teknikal: 20%
- Makroekonomi: 20%
- Sentimen Berita: 10%
- Valuasi: 10%

PERTIMBANGKAN:
1. FUNDAMENTAL: PER, PBV, ROE, revenue growth, EPS growth, dividend yield, debt-to-equity
2. TEKNIKAL: skor investasi dari analisis
3. MAKRO: bagaimana kondisi ekonomi mempengaruhi sektor Energi
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
{"sector":"Energi","recommendations":[{"ticker":"ADRO","score":85,"recommendation":"Strong Buy","rationale":"PER 6.2x murah dengan ROE 14.5% dan dividen yield 6.5% menarik. Harga batubara naik didorong permintaan China.","news_sentiment":"positif","key_headline":"Harga batubara menguat seiring permintaan China","risks":["Volatilitas harga komoditas","Regulasi lingkungan"],"key_metrics":{"per":6.2,"pbv":0.9,"roe":14.5,"revenue_growth":8.1,"dividend_yield":6.5},"fundamental_score":80,"valuation_score":85}]}
Max 10 rekomendasi, urut dari score tertinggi. JANGAN tulis apapun di luar JSON.
```

---

## 3. Analisis Berita (News Analysis)

### User Prompt

```
Anda analis AI pasar saham Indonesia. Analisis berita ekonomi global terbaru berikut.

BERITA TERBARU:
[{"title":"IHSG Ditutup Menguat ke Level 7.200","date":"2026-06-18","source":"Kontan","summary":"IHSG ditutup menguat 0.8% ke level 7.200 didorong aksi beli investor asing di sektor perbankan dan energi."},{"title":"BI Kembali Turunkan Suku Bunga 25 bps","date":"2026-06-17","source":"Bisnis","summary":"Bank Indonesia menurunkan suku bunga acuan sebesar 25 bps menjadi 5.75% untuk mendorong pertumbuhan ekonomi."},{"title":"Harga Minyak Mentah Menguat ke $78 per Barel","date":"2026-06-18","source":"Reuters","summary":"Harga minyak mentah dunia menguat didorong oleh pemangkasan produksi OPEC+ dan permintaan musim panas."}]

Buat analisis dalam Bahasa Indonesia dengan format JSON berikut:
{
  "ringkasan_1hari": "Ringkasan berita 1 hari terakhir dalam 4-5 kalimat, fokus pada dampak pasar",
  "ringkasan_terbaru": "Ringkasan berita paling baru/breaking dalam 3-4 kalimat",
  "sektor_diuntungkan": [
    {
      "sektor": "Nama sektor IDX (contoh: Keuangan, Teknologi, Energi, Bahan Baku, Konsumer, Konsumer Non-Primer, Infrastruktur, Kesehatan, Transportasi & Logistik, Telekomunikasi, Industri, Jasa & Perdagangan, Distribusi, Lainnya)",
      "alasan": "Penjelasan spesifik mengapa sektor ini diuntungkan berdasarkan berita terkini",
      "sentimen": "positif"/"sangat positif",
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

Gunakan data berita yang tersedia. Jika berita terbatas, tetap berikan analisis berdasarkan kondisi makroekonomi Indonesia.
JANGAN tulis apapun di luar JSON.
```

---

## Tips Playground

1. **Google Colab / API**: Gunakan Mistral API via Python:
```python
from mistralai.client import Mistral
client = Mistral(api_key="YOUR_API_KEY")
response = client.chat.complete(
    model="mistral-medium-latest",
    messages=[{"role": "user", "content": "prompt_anda_disini"}],
    temperature=0.3,
    max_tokens=16000,
    response_format={"type": "json_object"},
)
print(response.choices[0].message.content)
```

2. **Mistral Console**: Buka https://console.mistral.ai/chat/ → paste user prompt di chat → set temperature 0.3 → minta output JSON.

3. **Data real**: Prompt di atas menggunakan data contoh. Untuk data real, jalankan endpoint API berikut:
   - `GET /api/tradingview/summary?refresh=false&limit=500` → data fundamental saham
   - `GET /api/macro/indicators` → data makroekonomi
   - `GET /api/news/flow` → data berita
