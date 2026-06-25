"""Utility constants for LLM prompts used across agents.

All agents that need to enforce a strict JSON output should import the
corresponding constant from this module instead of hard‑coding the rules.
"""

# Rules for the news‑analysis agent (ihsg‑news‑analyst)
OUTPUT_RULES_NEWS = """OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key: ringkasan_1hari, ringkasan_terbaru, sektor_diuntungkan, sektor_digdaya_waspada, indikator_kunci, rekomendasi_umum
3. sektor_diuntungkan WAJIB diisi minimal 1 item — jangan pernah kosong
4. sektor_digdaya_waspada WAJIB diisi minimal 1 item — jangan pernah kosong
5. indikator_kunci WAJIB diisi minimal 3 item — jangan pernah kosong
6. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
7. JSON harus lengkap dan valid — jangan terpotong"""

# Rules for the stock‑recommender single‑response agent (ihsg‑stock‑recommender)
OUTPUT_RULES_RECOMMENDER_SINGLE = """OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key \"recommendations\" berisi array of objects
3. Jika tidak ada rekomendasi, return `{\"recommendations\": []}`
4. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
5. JSON harus lengkap dan valid — jangan terpotong"""

# Rules for the batch stock‑recommender agent (ihsg‑stock‑recommender‑batch)
OUTPUT_RULES_RECOMMENDER_BATCH = """OUTPUT FORMAT RULES (WAJIB):
1. Response HARUS berupa JSON object `{...}`, BUKAN array `[...]`
2. Wajib punya key \"recommendations\" berisi object, di mana key = nama sektor
3. Setiap sektor wajib punya key \"recommendations\" berisi array rekomendasi
4. Sertakan SEMUA sektor, gunakan `[]` untuk sektor tanpa rekomendasi
5. JANGAN sertakan markdown, code fences (```), atau teks apapun di luar JSON
6. JSON harus lengkap dan valid — jangan terpotong"""
