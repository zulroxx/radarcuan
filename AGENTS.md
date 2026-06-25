# Perbaikan Agent Mistral Console

Dokumen ini berisi perubahan yang perlu diterapkan di [console.mistral.ai](https://console.mistral.ai/) untuk agent `ihsg-news-analyst`, `ihsg-stock-recommender`, dan `ihsg-stock-recommender-batch`.

---

## 1. `ihsg-news-analyst` (Agent 1)

### Masalah
- Sektor yang Diuntungkan, Sektor Perlu Diwaspadai, dan Indikator Makroekonomi Kunci sering kosong/empty
- Kadang hanya mengembalikan ringkasan teks tanpa data sektor dan indikator

### Perbaikan di bagian **Instructions**
Tambah baris berikut SETELAH baris pertama (sebelum "Anda analis AI..."):

```
OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key: ringkasan_1hari, ringkasan_terbaru, sektor_diuntungkan, sektor_digdaya_waspada, indikator_kunci, rekomendasi_umum
3. sektor_diuntungkan WAJIB diisi minimal 1 item — jangan pernah kosong
4. sektor_digdaya_waspada WAJIB diisi minimal 1 item — jangan pernah kosong
5. indikator_kunci WAJIB diisi minimal 3 item — jangan pernah kosong
6. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
7. JSON harus lengkap dan valid — jangan terpotong
```

### Perbaikan di **Settings**
| Parameter | Value |
|-----------|-------|
| **Max Tokens** | `32000` *(naik dari default 4096)* |

### Response Format → JSON Schema
Tidak perlu diubah (schema sudah benar di `docs/mistral_agent_creation_guide.md`).

---

## 3. `ihsg-stock-recommender` (Agent 3)

### Masalah
Kadang mengembalikan **JSON array (`[...]`)** langsung sebagai response, bukan **object (`{"recommendations": [...]}`)**.

### Perbaikan di bagian **Instructions**
Tambah baris berikut setelah baris pertama:

```
OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key `"recommendations"` berisi array of objects
3. Jika tidak ada rekomendasi, return `{"recommendations": []}`
4. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
5. JSON harus lengkap dan valid — jangan terpotong
```

### Perbaikan di **Response Format → JSON Schema**
Tidak perlu diubah (schema sudah benar).

---

## 2. Verifikasi Agent 1 (`ihsg-news-analyst`)

Setelah update, restart backend dan pantau log untuk:
- `GitHub/Llama gagal` — jika muncul, artinya primary LLM (GitHub Models / Llama 3.3 70B) gagal dan fallback ke Mistral
- `Mistral agent gagal` — jika kedua LLM gagal, backend akan gunakan data cadangan otomatis
- `News: stored with AI analysis` — pastikan sukses menyimpan analysis ke cache
- `sektor_diuntungkan`, `sektor_digdaya_waspada`, `indikator_kunci` — pastikan tidak kosong (min 1/3 item)

Cek juga di website: setelah scheduler jalan, refresh halaman Prediksi dan periksa:
- Sektor yang Diuntungkan: harus muncul minimal 1 sektor
- Sektor Perlu Diwaspadai: harus muncul minimal 1 sektor
- Indikator Makroekonomi Kunci: harus muncul minimal 3 indikator

---

## 4. `ihsg-stock-recommender-batch` (Agent 4)

### Masalah
Response terpotong karena melebihi `max_tokens`.

### Perbaikan di **Settings**
| Parameter | Value |
|-----------|-------|
| **Max Tokens** | `32000` *(naik dari 4096)* |

### Perbaikan di bagian **Instructions**
Tambah baris berikut:

```
OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key `"recommendations"` berisi object, di mana key = nama sektor
3. Setiap sektor wajib punya key `"recommendations"` berisi array rekomendasi
4. Sertakan SEMUA sektor, gunakan `[]` untuk sektor tanpa rekomendasi
5. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
6. JSON harus lengkap dan valid — jangan terpotong
```

---

## 3. Verifikasi (Stock Recommender)

Setelah update, restart backend dan pantau log untuk:
- `Cerebras batch success:` — pastikan Cerebras merespon dengan JSON valid
- `Cerebras returned None (rate limited)` — jika muncul, artinya kena rate limit dan fallback ke Mistral
- `Batch Mistral response:` — pastikan `len` tidak mencapai batas `max_tokens`
- `LLM returned non-dict` — pastikan tidak muncul lagi
- `Cerebras API error (non-rate-limit)` — error selain 429, perlu investigasi

Cek juga apakah ada **agent tools/functions** yang mungkin menyebabkan response menyimpang dari format yang diharapkan.

### Log Pattern untuk Hybrid Fallback (Batch)

| Kondisi | Log yang diharapkan |
|---------|-------------------|
| Cerebras sukses | `Cerebras batch success: content_len=...` → method `batch_cerebras` |
| Cerebras 429 → Mistral ok | `Cerebras rate limited after N retries` → `Batch Mistral response: ...` |
| Cerebras 429 → Mistral 429 | Log kedua gagal → `All batch LLMs failed/empty, fallback per-sector` |
| Cerebras error lain | `Cerebras batch failed: ...` → fallback ke Mistral |
| CEREBRAS_API_KEY kosong | `Cerebras not configured, using Mistral...` → pakai Mistral langsung |

---

## Referensi

Panduan lengkap pembuatan agent: `docs/mistral_agent_creation_guide.md`
